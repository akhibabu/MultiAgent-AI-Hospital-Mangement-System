"""FastAPI auth dependencies (JWT verification via DI)."""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import TokenPayload, decode_supabase_jwt
from app.auth.service import auth_service
from app.schemas.auth import UserProfile

bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def get_access_token(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(bearer_scheme),
    ],
) -> str:
    return _extract_token(credentials)


def get_token_payload(
    token: Annotated[str, Depends(get_access_token)],
) -> TokenPayload:
    return decode_supabase_jwt(token)


def get_current_user(
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
) -> UserProfile:
    """Resolve the authenticated staff profile from public.users."""
    return auth_service.get_user_profile(payload.user_id)


CurrentUser = Annotated[UserProfile, Depends(get_current_user)]
AccessToken = Annotated[str, Depends(get_access_token)]
AuthenticatedPayload = Annotated[TokenPayload, Depends(get_token_payload)]
