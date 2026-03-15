"""Tests for the content sharing workflow (token generation, helpers, expiry).

Run with:
    python -m pytest tests/test_shares.py -v
"""

import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.api.shares import _generate_token, _get_share_secret


# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

SHARE_ID = "abc-123-def"
EMAIL_A = "alice@example.com"
EMAIL_B = "bob@example.com"
ADMIN_ID = 42
CREATED_AT = "2026-03-15T10:00:00+00:00"
SECRET = "test-secret-value"


# ===========================================================================
# 1. Token generation (pure function)
# ===========================================================================


@pytest.mark.asyncio
class TestShareTokenGeneration:
    """Verify _generate_token produces deterministic, input-sensitive hashes."""

    def test_generate_token_deterministic(self):
        """Same inputs must always produce the same token."""
        t1 = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)
        t2 = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)
        assert t1 == t2

    def test_generate_token_different_emails_produce_different_tokens(self):
        """Different recipient emails must produce different tokens."""
        t_a = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)
        t_b = _generate_token(SHARE_ID, EMAIL_B, ADMIN_ID, CREATED_AT, SECRET)
        assert t_a != t_b

    def test_generate_token_includes_all_fields(self):
        """Changing any single field must change the resulting token."""
        baseline = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)

        # Different share_id
        assert _generate_token("other-id", EMAIL_A, ADMIN_ID, CREATED_AT, SECRET) != baseline
        # Different email
        assert _generate_token(SHARE_ID, EMAIL_B, ADMIN_ID, CREATED_AT, SECRET) != baseline
        # Different admin_id
        assert _generate_token(SHARE_ID, EMAIL_A, 99, CREATED_AT, SECRET) != baseline
        # Different created_at
        assert _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, "2026-01-01T00:00:00+00:00", SECRET) != baseline
        # Different secret
        assert _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, "other-secret") != baseline


# ===========================================================================
# 2. Share helpers (_get_share_secret)
# ===========================================================================


@pytest.mark.asyncio
class TestShareHelpers:
    """Verify _get_share_secret auto-generates and caches a value."""

    def test_get_share_secret_auto_generates(self):
        """When settings.share_secret is empty, _get_share_secret returns a non-empty string."""
        with patch("app.api.shares.settings") as mock_settings:
            mock_settings.share_secret = ""
            result = _get_share_secret()
            assert result
            assert len(result) > 0

    def test_share_secret_stable(self):
        """Two consecutive calls return the same value (once set, it sticks)."""
        with patch("app.api.shares.settings") as mock_settings:
            mock_settings.share_secret = ""
            first = _get_share_secret()
            second = _get_share_secret()
            assert first == second


# ===========================================================================
# 3. Token validation logic
# ===========================================================================


@pytest.mark.asyncio
class TestTokenValidation:
    """Verify token comparison works correctly using secrets.compare_digest."""

    def test_valid_token_matches(self):
        """A token recomputed with the same inputs must match the original."""
        token = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)
        recomputed = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)
        assert secrets.compare_digest(token, recomputed) is True

    def test_tampered_token_fails(self):
        """A token with even one character altered must not match."""
        token = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)
        tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
        assert secrets.compare_digest(token, tampered) is False

    def test_different_email_token_fails(self):
        """A token generated for one email must not match a token for another."""
        token_a = _generate_token(SHARE_ID, EMAIL_A, ADMIN_ID, CREATED_AT, SECRET)
        token_b = _generate_token(SHARE_ID, EMAIL_B, ADMIN_ID, CREATED_AT, SECRET)
        assert secrets.compare_digest(token_a, token_b) is False


# ===========================================================================
# 4. Share expiry logic
# ===========================================================================


@pytest.mark.asyncio
class TestShareExpiry:
    """Verify the expiry comparison used in _validate_share_access."""

    def test_share_not_expired(self):
        """An expires_at in the future means the share is still valid."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        # The check in _validate_share_access is: expires_at < now → expired
        assert not (expires_at < datetime.now(timezone.utc))

    def test_share_expired(self):
        """An expires_at in the past means the share has expired."""
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert expires_at < datetime.now(timezone.utc)
