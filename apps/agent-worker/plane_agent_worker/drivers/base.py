# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Shared Harness driver contract.

A driver proves its Harness on the installed version before Plane shows it as
connected: authentication, a model report, one resumed follow-up, progress
events, interruption, permission enforcement (each write path the Harness offers
is denied by the boundary the Run uses) and recovery after the Harness process
is killed. It reports the
native capabilities (midturn input, native resume, permission prompt) apart from
the checks, because Plane offers its own queue and stop path where a native
control is missing.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

REQUIRED_CHECKS = (
    "authentication",
    "model_report",
    "follow_up",
    "progress",
    "interruption",
    "permission",
    "recovery",
)
CAPABILITY_FLAGS = ("midturn_input", "native_resume", "permission_prompt")
MAX_DETAIL_CHARS = 500
MAX_HINT_CHARS = 1000
# A wait wakes at least this often, so a cancelled deadline stops it soon.
WAIT_SLICE_SECONDS = 0.5


def bounded(text, limit):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


@dataclass
class CheckResult:
    name: str
    passed: bool = False
    detail: str = "not run"

    def set(self, passed, detail=""):
        self.passed = bool(passed)
        self.detail = bounded(detail, MAX_DETAIL_CHARS)


@dataclass
class ProbeOutcome:
    harness_version: str = ""
    location: str = ""
    checks: dict = field(default_factory=lambda: {name: CheckResult(name) for name in REQUIRED_CHECKS})
    models: list = field(default_factory=list)
    capabilities: dict = field(default_factory=lambda: dict.fromkeys(CAPABILITY_FLAGS, False))
    failure_hint: str = ""
    blocking_issue: str | None = None
    # True when the model list request failed and ``models`` is the static fallback list.
    models_from_fallback: bool = False
    # The suite result applied to this outcome (``conformance.SuiteResult``), if the suite was consulted.
    suite: object = None


@dataclass(frozen=True)
class ProbeWorkspace:
    """Directories of one probe. ``cwd`` is the Harness working directory and stays read-only for it."""

    run_root: Path
    own_dir: Path
    cwd: Path
    tmp: Path
    token_file: Path
    plane_checkout: Path


class Deadline:
    """A time limit. When ``cancel`` (a ``threading.Event``) is set, no time remains."""

    def __init__(self, seconds, cancel=None):
        self.end = time.monotonic() + seconds
        self.cancel = cancel

    @property
    def cancelled(self):
        return self.cancel is not None and self.cancel.is_set()

    def remaining(self):
        if self.cancelled:
            return 0.0
        return max(0.0, self.end - time.monotonic())

    def within(self, seconds):
        """The earlier of this deadline and ``seconds`` from now, as a new deadline with the same cancel event."""
        return Deadline(min(seconds, self.remaining()), self.cancel)

    @property
    def expired(self):
        return self.remaining() <= 0


class ProbeTimeout(Exception):
    """A Harness step did not finish before its deadline."""


class HarnessDriver(Protocol):
    harness: str
    suite_version: int

    def quick_check(self, workspace: ProbeWorkspace, deadline: Deadline) -> ProbeOutcome:
        """Version, authentication and model report of the installed CLI."""
        ...

    def run_suite(self, workspace: ProbeWorkspace, deadline: Deadline) -> ProbeOutcome:
        """Every check except authentication, on the installed CLI version."""
        ...
