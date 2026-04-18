<<<<<<< HEAD
"""Defensive OSINT reporting scaffold with typed models and guardrails."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse


DEFAULT_SCHEMA_VERSION = "1.0.0"
_ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_PATH = _ROOT_DIR / "docs" / "schemas" / "osint_report.schema.json"
DEFAULT_TEMPLATE_PATH = _ROOT_DIR / "docs" / "templates" / "osint_report.md.tmpl"
DEFAULT_DEV_CONFIG_PATH = _ROOT_DIR / "docs" / "config" / "osint_report.dev.json"

_ALLOWED_TLP = {"CLEAR", "GREEN", "AMBER", "AMBER+STRICT", "RED"}
_ALLOWED_INDICATOR_TYPES = {"domain", "email", "hash", "ip", "url"}
_ALLOWED_SEVERITIES = {"informational", "low", "medium", "high", "critical"}
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_HEX_HASH_RE = re.compile(r"^[A-Fa-f0-9]+$")


class ReportValidationError(ValueError):
    """Raised when an OSINT report payload fails validation."""


@dataclass(slots=True)
class ReportGuardrails:
    """Validation and safety limits for defensive OSINT reporting."""

    authorized_scope_only: bool = True
    evidence_required: bool = True
    allow_private_indicators: bool = False
    max_indicators: int = 25
    max_findings: int = 10
    max_recommendations: int = 12


@dataclass(slots=True)
class OSINTIndicator:
    """A single indicator referenced by a defensive OSINT report."""

    type: str
    value: str
    confidence: float = 0.5
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OSEvidence:
    """Evidence supporting an OSINT finding."""

    source_name: str
    source_url: str
    collected_at: str
    detail: str


@dataclass(slots=True)
class OSINTFinding:
    """A defensive finding backed by indicators and evidence."""

    title: str
    summary: str
    severity: str
    confidence: float
    indicator_refs: list[str]
    evidence: list[OSEvidence]
    recommendations: list[str]
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OSINTReportConfig:
    """Default report settings loaded from the dev config scaffold."""

    schema_version: str = DEFAULT_SCHEMA_VERSION
    default_author: str = "0AI OSINT Desk"
    default_organization: str = "CyberViser"
    default_tlp: str = "AMBER"
    guardrails: ReportGuardrails = field(default_factory=ReportGuardrails)


@dataclass(slots=True)
class OSINTReport:
    """Validated OSINT report document."""

    report_id: str
    schema_version: str
    generated_at: str
    subject: str
    objective: str
    author: str
    organization: str
    tlp: str
    authorized_scope: bool
    summary: str
    indicators: list[OSINTIndicator]
    findings: list[OSINTFinding]
    next_steps: list[str]
    guardrails: ReportGuardrails

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a JSON-serializable dictionary."""
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReportValidationError(f"{field_name} must be an object.")
    return value


def _require_text(value: Any, field_name: str, *, max_len: int | None = None) -> str:
    if not isinstance(value, str):
        raise ReportValidationError(f"{field_name} must be a string.")
    cleaned = value.strip()
    if not cleaned:
        raise ReportValidationError(f"{field_name} must not be empty.")
    if max_len is not None and len(cleaned) > max_len:
        raise ReportValidationError(
            f"{field_name} must be at most {max_len} characters long."
        )
    return cleaned


def _require_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ReportValidationError(f"{field_name} must be a list of strings.")
    cleaned: list[str] = []
    for idx, entry in enumerate(value):
        cleaned.append(_require_text(entry, f"{field_name}[{idx}]"))
    return cleaned


def _require_probability(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)):
        raise ReportValidationError(f"{field_name} must be a number between 0 and 1.")
    probability = float(value)
    if probability < 0 or probability > 1:
        raise ReportValidationError(f"{field_name} must be between 0 and 1.")
    return round(probability, 2)


def _normalize_tlp(value: Any) -> str:
    tlp = _require_text(value, "tlp").upper()
    if tlp not in _ALLOWED_TLP:
        supported = ", ".join(sorted(_ALLOWED_TLP))
        raise ReportValidationError(f"tlp must be one of: {supported}.")
    return tlp


def _validate_iso_datetime(value: Any, field_name: str) -> str:
    text = _require_text(value, field_name)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReportValidationError(f"{field_name} must be an ISO-8601 timestamp.") from exc
    return text


def _validate_public_ip(value: str, guardrails: ReportGuardrails) -> str:
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ReportValidationError("indicator.value must be a valid IP address.") from exc

    is_non_public = any(
        (
            parsed.is_private,
            parsed.is_loopback,
            parsed.is_link_local,
            parsed.is_multicast,
            parsed.is_reserved,
            parsed.is_unspecified,
        )
    )
    if is_non_public and not guardrails.allow_private_indicators:
        raise ReportValidationError(
            "Private or non-routable IP indicators are blocked by guardrails."
        )
    return str(parsed)


def _validate_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    if not _DOMAIN_RE.match(domain):
        raise ReportValidationError("indicator.value must be a valid domain.")
    if domain == "localhost":
        raise ReportValidationError("localhost is not a valid OSINT domain indicator.")
    return domain


def _validate_url(value: str, guardrails: ReportGuardrails) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ReportValidationError("indicator.value must use http or https.")
    if not parsed.netloc:
        raise ReportValidationError("indicator.value must include a hostname.")
    hostname = parsed.hostname or ""
    if hostname == "localhost":
        raise ReportValidationError("localhost URLs are not valid OSINT indicators.")
    try:
        _validate_public_ip(hostname, guardrails)
    except ReportValidationError:
        try:
            _validate_domain(hostname)
        except ReportValidationError as exc:
            raise ReportValidationError("indicator.value must reference a public host.") from exc
    return value.strip()


def _validate_hash(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) not in {32, 40, 64} or not _HEX_HASH_RE.match(normalized):
        raise ReportValidationError(
            "indicator.value must be a valid MD5, SHA1, or SHA256 hash."
        )
    return normalized


def _validate_email(value: str) -> str:
    normalized = value.strip().lower()
    if not _EMAIL_RE.match(normalized):
        raise ReportValidationError("indicator.value must be a valid email address.")
    return normalized


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class OSINTReportBuilder:
    """Build and render defensive OSINT reports from validated payloads."""

    def __init__(
        self,
        *,
        schema_path: str | Path = DEFAULT_SCHEMA_PATH,
        template_path: str | Path = DEFAULT_TEMPLATE_PATH,
        config_path: str | Path = DEFAULT_DEV_CONFIG_PATH,
    ) -> None:
        self.schema_path = Path(schema_path)
        self.template_path = Path(template_path)
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> OSINTReportConfig:
        payload = _load_json(self.config_path)
        defaults = payload.get("defaults", {})
        guardrails_payload = payload.get("guardrails", {})
        return OSINTReportConfig(
            schema_version=payload.get("schema_version", DEFAULT_SCHEMA_VERSION),
            default_author=defaults.get("author", "0AI OSINT Desk"),
            default_organization=defaults.get("organization", "CyberViser"),
            default_tlp=defaults.get("tlp", "AMBER").upper(),
            guardrails=ReportGuardrails(
                authorized_scope_only=bool(
                    guardrails_payload.get("authorized_scope_only", True)
                ),
                evidence_required=bool(
                    guardrails_payload.get("evidence_required", True)
                ),
                allow_private_indicators=bool(
                    guardrails_payload.get("allow_private_indicators", False)
                ),
                max_indicators=int(guardrails_payload.get("max_indicators", 25)),
                max_findings=int(guardrails_payload.get("max_findings", 10)),
                max_recommendations=int(
                    guardrails_payload.get("max_recommendations", 12)
                ),
            ),
        )

    def load_schema(self) -> dict[str, Any]:
        """Load the published JSON schema for the report contract."""
        return _load_json(self.schema_path)

    def build(self, payload: Mapping[str, Any]) -> OSINTReport:
        """Validate the payload and return a typed report object."""
        document = _require_mapping(payload, "report")
        guardrails = self._build_guardrails(document.get("guardrails"))
        authorized_scope = bool(document.get("authorized_scope"))
        if guardrails.authorized_scope_only and not authorized_scope:
            raise ReportValidationError(
                "authorized_scope must be true for defensive OSINT reporting."
            )

        indicators = self._build_indicators(document.get("indicators"), guardrails)
        known_indicators = {indicator.value for indicator in indicators}
        findings = self._build_findings(
            document.get("findings"),
            known_indicators=known_indicators,
            guardrails=guardrails,
        )
        next_steps = _require_string_list(document.get("next_steps"), "next_steps")
        if len(next_steps) > guardrails.max_recommendations:
            raise ReportValidationError(
                "next_steps exceeds the configured max_recommendations limit."
            )

        generated_at = document.get("generated_at", _utc_now_iso())
        report_id = document.get(
            "report_id",
            f"osint-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        )

        return OSINTReport(
            report_id=_require_text(report_id, "report_id", max_len=80),
            schema_version=self.config.schema_version,
            generated_at=_validate_iso_datetime(generated_at, "generated_at"),
            subject=_require_text(document.get("subject"), "subject", max_len=160),
            objective=_require_text(
                document.get("objective"), "objective", max_len=240
            ),
            author=_require_text(
                document.get("author", self.config.default_author),
                "author",
                max_len=120,
            ),
            organization=_require_text(
                document.get("organization", self.config.default_organization),
                "organization",
                max_len=120,
            ),
            tlp=_normalize_tlp(document.get("tlp", self.config.default_tlp)),
            authorized_scope=authorized_scope,
            summary=_require_text(document.get("summary"), "summary", max_len=1200),
            indicators=indicators,
            findings=findings,
            next_steps=next_steps,
            guardrails=guardrails,
        )

    def build_dict(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Validate the payload and return a serialized report."""
        return self.build(payload).to_dict()

    def render_markdown(self, report: OSINTReport) -> str:
        """Render a report instance into markdown using the scaffold template."""
        template = self.template_path.read_text(encoding="utf-8")
        context = {
            "report_id": report.report_id,
            "schema_version": report.schema_version,
            "generated_at": report.generated_at,
            "subject": report.subject,
            "objective": report.objective,
            "author": report.author,
            "organization": report.organization,
            "tlp": report.tlp,
            "authorized_scope": "yes" if report.authorized_scope else "no",
            "summary": report.summary,
            "indicator_count": str(len(report.indicators)),
            "finding_count": str(len(report.findings)),
            "indicators_table": self._render_indicators(report.indicators),
            "findings_markdown": self._render_findings(report.findings),
            "next_steps_markdown": self._render_next_steps(report.next_steps),
            "guardrails_markdown": self._render_guardrails(report.guardrails),
        }
        rendered = template
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered.strip() + "\n"

    def render_payload(self, payload: Mapping[str, Any]) -> str:
        """Validate and render a raw payload into markdown."""
        return self.render_markdown(self.build(payload))

    def _build_guardrails(self, payload: Any) -> ReportGuardrails:
        if payload is None:
            return self.config.guardrails
        data = _require_mapping(payload, "guardrails")
        merged = asdict(self.config.guardrails)
        merged.update(data)
        guardrails = ReportGuardrails(
            authorized_scope_only=bool(merged["authorized_scope_only"]),
            evidence_required=bool(merged["evidence_required"]),
            allow_private_indicators=bool(merged["allow_private_indicators"]),
            max_indicators=int(merged["max_indicators"]),
            max_findings=int(merged["max_findings"]),
            max_recommendations=int(merged["max_recommendations"]),
        )
        if guardrails.max_indicators < 1 or guardrails.max_findings < 1:
            raise ReportValidationError("Guardrail limits must be positive integers.")
        if guardrails.max_recommendations < 1:
            raise ReportValidationError("max_recommendations must be positive.")
        return guardrails

    def _build_indicators(
        self, payload: Any, guardrails: ReportGuardrails
    ) -> list[OSINTIndicator]:
        if not isinstance(payload, list) or not payload:
            raise ReportValidationError("indicators must be a non-empty list.")
        if len(payload) > guardrails.max_indicators:
            raise ReportValidationError(
                "indicators exceeds the configured max_indicators limit."
            )

        indicators: list[OSINTIndicator] = []
        seen_values: set[str] = set()
        for idx, raw in enumerate(payload):
            data = _require_mapping(raw, f"indicators[{idx}]")
            indicator_type = _require_text(data.get("type"), f"indicators[{idx}].type")
            normalized_type = indicator_type.lower()
            if normalized_type not in _ALLOWED_INDICATOR_TYPES:
                supported = ", ".join(sorted(_ALLOWED_INDICATOR_TYPES))
                raise ReportValidationError(
                    f"indicators[{idx}].type must be one of: {supported}."
                )
            raw_value = _require_text(data.get("value"), f"indicators[{idx}].value")
            normalized_value = self._normalize_indicator_value(
                normalized_type, raw_value, guardrails
            )
            if normalized_value in seen_values:
                raise ReportValidationError(
                    f"Duplicate indicator detected: {normalized_value}."
                )
            seen_values.add(normalized_value)
            indicators.append(
                OSINTIndicator(
                    type=normalized_type,
                    value=normalized_value,
                    confidence=_require_probability(
                        data.get("confidence", 0.5),
                        f"indicators[{idx}].confidence",
                    ),
                    tags=_require_string_list(data.get("tags", []), f"indicators[{idx}].tags"),
                )
            )
        return indicators

    def _build_findings(
        self,
        payload: Any,
        *,
        known_indicators: set[str],
        guardrails: ReportGuardrails,
    ) -> list[OSINTFinding]:
        if not isinstance(payload, list) or not payload:
            raise ReportValidationError("findings must be a non-empty list.")
        if len(payload) > guardrails.max_findings:
            raise ReportValidationError(
                "findings exceeds the configured max_findings limit."
            )

        findings: list[OSINTFinding] = []
        for idx, raw in enumerate(payload):
            data = _require_mapping(raw, f"findings[{idx}]")
            severity = _require_text(data.get("severity"), f"findings[{idx}].severity")
            normalized_severity = severity.lower()
            if normalized_severity not in _ALLOWED_SEVERITIES:
                supported = ", ".join(sorted(_ALLOWED_SEVERITIES))
                raise ReportValidationError(
                    f"findings[{idx}].severity must be one of: {supported}."
                )

            indicator_refs = _require_string_list(
                data.get("indicator_refs"), f"findings[{idx}].indicator_refs"
            )
            unknown_refs = [ref for ref in indicator_refs if ref not in known_indicators]
            if unknown_refs:
                raise ReportValidationError(
                    f"findings[{idx}].indicator_refs contains unknown indicators: "
                    + ", ".join(sorted(unknown_refs))
                )

            evidence = self._build_evidence(
                data.get("evidence"), field_name=f"findings[{idx}].evidence"
            )
            if guardrails.evidence_required and not evidence:
                raise ReportValidationError(
                    f"findings[{idx}].evidence must not be empty when evidence_required is true."
                )

            recommendations = _require_string_list(
                data.get("recommendations"), f"findings[{idx}].recommendations"
            )
            if len(recommendations) > guardrails.max_recommendations:
                raise ReportValidationError(
                    f"findings[{idx}].recommendations exceeds max_recommendations."
                )

            findings.append(
                OSINTFinding(
                    title=_require_text(data.get("title"), f"findings[{idx}].title", max_len=160),
                    summary=_require_text(
                        data.get("summary"),
                        f"findings[{idx}].summary",
                        max_len=1200,
                    ),
                    severity=normalized_severity,
                    confidence=_require_probability(
                        data.get("confidence"), f"findings[{idx}].confidence"
                    ),
                    indicator_refs=indicator_refs,
                    evidence=evidence,
                    recommendations=recommendations,
                    tags=_require_string_list(
                        data.get("tags", []), f"findings[{idx}].tags"
                    ),
                )
            )
        return findings

    def _build_evidence(self, payload: Any, *, field_name: str) -> list[OSEvidence]:
        if payload is None:
            return []
        if not isinstance(payload, list):
            raise ReportValidationError(f"{field_name} must be a list.")
        evidence: list[OSEvidence] = []
        for idx, raw in enumerate(payload):
            data = _require_mapping(raw, f"{field_name}[{idx}]")
            source_url = _require_text(data.get("source_url"), f"{field_name}[{idx}].source_url")
            parsed = urlparse(source_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ReportValidationError(
                    f"{field_name}[{idx}].source_url must be a valid http(s) URL."
                )
            if (parsed.hostname or "") == "localhost":
                raise ReportValidationError(
                    f"{field_name}[{idx}].source_url must not target localhost."
                )
            evidence.append(
                OSEvidence(
                    source_name=_require_text(
                        data.get("source_name"), f"{field_name}[{idx}].source_name", max_len=120
                    ),
                    source_url=source_url,
                    collected_at=_validate_iso_datetime(
                        data.get("collected_at"), f"{field_name}[{idx}].collected_at"
                    ),
                    detail=_require_text(
                        data.get("detail"), f"{field_name}[{idx}].detail", max_len=1000
                    ),
                )
            )
        return evidence

    @staticmethod
    def _normalize_indicator_value(
        indicator_type: str, value: str, guardrails: ReportGuardrails
    ) -> str:
        if indicator_type == "ip":
            return _validate_public_ip(value, guardrails)
        if indicator_type == "domain":
            return _validate_domain(value)
        if indicator_type == "url":
            return _validate_url(value, guardrails)
        if indicator_type == "hash":
            return _validate_hash(value)
        if indicator_type == "email":
            return _validate_email(value)
        raise ReportValidationError(f"Unsupported indicator type: {indicator_type}.")

    @staticmethod
    def _render_indicators(indicators: list[OSINTIndicator]) -> str:
        lines = [
            "| Type | Value | Confidence | Tags |",
            "| --- | --- | ---: | --- |",
        ]
        for indicator in indicators:
            tags = ", ".join(indicator.tags) if indicator.tags else "-"
            lines.append(
                f"| {indicator.type} | `{indicator.value}` | {indicator.confidence:.2f} | {tags} |"
            )
        return "\n".join(lines)

    @staticmethod
    def _render_findings(findings: list[OSINTFinding]) -> str:
        rendered: list[str] = []
        for finding in findings:
            rendered.append(
                "\n".join(
                    [
                        f"### {finding.title}",
                        f"- Severity: `{finding.severity}`",
                        f"- Confidence: `{finding.confidence:.2f}`",
                        f"- Indicators: {', '.join(f'`{ref}`' for ref in finding.indicator_refs)}",
                        f"- Summary: {finding.summary}",
                        "- Evidence:",
                        *[
                            (
                                f"  - {item.source_name} "
                                f"({item.collected_at}) - {item.source_url} - {item.detail}"
                            )
                            for item in finding.evidence
                        ],
                        "- Recommendations:",
                        *[f"  - {recommendation}" for recommendation in finding.recommendations],
                    ]
                )
            )
        return "\n\n".join(rendered)

    @staticmethod
    def _render_next_steps(next_steps: list[str]) -> str:
        return "\n".join(f"- {step}" for step in next_steps)

    @staticmethod
    def _render_guardrails(guardrails: ReportGuardrails) -> str:
        return "\n".join(
            [
                f"- authorized_scope_only: `{str(guardrails.authorized_scope_only).lower()}`",
                f"- evidence_required: `{str(guardrails.evidence_required).lower()}`",
                f"- allow_private_indicators: `{str(guardrails.allow_private_indicators).lower()}`",
                f"- max_indicators: `{guardrails.max_indicators}`",
                f"- max_findings: `{guardrails.max_findings}`",
                f"- max_recommendations: `{guardrails.max_recommendations}`",
            ]
        )


__all__ = [
    "DEFAULT_DEV_CONFIG_PATH",
    "DEFAULT_SCHEMA_PATH",
    "DEFAULT_SCHEMA_VERSION",
    "DEFAULT_TEMPLATE_PATH",
    "OSEvidence",
    "OSINTFinding",
    "OSINTIndicator",
    "OSINTReport",
    "OSINTReportBuilder",
    "OSINTReportConfig",
    "ReportGuardrails",
    "ReportValidationError",
]
=======
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .osint_guardrails import (
    GuardrailViolation,
    normalize_evidence_records,
    normalize_findings,
    unsafe_dev_options,
    validate_dev_config,
    validate_report_guardrails,
)
from .osint_report_models import ModelValidationError, OSINTReport


TOOL_VERSION = "0.6.0"


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str | Path, payload: Any) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _load_assets_from_inventory(path: str | Path | None) -> list[dict[str, Any]]:
    if not path:
        return []

    inventory_path = Path(path)
    if not inventory_path.exists():
        return []

    payload = load_json(inventory_path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return list(payload.get("assets", []))
    return []


def _default_recommendations() -> dict[str, list[dict[str, Any]]]:
    return {
        "immediate": [],
        "thirty_day": [],
        "long_term": [],
    }


def build_report_dict(config: dict[str, Any], evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    validate_dev_config(config)

    guardrails = config.get("guardrails", {})
    dev = config.get("dev", {})
    scope_config = config.get("scope_defaults", {})
    pii_policy = config.get("guardrails", {}).get("pii_policy", "mask-low-value")
    fail_on_missing_citation = bool(dev.get("fail_on_missing_citation", True))
    source_policy = str(scope_config.get("source_policy", "approved-only"))
    lab_mode = bool(dev.get("lab_mode", False))
    allowed_source_hosts = [str(item) for item in guardrails.get("allowed_source_hosts", [])]
    sample_limit = dev.get("sample_limit")
    if sample_limit is not None:
        sample_limit = int(sample_limit)

    evidence_records = normalize_evidence_records(
        list(evidence_bundle.get("evidence", [])),
        pii_policy=pii_policy,
        fail_on_missing_citation=fail_on_missing_citation,
        source_policy=source_policy,
        lab_mode=lab_mode,
        allowed_source_hosts=allowed_source_hosts,
        sample_limit=sample_limit,
    )
    evidence_ids = {item["id"] for item in evidence_records}

    finding_records = normalize_findings(
        list(evidence_bundle.get("findings", [])),
        evidence_ids=evidence_ids,
    )

    assets = list(evidence_bundle.get("assets", []))
    if not assets:
        assets = _load_assets_from_inventory(config.get("inputs", {}).get("asset_inventory"))

    metadata_overrides = dict(evidence_bundle.get("report_metadata", {}))
    engagement_defaults = dict(config.get("engagement_defaults", {}))
    engagement_defaults.update(evidence_bundle.get("engagement", {}))
    scope_defaults = dict(scope_config)
    scope_defaults.update(evidence_bundle.get("scope", {}))

    report_data = {
        "report_metadata": {
            "title": metadata_overrides.get("title") or f"{config['target']} Exposure Assessment",
            "target": metadata_overrides.get("target") or config["target"],
            "classification": metadata_overrides.get("classification")
            or config.get("render", {}).get("classification", "UNCLASSIFIED // OSINT"),
            "generated_at": metadata_overrides.get("generated_at")
            or datetime.now(timezone.utc).isoformat(),
            "analyst": metadata_overrides.get("analyst") or engagement_defaults.get("requester", "Hancock"),
            "report_profile": metadata_overrides.get("report_profile") or config["profile"],
            "tool_version": metadata_overrides.get("tool_version") or TOOL_VERSION,
            "authorized_use_only": True,
        },
        "engagement": {
            "requester": engagement_defaults.get("requester", "Security Engineering"),
            "business_owner": engagement_defaults.get("business_owner", config["target"]),
            "authorization_reference": engagement_defaults.get("authorization_reference", ""),
            "objective": engagement_defaults.get(
                "objective",
                "Generate a defensive OSINT exposure assessment report.",
            ),
            "report_profile": engagement_defaults.get("report_profile", config["profile"]),
        },
        "scope": {
            "in_scope": scope_defaults.get(
                "in_scope",
                list(config.get("scope", {}).get("authorized_assets", [])),
            ),
            "out_of_scope": scope_defaults.get("out_of_scope", []),
            "collection_constraints": scope_defaults.get(
                "collection_constraints",
                ["Passive evidence only", "Authorized defensive use only"],
            ),
            "source_policy": scope_defaults.get("source_policy", "approved-only"),
        },
        "assets": assets,
        "findings": finding_records,
        "evidence": evidence_records,
        "recommendations": evidence_bundle.get("recommendations", _default_recommendations()),
        "diagrams": list(evidence_bundle.get("diagrams", [])),
    }
    validate_report_guardrails(report_data, config)
    return report_data


def build_report(config: dict[str, Any], evidence_bundle: dict[str, Any]) -> OSINTReport:
    return OSINTReport.from_dict(build_report_dict(config, evidence_bundle))


def render_markdown(report: OSINTReport, *, unsafe_options: list[str] | None = None) -> str:
    data = report.to_dict()
    meta = data["report_metadata"]
    engagement = data["engagement"]
    scope = data["scope"]
    findings = data["findings"]
    evidence = data["evidence"]
    recommendations = data["recommendations"]
    unsafe_options = unsafe_options or []

    lines: list[str] = []
    lines.append(f"# {meta['title']}")
    lines.append("")
    if unsafe_options:
        lines.append("**WARNING:** Generated with non-default developer settings. Not for production distribution.")
        lines.append("")
        lines.append(f"Unsafe options: {', '.join(unsafe_options)}")
        lines.append("")
    lines.extend(
        [
            f"- **Target:** {meta['target']}",
            f"- **Classification:** {meta['classification']}",
            f"- **Generated At:** {meta['generated_at']}",
            f"- **Analyst:** {meta['analyst']}",
            f"- **Profile:** {meta['report_profile']}",
            f"- **Authorization Reference:** {engagement['authorization_reference']}",
            "",
            "## Executive Summary",
            "",
            f"This report summarizes defensive OSINT exposure for **{meta['target']}** within the approved scope. "
            f"It includes {len(findings)} findings across {len(data['assets'])} tracked assets with "
            f"{len(evidence)} cited evidence records.",
            "",
            "## Scope",
            "",
            f"- **In Scope:** {', '.join(scope['in_scope']) or 'None provided'}",
            f"- **Out of Scope:** {', '.join(scope['out_of_scope']) or 'None provided'}",
            f"- **Collection Constraints:** {', '.join(scope['collection_constraints']) or 'None provided'}",
            f"- **Source Policy:** {scope['source_policy']}",
            "",
            "## Key Findings",
            "",
            "| ID | Title | Severity | Confidence | Risk Score |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for finding in findings:
        lines.append(
            f"| {finding['id']} | {finding['title']} | {finding['severity']} | "
            f"{finding['confidence']:.1f}% | {finding['risk_score']:.1f} |"
        )

    lines.extend(["", "## Detailed Findings", ""])
    for finding in findings:
        lines.extend(
            [
                f"### {finding['id']} - {finding['title']}",
                f"- **Severity:** {finding['severity']}",
                f"- **Confidence:** {finding['confidence']:.1f}%",
                f"- **Risk Score:** {finding['risk_score']:.1f}",
                f"- **Status:** {finding['status']}",
                f"- **Summary:** {finding['summary']}",
                f"- **Assets:** {', '.join(finding['asset_refs']) or 'None'}",
                f"- **Evidence:** {', '.join(finding['evidence_refs']) or 'None'}",
                f"- **MITRE ATT&CK:** {', '.join(finding['mitre_attack']) or 'None'}",
                f"- **NIST / Control Mapping:** {', '.join(finding['nist_controls']) or 'None'}",
                "",
            ]
        )

    lines.extend(["## Evidence Register", ""])
    for item in evidence:
        lines.extend(
            [
                f"### {item['id']} - {item['source_name']}",
                f"- **Source URL:** {item['source_url']}",
                f"- **Retrieved At:** {item['retrieved_at']}",
                f"- **Sensitivity:** {item['sensitivity']}",
                f"- **Claim:** {item['claim']}",
            ]
        )
        if item.get("raw_artifact_path"):
            lines.append(f"- **Raw Artifact Path:** {item['raw_artifact_path']}")
        if item.get("notes"):
            lines.append(f"- **Notes:** {item['notes']}")
        lines.append("")

    lines.extend(["## Recommendations", ""])
    for label, bucket in (
        ("Immediate", recommendations["immediate"]),
        ("30-Day", recommendations["thirty_day"]),
        ("Long-Term", recommendations["long_term"]),
    ):
        lines.append(f"### {label}")
        if not bucket:
            lines.append("- None provided")
        for item in bucket:
            due = f" ({item['due_in_days']} days)" if "due_in_days" in item else ""
            lines.append(
                f"- `{item['priority']}` {item['action']} — owner: {item['owner']}{due}"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def summarize_report(report: OSINTReport, audience: str) -> str:
    data = report.to_dict()
    findings = data["findings"]
    highest = max((item["risk_score"] for item in findings), default=0)
    if audience == "ciso":
        return (
            f"{data['report_metadata']['target']} has {len(findings)} tracked findings. "
            f"Highest risk score: {highest:.1f}/10. Focus on ownership, external exposure reduction, and remediation SLA."
        )
    if audience == "soc":
        return (
            f"{data['report_metadata']['target']} has {len(findings)} findings with {len(data['evidence'])} evidence records. "
            "Prioritize verification, monitoring coverage, and incident-response routing."
        )
    return (
        f"{data['report_metadata']['target']} exposure assessment contains {len(findings)} findings "
        f"across {len(data['assets'])} assets."
    )


def _write_text(path: str | Path, content: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")


def _write_build_outputs(report: OSINTReport, config: dict[str, Any], output: str | None, json_output: str | None) -> None:
    unsafe = unsafe_dev_options(config)
    markdown_path = output or config.get("outputs", {}).get("markdown")
    json_path = json_output or config.get("outputs", {}).get("json")

    if markdown_path:
        _write_text(markdown_path, render_markdown(report, unsafe_options=unsafe))
    if json_path:
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        save_json(json_path, report.to_dict())


def _load_and_validate_report(path: str | Path) -> OSINTReport:
    return OSINTReport.from_dict(load_json(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hancock OSINT reporting prototype")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build Markdown / JSON report outputs")
    build_parser.add_argument("--config", required=True, help="Path to JSON config")
    build_parser.add_argument("--evidence", required=True, help="Path to evidence bundle JSON")
    build_parser.add_argument("--output", help="Markdown output path")
    build_parser.add_argument("--json-output", help="JSON output path")

    validate_parser = subparsers.add_parser("validate", help="Validate config + evidence or a report JSON")
    validate_parser.add_argument("--config", help="Path to JSON config")
    validate_parser.add_argument("--evidence", help="Path to evidence bundle JSON")
    validate_parser.add_argument("--report", help="Path to normalized report JSON")

    render_parser = subparsers.add_parser("render", help="Render Markdown from a normalized report JSON")
    render_parser.add_argument("--report", required=True, help="Path to normalized report JSON")
    render_parser.add_argument("--output", required=True, help="Markdown output path")

    summarize_parser = subparsers.add_parser("summarize", help="Print a short summary for an audience")
    summarize_parser.add_argument("--report", required=True, help="Path to normalized report JSON")
    summarize_parser.add_argument("--audience", default="joint", choices=["joint", "ciso", "soc"])

    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            config = load_json(args.config)
            evidence_bundle = load_json(args.evidence)
            report = build_report(config, evidence_bundle)
            _write_build_outputs(report, config, args.output, args.json_output)
            return 0

        if args.command == "validate":
            if args.report:
                _load_and_validate_report(args.report)
                return 0
            if not args.config or not args.evidence:
                raise GuardrailViolation("validate requires --report or both --config and --evidence")
            config = load_json(args.config)
            evidence_bundle = load_json(args.evidence)
            build_report(config, evidence_bundle)
            return 0

        if args.command == "render":
            report = _load_and_validate_report(args.report)
            _write_text(args.output, render_markdown(report))
            return 0

        if args.command == "summarize":
            report = _load_and_validate_report(args.report)
            print(summarize_report(report, args.audience))
            return 0

        raise GuardrailViolation(f"unsupported command: {args.command}")
    except (GuardrailViolation, ModelValidationError, FileNotFoundError, json.JSONDecodeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
>>>>>>> 67b2a2f85225a4610b2ed4affb5b23596733c8e7
