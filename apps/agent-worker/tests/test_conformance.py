# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane_agent_worker.conformance import remove_stale_probes, run_probe
from plane_agent_worker.drivers.base import ProbeOutcome


class RecordingDriver:
    harness = "claude_code"
    suite_version = 1

    def __init__(self):
        self.calls = 0

    def quick_check(self, workspace, deadline):
        self.calls += 1
        return ProbeOutcome()

    def run_suite(self, workspace, deadline):
        self.calls += 1
        return ProbeOutcome()


def test_folder_error_before_the_probe_gives_a_failed_report(private_dir, token_file):
    run_root = private_dir / "runs"
    run_root.mkdir(mode=0o700)
    # A file where the probes directory must be: creating the probe folder fails with an OSError.
    (run_root / "probes").write_text("not a directory")
    driver = RecordingDriver()

    report = run_probe(
        driver, run_root=run_root, probe_key="p1-1", token_file=token_file, plane_checkout=private_dir / "plane"
    )

    assert driver.calls == 0
    assert "internal error" in report["failure_hint"]
    assert not any(check["passed"] for check in report["checks"])


def test_stale_probe_folders_are_removed_at_start(private_dir):
    probes = private_dir / "runs" / "probes"
    (probes / "p1-1" / "workspace").mkdir(parents=True)
    (probes / "p2-3").mkdir()
    (private_dir / "runs" / "keep").mkdir()

    assert remove_stale_probes(private_dir / "runs") == 2

    assert list(probes.iterdir()) == []
    assert (private_dir / "runs" / "keep").exists()


def test_no_probes_directory_is_not_an_error(private_dir):
    assert remove_stale_probes(private_dir / "absent") == 0
