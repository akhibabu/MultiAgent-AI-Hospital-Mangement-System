"""Supabase JWT verification (HS256 legacy + ES256 JWKS)."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client

logger = get_logger("hospital_ai.auth.jwt")


@dataclass(frozen=True)
class TokenPayload:
    user_id: UUID
    email: str | None
    role: str | None
    raw: Dict[str, Any]


@lru_cache
def _load_jwks() -> Dict[str, Any]:
    settings = get_settings()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    response = get_http_client().get(url)
    response.raise_for_status()
    return response.json()


def _public_key_for_token(token: str):
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg", "")

    jwks = _load_jwks()
    keys = jwks.get("keys", [])
    matching = next((k for k in keys if k.get("kid") == kid), None)
    if matching is None and keys:
        matching = keys[0]
    if matching is None:
        raise jwt.InvalidTokenError("No JWKS signing keys available")

    if alg.startswith("ES") or matching.get("kty") == "EC":
        return ECAlgorithm.from_jwk(matching)
    if alg.startswith("RS") or matching.get("kty") == "RSA":
        return RSAAlgorithm.from_jwk(matching)
    raise jwt.InvalidTokenError(f"Unsupported signing algorithm: {alg}")


def _decode_with_key(token: str, key, algorithms: list[str]) -> Dict[str, Any]:
    return jwt.decode(
        token,
        key,
        algorithms=algorithms,
        audience="authenticated",
    )


def _payload_from_claims(payload: Dict[str, Any]) -> TokenPayload:
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject is not a valid user id",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenPayload(
        user_id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
        raw=payload,
    )


def _validate_via_auth_api(token: str) -> TokenPayload:
    """Fallback: ask Supabase Auth to resolve the bearer token."""
    settings = get_settings()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"
    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {token}",
    }
    response = get_http_client().get(url, headers=headers)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = response.json()
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenPayload(
        user_id=UUID(user_id),
        email=user.get("email"),
        role=None,
        raw=user,
    )


def decode_supabase_jwt(token: str) -> TokenPayload:
    """Validate a Supabase access token and return its claims."""
    settings = get_settings()

    if not settings.supabase_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_URL is not configured",
        )

    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")

        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise jwt.InvalidTokenError("SUPABASE_JWT_SECRET is not configured")
            payload = _decode_with_key(
                token,
                settings.supabase_jwt_secret,
                ["HS256"],
            )
            return _payload_from_claims(payload)

        # Newer Supabase projects sign with asymmetric keys (ES256 / RS256)
        key = _public_key_for_token(token)
        payload = _decode_with_key(token, key, [alg])
        return _payload_from_claims(payload)

    except HTTPException:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning("Local JWT verify failed (%s); trying Auth API", exc)
        try:
            return _validate_via_auth_api(token)
        except HTTPException:
            raise
        except Exception as inner:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from inner
