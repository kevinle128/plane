# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
from pathlib import Path

import pytest


@pytest.fixture
def private_dir(tmp_path):
    """A directory tree owned by the current user with mode 0700, like a real Worker directory."""
    root = Path(os.path.realpath(tmp_path))
    root.chmod(0o700)
    return root


@pytest.fixture
def token_file(private_dir):
    path = private_dir / "secrets" / "worker-token"
    path.parent.mkdir(mode=0o700)
    path.write_text("plane_aw_test-token-value-0001\n")
    path.chmod(0o600)
    return path
