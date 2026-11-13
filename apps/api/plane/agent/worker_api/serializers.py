# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Input validation for Worker requests. Every string and list has a bound."""

# Third party imports
from rest_framework import serializers

# Module imports
from plane.agent.services.harness_probe import BLOCKING_ISSUES, CAPABILITY_FLAGS, REQUIRED_CHECKS
from plane.db.models import AgentHarness

REPORT_VERSION = 1
MAX_MODELS = 50
# Model IDs go to the Harness command line, so only a safe character set is accepted.
MODEL_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:\[\]/-]{0,127}$"


class ProbeClaimSerializer(serializers.Serializer):
    harnesses = serializers.ListField(
        child=serializers.ChoiceField(choices=AgentHarness.choices), allow_empty=True, max_length=10
    )


class ProbeCheckSerializer(serializers.Serializer):
    name = serializers.ChoiceField(choices=REQUIRED_CHECKS)
    passed = serializers.BooleanField(required=True)
    detail = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")

    def to_internal_value(self, data):
        # A string such as "yes" must not pass as a boolean.
        if isinstance(data, dict) and not isinstance(data.get("passed"), bool):
            raise serializers.ValidationError({"passed": "Must be a boolean."})
        return super().to_internal_value(data)


class ProbeModelSerializer(serializers.Serializer):
    id = serializers.RegexField(MODEL_ID_PATTERN)
    label = serializers.CharField(max_length=128, allow_blank=True, required=False, default="")
    description = serializers.CharField(max_length=300, allow_blank=True, required=False, default="")


class ProbeCapabilitiesSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Must be an object.")
        unknown = set(data) - set(CAPABILITY_FLAGS)
        if unknown:
            raise serializers.ValidationError(f"Unknown capability: {sorted(unknown)[0]}.")
        flags = {}
        for name in CAPABILITY_FLAGS:
            value = data.get(name, False)
            if not isinstance(value, bool):
                raise serializers.ValidationError({name: "Must be a boolean."})
            flags[name] = value
        return flags


class ProbeReportSerializer(serializers.Serializer):
    version = serializers.IntegerField()
    generation = serializers.IntegerField(min_value=1)
    harness_version = serializers.CharField(max_length=64, allow_blank=True)
    location = serializers.CharField(max_length=1024, allow_blank=True)
    checks = ProbeCheckSerializer(many=True, max_length=len(REQUIRED_CHECKS) * 2)
    models = ProbeModelSerializer(many=True, max_length=MAX_MODELS)
    capabilities = ProbeCapabilitiesSerializer()
    failure_hint = serializers.CharField(max_length=1000, allow_blank=True, required=False, default="")
    blocking_issue = serializers.ChoiceField(choices=BLOCKING_ISSUES, required=False, allow_null=True, default=None)

    def validate_version(self, value):
        if value != REPORT_VERSION:
            raise serializers.ValidationError(f"Only report version {REPORT_VERSION} is supported.")
        return value

    def validate_checks(self, checks):
        names = [check["name"] for check in checks]
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Each check can appear once.")
        return checks

    def validate_models(self, models):
        ids = [model["id"] for model in models]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Each model can appear once.")
        return models
