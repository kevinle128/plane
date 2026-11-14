# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Worker poll loop: heartbeat, claim a pending probe, run it and report it.

A failed or rejected request is logged and the loop continues; it never stops on
a Plane error or on an unexpected error in one step. The claim gives the seconds
left before Plane's answer deadline; the probe budget ends before it. While a
probe runs, the Worker asks Plane every few seconds whether the probe is still
current and stops it when a newer Connect or a Disconnect replaced it. The report
carries the probe generation, so Plane also rejects a late report.
"""

import logging
import re
import threading
import time

from plane_agent_worker.conformance import PROBE_BUDGET_SECONDS
from plane_agent_worker.conformance import run_probe as default_run_probe
from plane_agent_worker.plane_client import PlaneClientError, ProbeRejected

HEARTBEAT_SECONDS = 30
PROBE_CHECK_SECONDS = 5
# Time kept after the probe budget for the report request itself.
REPORT_MARGIN_SECONDS = 10
# A probe with less time than this cannot finish; the Worker does not start it.
MIN_PROBE_SECONDS = 30
PROBE_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")

logger = logging.getLogger("plane_agent_worker.loop")


class WorkerLoop:
    def __init__(
        self,
        *,
        client,
        drivers,
        run_root,
        token_file,
        plane_checkout,
        run_probe=default_run_probe,
        heartbeat_seconds=HEARTBEAT_SECONDS,
        probe_check_seconds=PROBE_CHECK_SECONDS,
        clock=time.monotonic,
    ):
        self.client = client
        self.drivers = dict(drivers)
        self.run_root = run_root
        self.token_file = token_file
        self.plane_checkout = plane_checkout
        self.run_probe = run_probe
        self.heartbeat_seconds = heartbeat_seconds
        self.probe_check_seconds = probe_check_seconds
        self.clock = clock
        self._last_heartbeat = None

    def _heartbeat_if_due(self):
        now = self.clock()
        if self._last_heartbeat is not None and now - self._last_heartbeat < self.heartbeat_seconds:
            return
        self._last_heartbeat = now
        try:
            self.client.heartbeat()
        except PlaneClientError as error:
            logger.warning("Heartbeat failed: status %s (%s)", error.status, error.code)

    def run_once(self):
        """One poll step. Returns True when a probe was claimed."""
        self._heartbeat_if_due()
        try:
            probe = self.client.claim_probe(sorted(self.drivers))
        except PlaneClientError as error:
            logger.warning("Probe claim failed: status %s (%s)", error.status, error.code)
            return False
        if not probe:
            return False
        probe_id, generation = probe.get("id"), probe.get("generation")
        driver = self.drivers.get(probe.get("harness"))
        if driver is None or not isinstance(probe_id, str) or not PROBE_ID_PATTERN.match(probe_id):
            logger.warning("Ignoring a probe this Worker cannot run")
            return True
        if not isinstance(generation, int) or isinstance(generation, bool):
            logger.warning("Ignoring probe %s without a generation", probe_id)
            return True
        seconds_left = probe.get("seconds_left")
        if not isinstance(seconds_left, int | float) or isinstance(seconds_left, bool):
            logger.warning("Ignoring probe %s without an answer deadline", probe_id)
            return True
        budget = min(PROBE_BUDGET_SECONDS, seconds_left - REPORT_MARGIN_SECONDS)
        if budget < MIN_PROBE_SECONDS:
            logger.warning("Skipping probe %s: %.0f s left before its answer deadline", probe_id, seconds_left)
            return True

        logger.info("Running %s probe %s (generation %s, %.0f s)", driver.harness, probe_id, generation, budget)
        replaced = threading.Event()
        finished = threading.Event()
        watcher = threading.Thread(
            target=self._watch_probe, args=(probe_id, generation, replaced, finished), daemon=True
        )
        watcher.start()
        try:
            report = self.run_probe(
                driver,
                run_root=self.run_root,
                probe_key=f"{probe_id}-{generation}",
                token_file=self.token_file,
                plane_checkout=self.plane_checkout,
                budget_seconds=budget,
                cancel=replaced,
            )
        finally:
            finished.set()
            watcher.join(timeout=self.probe_check_seconds + 1)
        if replaced.is_set():
            logger.info("Probe %s was replaced in Plane; it was stopped and is not reported", probe_id)
            return True
        report["generation"] = generation
        try:
            result = self.client.report_probe(probe_id, report)
            logger.info("Probe %s reported: %s", probe_id, result.get("state") if isinstance(result, dict) else "")
        except ProbeRejected as error:
            logger.info("Plane rejected probe %s: %s", probe_id, error.code)
        except PlaneClientError as error:
            logger.warning("Probe %s report failed: status %s (%s)", probe_id, error.status, error.code)
        return True

    def _watch_probe(self, probe_id, generation, replaced, finished):
        """Heartbeat with the probe while it runs; set ``replaced`` when Plane says it is no longer current."""
        while not finished.wait(self.probe_check_seconds):
            try:
                answer = self.client.heartbeat(probe_id, generation)
            except PlaneClientError as error:
                logger.warning("Probe check failed: status %s (%s)", error.status, error.code)
                continue
            if isinstance(answer, dict) and answer.get("probe_current") is False:
                replaced.set()
                return

    def run_forever(self, stop_event, poll_seconds):
        while not stop_event.is_set():
            try:
                claimed = self.run_once()
            except Exception:  # one bad step must not stop the Worker; the next poll tries again
                logger.exception("Worker poll step failed")
                claimed = False
            if not claimed:
                stop_event.wait(poll_seconds)
