# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Worker poll loop: heartbeat, claim a pending probe, run it and report it.

A failed or rejected request is logged and the loop continues; it never stops on
a Plane error. The report carries the probe generation, so Plane rejects it if a
newer Connect or a Disconnect replaced the probe.
"""

import logging
import re
import time

from plane_agent_worker.conformance import run_probe as default_run_probe
from plane_agent_worker.plane_client import PlaneClientError, ProbeRejected

HEARTBEAT_SECONDS = 30
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
        sandbox,
        run_probe=default_run_probe,
        heartbeat_seconds=HEARTBEAT_SECONDS,
        clock=time.monotonic,
    ):
        self.client = client
        self.drivers = dict(drivers)
        self.run_root = run_root
        self.token_file = token_file
        self.plane_checkout = plane_checkout
        self.sandbox = sandbox
        self.run_probe = run_probe
        self.heartbeat_seconds = heartbeat_seconds
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

        logger.info("Running %s probe %s (generation %s)", driver.harness, probe_id, generation)
        report = self.run_probe(
            driver,
            run_root=self.run_root,
            probe_key=f"{probe_id}-{generation}",
            token_file=self.token_file,
            plane_checkout=self.plane_checkout,
            sandbox=self.sandbox,
        )
        report["generation"] = generation
        try:
            result = self.client.report_probe(probe_id, report)
            logger.info("Probe %s reported: %s", probe_id, result.get("state") if isinstance(result, dict) else "")
        except ProbeRejected as error:
            logger.info("Plane rejected probe %s: %s", probe_id, error.code)
        except PlaneClientError as error:
            logger.warning("Probe %s report failed: status %s (%s)", probe_id, error.status, error.code)
        return True

    def run_forever(self, stop_event, poll_seconds):
        while not stop_event.is_set():
            if not self.run_once():
                stop_event.wait(poll_seconds)
