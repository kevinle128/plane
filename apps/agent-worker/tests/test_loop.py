# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane_agent_worker.loop import WorkerLoop
from plane_agent_worker.plane_client import PlaneClientError, ProbeRejected


class FakeClient:
    def __init__(self, probe=None, report_error=None):
        self.probe = probe
        self.report_error = report_error
        self.calls = []

    def heartbeat(self):
        self.calls.append(("heartbeat",))
        return {"worker": "mini"}

    def claim_probe(self, harnesses):
        self.calls.append(("claim", list(harnesses)))
        probe, self.probe = self.probe, None
        return probe

    def report_probe(self, probe_id, report):
        self.calls.append(("report", probe_id, report))
        if self.report_error:
            raise self.report_error
        return {"state": "connected"}


class FakeDriver:
    harness = "claude_code"

    def __init__(self):
        self.runs = 0


def fake_run_probe(driver, **kwargs):
    driver.runs += 1
    return {"version": 1, "checks": [], "models": [], "capabilities": {}, "probe_key": kwargs["probe_key"]}


@pytest.fixture
def loop_for(private_dir, token_file):
    def build(client, driver):
        return WorkerLoop(
            client=client,
            drivers={"claude_code": driver},
            run_root=private_dir,
            token_file=token_file,
            plane_checkout=private_dir / "plane",
            sandbox=object(),
            run_probe=fake_run_probe,
            heartbeat_seconds=30,
        )

    return build


def test_claimed_probe_is_run_and_reported_with_its_generation(loop_for):
    client = FakeClient(probe={"id": "p1", "harness": "claude_code", "generation": 4})
    driver = FakeDriver()

    assert loop_for(client, driver).run_once() is True

    assert ("claim", ["claude_code"]) in client.calls
    report = next(call for call in client.calls if call[0] == "report")
    assert report[1] == "p1"
    assert report[2]["generation"] == 4
    assert report[2]["probe_key"] == "p1-4"
    assert driver.runs == 1


def test_no_pending_probe_reports_nothing(loop_for):
    client = FakeClient()

    assert loop_for(client, FakeDriver()).run_once() is False
    assert not [call for call in client.calls if call[0] == "report"]


def test_heartbeat_is_sent_once_per_interval(loop_for):
    client = FakeClient()
    loop = loop_for(client, FakeDriver())

    loop.run_once()
    loop.run_once()

    assert [call for call in client.calls if call[0] == "heartbeat"] == [("heartbeat",)]


def test_rejected_report_is_dropped_without_stopping_the_loop(loop_for):
    client = FakeClient(
        probe={"id": "p1", "harness": "claude_code", "generation": 1}, report_error=ProbeRejected(409, "probe_expired")
    )

    assert loop_for(client, FakeDriver()).run_once() is True


def test_probe_for_an_unknown_harness_is_not_run(loop_for):
    client = FakeClient(probe={"id": "p1", "harness": "codex", "generation": 1})
    driver = FakeDriver()

    loop_for(client, driver).run_once()

    assert driver.runs == 0
    assert not [call for call in client.calls if call[0] == "report"]


def test_plane_errors_do_not_stop_the_loop(loop_for):
    class BrokenClient(FakeClient):
        def claim_probe(self, harnesses):
            raise PlaneClientError(502, "bad_gateway")

    assert loop_for(BrokenClient(), FakeDriver()).run_once() is False
