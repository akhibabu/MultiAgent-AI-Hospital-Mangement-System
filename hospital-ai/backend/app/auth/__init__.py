"""Authentication package — Supabase Auth + JWT dependencies."""

from app.auth.dependencies import (
    AccessToken,
    AuthenticatedPayload,
    CurrentUser,
    get_access_token,
    get_current_user,
    get_token_payload,
)
from app.auth.service import AuthService, auth_service

__all__ = [
    "AccessToken",
    "AuthenticatedPayload",
    "AuthService",
    "CurrentUser",
    "auth_service",
    "get_access_token",
    "get_current_user",
    "get_token_payload",
]
