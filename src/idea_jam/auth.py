import os
from fastapi import HTTPException

COOKIE_NAME = "ij_pid"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # one week, well beyond event


def require_moderator(token: str) -> None:
    """Raise HTTPException if the supplied path token doesn't match MODERATOR_TOKEN env var."""
    expected = os.environ.get("MODERATOR_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="MODERATOR_TOKEN not configured")
    if token != expected:
        raise HTTPException(status_code=404)  # don't leak existence
