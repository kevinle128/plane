# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Git credential helper that reads the fetch token from an inherited pipe.

Git runs it as ``<python> git_credential_pipe.py <fd> <host> <action>``. The Worker
writes the token to the pipe and closes the write end before git starts, so the token
is never in argv, the environment or a file.

The helper answers only the ``get`` action, and only when git asks for ``https`` and
the expected host (with ``:port`` when the port is not 443). For any other request it
prints nothing, so git has no credential for a redirect target or another host.

This file runs as a separate script and uses the standard library only.
"""

import os
import sys

USERNAME = "oauth2"


def read_request(stream):
    attributes = {}
    for line in stream:
        line = line.rstrip("\n")
        if not line:
            break
        name, _, value = line.partition("=")
        attributes[name] = value
    return attributes


def read_token(fd):
    chunks = []
    while chunk := os.read(fd, 4096):
        chunks.append(chunk)
    return b"".join(chunks).decode()


def main(argv):
    if len(argv) != 3:
        return 1
    fd, expected_host, action = int(argv[0]), argv[1], argv[2]
    request = read_request(sys.stdin)
    if action != "get" or request.get("protocol") != "https" or request.get("host") != expected_host:
        return 0
    token = read_token(fd)
    if token:
        sys.stdout.write(f"username={USERNAME}\npassword={token}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
