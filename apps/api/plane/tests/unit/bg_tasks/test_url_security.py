# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
SSRF-protection tests for the webhook + link-unfurling clusters (advisories A/B/C):

  A — incomplete private-IP validation  -> is_blocked_ip hardening
  B — DNS-rebinding TOCTOU              -> connection pinned to the validated IP
  C — SSRF via HTTP redirect following  -> redirects re-resolved/re-validated/re-pinned
"""

import ipaddress

import pytest
import requests
from unittest.mock import MagicMock, patch

from plane.utils.ip_address import is_blocked_ip, resolve_and_validate, validate_url
from plane.utils.url_security import (
    PinnedIPAdapter,
    pinned_fetch,
    pinned_fetch_following_redirects,
)


def _addr(ip):
    """Build a single getaddrinfo-style result tuple for an IP string."""
    family = 6 if ":" in ip else 2
    return (family, None, None, None, (ip, 0))


def _resp(status_code=200, headers=None, content=b"OK"):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.content = content
    return resp


# ---------------------------------------------------------------------------
# Cluster A — robust IP classification (verified on Python 3.12 semantics)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestIsBlockedIp:
    @pytest.mark.parametrize(
        "ip",
        [
            "127.0.0.1",  # loopback
            "10.0.0.1",  # private
            "192.168.1.1",  # private
            "172.16.0.1",  # private
            "169.254.169.254",  # link-local / cloud metadata
            "0.0.0.0",  # unspecified
            "100.64.0.1",  # CGNAT / shared (NOT is_private on py3.12!)
            "224.0.0.1",  # multicast
            "239.255.255.250",  # SSDP multicast
            "255.255.255.255",  # limited broadcast
            "::1",  # IPv6 loopback
            "fe80::1",  # IPv6 link-local
            "fc00::1",  # IPv6 unique-local
            "ff02::1",  # IPv6 multicast
            "::ffff:127.0.0.1",  # IPv4-mapped loopback
            "::ffff:169.254.169.254",  # IPv4-mapped metadata
            "::ffff:10.0.0.1",  # IPv4-mapped private
            "64:ff9b::7f00:1",  # NAT64 well-known prefix embedding 127.0.0.1
            "64:ff9b::a9fe:a9fe",  # NAT64 well-known prefix embedding 169.254.169.254
            "64:ff9b:1::7f00:1",  # NAT64 local-use prefix (RFC 8215, /48)
            "64:ff9b:1:0100::1",  # NAT64 local-use prefix, outside the /96 subset
            "2002:7f00:1::",  # 6to4 embedding 127.0.0.1
            "2002:a00:1::",  # 6to4 embedding 10.0.0.1
        ],
    )
    def test_blocks_internal(self, ip):
        assert is_blocked_ip(ipaddress.ip_address(ip)) is True

    @pytest.mark.parametrize(
        "ip",
        [
            "8.8.8.8",
            "93.184.216.34",
            "1.1.1.1",
            "2606:4700:4700::1111",  # public IPv6 (Cloudflare)
            "2001:4860:4860::8888",  # public IPv6 (Google)
        ],
    )
    def test_allows_public(self, ip):
        assert is_blocked_ip(ipaddress.ip_address(ip)) is False


# ---------------------------------------------------------------------------
# resolve_and_validate — resolution + validation, returns IPs to pin
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestResolveAndValidate:
    def test_returns_public_ips(self):
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.return_value = [_addr("93.184.216.34")]
            assert resolve_and_validate("example.com") == ["93.184.216.34"]

    def test_raises_on_private(self):
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.return_value = [_addr("10.0.0.1")]
            with pytest.raises(ValueError, match="private/internal"):
                resolve_and_validate("internal.example.com")

    def test_raises_if_any_resolved_ip_is_private(self):
        # A hostname that resolves to BOTH a public and a private IP must fail
        # closed — an attacker could otherwise steer the connection to the
        # private one.
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.return_value = [_addr("93.184.216.34"), _addr("127.0.0.1")]
            with pytest.raises(ValueError, match="private/internal"):
                resolve_and_validate("rebinder.example.com")

    def test_allowlist_permits_private(self):
        allowed = [ipaddress.ip_network("10.0.0.0/8")]
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.return_value = [_addr("10.0.0.5")]
            assert resolve_and_validate("internal", allowed_ips=allowed) == ["10.0.0.5"]

    def test_unresolvable_raises(self):
        import socket as _socket

        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.side_effect = _socket.gaierror()
            with pytest.raises(ValueError, match="could not be resolved"):
                resolve_and_validate("nope.invalid")


# ---------------------------------------------------------------------------
# Cluster B — connection pinned to the validated IP (DNS-rebinding TOCTOU)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPinnedFetch:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_connects_to_validated_ip_not_hostname(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("POST", "https://example.com/hook", json={"a": 1})

        # The socket target is the validated IP literal — there is no second
        # DNS lookup, so a rebind between validation and connection is
        # impossible.
        method, url = session.request.call_args.args
        kwargs = session.request.call_args.kwargs
        assert method == "POST"
        assert url == "https://93.184.216.34:443/hook"
        # Host header + TLS SNI still target the real hostname.
        assert kwargs["headers"]["Host"] == "example.com"
        assert kwargs["allow_redirects"] is False
        assert kwargs["verify"] is True
        assert kwargs["json"] == {"a": 1}
        # Ambient proxy/env must not be honoured (would bypass pinning).
        assert session.trust_env is False
        assert kwargs["proxies"] == {"http": None, "https": None}

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_non_default_port_in_host_header(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("GET", "http://example.com:8080/x")

        _, url = session.request.call_args.args
        kwargs = session.request.call_args.kwargs
        assert url == "http://93.184.216.34:8080/x"
        assert kwargs["headers"]["Host"] == "example.com:8080"

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_ipv6_validated_ip_is_bracketed(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["2606:4700:4700::1111"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("GET", "https://example.com/x")

        _, url = session.request.call_args.args
        assert url == "https://[2606:4700:4700::1111]:443/x"

    @patch("plane.utils.url_security.resolve_and_validate")
    def test_blocked_target_raises_before_any_request(self, mock_resolve):
        mock_resolve.side_effect = ValueError(
            "Access to private/internal networks is not allowed"
        )
        with pytest.raises(ValueError, match="private/internal"):
            pinned_fetch("POST", "https://attacker.com/hook")

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_tries_next_ip_on_connection_error(self, mock_resolve, mock_session_cls):
        # Dual-stack host: first validated IP is unreachable, second works.
        mock_resolve.return_value = ["93.184.216.34", "93.184.216.35"]
        session = mock_session_cls.return_value
        session.request.side_effect = [
            requests.ConnectionError("down"),
            _resp(200),
        ]
        resp = pinned_fetch("GET", "https://example.com/x")
        assert resp.status_code == 200
        assert session.request.call_count == 2

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_allowed_host_skips_block_check_but_still_pins(self, mock_resolve, mock_session_cls):
        # Trusted host (e.g. internal docker service) whose IP is private: the
        # block check is skipped, but the connection is STILL pinned to the
        # resolved IP so it cannot be rebound to a different internal target.
        mock_resolve.return_value = ["172.18.0.5"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch(
            "POST",
            "http://silo:3000/hook",
            allowed_hosts=["silo"],
            json={"x": 1},
        )

        # Resolution happens with require_safe=False (trusted, skip block check).
        assert mock_resolve.call_args.kwargs.get("require_safe") is False
        # ...but the connection is pinned to the resolved IP literal, Host=silo.
        _, url = session.request.call_args.args
        assert url == "http://172.18.0.5:3000/hook"
        assert session.request.call_args.kwargs["headers"]["Host"] == "silo:3000"
        assert session.request.call_args.kwargs["allow_redirects"] is False


# ---------------------------------------------------------------------------
# Cluster C — redirects re-resolved / re-validated / re-pinned each hop
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPinnedFetchRedirects:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_no_redirect_returns_response(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        resp, final = pinned_fetch_following_redirects("GET", "https://example.com/a")
        assert resp.status_code == 200
        assert final == "https://example.com/a"

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_follows_and_revalidates_each_hop(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.side_effect = [
            _resp(301, headers={"Location": "https://other.com/page"}),
            _resp(200),
        ]

        resp, final = pinned_fetch_following_redirects("GET", "https://example.com/a")
        assert resp.status_code == 200
        assert final == "https://other.com/page"
        # Re-resolved (and thus re-validated + re-pinned) on each hop.
        assert mock_resolve.call_count == 2
        assert mock_resolve.call_args_list[0].args[0] == "example.com"
        assert mock_resolve.call_args_list[1].args[0] == "other.com"

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_blocks_redirect_to_private_ip(self, mock_resolve, mock_session_cls):
        # First hop resolves public; redirect target resolves private -> blocked
        mock_resolve.side_effect = [
            ["93.184.216.34"],
            ValueError("Access to private/internal networks is not allowed"),
        ]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(
            302, headers={"Location": "http://169.254.169.254/latest/meta-data/"}
        )
        with pytest.raises(ValueError, match="private/internal"):
            pinned_fetch_following_redirects("GET", "https://evil.com/r")

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_too_many_redirects(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(
            302, headers={"Location": "https://example.com/loop"}
        )
        with pytest.raises(requests.TooManyRedirects):
            pinned_fetch_following_redirects(
                "GET", "https://example.com/start", max_redirects=3
            )


# ---------------------------------------------------------------------------
# PinnedIPAdapter — TLS server_hostname injection (cert verified vs hostname)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPinnedIPAdapter:
    def test_injects_server_hostname_into_pool(self):
        adapter = PinnedIPAdapter(server_hostname="example.com")
        adapter.build_connection_pool_key_attributes = MagicMock(
            return_value=({"scheme": "https", "host": "93.184.216.34", "port": 443}, {})
        )
        adapter.poolmanager = MagicMock()

        request = MagicMock()
        adapter.get_connection_with_tls_context(request, verify=True)

        _, kwargs = adapter.poolmanager.connection_from_host.call_args
        assert kwargs["pool_kwargs"]["server_hostname"] == "example.com"


# ---------------------------------------------------------------------------
# validate_url — create/update-time defense in depth still rejects bypasses
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestValidateUrlHardening:
    @pytest.mark.parametrize("ip", ["100.64.0.1", "224.0.0.1", "0.0.0.0"])
    def test_rejects_newly_covered_ranges(self, ip):
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.return_value = [_addr(ip)]
            with pytest.raises(ValueError, match="private/internal"):
                validate_url("http://attacker.example.com")


# ---------------------------------------------------------------------------
# Review-feedback fixes (PR #9163)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestReviewFixes:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_url_embedded_credentials_become_basic_auth(self, mock_resolve, mock_session_cls):
        # user:pass@host -> Basic Auth preserved as auth=, userinfo stripped from URL
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("GET", "https://user:p%40ss@example.com/hook")

        _, url = session.request.call_args.args
        kwargs = session.request.call_args.kwargs
        assert url == "https://93.184.216.34:443/hook"  # no userinfo in the IP URL
        assert kwargs["auth"] == ("user", "p@ss")  # percent-decoded
        assert kwargs["headers"]["Host"] == "example.com"

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_no_credentials_passes_auth_none(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)
        pinned_fetch("GET", "https://example.com/x")
        assert session.request.call_args.kwargs["auth"] is None

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_ipv6_literal_host_header_is_bracketed(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["2606:4700:4700::1111"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("GET", "https://[2606:4700:4700::1111]/x")

        kwargs = session.request.call_args.kwargs
        assert kwargs["headers"]["Host"] == "[2606:4700:4700::1111]"

    def test_idna_unicode_error_is_treated_as_unresolvable(self):
        # getaddrinfo can raise UnicodeError (IDNA) before any lookup; it must
        # surface as ValueError so webhook_send_task records a URL rejection.
        with patch("plane.utils.ip_address.socket.getaddrinfo") as dns:
            dns.side_effect = UnicodeError("label empty or too long")
            with pytest.raises(ValueError, match="could not be resolved"):
                resolve_and_validate("xn--bad-name")

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_stream_defers_session_close_until_response_close(self, mock_resolve, mock_session_cls):
        # With stream=True the size cap can bound memory only if the session
        # stays open until the body is read; closing the response closes it.
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        resp = _resp(200)
        session.request.return_value = resp

        out = pinned_fetch("GET", "https://cdn.example.com/a.png", stream=True)

        assert session.request.call_args.kwargs["stream"] is True
        session.close.assert_not_called()  # deferred
        out.close()
        session.close.assert_called_once()


# ---------------------------------------------------------------------------
# Per-call trust for a custom CA bundle (Git provider connections)
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestPinnedFetchVerify:
    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_default_still_verifies_against_system_trust(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("GET", "https://example.com/x")

        assert session.request.call_args.kwargs["verify"] is True

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_ca_bundle_path_reaches_the_request(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("GET", "https://git.example.com/api/v4/version", verify="/tmp/plane-ca/abc.pem")

        assert session.request.call_args.kwargs["verify"] == "/tmp/plane-ca/abc.pem"

    @patch("plane.utils.url_security.requests.Session")
    @patch("plane.utils.url_security.resolve_and_validate")
    def test_a_second_host_in_the_same_process_keeps_system_trust(self, mock_resolve, mock_session_cls):
        mock_resolve.return_value = ["93.184.216.34"]
        session = mock_session_cls.return_value
        session.request.return_value = _resp(200)

        pinned_fetch("GET", "https://git.example.com/api/v4/version", verify="/tmp/plane-ca/abc.pem")
        pinned_fetch("GET", "https://other.example.com/hook")

        verifies = [call.kwargs["verify"] for call in session.request.call_args_list]
        assert verifies == ["/tmp/plane-ca/abc.pem", True]


def _streamed(status_code=200, headers=None, chunks=(b"{}",)):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {"Content-Type": "application/json"}
    response.iter_content.return_value = iter(chunks)
    return response


@pytest.mark.unit
class TestAgentGitHttpSeam:
    """Transport failures of the Git provider seam map to fixed reason codes."""

    def _request(self, **kwargs):
        from plane.agent.git_providers import http

        return http.request("GET", "https://git.example.com/api/v4/version", provider="gitlab", **kwargs)

    @pytest.mark.parametrize(
        "error, code, detail",
        [
            (ValueError("Hostname could not be resolved"), "gitlab_url_not_allowed_or_unresolved", ""),
            (
                ValueError("Access to private/internal networks is not allowed"),
                "gitlab_url_not_allowed_or_unresolved",
                "",
            ),
            (requests.exceptions.ConnectTimeout("timed out"), "gitlab_url_unreachable", "timeout"),
            (requests.exceptions.ReadTimeout("timed out"), "gitlab_url_unreachable", "timeout"),
            (requests.exceptions.ConnectionError("refused"), "gitlab_url_unreachable", "connection"),
            (requests.exceptions.SSLError("certificate verify failed"), "gitlab_tls_failed", ""),
        ],
        ids=["dns", "private-ip", "connect-timeout", "read-timeout", "refused", "tls"],
    )
    def test_transport_failures_map_to_codes(self, error, code, detail):
        from plane.agent.git_providers.base import ProviderError

        with patch("plane.agent.git_providers.http.pinned_fetch", side_effect=error):
            with pytest.raises(ProviderError) as raised:
                self._request()

        assert (raised.value.code, raised.value.detail) == (code, detail)

    def test_redirect_is_refused_and_shows_only_scheme_and_host(self):
        from plane.agent.git_providers.base import ProviderError

        response = _streamed(302, {"Location": "http://10.0.0.5/admin?private_token=leak"})
        with patch("plane.agent.git_providers.http.pinned_fetch", return_value=response):
            with pytest.raises(ProviderError) as raised:
                self._request()

        assert (raised.value.code, raised.value.detail) == ("gitlab_url_redirected", "http://10.0.0.5")
        response.close.assert_called_once()

    def test_body_over_one_mebibyte_is_refused(self):
        from plane.agent.git_providers.base import ProviderError

        chunk = b"x" * (64 * 1024)
        response = _streamed(chunks=[chunk] * 17)
        with patch("plane.agent.git_providers.http.pinned_fetch", return_value=response):
            with pytest.raises(ProviderError) as raised:
                self._request()

        assert (raised.value.code, raised.value.detail) == ("gitlab_unexpected_response", "response_too_large")
        response.close.assert_called_once()

    def test_body_at_the_limit_is_read(self):
        chunk = b"x" * (64 * 1024)
        response = _streamed(chunks=[chunk] * 16)
        with patch("plane.agent.git_providers.http.pinned_fetch", return_value=response):
            result = self._request()

        assert len(result.content) == 1024 * 1024

    def test_spent_budget_makes_no_request(self):
        from plane.agent.git_providers import http
        from plane.agent.git_providers.base import ProviderError

        with patch("plane.agent.git_providers.http.pinned_fetch") as fetch:
            with pytest.raises(ProviderError) as raised:
                self._request(deadline=http.new_deadline(-1))

        assert (raised.value.code, raised.value.detail) == ("gitlab_url_unreachable", "timeout")
        fetch.assert_not_called()

    def test_budget_spent_during_a_call_fails_the_call(self):
        from plane.agent.git_providers.base import ProviderError

        response = _streamed()
        times = iter([100.0, 131.0, 131.0])
        with (
            patch("plane.agent.git_providers.http.pinned_fetch", return_value=response),
            patch("plane.agent.git_providers.http.time.monotonic", side_effect=lambda: next(times)),
        ):
            with pytest.raises(ProviderError) as raised:
                self._request(deadline=130.0)

        assert (raised.value.code, raised.value.detail) == ("gitlab_url_unreachable", "timeout")

    def test_timeouts_never_exceed_the_remaining_budget(self):
        response = _streamed()
        with (
            patch("plane.agent.git_providers.http.pinned_fetch", return_value=response) as fetch,
            patch("plane.agent.git_providers.http.time.monotonic", return_value=100.0),
        ):
            self._request(deadline=103.0)

        assert fetch.call_args.kwargs["timeout"] == (3.0, 3.0)

    def test_ca_bundle_is_passed_as_a_private_file_and_default_is_system_trust(self, settings):
        import os
        import stat

        settings.AGENT_GIT_ALLOWED_HOSTS = ["git.internal"]
        settings.AGENT_GIT_ALLOWED_IPS = ["10.0.0.0/8"]
        pem = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"
        with patch("plane.agent.git_providers.http.pinned_fetch", side_effect=lambda *a, **k: _streamed()) as fetch:
            self._request(ca_bundle=pem)
            self._request()

        with_bundle, without_bundle = fetch.call_args_list
        path = with_bundle.kwargs["verify"]
        assert open(path).read() == pem
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
        assert stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode) == 0o700
        assert without_bundle.kwargs["verify"] is True
        assert with_bundle.kwargs["allowed_hosts"] == ["git.internal"]
        assert with_bundle.kwargs["allowed_ips"] == ["10.0.0.0/8"]
