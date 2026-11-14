# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Create an Agent Worker and write its token to a new private file.

The token is written only to ``--token-file`` (mode 0600, created exclusively,
symlinks refused). It is never printed. Plane stores only its SHA-256 hash.
"""

# Python imports
import os
import secrets

# Django imports
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction

# Module imports
from plane.agent.worker_api.authentication import hash_worker_token
from plane.db.models import AgentWorker

TOKEN_PREFIX = "plane_aw_"
MAX_NAME_LENGTH = 64


class Command(BaseCommand):
    help = "Create an Agent Worker and write its token to a new file with mode 0600."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Worker name, for example 'mini'.")
        parser.add_argument("--token-file", required=True, help="Path of a new file that receives the token.")

    def handle(self, *args, **options):
        name = options["name"].strip()
        token_file = os.path.abspath(options["token_file"])
        if not name or len(name) > MAX_NAME_LENGTH:
            raise CommandError(f"The name must have 1 to {MAX_NAME_LENGTH} characters.")
        if AgentWorker.objects.filter(name=name).exists():
            raise CommandError(f"An Agent Worker named '{name}' already exists.")

        try:
            descriptor = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError as error:
            raise CommandError(f"{token_file} already exists. Choose a new path.") from error
        except OSError as error:
            raise CommandError(f"Cannot create {token_file}: {error.strerror}.") from error

        token = TOKEN_PREFIX + secrets.token_urlsafe(32)
        try:
            with transaction.atomic():
                AgentWorker.objects.create(name=name, token_hash=hash_worker_token(token))
                os.fchmod(descriptor, 0o600)
                os.write(descriptor, f"{token}\n".encode())
                os.fsync(descriptor)
        except IntegrityError as error:
            os.close(descriptor)
            os.unlink(token_file)
            raise CommandError(f"An Agent Worker named '{name}' already exists.") from error
        except BaseException:
            os.close(descriptor)
            os.unlink(token_file)
            raise
        os.close(descriptor)
        self.stdout.write(f"Created Agent Worker '{name}'. The token is in {token_file} (mode 0600).")
