# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Scripted stand-in for the ``sbx`` CLI (Docker Sandboxes, v0.53.0 command shapes).

Each call appends its arguments as one JSON line to ``$FAKE_SBX_STATE/argv.jsonl``.
Sandboxes are JSON files in ``$FAKE_SBX_STATE/sandboxes``. ``exec`` runs the command
on this machine: in the working directory given with ``-w``, with ``HOME`` set to
``$FAKE_SBX_STATE/vm-home`` (the home folder of the VM), ``PATH`` from
``$FAKE_SBX_PATH`` and only the ``-e`` variables, like a VM that has none of the host
environment. A read-only mount to a target under ``/opt`` becomes a link under
``$FAKE_SBX_STATE/opt/<sandbox>``, and ``exec`` arguments that start with ``/opt/``
point there. ``$FAKE_SBX_SCENARIO`` selects a failure:

- ``ok``: every command succeeds.
- ``signed_out``: ``ls`` fails as when the Docker sign-in is missing.
- ``create_fails``: ``create`` fails.
- ``stale_settings``: the first health check of a sandbox fails with exit 1 (a stale
  single-file mount); after ``stop`` it succeeds.
- ``broken``: every ``exec`` of an existing sandbox fails with exit 1.
"""

import json
import os
import shutil
import sys
from pathlib import Path

STATE = Path(os.environ["FAKE_SBX_STATE"])
SCENARIO = os.environ.get("FAKE_SBX_SCENARIO", "ok")
SANDBOXES = STATE / "sandboxes"


def load(name):
    path = SANDBOXES / f"{name}.json"
    return json.loads(path.read_text()) if path.exists() else None


def save(name, record):
    SANDBOXES.mkdir(parents=True, exist_ok=True)
    (SANDBOXES / f"{name}.json").write_text(json.dumps(record))


def fail(message, code):
    print(message, file=sys.stderr)
    return code


def create(args):
    name = args[args.index("--name") + 1]
    if SCENARIO == "create_fails":
        return fail("error: failed to create sandbox", 1)
    if load(name):
        return fail(f"error: sandbox '{name}' already exists", 1)
    rest = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in ("--name", "--static-mcp", "--memory"):
            skip = True
            continue
        if arg.startswith("-"):
            continue
        rest.append(arg)
    kit, primary, mounts = rest[0], rest[1], rest[2:]
    opt_root = STATE / "opt" / name
    for mount in mounts:
        parts = mount.split(":")
        if len(parts) == 3 and parts[1].startswith("/opt/"):
            link = opt_root / parts[1].lstrip("/")
            link.parent.mkdir(parents=True, exist_ok=True)
            if link.is_symlink():
                link.unlink()
            link.symlink_to(parts[0])
    save(name, {"kit": kit, "primary": primary, "mounts": mounts, "rules": [], "running": True, "health_failed": False})
    return 0


def execute(args):
    interactive = False
    cwd = None
    env = {}
    index = 0
    while args[index].startswith("-"):
        flag = args[index]
        if flag == "-i":
            interactive = True
            index += 1
        elif flag == "-w":
            cwd = args[index + 1]
            index += 2
        elif flag == "-e":
            key, _, value = args[index + 1].partition("=")
            env[key] = value
            index += 2
        else:
            return fail(f"unknown flag {flag}", 2)
    name, command = args[index], args[index + 1 :]
    record = load(name)
    if record is None:
        return fail(f"error: sandbox '{name}' not found", 125)
    if SCENARIO == "broken":
        return fail("error: sandbox daemon failed", 1)
    record["running"] = True
    health = command[:2] == ["sh", "-c"] and command[2].startswith("test -r /opt/")
    if health and SCENARIO == "stale_settings" and not record["health_failed"]:
        record["health_failed"] = True
        save(name, record)
        return 1
    save(name, record)
    opt_root = STATE / "opt" / name
    command = [
        str(opt_root) + arg if arg.startswith("/opt/") else arg.replace(" /opt/", f" {opt_root}/opt/")
        for arg in command
    ]
    vm_home = STATE / "vm-home"
    vm_home.mkdir(parents=True, exist_ok=True)
    env.update(HOME=str(vm_home), PATH=os.environ.get("FAKE_SBX_PATH", "/usr/bin:/bin"))
    if not interactive:
        os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
    if cwd:
        os.chdir(cwd)
    os.execvpe(command[0], command, env)


def policy(args):
    action, _, _, name, rule = args[:5]
    record = load(name)
    if record is None:
        return fail(f"error: sandbox '{name}' not found", 1)
    record["rules"].append([action, rule])
    save(name, record)
    return 0


def main(args):
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / "argv.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps(args) + "\n")
    if args and args[0] == "--no-input":
        args = args[1:]
    command, rest = args[0], args[1:]
    if command == "ls":
        if SCENARIO == "signed_out":
            return fail("error: not signed in; run sbx login", 1)
        names = sorted(path.stem for path in SANDBOXES.glob("*.json")) if SANDBOXES.is_dir() else []
        print("\n".join(names) if names else "No sandboxes found")
        return 0
    if command == "create":
        return create(rest)
    if command == "exec":
        return execute(rest)
    if command == "policy":
        return policy(rest)
    if command == "stop":
        record = load(rest[0])
        if record is None:
            return fail(f"error: sandbox '{rest[0]}' not found", 1)
        record["running"] = False
        save(rest[0], record)
        return 0
    if command == "rm":
        for name in [arg for arg in rest if not arg.startswith("-")]:
            (SANDBOXES / f"{name}.json").unlink(missing_ok=True)
            shutil.rmtree(STATE / "opt" / name, ignore_errors=True)
        return 0
    return fail(f"unknown command {command}", 2)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
