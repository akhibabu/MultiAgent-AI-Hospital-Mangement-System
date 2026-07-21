"""Middleware that verifies Bearer JWTs on protected API paths."""

from typing import Callable, Iterable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.auth.jwt import decode_supabase_jwt
from app.core.logging import get_logger

logger = get_logger("hospital_ai.auth.middleware")

# Paths that require a valid Supabase access token.
PROTECTED_PREFIXES: tuple[str, ...] = (
    "/auth/me",
    "/auth/logout",
)

# Exact public paths under /auth that skip JWT checks.
PUBLIC_AUTH_PATHS: frozenset[str] = frozenset(
    {
        "/auth/login",
    }
)


def _is_protected(path: str, prefixes: Iterable[str]) -> bool:
    if path in PUBLIC_AUTH_PATHS:
        return False
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


class SupabaseJWTMiddleware(BaseHTTPMiddleware):
    """
    Reject unauthenticated requests to protected routes early.

    Route handlers still use `Depends(get_current_user)` for typed access
    to the verified profile. This middleware is a first-line gate.
    """

    def __init__(
        self,
        app,
        protected_prefixes: Iterable[str] = PROTECTED_PREFIXES,
    ):
        super().__init__(app)
        self.protected_prefixes = tuple(protected_prefixes)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if request.method == "OPTIONS" or not _is_protected(path, self.protected_prefixes):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = decode_supabase_jwt(token)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.user_id = str(payload.user_id)
        request.state.token_payload = payload
        return await call_next(request)
