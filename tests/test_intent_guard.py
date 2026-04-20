#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
"""Tests for security.intent_guard module."""
import pytest
from security.intent_guard import verify_intent_and_scope, gate_actions, DISALLOWED
from security.authz import Scope


class TestIntentGuard:
    """Test intent verification and action gating."""

    def test_verify_valid_intent(self):
        """Test that valid intents pass verification."""
        scopes = [Scope(name="authorized")]
        verify_intent_and_scope(
            goal="Enumerate subdomains for example.com within authorized scope",
            mode="pentest",
            scopes=scopes
        )
        # Should not raise

    def test_verify_disallowed_intent_ransomware(self):
        """Test that ransomware intent is blocked."""
        scopes = [Scope(name="authorized")]
        with pytest.raises(PermissionError, match="Intent not authorized"):
            verify_intent_and_scope(
                goal="Deploy ransomware to test.com",
                mode="pentest",
                scopes=scopes
            )

    def test_verify_disallowed_intent_ddos(self):
        """Test that DDoS intent is blocked."""
        scopes = [Scope(name="authorized")]
        with pytest.raises(PermissionError, match="Intent not authorized"):
            verify_intent_and_scope(
                goal="Launch DDoS attack against target",
                mode="pentest",
                scopes=scopes
            )

    def test_verify_no_authorized_scope(self):
        """Test that missing authorized scope is blocked."""
        scopes = [Scope(name="read_only")]
        with pytest.raises(PermissionError, match="No authorized testing scope"):
            verify_intent_and_scope(
                goal="Scan network for vulnerabilities",
                mode="pentest",
                scopes=scopes
            )

    def test_verify_unknown_mode(self):
        """Test that unknown mode is blocked."""
        scopes = [Scope(name="authorized")]
        with pytest.raises(PermissionError, match="Unknown mode"):
            verify_intent_and_scope(
                goal="Test security",
                mode="unknown_mode",
                scopes=scopes
            )

    def test_gate_actions_default_no_execute(self):
        """Test that actions are gated with execute=False by default."""
        scopes = [Scope(name="authorized")]
        actions = [
            {"stage": "recon", "suggestions": "Use nmap"},
            {"stage": "exploit", "suggestions": "Test SQLi"},
        ]
        gated = gate_actions(actions, "pentest", scopes)

        assert len(gated) == 2
        assert all(act["execute"] is False for act in gated)
        assert gated[0]["stage"] == "recon"
        assert gated[1]["stage"] == "exploit"

    def test_all_disallowed_terms(self):
        """Test that all disallowed terms are properly blocked."""
        scopes = [Scope(name="authorized")]
        for term in DISALLOWED:
            with pytest.raises(PermissionError):
                verify_intent_and_scope(
                    goal=f"Test {term} on target",
                    mode="pentest",
                    scopes=scopes
                )
