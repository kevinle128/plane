# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Connection probe runner.

Creates the private directories of one probe under the Run root, runs the driver
probe within a time budget below Plane's 120 s answer window, removes the
directories, and returns a version 1 report. The report is evidence only; Plane
decides whether the Harness is connected.
"""

import json
import logging
import shutil

from plane_agent_worker.drivers.base import (
    MAX_HINT_CHARS,
    Deadline,
    ProbeOutcome,
    ProbeWorkspace,
    bounded,
)

REPORT_VERSION = 1
# Plane reads a probe without a report after 120 s as failed; keep a margin for the report itself.
PROBE_BUDGET_SECONDS = 100

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
    }


def run_probe(
    driver,
    *,
    run_root,
    probe_key,
    token_file,
    plane_checkout,
    sandbox,
    budget_seconds=PROBE_BUDGET_SECONDS,
):
    workspace = prepare_workspace(run_root, probe_key, token_file, plane_checkout)
    try:
        outcome = driver.probe(workspace, sandbox, Deadline(budget_seconds))
    except Exception as error:  # a driver defect must still produce a failed report, never a crash
        logger.exception("Harness probe %s failed", driver.harness)
        outcome = ProbeOutcome(failure_hint=f"The probe stopped with an internal error ({type(error).__name__}).")
    finally:
        shutil.rmtree(workspace.own_dir, ignore_errors=True)
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
