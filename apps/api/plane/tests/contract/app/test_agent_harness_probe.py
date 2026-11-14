# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from freezegun import freeze_time
from rest_framework import status

from plane.db.models import AgentConnection
from plane.tests.agent_settings_fixtures import (
    REPORTED_MODELS,
    agents_url,
    failing_checks,
    make_worker,
    probe_report,
    suite_record,
    worker_client_for,
)

CLAIM_URL = "/api/agent-worker/v1/probes/claim/"
HEARTBEAT_URL = "/api/agent-worker/v1/heartbeat/"


def report_url(probe_id):
    return f"/api/agent-worker/v1/probes/{probe_id}/report/"


def connect(client, workspace, harness="claude_code"):
    return client.post(agents_url(workspace.slug, harness, "connect"), {}, format="json")


def claim(worker_client, harnesses=("claude_code",)):
    return worker_client.post(CLAIM_URL, {"harnesses": list(harnesses)}, format="json")


def connect_and_claim(session_client, worker_client, workspace):
    connect(session_client, workspace)
    probe = claim(worker_client).data["probe"]
    assert probe is not None
    return probe


def agent_state(client, workspace, harness="claude_code"):
    return client.get(agents_url(workspace.slug, harness)).data


@pytest.mark.contract
class TestConnect:
    @pytest.mark.django_db
    def test_connect_sets_connecting_and_a_new_generation(self, session_client, workspace):
        before = timezone.now()

        response = connect(session_client, workspace)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["connection"]["state"] == "connecting"
        assert response.data["connection"]["probe_generation"] == 1
        connection = AgentConnection.objects.get(agent__workspace=workspace, agent__harness="claude_code")
        assert connection.probe_requested_at >= before
        assert connection.probe_claimed_at is None

    @pytest.mark.django_db
    def test_retry_increments_the_generation(self, session_client, workspace):
        connect(session_client, workspace)

        response = connect(session_client, workspace)

        assert response.data["connection"]["probe_generation"] == 2

    @pytest.mark.django_db
    def test_member_cannot_connect(self, session_client, member_client, workspace):
        session_client.get(agents_url(workspace.slug))

        response = connect(member_client, workspace)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert agent_state(session_client, workspace)["connection"]["state"] == "not_connected"

    @pytest.mark.django_db
    @pytest.mark.parametrize("harness", ["codex", "grok", "omp"])
    def test_harness_without_a_probe_cannot_connect_yet(self, session_client, workspace, harness):
        response = connect(session_client, workspace, harness)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "harness_probe_unavailable"
        assert agent_state(session_client, workspace, harness)["connection"]["state"] == "not_connected"


@pytest.mark.contract
class TestProbeClaim:
    @pytest.mark.django_db
    def test_worker_claims_a_pending_probe_once(self, session_client, worker_client, workspace):
        connect(session_client, workspace)

        first = claim(worker_client)
        second = claim(worker_client)

        assert first.status_code == status.HTTP_200_OK
        assert first.data["probe"]["harness"] == "claude_code"
        assert first.data["probe"]["generation"] == 1
        assert second.data["probe"] is None

    @pytest.mark.django_db
    def test_worker_does_not_claim_a_harness_it_cannot_probe(self, session_client, worker_client, workspace):
        connect(session_client, workspace)

        assert claim(worker_client, harnesses=["codex"]).data["probe"] is None

    @pytest.mark.django_db
    def test_expired_probe_is_not_claimed(self, session_client, worker_client, workspace):
        with freeze_time(timezone.now() - timedelta(seconds=121)):
            connect(session_client, workspace)

        assert claim(worker_client).data["probe"] is None

    @pytest.mark.django_db
    def test_claim_returns_the_answer_deadline_and_the_seconds_left(self, session_client, worker_client, workspace):
        start = timezone.now().replace(microsecond=0)
        with freeze_time(start):
            connect(session_client, workspace)
        with freeze_time(start + timedelta(seconds=20)):
            probe = claim(worker_client).json()["probe"]

        assert probe["seconds_left"] == 100
        assert parse_datetime(probe["deadline"]) == start + timedelta(seconds=120)

    @pytest.mark.django_db
    def test_probe_near_the_claim_cutoff_is_claimed_with_the_time_left(self, session_client, worker_client, workspace):
        start = timezone.now().replace(microsecond=0)
        with freeze_time(start):
            connect(session_client, workspace)
        with freeze_time(start + timedelta(seconds=59)):
            probe = claim(worker_client).data["probe"]

        assert probe is not None
        assert probe["seconds_left"] == 61

    @pytest.mark.django_db
    def test_probe_without_enough_time_left_is_not_claimed(self, session_client, worker_client, workspace):
        start = timezone.now()
        with freeze_time(start):
            connect(session_client, workspace)
        with freeze_time(start + timedelta(seconds=61)):
            assert claim(worker_client).data["probe"] is None

        connection = AgentConnection.objects.get(agent__workspace=workspace, agent__harness="claude_code")
        assert connection.probe_claimed_at is None

    @pytest.mark.django_db
    def test_invalid_harness_list_returns_400(self, worker_client):
        response = worker_client.post(CLAIM_URL, {"harnesses": "claude_code"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


def probe_check(worker_client, probe_id, generation):
    return worker_client.post(HEARTBEAT_URL, {"probe": {"id": probe_id, "generation": generation}}, format="json")


@pytest.mark.contract
class TestProbeCurrentCheck:
    @pytest.mark.django_db
    def test_running_probe_is_current(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)

        response = probe_check(worker_client, probe["id"], probe["generation"])

        assert response.status_code == status.HTTP_200_OK
        assert response.data["probe_current"] is True

    @pytest.mark.django_db
    def test_probe_replaced_by_retry_is_not_current(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        connect(session_client, workspace)

        assert probe_check(worker_client, probe["id"], probe["generation"]).data["probe_current"] is False

    @pytest.mark.django_db
    def test_probe_stopped_by_disconnect_is_not_current(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        session_client.post(agents_url(workspace.slug, "claude_code", "disconnect"), {}, format="json")

        assert probe_check(worker_client, probe["id"], probe["generation"]).data["probe_current"] is False

    @pytest.mark.django_db
    def test_probe_past_its_deadline_is_not_current(self, session_client, worker_client, workspace):
        start = timezone.now()
        with freeze_time(start):
            probe = connect_and_claim(session_client, worker_client, workspace)
        with freeze_time(start + timedelta(seconds=121)):
            assert probe_check(worker_client, probe["id"], probe["generation"]).data["probe_current"] is False

    @pytest.mark.django_db
    def test_probe_of_another_worker_is_not_current(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        _, other_token = make_worker(name="other")

        response = probe_check(worker_client_for(other_token), probe["id"], probe["generation"])

        assert response.data["probe_current"] is False

    @pytest.mark.django_db
    def test_unknown_probe_is_not_current(self, worker_client):
        response = probe_check(worker_client, "00000000-0000-0000-0000-000000000000", 1)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["probe_current"] is False

    @pytest.mark.django_db
    def test_heartbeat_without_a_probe_has_no_probe_answer(self, worker_client):
        response = worker_client.post(HEARTBEAT_URL, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "probe_current" not in response.data

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "body",
        [{"probe": {"id": "not-a-uuid", "generation": 1}}, {"probe": {"id": "00000000-0000-0000-0000-000000000000"}}],
    )
    def test_malformed_probe_check_returns_400(self, worker_client, body):
        assert worker_client.post(HEARTBEAT_URL, body, format="json").status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestProbeReport:
    @pytest.mark.django_db
    def test_full_pass_sets_connected_with_models_and_capabilities(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)

        response = worker_client.post(report_url(probe["id"]), probe_report(probe["generation"]), format="json")

        assert response.status_code == status.HTTP_200_OK
        agent = agent_state(session_client, workspace)
        assert agent["connection"]["state"] == "connected"
        assert agent["connection"]["models"] == REPORTED_MODELS
        assert agent["connection"]["capabilities"] == {
            "midturn_input": False,
            "native_resume": True,
            "permission_prompt": True,
        }
        assert agent["connection"]["harness_version"] == "2.1.289"
        assert agent["connection"]["verified_at"] is not None
        assert agent["connection"]["missing_action"] == ""
        assert agent["available_for_mentions"] is True

    @pytest.mark.django_db
    def test_cached_suite_record_sets_connected_with_the_record_time(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        verified_at = timezone.now() - timedelta(days=3)
        suite = suite_record(verified_at=verified_at.isoformat(), ran_now=False)
        report = probe_report(probe["generation"], suite=suite)

        response = worker_client.post(report_url(probe["id"]), report, format="json")

        assert response.status_code == status.HTTP_200_OK
        connection = agent_state(session_client, workspace)["connection"]
        assert connection["state"] == "connected"
        assert connection["verified_at"] == verified_at

    @pytest.mark.django_db
    def test_failed_report_without_a_suite_record_sets_failed(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        report = probe_report(
            probe["generation"], checks=failing_checks("interruption", "the turn was not interrupted"), suite=None
        )

        response = worker_client.post(report_url(probe["id"]), report, format="json")

        assert response.status_code == status.HTTP_200_OK
        connection = agent_state(session_client, workspace)["connection"]
        assert connection["state"] == "failed"
        assert connection["missing_action"] == "interruption"
        assert connection["verified_at"] is None

    @pytest.mark.django_db
    def test_report_without_the_suite_field_returns_400(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        report = probe_report(probe["generation"])
        del report["suite"]

        response = worker_client.post(report_url(probe["id"]), report, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_failed_check_sets_failed_with_the_missing_action(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        report = probe_report(
            probe["generation"],
            checks=failing_checks("authentication"),
            models=[],
            failure_hint="claude exited 1 · not logged in",
        )

        response = worker_client.post(report_url(probe["id"]), report, format="json")

        assert response.status_code == status.HTTP_200_OK
        agent = agent_state(session_client, workspace)
        assert agent["connection"]["state"] == "failed"
        assert agent["connection"]["missing_action"] == "authentication"
        assert agent["connection"]["failure_hint"] == "claude exited 1 · not logged in"
        assert agent["connection"]["models"] == []
        assert agent["available_for_mentions"] is False

    @pytest.mark.django_db
    def test_missing_permission_check_fails_with_named_action(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        report = probe_report(probe["generation"], checks=failing_checks("permission"))

        worker_client.post(report_url(probe["id"]), report, format="json")

        agent = agent_state(session_client, workspace)
        assert agent["connection"]["state"] == "failed"
        assert agent["connection"]["missing_action"] == "permission"
        assert agent["connection"]["models"] == []

    @pytest.mark.django_db
    def test_check_absent_from_the_report_counts_as_failed(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        checks = [check for check in probe_report(1)["checks"] if check["name"] != "recovery"]

        worker_client.post(report_url(probe["id"]), probe_report(probe["generation"], checks=checks), format="json")

        connection = agent_state(session_client, workspace)["connection"]
        assert connection["state"] == "failed"
        assert connection["missing_action"] == "recovery"

    @pytest.mark.django_db
    def test_passing_checks_without_models_fail_the_model_report(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)

        worker_client.post(report_url(probe["id"]), probe_report(probe["generation"], models=[]), format="json")

        connection = agent_state(session_client, workspace)["connection"]
        assert connection["state"] == "failed"
        assert connection["missing_action"] == "model_report"

    @pytest.mark.django_db
    def test_blocking_issue_is_the_missing_action(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        report = probe_report(
            probe["generation"],
            checks=[],
            models=[],
            blocking_issue="unsupported_version",
            failure_hint="claude 3.0.0 is not supported",
        )

        worker_client.post(report_url(probe["id"]), report, format="json")

        connection = agent_state(session_client, workspace)["connection"]
        assert connection["state"] == "failed"
        assert connection["missing_action"] == "unsupported_version"

    @pytest.mark.django_db
    def test_old_generation_report_returns_409(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        connect(session_client, workspace)

        response = worker_client.post(report_url(probe["id"]), probe_report(probe["generation"]), format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "probe_superseded"
        assert agent_state(session_client, workspace)["connection"]["state"] == "connecting"

    @pytest.mark.django_db
    def test_report_from_another_worker_returns_409(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        _, other_token = make_worker(name="other")

        response = worker_client_for(other_token).post(
            report_url(probe["id"]), probe_report(probe["generation"]), format="json"
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "probe_not_claimed"

    @pytest.mark.django_db
    def test_second_report_for_the_same_generation_returns_409(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        worker_client.post(report_url(probe["id"]), probe_report(probe["generation"]), format="json")

        response = worker_client.post(
            report_url(probe["id"]),
            probe_report(probe["generation"], checks=failing_checks("progress")),
            format="json",
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert agent_state(session_client, workspace)["connection"]["state"] == "connected"

    @pytest.mark.django_db
    def test_report_after_the_answer_deadline_returns_409(self, session_client, worker_client, workspace):
        start = timezone.now()
        with freeze_time(start):
            probe = connect_and_claim(session_client, worker_client, workspace)

        with freeze_time(start + timedelta(seconds=121)):
            response = worker_client.post(report_url(probe["id"]), probe_report(probe["generation"]), format="json")
            agent = agent_state(session_client, workspace)

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["error"] == "probe_expired"
        assert agent["connection"]["state"] == "failed"
        assert agent["connection"]["missing_action"] == "worker_did_not_answer"

    @pytest.mark.django_db
    def test_unknown_probe_returns_404(self, worker_client):
        response = worker_client.post(
            report_url("00000000-0000-4000-8000-000000000000"), probe_report(1), format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "overrides",
        [
            {"version": 1},
            {"generation": "one"},
            {"checks": [{"name": "teleport", "passed": True, "detail": ""}]},
            {"checks": [{"name": "progress", "passed": "yes", "detail": ""}]},
            {"models": [{"id": "x" * 200, "label": "Long", "description": ""}]},
            {"models": [{"id": "bad id; rm -rf", "label": "Bad", "description": ""}]},
            {"models": [{"id": f"m{index}", "label": "M", "description": ""} for index in range(51)]},
            {"capabilities": {"midturn_input": "maybe"}},
            {"failure_hint": "x" * 1001},
            {"blocking_issue": "something_else"},
            # Every check passed, so the report must carry the passing suite record of this version.
            {"suite": None},
            {"suite": suite_record(cli_version="2.1.288")},
            {"suite": suite_record(suite_version=0)},
            {"suite": suite_record(ran_now="yes")},
            {"suite": suite_record(verified_at="yesterday")},
            {"suite": suite_record(verified_at=(timezone.now() + timedelta(hours=1)).isoformat())},
        ],
    )
    def test_malformed_report_returns_400_and_changes_nothing(
        self, session_client, worker_client, workspace, overrides
    ):
        probe = connect_and_claim(session_client, worker_client, workspace)

        report = probe_report(probe["generation"])
        report.update(overrides)

        response = worker_client.post(report_url(probe["id"]), report, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert agent_state(session_client, workspace)["connection"]["state"] == "connecting"


@pytest.mark.contract
class TestProbeAnswerDeadline:
    @pytest.mark.django_db
    def test_connecting_reads_connecting_until_120_seconds(self, session_client, workspace):
        start = timezone.now()
        with freeze_time(start):
            connect(session_client, workspace)

        with freeze_time(start + timedelta(seconds=119)):
            connection = agent_state(session_client, workspace)["connection"]

        assert connection["state"] == "connecting"

    @pytest.mark.django_db
    def test_connecting_without_a_report_reads_failed_after_120_seconds(self, session_client, workspace):
        start = timezone.now()
        with freeze_time(start):
            connect(session_client, workspace)

        with freeze_time(start + timedelta(seconds=121)):
            listed = session_client.get(agents_url(workspace.slug)).data[0]["connection"]
            detail = agent_state(session_client, workspace)["connection"]

        for connection in (listed, detail):
            assert connection["state"] == "failed"
            assert connection["missing_action"] == "worker_did_not_answer"


@pytest.mark.contract
class TestDisconnect:
    @pytest.mark.django_db
    def test_disconnect_blocks_new_mentions_and_rejects_the_old_report(self, session_client, worker_client, workspace):
        probe = connect_and_claim(session_client, worker_client, workspace)
        worker_client.post(report_url(probe["id"]), probe_report(probe["generation"]), format="json")
        assert agent_state(session_client, workspace)["available_for_mentions"] is True

        response = session_client.post(agents_url(workspace.slug, "claude_code", "disconnect"), {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["connection"]["state"] == "not_connected"
        assert response.data["connection"]["models"] == []
        assert response.data["available_for_mentions"] is False
        late = worker_client.post(report_url(probe["id"]), probe_report(probe["generation"]), format="json")
        assert late.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.django_db
    def test_member_cannot_disconnect(self, session_client, member_client, workspace):
        connect(session_client, workspace)

        response = member_client.post(agents_url(workspace.slug, "claude_code", "disconnect"), {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert agent_state(session_client, workspace)["connection"]["state"] == "connecting"
