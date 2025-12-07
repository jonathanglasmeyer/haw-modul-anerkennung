"""Tests for authentication and session management."""
import pytest
import os
from matching.auth import (
    verify_admin_password,
    create_session,
    verify_session,
    delete_session,
)


class TestAdminPasswordAuth:
    """Test admin password verification."""

    def test_verify_admin_password_correct(self, monkeypatch):
        """Test verifying correct admin password."""
        monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
        assert verify_admin_password("test-password") is True

    def test_verify_admin_password_incorrect(self, monkeypatch):
        """Test verifying incorrect admin password."""
        monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
        assert verify_admin_password("wrong-password") is False

    def test_verify_admin_password_empty(self, monkeypatch):
        """Test verifying empty password."""
        monkeypatch.setenv("ADMIN_PASSWORD", "test-password")
        assert verify_admin_password("") is False

    def test_verify_admin_password_missing_env(self, monkeypatch):
        """Test when ADMIN_PASSWORD env var is missing."""
        monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
        # Should raise ValueError when env var is missing
        with pytest.raises(ValueError, match="ADMIN_PASSWORD"):
            verify_admin_password("any-password")


class TestSessionManagement:
    """Test session token management."""

    def test_create_session_generates_token(self):
        """Test that create_session generates a valid token."""
        token = create_session()
        assert isinstance(token, str)
        assert len(token) > 0
        # Should be a UUID format
        assert len(token) == 36  # UUID format: 8-4-4-4-12

    def test_create_session_is_valid(self):
        """Test that created session is immediately valid."""
        token = create_session()
        assert verify_session(token) is True

    def test_verify_session_valid_token(self):
        """Test verifying a valid session token."""
        token = create_session()
        assert verify_session(token) is True

    def test_verify_session_invalid_token(self):
        """Test verifying an invalid session token."""
        assert verify_session("invalid-token-12345") is False

    def test_verify_session_empty_token(self):
        """Test verifying an empty token."""
        assert verify_session("") is False

    def test_verify_session_none_token(self):
        """Test verifying a None token."""
        assert verify_session(None) is False

    def test_delete_session_removes_token(self):
        """Test that delete_session removes the token."""
        token = create_session()
        assert verify_session(token) is True

        delete_session(token)
        assert verify_session(token) is False

    def test_delete_session_invalid_token_is_safe(self):
        """Test that deleting an invalid token doesn't raise."""
        # Should not raise an exception
        delete_session("non-existent-token")

    def test_session_lifecycle(self):
        """Test full session lifecycle: create, verify, delete."""
        # Create session
        token = create_session()
        assert verify_session(token) is True

        # Delete session
        delete_session(token)
        assert verify_session(token) is False

    def test_multiple_sessions(self):
        """Test that multiple sessions can coexist."""
        token1 = create_session()
        token2 = create_session()
        token3 = create_session()

        assert token1 != token2 != token3
        assert verify_session(token1) is True
        assert verify_session(token2) is True
        assert verify_session(token3) is True

        # Delete one session
        delete_session(token2)
        assert verify_session(token1) is True
        assert verify_session(token2) is False
        assert verify_session(token3) is True
