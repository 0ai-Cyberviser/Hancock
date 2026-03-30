"""Authentication module for Hancock API.

Provides JWT token generation/validation, role-based access control,
and authentication audit logging for the Hancock REST API.

Usage:
    from auth import TokenManager, AuthAuditor, Role

    mgr = TokenManager(secret="...", issuer="hancock")
    token = mgr.issue_token(subject="admin", role=Role.ADMIN)
    payload = mgr.verify_token(token)

    auditor = AuthAuditor()
    auditor.log_auth_event("success", ip="10.0.0.1", subject="admin")
"""
from __future__ import annotations

import hashlib
import hmac as _hmac
import logging
import os
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)

# ── Optional JWT dependency ──────────────────────────────────────────────────
try:
    import jwt
except ImportError:  # pragma: no cover
    jwt = None  # type: ignore[assignment]

# ── Roles ────────────────────────────────────────────────────────────────────


class Role(str, Enum):
    """API access roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    READONLY = "readonly"


ALL_ROLES = tuple(r.value for r in Role)

# ── Token Manager ────────────────────────────────────────────────────────────


class TokenManager:
    """Issue and verify JWT tokens for Hancock API authentication.

    Parameters
    ----------
    secret : str
        HMAC secret used for HS256 signing.  Defaults to
        ``HANCOCK_JWT_SECRET`` env var.
    issuer : str
        ``iss`` claim written into every token.
    default_ttl : int
        Default token lifetime in seconds (default: 3600 = 1 h).
    refresh_ttl : int
        Lifetime of refresh tokens in seconds (default: 86400 = 24 h).
    """

    ALGORITHM = "HS256"

    def __init__(
        self,
        secret: str = "",
        issuer: str = "hancock",
        default_ttl: int = 3600,
        refresh_ttl: int = 86400,
    ):
        self._secret = secret or os.getenv("HANCOCK_JWT_SECRET", "")
        self._issuer = issuer
        self._default_ttl = default_ttl
        self._refresh_ttl = refresh_ttl

    @property
    def default_ttl(self) -> int:
        """Default access token lifetime in seconds."""
        return self._default_ttl

    @property
    def enabled(self) -> bool:
        """True when a JWT secret is configured and PyJWT is installed."""
        return bool(self._secret and jwt is not None)

    # ── Issue ────────────────────────────────────────────────────────────────

    def issue_token(
        self,
        subject: str,
        role: Role = Role.ANALYST,
        ttl: Optional[int] = None,
    ) -> str:
        """Return a signed JWT access token.

        Raises ``RuntimeError`` if JWT support is not available.
        """
        if not self.enabled:
            raise RuntimeError(
                "JWT not available: set HANCOCK_JWT_SECRET and install PyJWT"
            )
        now = int(time.time())
        payload = {
            "sub": subject,
            "role": role.value if isinstance(role, Role) else str(role),
            "iss": self._issuer,
            "iat": now,
            "exp": now + (ttl if ttl is not None else self._default_ttl),
            "type": "access",
        }
        return jwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    def issue_refresh_token(self, subject: str, role: Role = Role.ANALYST) -> str:
        """Return a signed JWT refresh token (longer TTL, type=refresh)."""
        if not self.enabled:
            raise RuntimeError(
                "JWT not available: set HANCOCK_JWT_SECRET and install PyJWT"
            )
        now = int(time.time())
        payload = {
            "sub": subject,
            "role": role.value if isinstance(role, Role) else str(role),
            "iss": self._issuer,
            "iat": now,
            "exp": now + self._refresh_ttl,
            "type": "refresh",
        }
        return jwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    # ── Verify ───────────────────────────────────────────────────────────────

    def verify_token(self, token: str, *, expected_type: str = "access") -> dict:
        """Decode *token* and validate claims.

        Returns the decoded payload dict on success.
        Raises ``ValueError`` with a human-readable message on failure.
        """
        if not self.enabled:
            raise RuntimeError(
                "JWT not available: set HANCOCK_JWT_SECRET and install PyJWT"
            )
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self.ALGORITHM],
                issuer=self._issuer,
                options={"require": ["sub", "role", "exp", "iss", "iat", "type"]},
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token expired")
        except jwt.InvalidIssuerError:
            raise ValueError("Invalid token issuer")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}")
        if payload.get("type") != expected_type:
            raise ValueError(
                f"Wrong token type: expected {expected_type}, "
                f"got {payload.get('type')}"
            )
        if payload.get("role") not in ALL_ROLES:
            raise ValueError(f"Unknown role: {payload.get('role')}")
        return payload

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self, refresh_token: str) -> dict:
        """Exchange a valid refresh token for new access + refresh tokens.

        Returns ``{"access_token": "...", "refresh_token": "...", "expires_in": N}``.
        Raises ``ValueError`` on invalid/expired refresh token.
        """
        payload = self.verify_token(refresh_token, expected_type="refresh")
        subject = payload["sub"]
        role = Role(payload["role"])
        return {
            "access_token": self.issue_token(subject, role),
            "refresh_token": self.issue_refresh_token(subject, role),
            "expires_in": self._default_ttl,
            "token_type": "Bearer",
        }


# ── Auth Auditor ─────────────────────────────────────────────────────────────


class AuthAuditor:
    """Structured audit logging for authentication events."""

    def __init__(self, logger_name: str = "hancock.auth"):
        self._logger = logging.getLogger(logger_name)

    def log_auth_event(
        self,
        outcome: str,
        *,
        ip: str = "",
        subject: str = "",
        method: str = "",
        endpoint: str = "",
        reason: str = "",
    ) -> None:
        """Record an authentication event.

        Parameters
        ----------
        outcome : str
            ``"success"``, ``"failure"``, or ``"denied"``.
        ip : str
            Client IP address.
        subject : str
            Authenticated user/service identifier.
        method : str
            Auth method used (``"bearer"``, ``"jwt"``, ``"webhook_hmac"``).
        endpoint : str
            The API endpoint being accessed.
        reason : str
            Reason for failure/denial (empty on success).
        """
        extra = {
            "auth_outcome": outcome,
            "auth_ip": ip,
            "auth_subject": subject,
            "auth_method": method,
            "auth_endpoint": endpoint,
        }
        if outcome == "success":
            self._logger.info(
                "AUTH %s: %s via %s -> %s",
                outcome.upper(), subject or "anonymous", method, endpoint,
                extra=extra,
            )
        else:
            extra["auth_reason"] = reason
            self._logger.warning(
                "AUTH %s: %s via %s -> %s (%s)",
                outcome.upper(), ip, method, endpoint, reason,
                extra=extra,
            )


# ── Bearer / API-key check (standalone helper) ──────────────────────────────


def check_bearer_token(header_value: str, expected_key: str) -> bool:
    """Constant-time comparison of Bearer token against *expected_key*."""
    token = header_value.removeprefix("Bearer ").strip()
    return _hmac.compare_digest(token, expected_key)


def check_webhook_signature(
    body: bytes, signature_header: str, secret: str
) -> bool:
    """Verify HMAC-SHA256 webhook signature."""
    if not secret:
        return True  # Signature verification disabled
    expected = "sha256=" + _hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return _hmac.compare_digest(signature_header, expected)
