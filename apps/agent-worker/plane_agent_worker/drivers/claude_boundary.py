# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Q&A boundary for Claude Code: its built-in sandbox and permission rules.

The ``claude`` process itself runs without an outer OS sandbox, so it writes its
own session history and ``--resume`` works. Claude reads its own setting sources
as installed (user settings, hooks and MCP servers included). The boundary is in
a settings file that the Worker writes for each probe or Run, next to the
working directory and not inside it (mode 0600), and passes with ``--settings``.
That file ranks above the user, project and local settings files. Lists such as
``permissions.deny`` merge across scopes, and a deny rule wins over an allow
rule from any scope. The settings:

- Bash and its child processes run in the built-in sandbox (Seatbelt on macOS).
  The sandbox must start (``failIfUnavailable``) and a command cannot retry
  outside it (``allowUnsandboxedCommands: false``). Writes in the working
  directory are denied; the sandbox denies writes outside it by default. The
  one exception is Claude Code's per-user temporary directory, which the Bash
  tool needs for its shell state.
- The sandbox denies reads of the Run root (other Runs and probes), the Worker
  token, the Plane checkout, the Claude configuration directory (sessions and
  credentials) and the usual credential stores. Only this probe or Run directory
  is readable inside the Run root.
- Bare-name deny rules remove Edit, Write and NotebookEdit, so no file tool can
  write anywhere, and a user allow rule cannot bring them back. A bare name adds
  no path to the sandbox write denials, so Bash keeps its temporary directory
  (checked with Claude Code 2.1.289). Read is limited to the working directory;
  ``Read`` deny rules repeat the secret paths, because a symbolic link in the
  working directory can point at them.
- Bypass mode is refused.

Not closed by this file: a user ``sandbox.filesystem.allowRead`` entry re-opens
a narrower part of a denied read path, and user ``sandbox.excludedCommands`` run
outside the sandbox. Only managed settings can lock those lists.
"""

import json
import os
from pathlib import Path

SETTINGS_FILE = "claude-settings.json"
# Bare tool names: each deny rule removes the tool from the session.
FILE_TOOLS = ("Edit", "Write", "NotebookEdit")

# Credential stores under the home directory that no Harness command may read.
CREDENTIAL_DIRECTORIES = (".ssh", ".aws", ".config/gh", ".gnupg", ".docker", ".kube")
CREDENTIAL_FILES = (".claude.json", ".netrc", ".git-credentials")


def _real(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError(f"Boundary paths must be absolute: {path}")
    return os.path.realpath(path)


def boundary_settings(workspace, config_dir, home):
    """The settings document for one probe or Run working in ``workspace``."""
    cwd = _real(workspace.cwd)
    home = Path(home)
    secret_directories = [
        _real(workspace.plane_checkout),
        _real(config_dir),
        *(_real(home / name) for name in CREDENTIAL_DIRECTORIES),
    ]
    secret_files = [
        _real(workspace.token_file),
        *(_real(home / name) for name in CREDENTIAL_FILES),
    ]
    read_rules = [f"Read(/{path}/**)" for path in secret_directories] + [f"Read(/{path})" for path in secret_files]
    return {
        "sandbox": {
            "enabled": True,
            "failIfUnavailable": True,
            "allowUnsandboxedCommands": False,
            "autoAllowBashIfSandboxed": True,
            "filesystem": {
                "denyWrite": [cwd],
                "denyRead": [_real(workspace.run_root), *secret_directories, *secret_files],
                "allowRead": [_real(workspace.own_dir)],
            },
        },
        "permissions": {
            "deny": [*FILE_TOOLS, *read_rules],
            "disableBypassPermissionsMode": "disable",
            "blockReadsOutsideWorkingDirectories": True,
        },
    }


def write_boundary_settings(workspace, config_dir, home):
    """Write the settings file once, private to the Worker user. Returns its path."""
    path = Path(workspace.own_dir) / SETTINGS_FILE
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(boundary_settings(workspace, config_dir, home), handle, indent=2)
    return path
