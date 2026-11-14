# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A ``git`` shim for tests: log argv and environment as one JSON line, then run the real git.

Usage: ``git_shim.py <log file> <real git> <git arguments...>``. A small ``git`` script
first on the test ``PATH`` calls it.
"""

import json
import os
import sys


def main():
    log_path, real_git, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({"argv": args, "env": dict(os.environ)}) + "\n")
    os.execv(real_git, [real_git, *args])


if __name__ == "__main__":
    main()
