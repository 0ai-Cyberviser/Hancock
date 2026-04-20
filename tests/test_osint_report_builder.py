"""Tests for the defensive OSINT reporting scaffold."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.osint_report_builder import (
    DEFAULT_DEV_CONFIG_PATH,
    DEFAULT_SCHEMA_PATH,
    DEFAULT_TEMPLATE_PATH,
    OSINTReportBuilder,
    ReportValidationError,
)


def _payload() -> dict:
    return {
        "report_id": "osint-demo-001",
        "generated_at": "2026-04-18T12:00:00+00:00",
        "subject": "Suspicious infrastructure cluster for phishing triage",
        "objective": "Summarize public indicators and defensive next steps.",
        "authorized_scope": True,
        "summary": (
            "Two public indicators overlap on hosting and registration timing, "
            "which warrants containment and blocking review."
        ),
        "indicators": [
            {
                "type": "domain",
                "value": "phish-login-support.com",
                "confidence": 0.92,
                "tags": ["phishing", "credential-harvest"],
            },
            {
                "type": "ip",
                "value": "93.184.216.34",
                "confidence": 0.81,
                "tags": ["hosting"],
            },
            {
                "type": "url",
                "value": "https://phish-login-support.com/login",
                "confidence": 0.88,
                "tags": ["landing-page"],
            },
        ],
        "findings": [
            {
                "title": "Credential harvesting host overlaps with known lure theme",
                "summary": (
                    "The domain and landing URL reuse a login-support naming pattern "
                    "consistent with recent phishing infrastructure."
                ),
                "severity": "high",
                "confidence": 0.86,
                "indicator_refs": [
                    "phish-login-support.com",
                    "https://phish-login-support.com/login",
                ],
                "evidence": [
                    {
                        "source_name": "Passive DNS",
                        "source_url": "https://intel.example/pdns/phish-login-support",
                        "collected_at": "2026-04-18T11:30:00+00:00",
                        "detail": "Observed first resolution within the last 24 hours.",
                    },
                    {
                        "source_name": "Certificate Transparency",
                        "source_url": "https://intel.example/ct/phish-login-support",
                        "collected_at": "2026-04-18T11:45:00+00:00",
                        "detail": "A fresh certificate was issued for the same hostname.",
                    },
                ],
                "recommendations": [
                    "Block the domain and landing URL at secure web gateways.",
                    "Hunt for inbound mail referencing the lure text.",
                ],
                "tags": ["phishing", "triage"],
            }
        ],
        "next_steps": [
            "Add the domain and IP to monitoring and block lists.",
            "Review mailbox telemetry for matching lure subjects.",
        ],
    }


def test_builder_creates_typed_report_with_defaults():
    builder = OSINTReportBuilder()

    report = builder.build(_payload())

    assert report.report_id == "osint-demo-001"
    assert report.author == "0AI OSINT Desk"
    assert report.organization == "CyberViser"
    assert report.tlp == "AMBER"
    assert len(report.indicators) == 3
    assert report.findings[0].severity == "high"
    assert report.findings[0].indicator_refs[0] == "phish-login-support.com"


def test_builder_serializes_and_renders_markdown():
    builder = OSINTReportBuilder()

    report_dict = builder.build_dict(_payload())
    rendered = builder.render_payload(_payload())

    assert report_dict["schema_version"] == "1.0.0"
    assert "Defensive OSINT Report" in rendered
    assert "phish-login-support.com" in rendered
    assert "Credential harvesting host overlaps" in rendered


def test_builder_loads_schema_template_and_dev_config():
    builder = OSINTReportBuilder()

    schema = builder.load_schema()

    assert Path(DEFAULT_SCHEMA_PATH).exists()
    assert Path(DEFAULT_TEMPLATE_PATH).exists()
    assert Path(DEFAULT_DEV_CONFIG_PATH).exists()
    assert schema["title"] == "Hancock Defensive OSINT Report"
    assert "subject" in schema["required"]
    assert "findings" in schema["properties"]


def test_builder_uses_custom_dev_config_defaults(tmp_path):
    config_path = tmp_path / "osint_report.dev.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "defaults": {
                    "author": "Custom Analyst",
                    "organization": "Blue Team Lab",
                    "tlp": "GREEN",
                },
                "guardrails": {
                    "authorized_scope_only": True,
                    "evidence_required": True,
                    "allow_private_indicators": False,
                    "max_indicators": 5,
                    "max_findings": 5,
                    "max_recommendations": 5,
                },
            }
        ),
        encoding="utf-8",
    )

    builder = OSINTReportBuilder(config_path=config_path)
    report = builder.build(_payload())

    assert report.author == "Custom Analyst"
    assert report.organization == "Blue Team Lab"
    assert report.tlp == "GREEN"


@pytest.mark.parametrize(
    "mutator,expected_message",
    [
        (
            lambda payload: payload.update({"authorized_scope": False}),
            "authorized_scope must be true",
        ),
        (
            lambda payload: payload["indicators"].append(
                {"type": "ip", "value": "10.0.0.5", "confidence": 0.6, "tags": []}
            ),
            "Private or non-routable IP indicators are blocked by guardrails.",
        ),
        (
            lambda payload: payload["indicators"].append(
                {
                    "type": "url",
                    "value": "ftp://phish-login-support.com/drop",
                    "confidence": 0.6,
                    "tags": [],
                }
            ),
            "must use http or https",
        ),
        (
            lambda payload: payload["indicators"].append(
                {
                    "type": "domain",
                    "value": "phish-login-support.com",
                    "confidence": 0.6,
                    "tags": [],
                }
            ),
            "Duplicate indicator detected",
        ),
        (
            lambda payload: payload["findings"][0].update(
                {
                    "indicator_refs": ["unknown.example"],
                }
            ),
            "unknown indicators",
        ),
        (
            lambda payload: payload["findings"][0].update({"evidence": []}),
            "must not be empty when evidence_required is true",
        ),
    ],
)
def test_builder_rejects_invalid_payloads(mutator, expected_message):
    builder = OSINTReportBuilder()
    payload = deepcopy(_payload())
    mutator(payload)

    with pytest.raises(ReportValidationError, match=expected_message):
        builder.build(payload)


def test_builder_enforces_guardrail_limits():
    builder = OSINTReportBuilder()
    payload = deepcopy(_payload())
    payload["guardrails"] = {
        "max_indicators": 2,
        "max_findings": 10,
        "max_recommendations": 12,
        "authorized_scope_only": True,
        "evidence_required": True,
        "allow_private_indicators": False,
    }

    with pytest.raises(ReportValidationError, match="max_indicators"):
        builder.build(payload)


def test_builder_rejects_invalid_evidence_url():
    builder = OSINTReportBuilder()
    payload = deepcopy(_payload())
    payload["findings"][0]["evidence"][0]["source_url"] = "file:///tmp/evidence.txt"

    with pytest.raises(ReportValidationError, match="valid http\\(s\\) URL"):
        builder.build(payload)


def test_builder_rejects_out_of_range_confidence():
    builder = OSINTReportBuilder()
    payload = deepcopy(_payload())
    payload["findings"][0]["confidence"] = 1.5

    with pytest.raises(ReportValidationError, match="must be between 0 and 1"):
        builder.build(payload)
