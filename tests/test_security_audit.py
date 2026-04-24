"""Tests for qa/security_audit.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SECURITY_AUDIT_PATH = REPO_ROOT / "qa" / "security_audit.py"


def _load_security_audit_module():
    spec = importlib.util.spec_from_file_location("security_audit_under_test", SECURITY_AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_scan_for_secrets_detects_real_findings_and_skips_examples(tmp_path, monkeypatch):
    security_audit = _load_security_audit_module()

    secret_file = tmp_path / "bad.py"
    secret_file.write_text(
        '\n'.join(
            [
                'password = "supersecret12"',
                'demo_value = os.getenv("OPENAI_API_KEY", "example-value")',
                'example_token = "sk-exampletokenvalue1234567890"',
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(security_audit, "EXCLUDE", [])

    findings = security_audit.scan_for_secrets()

    assert findings == [
        {
            "file": "bad.py",
            "line": 1,
            "type": "hardcoded credential",
        }
    ]


def test_scan_for_secrets_reads_each_file_once(tmp_path, monkeypatch):
    security_audit = _load_security_audit_module()

    secret_file = tmp_path / "secret.py"
    clean_file = tmp_path / "clean.py"
    secret_file.write_text('token = "supersecret12"\n', encoding="utf-8")
    clean_file.write_text('print("hello")\n', encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(security_audit, "EXCLUDE", [])

    read_counts: dict[str, int] = {}
    original_read_text = Path.read_text

    def counting_read_text(self: Path, *args, **kwargs):
        path_key = str(self)
        read_counts[path_key] = read_counts.get(path_key, 0) + 1
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counting_read_text)

    findings = security_audit.scan_for_secrets()

    assert any(f["file"] == "secret.py" for f in findings)
    assert read_counts == {
        "clean.py": 1,
        "secret.py": 1,
    }
