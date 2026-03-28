"""Tests for the input_validator module."""

import pytest

from input_validator import (
    detect_ioc_type,
    validate_payload,
    validate_mode,
    validate_siem,
    validate_ciso_output,
    validate_ioc_type,
    sanitize_string,
    VALID_MODES,
    VALID_SIEMS,
    VALID_IOC_TYPES,
    VALID_CISO_OUTPUTS,
)


# ── detect_ioc_type ──────────────────────────────────────────────────────────

class TestDetectIocType:
    def test_ipv4(self):
        assert detect_ioc_type("8.8.8.8") == "ipv4"
        assert detect_ioc_type("192.168.1.1") == "ipv4"
        assert detect_ioc_type("0.0.0.0") == "ipv4"

    def test_ipv6(self):
        assert detect_ioc_type("::1") == "ipv6"
        assert detect_ioc_type("2001:db8::1") == "ipv6"
        assert detect_ioc_type("fe80::1%eth0") == "ipv6"

    def test_md5(self):
        assert detect_ioc_type("d41d8cd98f00b204e9800998ecf8427e") == "md5"

    def test_sha1(self):
        assert detect_ioc_type("da39a3ee5e6b4b0d3255bfef95601890afd80709") == "sha1"

    def test_sha256(self):
        h = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert detect_ioc_type(h) == "sha256"

    def test_url(self):
        assert detect_ioc_type("https://evil.com/payload") == "url"
        assert detect_ioc_type("http://192.168.1.1/shell") == "url"

    def test_cve(self):
        assert detect_ioc_type("CVE-2024-12345") == "cve"
        assert detect_ioc_type("cve-2023-0001") == "cve"

    def test_email(self):
        assert detect_ioc_type("attacker@evil.com") == "email"

    def test_domain(self):
        assert detect_ioc_type("evil.com") == "domain"
        assert detect_ioc_type("sub.evil.co.uk") == "domain"

    def test_unknown(self):
        assert detect_ioc_type("random string") == "unknown"
        assert detect_ioc_type("") == "unknown"

    def test_whitespace_stripped(self):
        assert detect_ioc_type("  8.8.8.8  ") == "ipv4"


# ── validate_payload ──────────────────────────────────────────────────────────

class TestValidatePayload:
    def test_valid_payload(self):
        errors = validate_payload(
            {"alert": "Suspicious login", "severity": "high"},
            required=["alert"],
        )
        assert errors == []

    def test_missing_required_field(self):
        errors = validate_payload(
            {"severity": "high"},
            required=["alert"],
        )
        assert any("alert is required" in e for e in errors)

    def test_empty_required_field(self):
        errors = validate_payload(
            {"alert": "  ", "severity": "high"},
            required=["alert"],
        )
        assert any("alert is required" in e for e in errors)

    def test_empty_list_required(self):
        errors = validate_payload(
            {"indicators": []},
            required=["indicators"],
        )
        assert any("indicators is required" in e for e in errors)

    def test_field_too_long(self):
        errors = validate_payload(
            {"alert": "x" * 30_000},
            max_lengths={"alert": 20_000},
        )
        assert any("exceeds maximum length" in e for e in errors)

    def test_non_dict_body(self):
        errors = validate_payload("not a dict")
        assert errors == ["request body must be a JSON object"]

    def test_default_max_lengths_applied(self):
        errors = validate_payload(
            {"mode": "x" * 100},
        )
        assert any("mode" in e and "exceeds" in e for e in errors)

    def test_multiple_errors(self):
        errors = validate_payload(
            {"alert": "", "mode": "x" * 100},
            required=["alert"],
        )
        assert len(errors) >= 2


# ── validate_mode ─────────────────────────────────────────────────────────────

class TestValidateMode:
    def test_valid_modes(self):
        for mode in VALID_MODES:
            assert validate_mode(mode) is None

    def test_invalid_mode(self):
        err = validate_mode("hacker")
        assert err is not None
        assert "invalid mode" in err


# ── validate_siem ─────────────────────────────────────────────────────────────

class TestValidateSiem:
    def test_valid_siems(self):
        for siem in VALID_SIEMS:
            assert validate_siem(siem) is None

    def test_invalid_siem(self):
        err = validate_siem("unknown_siem")
        assert err is not None
        assert "invalid siem" in err


# ── validate_ciso_output ──────────────────────────────────────────────────────

class TestValidateCisoOutput:
    def test_valid_outputs(self):
        for output in VALID_CISO_OUTPUTS:
            assert validate_ciso_output(output) is None

    def test_invalid_output(self):
        err = validate_ciso_output("invalid")
        assert err is not None
        assert "invalid output" in err


# ── validate_ioc_type ─────────────────────────────────────────────────────────

class TestValidateIocType:
    def test_valid_types(self):
        for t in VALID_IOC_TYPES:
            assert validate_ioc_type(t) is None

    def test_invalid_type(self):
        err = validate_ioc_type("invalid_type")
        assert err is not None
        assert "invalid IOC type" in err


# ── sanitize_string ───────────────────────────────────────────────────────────

class TestSanitizeString:
    def test_strip_whitespace(self):
        assert sanitize_string("  hello  ") == "hello"

    def test_truncate(self):
        result = sanitize_string("a" * 200, max_length=100)
        assert len(result) == 100

    def test_empty_string(self):
        assert sanitize_string("") == ""

    def test_no_truncation_needed(self):
        assert sanitize_string("short") == "short"


# ── Constants sanity ──────────────────────────────────────────────────────────

class TestConstants:
    def test_valid_modes_frozen(self):
        with pytest.raises(AttributeError):
            VALID_MODES.add("new")

    def test_valid_siems_frozen(self):
        with pytest.raises(AttributeError):
            VALID_SIEMS.add("new")
