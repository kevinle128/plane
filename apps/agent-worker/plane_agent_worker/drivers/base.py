# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Shared Harness driver contract.

A driver proves its Harness on the installed version before Plane shows it as
connected: authentication, a model report, one resumed follow-up, progress
events, interruption, permission enforcement (a write is denied under the OS
boundary) and recovery after the Harness process is killed. It reports the
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
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def remaining(self):
        return max(0.0, self.end - time.monotonic())

    def within(self, seconds):
        """The earlier of this deadline and ``seconds`` from now, as a new deadline."""
        return Deadline(min(seconds, self.remaining()))

    @property
    def expired(self):
        return self.remaining() <= 0


class ProbeTimeout(Exception):
    """A Harness step did not finish before its deadline."""


class HarnessDriver(Protocol):
    harness: str

    def probe(self, workspace: ProbeWorkspace, sandbox, deadline: Deadline) -> ProbeOutcome: ...
