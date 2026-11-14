# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A local HTTPS git remote for the git transport tests.

``make_ca`` creates a throwaway CA and a server certificate for 127.0.0.1 with the
``openssl`` CLI. ``GitHttpsServer`` serves the bare repositories under a folder through
``git http-backend`` with Basic auth, or answers every request with a 302 to another URL.
Each server records the requests it receives.
"""

import base64
import http.server
import os
import shutil
import ssl
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

REAL_GIT = shutil.which("git")

_CA_CONFIG = """[req]
distinguished_name = dn
prompt = no
[dn]
CN = {name}
[v3_ca]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
subjectKeyIdentifier = hash
"""
_SERVER_CONFIG = """[req]
distinguished_name = dn
prompt = no
[dn]
CN = 127.0.0.1
"""
_SERVER_EXTENSIONS = """basicConstraints = CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = IP:127.0.0.1,DNS:localhost
"""


@dataclass(frozen=True)
class Certificates:
    ca_pem: Path
    server_cert: Path
    server_key: Path


def _openssl(*args, cwd):
    subprocess.run(["openssl", *args], cwd=cwd, check=True, capture_output=True)


def make_ca(folder, name):
    """A CA and a server certificate for 127.0.0.1 signed by it, under ``folder``."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "ca.cnf").write_text(_CA_CONFIG.format(name=name))
    (folder / "server.cnf").write_text(_SERVER_CONFIG)
    (folder / "server.ext").write_text(_SERVER_EXTENSIONS)
    _openssl(
        "req", "-x509", "-new", "-nodes", "-newkey", "rsa:2048", "-days", "2",
        "-keyout", "ca.key", "-out", "ca.pem", "-config", "ca.cnf", "-extensions", "v3_ca",
        cwd=folder,
    )  # fmt: skip
    _openssl(
        "req", "-new", "-nodes", "-newkey", "rsa:2048",
        "-keyout", "server.key", "-out", "server.csr", "-config", "server.cnf",
        cwd=folder,
    )  # fmt: skip
    _openssl(
        "x509", "-req", "-in", "server.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial",
        "-days", "2", "-extfile", "server.ext", "-out", "server.pem",
        cwd=folder,
    )  # fmt: skip
    return Certificates(folder / "ca.pem", folder / "server.pem", folder / "server.key")


def make_bare_repository(root, name="repo.git"):
    """A bare repository with one commit on ``main`` and one on ``feature``."""
    root = Path(root)
    bare = root / name
    work = root / f"{name}.work"
    git_env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(root),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }

    def git(*args, cwd=root):
        subprocess.run([REAL_GIT, *args], cwd=cwd, env=git_env, check=True, capture_output=True)

    git("init", "-q", "--bare", "-b", "main", str(bare))
    git("init", "-q", "-b", "main", str(work))
    (work / "README.md").write_text("main\n")
    git("add", "README.md", cwd=work)
    git("commit", "-q", "-m", "main", cwd=work)
    git("checkout", "-q", "-b", "feature", cwd=work)
    (work / "FEATURE.md").write_text("feature\n")
    git("add", "FEATURE.md", cwd=work)
    git("commit", "-q", "-m", "feature", cwd=work)
    git("push", "-q", str(bare), "main", "feature", cwd=work)
    shutil.rmtree(work)
    return bare


@dataclass
class Request:
    method: str
    path: str
    authorization: str | None


@dataclass
class GitHttpsServer:
    """Serve ``project_root`` over HTTPS on 127.0.0.1, or redirect every request when ``redirect_to`` is set."""

    certificates: Certificates
    project_root: Path | None = None
    username: str = "oauth2"
    password: str = ""
    redirect_to: str | None = None
    requests: list = field(default_factory=list)

    def __post_init__(self):
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self._handle()

            def do_POST(self):
                self._handle()

            def _handle(self):
                authorization = self.headers.get("Authorization")
                server.requests.append(Request(self.command, self.path, authorization))
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                if server.redirect_to:
                    self.send_response(302)
                    self.send_header("Location", server.redirect_to + self.path)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                expected = "Basic " + base64.b64encode(f"{server.username}:{server.password}".encode()).decode()
                if authorization != expected:
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="test"')
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self._backend(body)

            def _backend(self, body):
                path, _, query = self.path.partition("?")
                env = {
                    "PATH": os.environ.get("PATH", ""),
                    "GIT_PROJECT_ROOT": str(server.project_root),
                    "GIT_HTTP_EXPORT_ALL": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "PATH_INFO": path,
                    "QUERY_STRING": query,
                    "REQUEST_METHOD": self.command,
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                    "CONTENT_LENGTH": str(len(body)),
                    "REMOTE_USER": server.username,
                    "REMOTE_ADDR": "127.0.0.1",
                    "GIT_PROTOCOL": self.headers.get("Git-Protocol", ""),
                    "HTTP_CONTENT_ENCODING": self.headers.get("Content-Encoding", ""),
                }
                result = subprocess.run([REAL_GIT, "http-backend"], input=body, env=env, capture_output=True)
                head, _, payload = result.stdout.partition(b"\r\n\r\n")
                status = 200
                headers = []
                for line in head.decode("latin-1").split("\r\n"):
                    name, _, value = line.partition(":")
                    if name.lower() == "status":
                        status = int(value.strip().split()[0])
                    elif name:
                        headers.append((name, value.strip()))
                self.send_response(status)
                for name, value in headers:
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        class Server(http.server.ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                # A client that rejects the certificate ends the handshake; the tests expect that.
                pass

        self._server = Server(("127.0.0.1", 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.certificates.server_cert, self.certificates.server_key)
        self._server.socket = context.wrap_socket(self._server.socket, server_side=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def port(self):
        return self._server.server_address[1]

    @property
    def host(self):
        return f"127.0.0.1:{self.port}"

    def url(self, name="repo.git"):
        return f"https://{self.host}/{name}"

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
