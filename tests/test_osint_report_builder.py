<<<<<<< HEAD
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
=======
import json

import pytest

from collectors.osint_guardrails import GuardrailViolation
from collectors.osint_report_builder import (
    build_report,
    main,
    render_markdown,
    summarize_report,
)


def _base_config(tmp_path):
    return {
        "profile": "joint",
        "target": "Example Corp",
        "scope": {
            "authorized_assets": ["example.com"]
        },
        "inputs": {
            "asset_inventory": str(tmp_path / "assets.json"),
            "evidence_bundle": str(tmp_path / "evidence.json"),
        },
        "engagement_defaults": {
            "requester": "Security Engineering",
            "business_owner": "Example Corp Security",
            "authorization_reference": "AUTH-001",
            "objective": "Generate a defensive exposure assessment report.",
            "report_profile": "joint",
        },
        "scope_defaults": {
            "in_scope": ["example.com"],
            "out_of_scope": [],
            "collection_constraints": ["Passive evidence only"],
            "source_policy": "approved-only",
        },
        "outputs": {
            "markdown": str(tmp_path / "report.md"),
            "json": str(tmp_path / "report.json"),
            "html": None,
        },
        "render": {
            "classification": "UNCLASSIFIED // OSINT",
            "redact_pii": True,
            "include_social_summary": True,
            "include_appendix": True,
        },
        "enrichment": {
            "geoip": True,
            "threat_intel": True,
            "historical_dns": False,
            "brand_monitoring": True,
        },
        "guardrails": {
            "authorization_required": True,
            "allow_active_collection": False,
            "forbid_dark_web_collection": True,
            "allowed_source_hosts": ["example.com"],
            "min_confidence": 60,
            "pii_policy": "mask-low-value",
        },
        "dev": {
            "lab_mode": False,
            "strict_schema_validation": True,
            "save_intermediates": True,
            "fail_on_missing_citation": True,
            "sample_limit": 100,
            "debug": False,
        },
    }


def _base_bundle():
    return {
        "assets": [
            {
                "asset_id": "A-001",
                "asset_type": "domain",
                "value": "example.com",
                "owner": "Security Engineering",
                "criticality": "high",
            }
        ],
        "findings": [
            {
                "title": "Public security contact needs rotation",
                "severity": "medium",
                "summary": "Legacy public contact information is still published in a security page.",
                "asset_refs": ["A-001"],
                "evidence_refs": ["EVID-001"],
                "confidence": 85,
                "risk_score": 5.5,
                "status": "open",
            }
        ],
        "evidence": [
            {
                "type": "web",
                "source_name": "Example Corp Security",
                "source_url": "https://example.com/security",
                "retrieved_at": "2026-04-15T00:00:00Z",
                "claim": "Contact security@example.com or +1 555 123 4567 for urgent issues.",
                "sensitivity": "public",
            }
        ],
        "recommendations": {
            "immediate": [
                {
                    "action": "Rotate the public security contact and owner metadata.",
                    "owner": "Security Engineering",
                    "priority": "P1",
                    "due_in_days": 7,
                }
            ],
            "thirty_day": [],
            "long_term": [],
        },
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_report_redacts_low_value_pii(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()

    report = build_report(config, bundle)

    assert report.report_metadata.title == "Example Corp Exposure Assessment"
    assert report.findings[0].id == "F-001"
    assert report.evidence[0].id == "EVID-001"
    assert "[REDACTED-EMAIL]" in report.evidence[0].claim
    assert "[REDACTED-PHONE]" in report.evidence[0].claim


def test_build_report_rejects_missing_citation(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    del bundle["evidence"][0]["source_url"]

    with pytest.raises(GuardrailViolation, match="source_url and retrieved_at"):
        build_report(config, bundle)


def test_build_report_collapses_duplicate_evidence_and_renders_markdown(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["evidence"].append(dict(bundle["evidence"][0]))

    report = build_report(config, bundle)
    markdown = render_markdown(report)

    assert len(report.evidence) == 1
    assert "## Executive Summary" in markdown
    assert "## Key Findings" in markdown
    assert "## Evidence Register" in markdown


def test_guardrails_reject_active_collection_without_lab_mode(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    config["guardrails"]["allow_active_collection"] = True
    config["dev"]["lab_mode"] = False

    with pytest.raises(GuardrailViolation, match="requires dev.lab_mode=true"):
        build_report(config, bundle)


def test_guardrails_reject_disabled_dark_web_block(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    config["guardrails"]["forbid_dark_web_collection"] = False

    with pytest.raises(GuardrailViolation, match="cannot be disabled"):
        build_report(config, bundle)


def test_build_report_uses_asset_inventory_fallback(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["assets"] = []
    bundle["findings"][0]["asset_refs"] = ["A-002"]

    inventory = {
        "assets": [
            {
                "asset_id": "A-002",
                "asset_type": "repo",
                "value": "github.com/example/repo",
                "owner": "Platform Security",
                "criticality": "medium",
            }
        ]
    }
    _write_json(tmp_path / "assets.json", inventory)

    report = build_report(config, bundle)

    assert len(report.assets) == 1
    assert report.assets[0].asset_id == "A-002"
    assert report.assets[0].value == "github.com/example/repo"


def test_build_report_rejects_unknown_evidence_reference(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["findings"][0]["evidence_refs"] = ["EVID-999"]

    with pytest.raises(GuardrailViolation, match="references unknown evidence"):
        build_report(config, bundle)


def test_render_markdown_includes_unsafe_dev_warning(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    report = build_report(config, bundle)

    markdown = render_markdown(
        report,
        unsafe_options=["dev.debug=true", "dev.fail_on_missing_citation=false"],
    )

    assert "Generated with non-default developer settings" in markdown
    assert "dev.debug=true" in markdown
    assert "dev.fail_on_missing_citation=false" in markdown


def test_summarize_report_returns_audience_specific_text(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    report = build_report(config, bundle)

    ciso_summary = summarize_report(report, "ciso")
    soc_summary = summarize_report(report, "soc")
    joint_summary = summarize_report(report, "joint")

    assert "Highest risk score" in ciso_summary
    assert "incident-response routing" in soc_summary
    assert "exposure assessment contains" in joint_summary


def test_build_report_rejects_non_https_source_outside_lab_mode(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["evidence"][0]["source_url"] = "http://example.com/security"

    with pytest.raises(GuardrailViolation, match="must use https outside lab mode"):
        build_report(config, bundle)


def test_build_report_rejects_non_allowlisted_source_host(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["evidence"][0]["source_url"] = "https://evil.example.net/security"

    with pytest.raises(GuardrailViolation, match="approved source allowlist"):
        build_report(config, bundle)


def test_build_report_rejects_localhost_source_outside_lab_mode(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["evidence"][0]["source_url"] = "https://localhost/security"

    with pytest.raises(GuardrailViolation, match="private network hosts"):
        build_report(config, bundle)


def test_build_report_rejects_invalid_retrieval_timestamp(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["evidence"][0]["retrieved_at"] = "not-a-timestamp"

    with pytest.raises(GuardrailViolation, match="valid ISO-8601 datetime"):
        build_report(config, bundle)


def test_build_report_rejects_findings_below_min_confidence(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["findings"][0]["confidence"] = 59

    with pytest.raises(GuardrailViolation, match="below min_confidence"):
        build_report(config, bundle)


def test_build_report_rejects_findings_without_evidence_refs(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    bundle["findings"][0]["evidence_refs"] = []

    with pytest.raises(GuardrailViolation, match="must cite at least one evidence item"):
        build_report(config, bundle)


def test_build_report_enforces_sample_limit(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    config["dev"]["sample_limit"] = 1
    bundle["evidence"].append(
        {
            "type": "web",
            "source_name": "Example Corp Status",
            "source_url": "https://example.com/status",
            "retrieved_at": "2026-04-15T01:00:00Z",
            "claim": "Status page references the same service boundary.",
            "sensitivity": "public",
        }
    )
    bundle["findings"][0]["evidence_refs"] = ["EVID-001", "EVID-002"]

    with pytest.raises(GuardrailViolation, match="exceeds sample_limit=1"):
        build_report(config, bundle)


def test_build_report_allows_http_localhost_in_lab_mode(tmp_path):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    config["dev"]["lab_mode"] = True
    config["guardrails"]["allowed_source_hosts"] = []
    config["scope_defaults"]["source_policy"] = "lab-only"
    bundle["evidence"][0]["source_url"] = "http://localhost:8080/security"

    report = build_report(config, bundle)

    assert report.evidence[0].source_url == "http://localhost:8080/security"


def test_cli_build_validate_render_and_summarize(tmp_path, capsys):
    config = _base_config(tmp_path)
    bundle = _base_bundle()
    config_path = tmp_path / "config.json"
    evidence_path = tmp_path / "evidence.json"
    report_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    rendered_path = tmp_path / "rendered.md"

    _write_json(config_path, config)
    _write_json(evidence_path, bundle)

    assert main(
        [
            "build",
            "--config",
            str(config_path),
            "--evidence",
            str(evidence_path),
            "--output",
            str(markdown_path),
            "--json-output",
            str(report_path),
        ]
    ) == 0
    assert markdown_path.exists()
    assert report_path.exists()

    assert main(["validate", "--report", str(report_path)]) == 0
    assert main(["render", "--report", str(report_path), "--output", str(rendered_path)]) == 0
    assert rendered_path.exists()

    assert main(["summarize", "--report", str(report_path), "--audience", "soc"]) == 0
    captured = capsys.readouterr()
    assert "incident-response routing" in captured.out
>>>>>>> 67b2a2f85225a4610b2ed4affb5b23596733c8e7
