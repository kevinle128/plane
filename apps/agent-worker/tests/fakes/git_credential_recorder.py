# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A git credential helper for tests: log each call, and answer ``get`` with a fixed credential.

Usage: ``git_credential_recorder.py <log file> <username> <password> <action>``. Each call
appends one JSON line with the action and the attributes that git sent.
"""

import json
import sys


def main():
    log_path, username, password, action = sys.argv[1:5]
    attributes = dict(line.split("=", 1) for line in sys.stdin.read().splitlines() if "=" in line)
    attributes.pop("password", None)
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"action": action, "attributes": attributes}) + "\n")
    if action == "get":
        sys.stdout.write(f"username={username}\npassword={password}\n")


if __name__ == "__main__":
    main()
