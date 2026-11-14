# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import threading

import pytest

from plane_agent_worker.loop import MIN_PROBE_SECONDS, REPORT_MARGIN_SECONDS, WorkerLoop
from plane_agent_worker.plane_client import PlaneClientError, ProbeRejected


def claimed(probe_id="p1", generation=1, seconds_left=120, harness="claude_code"):
    return {"id": probe_id, "harness": harness, "generation": generation, "seconds_left": seconds_left}


class FakeClient:
    def __init__(self, probe=None, report_error=None, probe_current=True):
        self.probe = probe
        self.report_error = report_error
        self.probe_current = probe_current
        self.calls = []

    def heartbeat(self, probe_id=None, generation=None):
        if probe_id is None:
            self.calls.append(("heartbeat",))
            return {"worker": "mini"}
        self.calls.append(("probe_check", probe_id, generation))
        return {"worker": "mini", "probe_current": self.probe_current}

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
    driver.kwargs = kwargs
    return {"version": 1, "checks": [], "models": [], "capabilities": {}, "probe_key": kwargs["probe_key"]}


def waiting_run_probe(driver, **kwargs):
    """A probe that runs until it is cancelled, or 5 s at most."""
    driver.runs += 1
    driver.cancelled = kwargs["cancel"].wait(5)
    return {"version": 1, "checks": [], "models": [], "capabilities": {}}


@pytest.fixture
def loop_for(private_dir, token_file):
    def build(client, driver, run_probe=fake_run_probe):
        return WorkerLoop(
            client=client,
            drivers={"claude_code": driver},
            run_root=private_dir,
            token_file=token_file,
            plane_checkout=private_dir / "plane",
            run_probe=run_probe,
            heartbeat_seconds=30,
            probe_check_seconds=0.05,
        )

    return build


def test_claimed_probe_is_run_and_reported_with_its_generation(loop_for):
    client = FakeClient(probe=claimed(generation=4))
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
    client = FakeClient(probe=claimed(), report_error=ProbeRejected(409, "probe_expired"))

    assert loop_for(client, FakeDriver()).run_once() is True


def test_probe_for_an_unknown_harness_is_not_run(loop_for):
    client = FakeClient(probe=claimed(harness="codex"))
    driver = FakeDriver()

    loop_for(client, driver).run_once()

    assert driver.runs == 0
    assert not [call for call in client.calls if call[0] == "report"]


def test_plane_errors_do_not_stop_the_loop(loop_for):
    class BrokenClient(FakeClient):
        def claim_probe(self, harnesses):
            raise PlaneClientError(502, "bad_gateway")

    assert loop_for(BrokenClient(), FakeDriver()).run_once() is False


def test_probe_budget_is_100_seconds_when_plane_gives_more_time(loop_for):
    driver = FakeDriver()

    loop_for(FakeClient(probe=claimed(seconds_left=120)), driver).run_once()

    assert driver.kwargs["budget_seconds"] == 100


def test_probe_budget_ends_before_the_answer_deadline(loop_for):
    driver = FakeDriver()

    loop_for(FakeClient(probe=claimed(seconds_left=65)), driver).run_once()

    assert driver.kwargs["budget_seconds"] == 65 - REPORT_MARGIN_SECONDS


def test_probe_claimed_too_close_to_the_deadline_is_not_run(loop_for):
    client = FakeClient(probe=claimed(seconds_left=MIN_PROBE_SECONDS + REPORT_MARGIN_SECONDS - 1))
    driver = FakeDriver()

    assert loop_for(client, driver).run_once() is True

    assert driver.runs == 0
    assert not [call for call in client.calls if call[0] == "report"]


def test_probe_without_an_answer_deadline_is_not_run(loop_for):
    probe = claimed()
    del probe["seconds_left"]
    driver = FakeDriver()

    loop_for(FakeClient(probe=probe), driver).run_once()

    assert driver.runs == 0


def test_replaced_probe_is_stopped_and_not_reported(loop_for):
    client = FakeClient(probe=claimed(generation=2), probe_current=False)
    driver = FakeDriver()

    loop_for(client, driver, run_probe=waiting_run_probe).run_once()

    assert driver.cancelled is True
    assert ("probe_check", "p1", 2) in client.calls
    assert not [call for call in client.calls if call[0] == "report"]


def test_current_probe_keeps_running_and_is_reported(loop_for):
    client = FakeClient(probe=claimed(), probe_current=True)
    driver = FakeDriver()

    def short_run_probe(driver, **kwargs):
        driver.runs += 1
        driver.cancelled = kwargs["cancel"].wait(0.3)
        return {"version": 1, "checks": [], "models": [], "capabilities": {}}

    loop_for(client, driver, run_probe=short_run_probe).run_once()

    assert driver.cancelled is False
    assert [call for call in client.calls if call[0] == "probe_check"]
    assert [call for call in client.calls if call[0] == "report"]


def test_unexpected_error_in_a_poll_step_does_not_stop_the_loop(loop_for):
    class FailingClient(FakeClient):
        def claim_probe(self, harnesses):
            self.calls.append(("claim", list(harnesses)))
            raise RuntimeError("unexpected")

    client = FailingClient()
    loop = loop_for(client, FakeDriver())
    stop = threading.Event()
    original_wait = stop.wait

    def wait_then_stop(seconds):
        if len([call for call in client.calls if call[0] == "claim"]) >= 2:
            stop.set()
        return original_wait(0)

    stop.wait = wait_then_stop

    loop.run_forever(stop, poll_seconds=0)

    assert len([call for call in client.calls if call[0] == "claim"]) >= 2
