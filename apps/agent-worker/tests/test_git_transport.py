# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import ipaddress
import json
import logging
import os
import socket
import stat
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from plane_agent_worker import git_transport
from plane_agent_worker.git_transport import GitTransportError, clone_repository, failure_code, is_blocked_ip
from tests.fakes.git_http_server import REAL_GIT, GitHttpsServer, make_bare_repository, make_ca

FAKES = Path(__file__).parent / "fakes"
TOKEN = "glpat-test-token-7f3a9c1e5b"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost"})
PIPE_HELPER = Path(git_transport.__file__).with_name("git_credential_pipe.py")


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    root = tmp_path_factory.mktemp("certificates")
    return {name: make_ca(root / name, f"Test CA {name}") for name in ("a", "b")}


@pytest.fixture(scope="module")
def project_root(tmp_path_factory):
    root = tmp_path_factory.mktemp("remote")
    make_bare_repository(root)
    return root


@pytest.fixture
def server(certificates, project_root):
    with GitHttpsServer(certificates["a"], project_root, password=TOKEN) as running:
        yield running


class GitRecorder:
    """A git environment with a recording shim first on PATH and a recording system credential helper."""

    def __init__(self, root):
        root.mkdir(mode=0o700)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        self.shim_log = root / "git-shim.jsonl"
        self.helper_log = root / "system-helper.jsonl"
        shim = bin_dir / "git"
        shim.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{FAKES / "git_shim.py"}" "{self.shim_log}" "{REAL_GIT}" "$@"\n'
        )
        shim.chmod(0o755)
        system_config = root / "gitconfig-system"
        recorder = f"{sys.executable} {FAKES / 'git_credential_recorder.py'} {self.helper_log} oauth2 {TOKEN}"
        system_config.write_text(f'[credential]\n\thelper = "!{recorder}"\n')
        home = root / "home"
        home.mkdir()
        self.env = {
            "PATH": os.pathsep.join([str(bin_dir), os.path.dirname(REAL_GIT), "/usr/bin", "/bin"]),
            "HOME": str(home),
            "LANG": "C",
            "GIT_CONFIG_GLOBAL": str(root / "gitconfig-global-missing"),
            "GIT_CONFIG_SYSTEM": str(system_config),
        }

    def calls(self):
        if not self.shim_log.exists():
            return []
        return [json.loads(line) for line in self.shim_log.read_text().splitlines()]

    def helper_calls(self):
        if not self.helper_log.exists():
            return []
        return [json.loads(line) for line in self.helper_log.read_text().splitlines()]


@pytest.fixture
def recorder(private_dir):
    return GitRecorder(private_dir / "git")


@pytest.fixture
def ca_dir(private_dir):
    folder = private_dir / "ca"
    folder.mkdir(mode=0o700)
    return folder


class TokenSource:
    def __init__(self, token=TOKEN):
        self.token = token
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.token


def never_called():
    raise AssertionError("fetch_token must not be called")


def clone(recorder, ca_dir, destination, *, url, host, ca_pem=None, mode="plane_token", fetch=None, **kwargs):
    kwargs.setdefault("allowed_hosts", LOCAL_HOSTS)
    clone_repository(
        clone_url=url,
        host=host,
        credential_mode=mode,
        destination=destination,
        ca_bundle=ca_pem.read_text() if ca_pem else None,
        ca_dir=ca_dir,
        fetch_token=fetch or TokenSource(),
        env=recorder.env,
        **kwargs,
    )


def clone_error(*args, **kwargs):
    with pytest.raises(GitTransportError) as caught:
        clone(*args, **kwargs)
    return caught.value


def option_values(argv):
    return [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "-c"]


def tree_bytes(folder):
    for path in Path(folder).rglob("*"):
        if path.is_file() and not path.is_symlink():
            yield path, path.read_bytes()


# Successful clone ------------------------------------------------------------


def test_plane_token_clone_succeeds_with_ca_bundle(server, certificates, recorder, ca_dir, private_dir):
    destination = private_dir / "clone"
    fetch = TokenSource()

    clone(
        recorder, ca_dir, destination, url=server.url(), host=server.host, ca_pem=certificates["a"].ca_pem, fetch=fetch
    )

    assert (destination / "README.md").read_text() == "main\n"
    assert fetch.calls == 1
    assert any(request.authorization for request in server.requests)
    ca_file = ca_dir / "ca.pem"
    assert ca_file.read_text() == certificates["a"].ca_pem.read_text()
    assert stat.S_IMODE(ca_file.stat().st_mode) == 0o600
    shallow = subprocess.run(
        [REAL_GIT, "-C", str(destination), "rev-parse", "--is-shallow-repository"],
        capture_output=True,
        text=True,
        env=recorder.env,
    )
    assert shallow.stdout.strip() == "true"


def test_clone_uses_the_hardened_git_options(server, certificates, recorder, ca_dir, private_dir):
    host = f"localhost:{server.port}"
    url = f"https://{host}/repo.git"
    clone(recorder, ca_dir, private_dir / "clone", url=url, host=host, ca_pem=certificates["a"].ca_pem)

    calls = recorder.calls()
    assert calls
    for call in calls:
        options = option_values(call["argv"])
        assert "http.followRedirects=false" in options
        assert "core.askPass=" in options
        assert call["env"]["GIT_TERMINAL_PROMPT"] == "0"
    clone_call = next(call for call in calls if "clone" in call["argv"])
    argv = clone_call["argv"]
    assert {"--depth", "1", "--single-branch", "--no-tags"} <= set(argv)
    options = option_values(argv)
    pins = [value for value in options if value.startswith(f"http.curloptResolve=localhost:{server.port}:")]
    assert len(pins) == 1
    assert "127.0.0.1" in pins[0].split(":", 2)[2].split(",")
    assert f"http.https://{host}/.sslCAInfo={ca_dir / 'ca.pem'}" in options
    reset = options.index("credential.helper=")
    pipe = next(index for index, value in enumerate(options) if str(PIPE_HELPER) in value)
    assert reset < pipe
    assert options[pipe].startswith("credential.helper=!")
    assert options[pipe].endswith(f" {host}")


def test_branch_is_cloned_when_set(server, certificates, recorder, ca_dir, private_dir):
    destination = private_dir / "clone"

    clone(
        recorder,
        ca_dir,
        destination,
        url=server.url(),
        host=server.host,
        ca_pem=certificates["a"].ca_pem,
        branch="feature",
    )

    assert (destination / "FEATURE.md").read_text() == "feature\n"


def test_remote_url_is_the_clone_url(server, certificates, recorder, ca_dir, private_dir):
    destination = private_dir / "clone"

    clone(recorder, ca_dir, destination, url=server.url(), host=server.host, ca_pem=certificates["a"].ca_pem)

    remote = subprocess.run(
        [REAL_GIT, "-C", str(destination), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        env=recorder.env,
    )
    assert remote.stdout.strip() == server.url()
    assert any("set-url" in call["argv"] for call in recorder.calls())


# Token secrecy ----------------------------------------------------------------


def test_token_is_absent_from_argv_env_config_files_and_logs(
    server, certificates, recorder, ca_dir, private_dir, caplog
):
    caplog.set_level(logging.DEBUG)
    destination = private_dir / "clone"

    clone(recorder, ca_dir, destination, url=server.url(), host=server.host, ca_pem=certificates["a"].ca_pem)

    calls = recorder.calls()
    assert calls
    for call in calls:
        assert all(TOKEN not in value for value in call["argv"])
        assert all(TOKEN not in name and TOKEN not in value for name, value in call["env"].items())
    assert TOKEN not in (destination / ".git" / "config").read_text()
    for path, content in [*tree_bytes(destination), *tree_bytes(ca_dir)]:
        assert TOKEN.encode() not in content, path
    assert TOKEN not in caplog.text


def test_system_credential_helper_never_runs_in_plane_token_mode(server, certificates, recorder, ca_dir, private_dir):
    clone(recorder, ca_dir, private_dir / "clone", url=server.url(), host=server.host, ca_pem=certificates["a"].ca_pem)

    assert recorder.helper_calls() == []


def test_system_credential_helper_never_runs_when_the_token_is_rejected(
    certificates, project_root, recorder, ca_dir, private_dir
):
    with GitHttpsServer(certificates["a"], project_root, password="another-token") as other:
        error = clone_error(
            recorder, ca_dir, private_dir / "clone", url=other.url(), host=other.host, ca_pem=certificates["a"].ca_pem
        )

    assert error.code == "git_auth_failed"
    assert recorder.helper_calls() == []


def test_pipe_helper_answers_only_get_for_https_and_the_expected_host():
    def ask(action, request, token=TOKEN):
        read_end, write_end = os.pipe()
        os.write(write_end, token.encode())
        os.close(write_end)
        try:
            result = subprocess.run(
                [sys.executable, str(PIPE_HELPER), str(read_end), "git.example.com:8443", action],
                input=request,
                capture_output=True,
                text=True,
                pass_fds=(read_end,),
                timeout=10,
            )
        finally:
            os.close(read_end)
        return result.stdout

    assert ask("get", "protocol=https\nhost=git.example.com:8443\n\n") == f"username=oauth2\npassword={TOKEN}\n"
    assert ask("get", "protocol=https\nhost=other.example.com:8443\n\n") == ""
    assert ask("get", "protocol=https\nhost=git.example.com\n\n") == ""
    assert ask("get", "protocol=http\nhost=git.example.com:8443\n\n") == ""
    assert ask("store", "protocol=https\nhost=git.example.com:8443\nusername=oauth2\npassword=x\n\n") == ""
    assert ask("erase", "protocol=https\nhost=git.example.com:8443\n\n") == ""


# CA bundle scope ---------------------------------------------------------------


def test_clone_without_ca_bundle_fails_with_tls_error(server, recorder, ca_dir, private_dir):
    destination = private_dir / "clone"

    error = clone_error(recorder, ca_dir, destination, url=server.url(), host=server.host)

    assert error.code == "git_tls_failed"
    assert not destination.exists()


def test_ca_bundle_of_another_host_does_not_apply(certificates, project_root, recorder, ca_dir, private_dir):
    with GitHttpsServer(certificates["b"], project_root, password=TOKEN) as other:
        error = clone_error(
            recorder, ca_dir, private_dir / "clone", url=other.url(), host=other.host, ca_pem=certificates["a"].ca_pem
        )

    assert error.code == "git_tls_failed"


def test_ca_bundle_option_does_not_apply_to_another_port(
    server, certificates, project_root, recorder, ca_dir, private_dir
):
    clone(recorder, ca_dir, private_dir / "clone", url=server.url(), host=server.host, ca_pem=certificates["a"].ca_pem)
    clone_call = next(call for call in recorder.calls() if "clone" in call["argv"])
    ca_options = [value for value in option_values(clone_call["argv"]) if "sslCAInfo" in value]
    assert ca_options

    # The second server uses a certificate of the same CA, so only the URL scope of the option can refuse it.
    with GitHttpsServer(certificates["a"], project_root, password=TOKEN) as other:
        options = [part for value in ca_options for part in ("-c", value)]
        result = subprocess.run(
            [REAL_GIT, *options, "ls-remote", other.url()],
            capture_output=True,
            text=True,
            env={**recorder.env, "GIT_TERMINAL_PROMPT": "0"},
            timeout=60,
        )

    assert result.returncode != 0
    assert failure_code(result.stderr) == "git_tls_failed"


# Redirects -----------------------------------------------------------------------


def test_redirect_fails_and_the_second_host_gets_no_token(certificates, project_root, recorder, ca_dir, private_dir):
    with GitHttpsServer(certificates["a"], project_root, password=TOKEN) as target:
        with GitHttpsServer(certificates["a"], redirect_to=f"https://{target.host}") as redirecting:
            error = clone_error(
                recorder,
                ca_dir,
                private_dir / "clone",
                url=redirecting.url(),
                host=redirecting.host,
                ca_pem=certificates["a"].ca_pem,
            )

    assert error.code.startswith("git_")
    assert redirecting.requests
    assert all(request.authorization is None for request in target.requests)
    assert not (private_dir / "clone").exists()


# Blocked hosts --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "host"),
    [
        ("https://127.0.0.1:8443/repo.git", "127.0.0.1:8443"),
        ("https://localhost/repo.git", "localhost"),
        ("https://10.1.2.3/repo.git", "10.1.2.3"),
        ("https://[::1]/repo.git", "[::1]"),
    ],
)
def test_blocked_host_is_refused_before_git_runs(url, host, recorder, ca_dir, private_dir):
    fetch = TokenSource()

    error = clone_error(
        recorder, ca_dir, private_dir / "clone", url=url, host=host, fetch=fetch, allowed_hosts=frozenset()
    )

    assert error.code == "git_host_blocked"
    assert recorder.calls() == []
    assert fetch.calls == 0


def test_allowed_ip_network_lets_a_private_address_through(server, certificates, recorder, ca_dir, private_dir):
    destination = private_dir / "clone"

    clone(
        recorder,
        ca_dir,
        destination,
        url=server.url(),
        host=server.host,
        ca_pem=certificates["a"].ca_pem,
        allowed_hosts=frozenset(),
        allowed_ips=(ipaddress.ip_network("127.0.0.0/8"),),
    )

    assert (destination / "README.md").exists()


def test_non_https_url_is_refused_before_git_runs(recorder, ca_dir, private_dir):
    error = clone_error(
        recorder, ca_dir, private_dir / "clone", url="http://127.0.0.1:8080/repo.git", host="127.0.0.1:8080"
    )

    assert error.code == "git_host_blocked"
    assert recorder.calls() == []


@pytest.mark.parametrize(
    ("address", "blocked"),
    [
        ("127.0.0.1", True),
        ("10.0.0.1", True),
        ("192.168.1.1", True),
        ("169.254.169.254", True),
        ("100.64.0.1", True),
        ("0.0.0.0", True),
        ("::1", True),
        ("::ffff:10.0.0.1", True),
        ("64:ff9b::7f00:1", True),
        ("2002:7f00:1::", True),
        ("8.8.8.8", False),
        ("2606:4700:4700::1111", False),
    ],
)
def test_blocked_address_rule(address, blocked):
    assert is_blocked_ip(ipaddress.ip_address(address)) is blocked


# Failure codes ----------------------------------------------------------------------


def test_unknown_host_fails_with_dns_error(recorder, ca_dir, private_dir):
    error = clone_error(
        recorder,
        ca_dir,
        private_dir / "clone",
        url="https://unknown-host.invalid/repo.git",
        host="unknown-host.invalid",
    )

    assert error.code == "git_dns_failed"
    assert recorder.calls() == []


def test_closed_port_fails_as_unreachable(recorder, ca_dir, private_dir):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    destination = private_dir / "clone"

    error = clone_error(
        recorder, ca_dir, destination, url=f"https://127.0.0.1:{port}/repo.git", host=f"127.0.0.1:{port}"
    )

    assert error.code == "git_unreachable"
    assert not destination.exists()


def test_wrong_token_fails_with_auth_error(server, certificates, recorder, ca_dir, private_dir):
    destination = private_dir / "clone"

    error = clone_error(
        recorder,
        ca_dir,
        destination,
        url=server.url(),
        host=server.host,
        ca_pem=certificates["a"].ca_pem,
        fetch=TokenSource("glpat-wrong-token"),
    )

    assert error.code == "git_auth_failed"
    assert "glpat-wrong-token" not in error.detail
    assert not destination.exists()


def test_missing_repository_fails_with_not_found(server, certificates, recorder, ca_dir, private_dir):
    destination = private_dir / "clone"

    error = clone_error(
        recorder, ca_dir, destination, url=server.url("missing.git"), host=server.host, ca_pem=certificates["a"].ca_pem
    )

    assert error.code == "git_not_found"
    assert not destination.exists()


def test_hanging_server_fails_as_unreachable(monkeypatch, recorder, ca_dir, private_dir):
    monkeypatch.setattr(git_transport, "CLONE_TIMEOUT_SECONDS", 2)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    accepted = []
    thread = threading.Thread(target=lambda: accepted.append(listener.accept()), daemon=True)
    thread.start()
    port = listener.getsockname()[1]
    destination = private_dir / "clone"
    try:
        error = clone_error(
            recorder, ca_dir, destination, url=f"https://127.0.0.1:{port}/repo.git", host=f"127.0.0.1:{port}"
        )
    finally:
        for connection, _ in accepted:
            connection.close()
        listener.close()

    assert error.code == "git_unreachable"
    assert not destination.exists()


@pytest.mark.parametrize(
    ("stderr", "code"),
    [
        ("fatal: unable to access 'https://h/r/': Could not resolve host: h", "git_dns_failed"),
        (
            "fatal: unable to access 'https://h:1/r/': Failed to connect to h port 1: Connection refused",
            "git_unreachable",
        ),
        (
            "fatal: unable to access 'https://h/r/': Connection timed out after 300000 milliseconds",
            "git_unreachable",
        ),
        ("fatal: unable to access 'https://h/r/': Couldn't connect to server", "git_unreachable"),
        (
            "fatal: unable to access 'https://h/r/': SSL certificate problem: self-signed certificate",
            "git_tls_failed",
        ),
        (
            "fatal: unable to access 'https://h/r/': server certificate verification failed. CAfile: none",
            "git_tls_failed",
        ),
        (
            "fatal: unable to access 'https://h/r/': server verification failed: certificate signer not trusted. "
            "(CAfile: /etc/ssl/certs/ca-certificates.crt CRLfile: none)",
            "git_tls_failed",
        ),
        ("remote: HTTP Basic: Access denied\nfatal: Authentication failed for 'https://h/r.git/'", "git_auth_failed"),
        ("fatal: unable to access 'https://h/r/': The requested URL returned error: 403", "git_auth_failed"),
        ("fatal: could not read Username for 'https://h': terminal prompts disabled", "git_auth_failed"),
        ("fatal: repository 'https://h:40123/r.git/' not found", "git_not_found"),
        ("remote: Repository not found.", "git_not_found"),
        ("fatal: unable to access 'https://h/r/': The requested URL returned error: 404", "git_not_found"),
        ("fatal: unable to access 'https://h:40123/r.git/': The requested URL returned error: 302", "git_failed"),
        ("fatal: something else", "git_failed"),
    ],
)
def test_failure_code_mapping(stderr, code):
    assert failure_code(stderr) == code


# Host mode and input checks -------------------------------------------------------------


def test_host_mode_keeps_the_system_helper_and_never_fetches_a_token(
    server, certificates, recorder, ca_dir, private_dir
):
    destination = private_dir / "clone"

    clone(
        recorder,
        ca_dir,
        destination,
        url=server.url(),
        host=server.host,
        ca_pem=certificates["a"].ca_pem,
        mode="host",
        fetch=never_called,
    )

    assert (destination / "README.md").exists()
    assert [call["action"] for call in recorder.helper_calls()] == ["get", "store"]
    for call in recorder.calls():
        options = option_values(call["argv"])
        assert not any(value.startswith("credential.helper") for value in options)
        assert "http.followRedirects=false" in options


def test_existing_destination_is_refused_and_kept(recorder, ca_dir, private_dir):
    destination = private_dir / "clone"
    destination.mkdir()
    (destination / "keep").write_text("x")

    error = clone_error(recorder, ca_dir, destination, url="https://127.0.0.1:8443/repo.git", host="127.0.0.1:8443")

    assert error.code == "git_failed"
    assert (destination / "keep").exists()
    assert recorder.calls() == []


def test_host_that_does_not_match_the_url_is_refused(recorder, ca_dir, private_dir):
    error = clone_error(
        recorder, ca_dir, private_dir / "clone", url="https://127.0.0.1:8443/repo.git", host="127.0.0.1"
    )

    assert error.code == "git_failed"
    assert recorder.calls() == []


def test_url_with_credentials_is_refused(recorder, ca_dir, private_dir):
    error = clone_error(
        recorder,
        ca_dir,
        private_dir / "clone",
        url=f"https://oauth2:{TOKEN}@127.0.0.1:8443/repo.git",
        host="127.0.0.1:8443",
    )

    assert error.code == "git_failed"
    assert TOKEN not in error.detail
    assert recorder.calls() == []


@pytest.mark.parametrize("token", ["", "abc\nhost=evil.example.com", "abc\x00def"])
def test_malformed_token_is_refused_before_git_runs(token, recorder, ca_dir, private_dir):
    error = clone_error(
        recorder,
        ca_dir,
        private_dir / "clone",
        url="https://127.0.0.1:8443/repo.git",
        host="127.0.0.1:8443",
        fetch=TokenSource(token),
    )

    assert error.code == "git_auth_failed"
    assert recorder.calls() == []
