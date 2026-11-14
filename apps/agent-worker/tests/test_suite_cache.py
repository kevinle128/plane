# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import threading
import time

import pytest

from plane_agent_worker.conformance import SuiteCache, ensure_verified
from plane_agent_worker.drivers.base import Deadline, ProbeOutcome
from plane_agent_worker.drivers.claude import SUITE_VERSION, suite_fingerprint

# A change to the required checks, the Claude session flags or the boundary settings changes the
# fingerprint. Then give the suite a new SUITE_VERSION and add its fingerprint here, so the
# cached results of the old suite are not used.
PINNED_FINGERPRINTS = {
    1: "640e1597a067716a3475644d454553730cf47815a5970da00f85d869e0f70885",
}


def test_suite_fingerprint_is_pinned_to_the_suite_version():
    assert PINNED_FINGERPRINTS.get(SUITE_VERSION) == suite_fingerprint()


def passing_suite(version="2.1.289"):
    outcome = ProbeOutcome(harness_version=version)
    for check in outcome.checks.values():
        check.set(True)
    outcome.models = [{"id": "haiku", "label": "Haiku", "description": ""}]
    outcome.capabilities["native_resume"] = True
    return outcome


class SuiteDriver:
    """A driver whose suite result is fixed. ``delay`` makes the suite slow."""

    harness = "claude_code"

    def __init__(self, outcome_factory=passing_suite, delay=0.0, suite_version=1):
        self.outcome_factory = outcome_factory
        self.delay = delay
        self.suite_version = suite_version
        self.suite_runs = 0
        self.lock = threading.Lock()

    def run_suite(self, workspace, deadline):
        with self.lock:
            self.suite_runs += 1
        time.sleep(self.delay)
        return self.outcome_factory()


def verify(driver, private_dir, token_file, version="2.1.289", seconds=30, cancel=None):
    run_root = private_dir / "runs"
    run_root.mkdir(exist_ok=True, mode=0o700)
    return ensure_verified(
        driver,
        version,
        Deadline(seconds, cancel),
        run_root=run_root,
        token_file=token_file,
        plane_checkout=private_dir / "plane",
    )


def test_unverified_version_runs_the_suite_and_stores_a_private_record(private_dir, token_file):
    driver = SuiteDriver()

    result = verify(driver, private_dir, token_file)

    assert driver.suite_runs == 1
    assert result.ran_now is True
    assert result.record["cli_version"] == "2.1.289"
    assert result.record["suite_version"] == 1
    path = private_dir / "runs" / "state" / "conformance.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert (path.parent.stat().st_mode & 0o777) == 0o700
    stored = SuiteCache(path).get("claude_code", "2.1.289", 1)
    assert stored == result.record
    # The suite folder is removed after the suite.
    assert list((private_dir / "runs" / "probes").iterdir()) == []


def test_cached_version_does_not_run_the_suite_again(private_dir, token_file):
    driver = SuiteDriver()
    first = verify(driver, private_dir, token_file)

    second = verify(driver, private_dir, token_file)

    assert driver.suite_runs == 1
    assert second.ran_now is False
    assert second.record == first.record
    assert all(check.passed for check in second.checks.values())
    assert second.capabilities["native_resume"] is True


def test_failed_suite_is_not_stored_and_runs_again(private_dir, token_file):
    def failing():
        outcome = passing_suite()
        outcome.checks["interruption"].set(False, "the turn was not interrupted")
        return outcome

    driver = SuiteDriver(failing)
    first = verify(driver, private_dir, token_file)
    second = verify(driver, private_dir, token_file)

    assert driver.suite_runs == 2
    assert first.record is None and second.record is None
    assert first.checks["interruption"].passed is False
    assert SuiteCache(private_dir / "runs" / "state" / "conformance.json").get("claude_code", "2.1.289", 1) is None


def test_suite_without_a_real_model_report_is_not_stored(private_dir, token_file):
    def no_models():
        outcome = passing_suite()
        outcome.models = []
        outcome.checks["model_report"].set(False, "the CLI reported no usable model")
        return outcome

    driver = SuiteDriver(no_models)
    result = verify(driver, private_dir, token_file)

    assert result.record is None
    assert result.checks["model_report"].passed is False


def test_suite_on_another_cli_version_than_requested_is_not_stored(private_dir, token_file):
    driver = SuiteDriver(lambda: passing_suite("2.1.290"))

    result = verify(driver, private_dir, token_file, version="2.1.289")

    assert result.record is None
    assert not all(check.passed for check in result.checks.values())


@pytest.mark.parametrize("change", ["suite_version", "cli_version"])
def test_another_suite_version_or_cli_version_misses_the_cache(private_dir, token_file, change):
    driver = SuiteDriver()
    verify(driver, private_dir, token_file)

    if change == "suite_version":
        driver.suite_version = 2
        result = verify(driver, private_dir, token_file)
    else:
        driver.outcome_factory = lambda: passing_suite("2.1.290")
        result = verify(driver, private_dir, token_file, version="2.1.290")

    assert driver.suite_runs == 2
    assert result.ran_now is True and result.record is not None


def test_two_checks_of_one_version_start_one_suite(private_dir, token_file):
    driver = SuiteDriver(delay=0.5)
    (private_dir / "runs").mkdir(mode=0o700)
    results = []

    def check():
        results.append(verify(driver, private_dir, token_file))

    threads = [threading.Thread(target=check) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert driver.suite_runs == 1
    assert sorted(result.ran_now for result in results) == [False, True]
    assert results[0].record == results[1].record


def test_cancelled_wait_for_a_running_suite_returns_without_a_record(private_dir, token_file):
    driver = SuiteDriver(delay=1.0)
    (private_dir / "runs").mkdir(mode=0o700)
    runner = threading.Thread(target=verify, args=(driver, private_dir, token_file))
    runner.start()
    time.sleep(0.2)
    cancel = threading.Event()
    cancel.set()

    started = time.monotonic()
    result = verify(driver, private_dir, token_file, cancel=cancel)

    assert time.monotonic() - started < 0.9
    assert result.record is None
    assert not any(check.passed for check in result.checks.values())
    runner.join(timeout=5)
    assert driver.suite_runs == 1


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps([1, 2]),
        json.dumps({"records": {"claude_code/2.1.289/1": {"cli_version": "2.1.289"}}}),
    ],
)
def test_unreadable_cache_file_counts_as_empty(private_dir, token_file, content):
    state = private_dir / "runs" / "state"
    state.mkdir(parents=True, mode=0o700)
    (state / "conformance.json").write_text(content)
    driver = SuiteDriver()

    result = verify(driver, private_dir, token_file)

    assert driver.suite_runs == 1
    assert result.record is not None
    assert SuiteCache(state / "conformance.json").get("claude_code", "2.1.289", 1) == result.record


def test_only_the_question_and_answer_mode_exists(private_dir, token_file):
    with pytest.raises(ValueError):
        ensure_verified(
            SuiteDriver(),
            "2.1.289",
            Deadline(5),
            run_root=private_dir,
            token_file=token_file,
            plane_checkout=private_dir / "plane",
            mode="code",
        )
