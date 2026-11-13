# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Read-only OS boundary for Harness processes on macOS.

``MacOSSandbox.wrap`` runs a command under ``sandbox-exec`` with the
``sandbox/qa-readonly.sb`` profile. The profile denies every Host write except
the private temporary directory and the Harness session directory of this probe
or Run, and denies reads of other Runs, other sessions, the Worker token and the
Plane checkout. Every path must be absolute; the profile receives real paths
(for example ``/private/tmp``, not ``/tmp``), because the kernel matches real paths.
"""

import os
import subprocess
from pathlib import Path
from typing import NamedTuple

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
PROFILE_PATH = Path(__file__).with_name("sandbox") / "qa-readonly.sb"
WRITE_CHECK_FILE = ".plane-boundary-check"


class SandboxPaths(NamedTuple):
    run_root: Path
    own_dir: Path
    private_tmp: Path
    session_root: Path
    session_dir: Path
    token_file: Path
    plane_checkout: Path


PARAMETERS = (
    ("RUN_ROOT", "run_root"),
    ("OWN_DIR", "own_dir"),
    ("PRIVATE_TMP", "private_tmp"),
    ("SESSION_ROOT", "session_root"),
    ("SESSION_DIR", "session_dir"),
    ("TOKEN_FILE", "token_file"),
    ("PLANE_CHECKOUT", "plane_checkout"),
)


def real_path(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError(f"Sandbox paths must be absolute: {path}")
    return Path(os.path.realpath(path))


class MacOSSandbox:
    def wrap(self, argv, paths):
        command = [SANDBOX_EXEC, "-f", str(PROFILE_PATH)]
        for parameter, attribute in PARAMETERS:
            command += ["-D", f"{parameter}={real_path(getattr(paths, attribute))}"]
        return command + list(argv)

    def verify_write_denied(self, directory, paths):
        """Prove that a sandboxed process cannot write in ``directory``. Returns ``(denied, detail)``."""
        target = real_path(directory) / WRITE_CHECK_FILE
        command = self.wrap(["/bin/sh", "-c", 'echo probe > "$1"', "sh", str(target)], paths)
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, f"the sandbox did not run: {type(error).__name__}"
        if target.exists():
            target.unlink()
            return False, "a sandboxed write in the workspace succeeded"
        if result.returncode == 0:
            return False, "the sandboxed write command reported success"
        return True, ""
