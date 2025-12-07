"""Simple admin authentication with session management."""
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

# In-memory session storage (will be lost on restart)
_sessions: Dict[str, datetime] = {}

# Session timeout (24 hours)
SESSION_TIMEOUT = timedelta(hours=24)


def verify_admin_password(password: str) -> bool:
    """Verify admin password against environment variable.

    Args:
        password: Password to verify

    Returns:
        True if password matches ADMIN_PASSWORD env var
    """
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        raise ValueError("ADMIN_PASSWORD environment variable not set")
    return password == admin_password


def create_session() -> str:
    """Create a new session token.

    Returns:
        Session token (UUID)
    """
    token = str(uuid.uuid4())
    _sessions[token] = datetime.utcnow()
    return token


def verify_session(token: str) -> bool:
    """Verify if session token is valid and not expired.

    Args:
        token: Session token to verify

    Returns:
        True if session is valid and not expired
    """
    if token not in _sessions:
        return False

    session_time = _sessions[token]
    if datetime.utcnow() - session_time > SESSION_TIMEOUT:
        # Session expired, remove it
        del _sessions[token]
        return False

    # Update session time (rolling timeout)
    _sessions[token] = datetime.utcnow()
    return True


def delete_session(token: str) -> None:
    """Delete a session token (logout).

    Args:
        token: Session token to delete
    """
    if token in _sessions:
        del _sessions[token]


def cleanup_expired_sessions() -> int:
    """Remove all expired sessions.

    Returns:
        Number of sessions removed
    """
    now = datetime.utcnow()
    expired = [
        token for token, session_time in _sessions.items()
        if now - session_time > SESSION_TIMEOUT
    ]
    for token in expired:
        del _sessions[token]
    return len(expired)
