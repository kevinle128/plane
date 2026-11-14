# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Connection probe runner and the behavior-suite cache.

A Connect runs the quick check of the driver (version, login, model list). The
behavior suite (progress, permission, interruption, follow-up, recovery) runs
once per CLI version: ``ensure_verified`` reuses a passing result from the cache
file ``<run_root>/state/conformance.json`` (mode 0600, written only by the
Worker) and otherwise runs the suite in its own probe folder. Only a passing
result is stored, so a failed suite runs again at the next Connect. One lock per
(Harness, CLI version) makes concurrent callers wait for one suite.

``run_probe`` creates the private directories of one probe under the Run root,
runs both parts within a time budget that ends before Plane's answer deadline,
removes the directories and returns a version 2 report: the checks, the models,
the capabilities and the suite record the behavior checks come from. The report
is evidence only;
Plane decides whether the Harness is connected.
"""

import json
import logging
import os
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from plane_agent_worker.drivers.base import (
    CAPABILITY_FLAGS,
    MAX_HINT_CHARS,
    WAIT_SLICE_SECONDS,
    CheckResult,
    Deadline,
    ProbeOutcome,
    ProbeWorkspace,
    bounded,
)

REPORT_VERSION = 2
# Plane reads a probe without a report after 120 s as failed; keep a margin for the report itself.
PROBE_BUDGET_SECONDS = 100
# The checks that the behavior suite proves. Authentication always comes from the current check.
SUITE_CHECKS = ("model_report", "follow_up", "progress", "interruption", "permission", "recovery")
SUITE_MODES = ("qa",)
CACHE_FILE_VERSION = 1

logger = logging.getLogger("plane_agent_worker.conformance")


def prepare_workspace(run_root, probe_key, token_file, plane_checkout):
    if not probe_key or "/" in probe_key or probe_key.startswith("."):
        raise ValueError("A probe key is a plain directory name.")
    own_dir = run_root / "probes" / probe_key
    if own_dir.exists():
        shutil.rmtree(own_dir)
    (run_root / "probes").mkdir(mode=0o700, exist_ok=True)
    own_dir.mkdir(mode=0o700)
    cwd = own_dir / "workspace"
    tmp = own_dir / "tmp"
    cwd.mkdir(mode=0o700)
    tmp.mkdir(mode=0o700)
    return ProbeWorkspace(
        run_root=run_root,
        own_dir=own_dir,
        cwd=cwd,
        tmp=tmp,
        token_file=token_file,
        plane_checkout=plane_checkout,
    )


def remove_stale_probes(run_root):
    """Remove the probe directories of a previous Worker. No probe continues after a Worker restart."""
    probes = run_root / "probes"
    if not probes.is_dir():
        return 0
    removed = 0
    for entry in probes.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry, ignore_errors=True)
        else:
            entry.unlink(missing_ok=True)
        removed += 1
    return removed


# Suite cache -------------------------------------------------------------------


def _valid_record(record, harness, cli_version, suite_version):
    if not isinstance(record, dict):
        return False
    checks = record.get("checks")
    capabilities = record.get("capabilities")
    return (
        record.get("harness") == harness
        and record.get("cli_version") == cli_version
        and record.get("suite_version") == suite_version
        and isinstance(record.get("verified_at"), str)
        and isinstance(checks, list)
        and {check.get("name") for check in checks if isinstance(check, dict) and check.get("passed") is True}
        >= set(SUITE_CHECKS)
        and isinstance(capabilities, dict)
        and set(capabilities) <= set(CAPABILITY_FLAGS)
        and all(isinstance(value, bool) for value in capabilities.values())
    )


class SuiteCache:
    """Passing suite results by (Harness, CLI version, suite version), in one private JSON file."""

    # Read-modify-write of the file is serialized for every cache in this process.
    _file_lock = threading.Lock()

    def __init__(self, path):
        self.path = path

    @staticmethod
    def key(harness, cli_version, suite_version):
        return f"{harness}/{cli_version}/{suite_version}"

    def _records(self):
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as error:
            logger.warning("Ignoring the unreadable suite cache %s (%s)", self.path, type(error).__name__)
            return {}
        records = document.get("records") if isinstance(document, dict) else None
        if not isinstance(records, dict):
            logger.warning("Ignoring the suite cache %s: unexpected content", self.path)
            return {}
        return records

    def get(self, harness, cli_version, suite_version):
        """The passing record, or ``None``. A record with an unexpected shape counts as absent."""
        with self._file_lock:
            record = self._records().get(self.key(harness, cli_version, suite_version))
        return record if _valid_record(record, harness, cli_version, suite_version) else None

    def put(self, record):
        key = self.key(record["harness"], record["cli_version"], record["suite_version"])
        with self._file_lock:
            records = {
                name: item
                for name, item in self._records().items()
                if isinstance(item, dict)
                and _valid_record(item, item.get("harness"), item.get("cli_version"), item.get("suite_version"))
            }
            records[key] = record
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            temporary = self.path.parent / f".{self.path.name}.{uuid.uuid4().hex}"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    json.dump({"version": CACHE_FILE_VERSION, "records": records}, handle, indent=2)
                os.replace(temporary, self.path)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise


def suite_cache(run_root):
    return SuiteCache(run_root / "state" / "conformance.json")


@dataclass
class SuiteResult:
    """The suite checks and capabilities for one CLI version. ``record`` is set only when they all passed."""

    checks: dict
    capabilities: dict = field(default_factory=lambda: dict.fromkeys(CAPABILITY_FLAGS, False))
    record: dict | None = None
    ran_now: bool = False
    failure_hint: str = ""

    @classmethod
    def from_record(cls, record, ran_now):
        checks = {name: CheckResult(name) for name in SUITE_CHECKS}
        for check in record["checks"]:
            if check.get("name") in checks:
                checks[check["name"]].set(check["passed"], check.get("detail", ""))
        capabilities = dict.fromkeys(CAPABILITY_FLAGS, False) | record["capabilities"]
        return cls(checks=checks, capabilities=capabilities, record=record, ran_now=ran_now)

    @classmethod
    def not_run(cls, detail, failure_hint=""):
        checks = {name: CheckResult(name) for name in SUITE_CHECKS}
        for check in checks.values():
            check.set(False, detail)
        return cls(checks=checks, failure_hint=failure_hint)


_suite_locks = {}
_suite_locks_guard = threading.Lock()


def _suite_lock(harness, cli_version):
    with _suite_locks_guard:
        return _suite_locks.setdefault((harness, cli_version), threading.Lock())


def _acquire(lock, deadline):
    """Wait for ``lock`` in short slices, so a cancelled or expired deadline stops the wait."""
    while True:
        remaining = deadline.remaining()
        if remaining <= 0:
            return False
        if lock.acquire(timeout=min(WAIT_SLICE_SECONDS, remaining)):
            return True


def _run_suite(driver, cli_version, deadline, run_root, token_file, plane_checkout):
    probe_key = f"suite-{driver.harness}-{cli_version}"
    own_dir = run_root / "probes" / probe_key
    try:
        workspace = prepare_workspace(run_root, probe_key, token_file, plane_checkout)
        return driver.run_suite(workspace, deadline)
    except Exception as error:  # a driver or disk defect must give a failed suite, never a crash
        logger.exception("Behavior suite of %s %s failed", driver.harness, cli_version)
        return ProbeOutcome(failure_hint=f"The suite stopped with an internal error ({type(error).__name__}).")
    finally:
        shutil.rmtree(own_dir, ignore_errors=True)


def ensure_verified(driver, cli_version, deadline, *, run_root, token_file, plane_checkout, mode="qa"):
    """The suite result for ``cli_version``: from the cache when it passed before, else from a new suite run.

    This is the single entry point for the conformance suite; a Connect and a Run both call it.
    """
    if mode not in SUITE_MODES:
        raise ValueError(f"Unknown suite mode: {mode}")
    cache = suite_cache(run_root)
    record = cache.get(driver.harness, cli_version, driver.suite_version)
    if record:
        return SuiteResult.from_record(record, ran_now=False)
    lock = _suite_lock(driver.harness, cli_version)
    if not _acquire(lock, deadline):
        return SuiteResult.not_run(
            "not run: the check of this version did not finish in time",
            "Another connection check of this Claude Code version is still running. Retry in a minute.",
        )
    try:
        # A caller that waited on the lock uses the result of the suite it waited for.
        record = cache.get(driver.harness, cli_version, driver.suite_version)
        if record:
            return SuiteResult.from_record(record, ran_now=False)
        outcome = _run_suite(driver, cli_version, deadline, run_root, token_file, plane_checkout)
        if outcome.harness_version and outcome.harness_version != cli_version:
            return SuiteResult.not_run(
                f"not proven: the CLI changed to version {bounded(outcome.harness_version, 64)} during the check",
                "The CLI version changed during the connection check. Retry.",
            )
        checks = {name: outcome.checks[name] for name in SUITE_CHECKS}
        if outcome.blocking_issue is None and all(check.passed for check in checks.values()):
            record = {
                "harness": driver.harness,
                "cli_version": cli_version,
                "suite_version": driver.suite_version,
                "verified_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "checks": [{"name": name, "passed": True, "detail": check.detail} for name, check in checks.items()],
                "capabilities": dict(outcome.capabilities),
            }
            cache.put(record)
            return SuiteResult.from_record(record, ran_now=True)
        return SuiteResult(
            checks=checks,
            capabilities=dict(outcome.capabilities),
            ran_now=True,
            failure_hint=outcome.failure_hint,
        )
    finally:
        lock.release()


# Probe -------------------------------------------------------------------------


def apply_suite(outcome, suite):
    """Put the suite checks and capabilities into the Connect outcome.

    The model report needs the model list of this Connect and, when the suite ran now, the suite's
    own model report too, so a report with every check passed always has a passing suite record.
    When this Connect fell back to the static model list, the model report is the suite's: a real
    report of the same CLI version.
    """
    for name, check in suite.checks.items():
        if name == "model_report":
            own = outcome.checks[name]
            if outcome.models_from_fallback:
                own.set(check.passed, f"suite: {check.detail}" if check.detail else "")
            elif own.passed and not check.passed:
                own.set(False, f"suite: {check.detail}")
            continue
        outcome.checks[name] = check
    outcome.capabilities = dict(suite.capabilities)
    outcome.failure_hint = outcome.failure_hint or suite.failure_hint
    outcome.suite = suite


def build_report(outcome):
    checks = list(outcome.checks.values())
    hint = outcome.failure_hint
    if not hint:
        failed = next((check for check in checks if not check.passed), None)
        hint = f"{failed.name}: {failed.detail}" if failed else ""
    return {
        "version": REPORT_VERSION,
        "harness_version": bounded(outcome.harness_version, 64),
        "location": bounded(outcome.location, 1024),
        "checks": [{"name": check.name, "passed": check.passed, "detail": check.detail} for check in checks],
        "models": outcome.models,
        "capabilities": dict(outcome.capabilities),
        "failure_hint": bounded(hint, MAX_HINT_CHARS),
        "blocking_issue": outcome.blocking_issue,
        "suite": suite_summary(outcome.suite),
    }


def suite_summary(suite):
    """The passing suite record that the behavior checks come from, or ``None`` when there is none."""
    if suite is None or suite.record is None:
        return None
    record = suite.record
    return {
        "suite_version": record["suite_version"],
        "cli_version": record["cli_version"],
        "verified_at": record["verified_at"],
        "ran_now": suite.ran_now,
    }


def run_probe(
    driver,
    *,
    run_root,
    probe_key,
    token_file,
    plane_checkout,
    budget_seconds=PROBE_BUDGET_SECONDS,
    cancel=None,
):
    """Run one probe. ``cancel`` (a ``threading.Event``) stops it early, for example when Plane replaced it."""
    own_dir = run_root / "probes" / probe_key
    deadline = Deadline(budget_seconds, cancel)
    try:
        workspace = prepare_workspace(run_root, probe_key, token_file, plane_checkout)
        outcome = driver.quick_check(workspace, deadline)
        if outcome.blocking_issue is None and outcome.checks["authentication"].passed and not outcome.failure_hint:
            suite = ensure_verified(
                driver,
                outcome.harness_version,
                deadline,
                run_root=run_root,
                token_file=token_file,
                plane_checkout=plane_checkout,
            )
            apply_suite(outcome, suite)
    except Exception as error:  # a driver or disk defect must still produce a failed report, never a crash
        logger.exception("Harness probe %s failed", driver.harness)
        outcome = ProbeOutcome(failure_hint=f"The probe stopped with an internal error ({type(error).__name__}).")
    finally:
        if probe_key and "/" not in probe_key and not probe_key.startswith("."):
            shutil.rmtree(own_dir, ignore_errors=True)
    return build_report(outcome)


# Keys that carry account data, signatures, usage or machine-specific listings. They never enter a recording.
RECORDING_DROP_KEYS = frozenset(
    {
        "account",
        "agents",
        "analytics_disabled",
        "apiKeySource",
        "available_output_styles",
        "commands",
        "fast_mode_disabled_reason",
        "fast_mode_state",
        "feedback_mode",
        "ide_rc_auto_enable_gate",
        "iterations",
        "mcp_servers",
        "memory_paths",
        "modelUsage",
        "output_style",
        "pid",
        "plugins",
        "remote_control_auto_connect_default",
        "remote_control_auto_enable",
        "remote_control_auto_on_by_default",
        "remote_control_available",
        "signature",
        "skills",
        "slash_commands",
        "total_cost_usd",
        "usage",
        "user_output_styles_dir",
    }
)


def scrub_message(value, replacements):
    """A copy of ``value`` without the dropped keys and with local paths replaced by placeholders."""
    if isinstance(value, dict):
        return {key: scrub_message(item, replacements) for key, item in value.items() if key not in RECORDING_DROP_KEYS}
    if isinstance(value, list):
        return [scrub_message(item, replacements) for item in value]
    if isinstance(value, str):
        for original, placeholder in replacements:
            value = value.replace(original, placeholder)
        return value
    return value


class TranscriptRecorder:
    """Writes scrubbed protocol messages of a native probe to ``<directory>/<session>.jsonl``."""

    def __init__(self, directory, replacements):
        self.directory = directory
        self.replacements = sorted(replacements, key=lambda pair: len(pair[0]), reverse=True)
        self.directory.mkdir(parents=True, exist_ok=True)

    def __call__(self, key, direction, message):
        session = key.rsplit("-session-", 1)[-1] if "-session-" in key else key.rsplit("-", 1)[-1]
        name = f"session-{session}" if "-session-" in key else session
        line = {"direction": direction, "message": scrub_message(message, self.replacements)}
        with open(self.directory / f"{name}.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
