import os
from fastapi import HTTPException, Request

COOKIE_NAME = "ij_pid"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # one week, well beyond event

MOD_COOKIE_NAME = "ij_mod"
MOD_COOKIE_MAX_AGE = 60 * 60 * 12  # 12 hours, well past the event


def _expected_token() -> str:
    expected = os.environ.get("MODERATOR_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="MODERATOR_TOKEN not configured")
    return expected


def check_moderator_password(submitted: str) -> bool:
    """True if the submitted token matches the env var."""
    return submitted == _expected_token()


def require_moderator(request: Request) -> None:
    """Raise 404 if the request lacks a valid moderator cookie."""
    cookie_val = request.cookies.get(MOD_COOKIE_NAME)
    if not cookie_val:
        raise HTTPException(status_code=404)
    if not check_moderator_password(cookie_val):
        raise HTTPException(status_code=404)
