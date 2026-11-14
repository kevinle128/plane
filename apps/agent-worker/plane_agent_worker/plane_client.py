# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""HTTP client for the Plane Worker API.

The token goes only in ``Authorization: Bearer``, never in ``X-Api-Key`` (Plane
logs request and response bodies of ``X-Api-Key`` requests). The client follows
no redirect and uses no proxy, so the token goes only to the configured
localhost origin. Errors carry the HTTP status and the API error code, never the
token or the raw response.
"""

import json
import urllib.error
import urllib.request
from urllib.parse import quote

API_PREFIX = "/api/agent-worker/v1"
MAX_RESPONSE_BYTES = 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15


class PlaneClientError(Exception):
    """A request to Plane did not succeed. ``status`` is ``None`` when Plane was not reached."""

    def __init__(self, status, code):
        super().__init__(f"Plane request failed (status {status}, {code})")
        self.status = status
        self.code = code


class Conflict(PlaneClientError):
    """Plane refused the request with 409: a newer probe or lease replaced the caller's."""


class ProbeRejected(Conflict):
    """Plane refused a probe report with 409, for example because a newer probe replaced it."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PlaneClient:
    def __init__(self, origin, token, timeout=DEFAULT_TIMEOUT_SECONDS):
        self.origin = origin.rstrip("/")
        self._token = token
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def __repr__(self):
        return f"PlaneClient(origin={self.origin!r})"

    def _post(self, path, body):
        return self._request("POST", path, body)

    def _get(self, path):
        return self._request("GET", path, None)

    def _request(self, method, path, body):
        request = urllib.request.Request(
            f"{self.origin}{API_PREFIX}{path}",
            data=None if body is None else json.dumps(body).encode(),
            method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return self._decode(response.status, response.read(MAX_RESPONSE_BYTES + 1))
        except urllib.error.HTTPError as error:
            raw = error.read(MAX_RESPONSE_BYTES + 1) if error.fp else b""
            error.close()
            code = self._error_code(raw)
            if error.code == 409:
                raise (ProbeRejected if path.startswith("/probes/") else Conflict)(409, code) from None
            raise PlaneClientError(error.code, code) from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise PlaneClientError(None, type(reason).__name__) from None

    @staticmethod
    def _decode(status, raw):
        if len(raw) > MAX_RESPONSE_BYTES:
            raise PlaneClientError(status, "response too large")
        try:
            return json.loads(raw or b"{}")
        except (ValueError, RecursionError):
            raise PlaneClientError(status, "response is not JSON") from None

    @staticmethod
    def _error_code(raw):
        if len(raw) > MAX_RESPONSE_BYTES:
            return "response too large"
        try:
            body = json.loads(raw or b"{}")
        except (ValueError, RecursionError):
            return "unexpected response"
        if isinstance(body, dict) and isinstance(body.get("error"), str):
            return body["error"][:64]
        return "request failed"

    def heartbeat(self, probe_id=None, generation=None):
        """Record that the Worker is alive. With a probe, Plane also answers whether the probe is still current."""
        body = {} if probe_id is None else {"probe": {"id": str(probe_id), "generation": generation}}
        return self._post("/heartbeat/", body)

    def claim_probe(self, harnesses):
        body = self._post("/probes/claim/", {"harnesses": list(harnesses)})
        probe = body.get("probe") if isinstance(body, dict) else None
        return probe if isinstance(probe, dict) else None

    def report_probe(self, probe_id, report):
        return self._post(f"/probes/{quote(str(probe_id), safe='')}/report/", report)

    # Runs ----------------------------------------------------------------------

    @staticmethod
    def _run_path(run_id, action):
        return f"/runs/{quote(str(run_id), safe='')}/{action}/"

    def claim_run(self, harnesses):
        body = self._post("/runs/claim/", {"harnesses": list(harnesses)})
        run = body.get("run") if isinstance(body, dict) else None
        return run if isinstance(run, dict) else None

    def renew_run(self, run_id, lease_generation):
        return self._post(self._run_path(run_id, "renew"), {"lease_generation": lease_generation})

    def report_clone(self, run_id, lease_generation, *, ok, clone_path=None, error_code=None, error_detail=None):
        body = {"lease_generation": lease_generation, "ok": ok}
        if ok:
            body["clone_path"] = clone_path
        else:
            body.update(error_code=error_code, error_detail=error_detail or "")
        return self._post(self._run_path(run_id, "clone"), body)

    def git_credential(self, run_id, lease_generation):
        """The fetch token of a GitLab Run. The response is never logged."""
        body = self._post(
            self._run_path(run_id, "git-credential"), {"lease_generation": lease_generation, "purpose": "fetch"}
        )
        password = body.get("password") if isinstance(body, dict) else None
        if not isinstance(password, str) or not password:
            raise PlaneClientError(200, "no credential in the response")
        return password

    def run_context(self, run_id, lease_generation):
        return self._get(f"{self._run_path(run_id, 'context')}?lease_generation={int(lease_generation)}")

    def post_events(self, run_id, lease_generation, turn_index, events):
        body = {"lease_generation": lease_generation, "turn_index": turn_index, "events": list(events)}
        answer = self._post(self._run_path(run_id, "events"), body)
        stored = answer.get("events") if isinstance(answer, dict) else None
        return stored if isinstance(stored, list) else []

    def post_result(self, run_id, lease_generation, result):
        return self._post(self._run_path(run_id, "result"), {"lease_generation": lease_generation, **result})
