# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""One claimed Q&A Run on the Worker: clone, sandbox, version check, turn, result.

Plane is the only writer of Run state; the Worker sends evidence. Every call
carries the lease generation, and a renewal thread keeps the lease while the Run
works. When Plane answers 409 (the lease moved on), the Worker stops the turn and
posts nothing more.

Steps:
1. Clone the bound repository on the host into ``<key>/clones/<run_id>/clone``
   (``git_transport``; a GitLab token comes from Plane only through the clone) and
   report the clone path or the ``git_*`` failure code.
2. Make sure the Q&A sandbox of the repository key exists and runs (``sandbox``).
3. Read ``claude --version`` inside it and check the per-version suite
   (``conformance.ensure_verified``); an unverified version runs the suite first in
   the probe sandbox, and a failed suite fails the Run with
   ``harness_version_unverified``.
4. Run one Claude turn with the clone as working directory, the prompt built from
   the context snapshot, and an MCP config with the Plane server (per-turn handle)
   and the listed servers. Events go to Plane as they come.
5. Post the result: the answer, or a failure code with a short reason.
"""

import json
import logging
import os
import shutil
import threading
import time

from plane_agent_worker import git_transport
from plane_agent_worker.conformance import SUITE_CHECKS, ensure_verified, suite_cache
from plane_agent_worker.drivers.base import Deadline, bounded
from plane_agent_worker.events import EventMapper, status_event
from plane_agent_worker.git_transport import GitTransportError
from plane_agent_worker.mcp_server import imported_allow_rules, turn_mcp_config
from plane_agent_worker.plane_client import Conflict, PlaneClientError
from plane_agent_worker.prompt import build_prompt
from plane_agent_worker.sandbox import Mount, SandboxError, SandboxSpec, user_config_mounts
from plane_agent_worker.workspace import run_layout

RENEW_SECONDS = 60
# A Q&A turn ends at the latest after this time.
TURN_LIMIT_SECONDS = 30 * 60
VERSION_SECONDS = 60
SUITE_BUDGET_SECONDS = 100
EVENT_BATCH = 100
MAX_MESSAGE_CHARS = 1000
CREDENTIAL_MODES = frozenset({"host", "plane_token"})
# The 409 codes of a lost lease. Any other 409 is a refusal of the request itself.
LEASE_CODES = frozenset({"lease_superseded", "run_finished"})
# Waits before each new try of a result post; Plane applies a result only once, so a retry is safe.
RESULT_RETRY_SECONDS = (2, 5, 10)

logger = logging.getLogger("plane_agent_worker.runs")


class RunFailure(Exception):
    def __init__(self, code, message, **extra):
        super().__init__(code)
        self.code = code
        self.message = bounded(message, MAX_MESSAGE_CHARS)
        self.extra = extra


class LeaseLost(Exception):
    """Plane gave the Run to a newer lease; this Worker stops and posts nothing more."""


class EventSink:
    """Sends events in order. A failed send keeps them for the next send; a 409 means the lease is lost."""

    def __init__(self, client, run_id, generation, turn_index):
        self.client = client
        self.run_id = run_id
        self.generation = generation
        self.turn_index = turn_index
        self.pending = []
        self.lock = threading.Lock()

    def add(self, events):
        with self.lock:
            self.pending.extend(events)
            self._flush()

    def flush(self):
        with self.lock:
            self._flush()

    def _flush(self):
        while self.pending:
            batch = self.pending[:EVENT_BATCH]
            try:
                self.client.post_events(self.run_id, self.generation, self.turn_index, batch)
            except Conflict as error:
                raise LeaseLost(error.code) from None
            except PlaneClientError as error:
                logger.warning("Run %s: events not sent yet (status %s, %s)", self.run_id, error.status, error.code)
                return
            del self.pending[: len(batch)]


class RunExecutor:
    def __init__(
        self,
        *,
        client,
        drivers,
        sandboxes,
        mcp,
        run_root,
        token_file,
        plane_checkout,
        imported_servers=None,
        git_allowed_hosts=frozenset(),
        git_allowed_ips=(),
        clone=None,
        first_output_seconds=None,
    ):
        self.client = client
        self.drivers = dict(drivers)
        self.sandboxes = sandboxes
        self.mcp = mcp
        self.run_root = run_root
        self.token_file = token_file
        self.plane_checkout = plane_checkout
        self.imported_servers = dict(imported_servers or {})
        self.git_allowed_hosts = git_allowed_hosts
        self.git_allowed_ips = git_allowed_ips
        self.clone = clone or git_transport.clone_repository
        self.first_output_seconds = first_output_seconds
        self.renew_seconds = RENEW_SECONDS

    # Entry --------------------------------------------------------------------

    def execute(self, run):
        """Work one claimed Run to its result. Never raises."""
        try:
            layout = run_layout(self.run_root, run)
            generation = run["lease_generation"]
            driver = self.drivers[run["harness"]]
            repository = run["repository"]
            if not isinstance(generation, int) or repository.get("credential_mode") not in CREDENTIAL_MODES:
                raise ValueError("unexpected claim")
        except (KeyError, TypeError, ValueError, AttributeError):
            logger.warning("Ignoring a Run claim this Worker cannot work")
            return
        run_id = run["id"]
        cancel = threading.Event()
        lease = {"lost": False}
        stop_renewal = threading.Event()
        renewer = threading.Thread(
            target=self._renew, args=(run_id, generation, stop_renewal, cancel, lease), daemon=True
        )
        renewer.start()
        sink = EventSink(self.client, run_id, generation, (run.get("turn") or {}).get("index", 0))
        try:
            self._work(run, layout, driver, sink, cancel, lease)
        except LeaseLost:
            lease["lost"] = True
        except RunFailure as failure:
            self._post_failure(run_id, generation, sink, failure, lease)
        except Exception:  # a Worker defect must still give a failed Run, never a stuck one
            logger.exception("Run %s stopped with an internal error", run_id)
            failure = RunFailure(
                "worker_error", "The Worker stopped this Run after an internal error. See the Worker log."
            )
            self._post_failure(run_id, generation, sink, failure, lease)
        finally:
            stop_renewal.set()
            renewer.join(timeout=5)
            shutil.rmtree(layout.host_dir, ignore_errors=True)
            if lease["lost"]:
                logger.info("Run %s: the lease moved on; this Worker stopped it", run_id)

    def _renew(self, run_id, generation, stop, cancel, lease):
        while not stop.wait(self.renew_seconds):
            try:
                self.client.renew_run(run_id, generation)
            except Conflict:
                lease["lost"] = True
                cancel.set()
                return
            except PlaneClientError as error:
                logger.warning("Run %s: lease renewal failed (status %s, %s)", run_id, error.status, error.code)

    def _post_failure(self, run_id, generation, sink, failure, lease):
        if lease["lost"]:
            return
        try:
            sink.flush()
            result = {
                "status": "failed",
                "conclusion": "",
                "failure_code": failure.code,
                "failure_message": failure.message,
                **failure.extra,
            }
            self._post_result(run_id, generation, result)
        except LeaseLost:
            lease["lost"] = True
        except PlaneClientError as error:
            logger.warning("Run %s: the failed result was not sent (status %s, %s)", run_id, error.status, error.code)

    def _post_result(self, run_id, generation, result):
        """Post the result. Retry a failed post a bounded number of times; a 409 means the lease is lost."""
        for delay in (*RESULT_RETRY_SECONDS, None):
            try:
                return self.client.post_result(run_id, generation, result)
            except Conflict as error:
                raise LeaseLost(error.code) from None
            except PlaneClientError as error:
                if delay is None:
                    raise
                logger.warning("Run %s: result not sent (status %s, %s); retrying", run_id, error.status, error.code)
                time.sleep(delay)

    # Steps --------------------------------------------------------------------

    def _work(self, run, layout, driver, sink, cancel, lease):
        run_id, generation = run["id"], run["lease_generation"]
        turn_index = sink.turn_index
        repository = run["repository"]
        # The Run root is outside the Plane checkout (checked at Worker start), and so is every Run folder.
        layout.create()

        sink.add([status_event(turn_index, "cloning", f"Cloning {repository.get('full_name')}")])
        self._clone(run, layout)

        sink.add([status_event(turn_index, "sandbox_starting", "Starting the sandbox")])
        spec = SandboxSpec(
            name=self.sandboxes.qa_name(layout.key),
            primary=layout.scratch,
            mounts=(Mount(str(layout.clones)), *user_config_mounts(self.sandboxes.home)),
            allow=(f"localhost:{self.mcp.port}", *imported_allow_rules(self.imported_servers)),
        )
        try:
            self.sandboxes.ensure(spec)
        except SandboxError as error:
            raise RunFailure(error.code, f"The sandbox is not available: {error.detail}") from None

        deadline = Deadline(TURN_LIMIT_SECONDS, cancel)
        self._check_version(driver, spec.name, run_id, layout, turn_index, sink, deadline)

        try:
            context = self.client.run_context(run_id, generation)
        except Conflict as error:
            raise LeaseLost(error.code) from None
        payload = context.get("payload") if isinstance(context, dict) else None
        if not isinstance(payload, dict):
            raise RunFailure("worker_error", "Plane did not return the Run context.")

        handle = self.mcp.open_turn(run_id=run_id, turn_index=turn_index, lease_generation=generation, context=payload)
        try:
            mcp_config = layout.run_scratch / "mcp.json"
            descriptor = os.open(mcp_config, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle_file:
                json.dump(turn_mcp_config(self.mcp.port, handle, self.imported_servers), handle_file)
            mapper = EventMapper(turn_index)
            turn_kwargs = {}
            if self.first_output_seconds is not None:
                turn_kwargs["first_output_seconds"] = self.first_output_seconds
            outcome = driver.run_turn(
                key=f"run-{run_id}-{turn_index}",
                sandbox=spec.name,
                cwd=layout.clone,
                host_dir=layout.run_scratch,
                pidfile=layout.run_scratch / "agent.pid",
                prompt=build_prompt(payload),
                mcp_config=mcp_config,
                model=run.get("model") or "",
                deadline=deadline,
                on_message=lambda message: sink.add(mapper.map(message)),
                **turn_kwargs,
            )
        finally:
            self.mcp.close_turn(handle)
        if lease["lost"]:
            raise LeaseLost("lease_superseded")
        sink.flush()
        self._finish(run_id, generation, outcome)

    def _clone(self, run, layout):
        run_id, generation = run["id"], run["lease_generation"]
        repository = run["repository"]

        def fetch_token():
            try:
                return self.client.git_credential(run_id, generation)
            except Conflict as error:
                if error.code in LEASE_CODES:
                    raise LeaseLost(error.code) from None
                raise RunFailure(
                    error.code,
                    f"Plane did not give the GitLab credential ({error.code}). "
                    "Reconnect GitLab in the workspace settings, then mention the Agent again.",
                ) from None

        try:
            self.clone(
                clone_url=repository["clone_url"],
                host=repository["host"],
                credential_mode=repository["credential_mode"],
                destination=layout.clone,
                ca_bundle=repository.get("ca_bundle"),
                ca_dir=layout.host_dir,
                fetch_token=fetch_token,
                allowed_hosts=self.git_allowed_hosts,
                allowed_ips=self.git_allowed_ips,
                branch=repository.get("base_ref") or repository.get("default_branch") or None,
            )
        except GitTransportError as error:
            self._report_clone(run_id, generation, ok=False, error_code=error.code, error_detail=error.detail)
            raise RunFailure(
                error.code, f"The Worker cannot reach {repository.get('host')}: {error.detail or error.code}"
            ) from None
        self._report_clone(run_id, generation, ok=True, clone_path=str(layout.clone))

    def _report_clone(self, run_id, generation, **body):
        try:
            self.client.report_clone(run_id, generation, **body)
        except Conflict as error:
            raise LeaseLost(error.code) from None
        except PlaneClientError as error:
            logger.warning("Run %s: clone report failed (status %s, %s)", run_id, error.status, error.code)

    def _check_version(self, driver, sandbox, run_id, layout, turn_index, sink, deadline):
        version = driver.cli_version(f"run-{run_id}", sandbox, layout.clone, deadline.within(VERSION_SECONDS))
        if version is None:
            raise RunFailure("harness_not_found", "claude --version did not report a version in the sandbox.")
        if suite_cache(self.run_root).get(driver.harness, version, driver.suite_version) is None:
            sink.add([status_event(turn_index, "checking_version", f"Checking Claude Code {version}")])
        suite = ensure_verified(
            driver,
            version,
            deadline.within(SUITE_BUDGET_SECONDS),
            run_root=self.run_root,
            token_file=self.token_file,
            plane_checkout=self.plane_checkout,
        )
        if suite.record is None:
            failed = next((name for name in SUITE_CHECKS if not suite.checks[name].passed), "")
            detail = suite.checks[failed].detail if failed else suite.failure_hint
            raise RunFailure(
                "harness_version_unverified",
                f"Claude Code {version} did not pass the {failed or 'behavior'} check: {detail}",
                harness_version=version,
                failed_check=failed,
            )

    def _finish(self, run_id, generation, outcome):
        if outcome.succeeded:
            result = {"status": "completed", "conclusion": outcome.text, "session_ref": outcome.session_id or ""}
            self._post_result(run_id, generation, result)
            return
        if outcome.no_output:
            raise RunFailure(
                "harness_no_response",
                "Claude Code sent no answer in time. Check the gateway URL and token in ~/.claude/settings.json "
                "on the Worker machine.",
            )
        if outcome.timed_out:
            raise RunFailure("harness_timeout", "The turn did not finish in time.")
        if outcome.result is not None:
            text = outcome.text or "Claude Code reported an error."
            code = "harness_auth_failed" if "401" in text or "authentication" in text.lower() else "harness_error"
            raise RunFailure(code, text)
        if outcome.stderr_tail:
            logger.warning("Run %s: Claude stopped: %s", run_id, bounded(outcome.stderr_tail, 1000))
        raise RunFailure("harness_exited", "Claude Code stopped without an answer. See the Worker log.")
