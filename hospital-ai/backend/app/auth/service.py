"""Authentication business logic."""

from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.auth import AuthTokens, LoginResponse, UserProfile
from app.schemas.enums import UserRole

logger = get_logger("hospital_ai.auth")


class AuthService:
    """Reusable auth operations backed by Supabase Auth + public.users."""

    def login(self, email: str, password: str) -> LoginResponse:
        settings = get_settings()
        try:
            settings.require_supabase()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
        headers = {
            "apikey": settings.supabase_anon_key,
            "Content-Type": "application/json",
        }
        payload = {"email": email, "password": password}

        try:
            response = get_http_client().post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.error("Supabase auth unreachable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Unable to reach Supabase Auth. "
                    "If you are behind SSL inspection, set SUPABASE_SSL_VERIFY=false "
                    "in backend/.env and restart the API."
                ),
            ) from exc

        if response.status_code >= 400:
            logger.warning(
                "Login failed for %s: %s %s",
                email,
                response.status_code,
                response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        data = response.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        user = data.get("user") or {}
        user_id = user.get("id")

        if not access_token or not refresh_token or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        profile = self.get_user_profile(UUID(user_id))

        return LoginResponse(
            tokens=AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=data.get("expires_in"),
            ),
            user=profile,
        )

    def logout(self, access_token: str) -> None:
        """Invalidate the current Supabase session via GoTrue logout."""
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_anon_key:
            return

        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/logout"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "apikey": settings.supabase_anon_key,
        }
        try:
            response = get_http_client().post(url, headers=headers)
            if response.status_code >= 400:
                logger.info(
                    "Supabase logout returned %s: %s",
                    response.status_code,
                    response.text,
                )
        except Exception as exc:  # noqa: BLE001
            logger.info("Supabase logout soft-failed: %s", exc)

    def get_user_profile(self, user_id: UUID) -> UserProfile:
        settings = get_settings()
        try:
            settings.require_supabase()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        url = (
            f"{settings.supabase_url.rstrip('/')}/rest/v1/users"
            f"?id=eq.{user_id}"
            "&select=id,full_name,email,role,created_at,updated_at"
        )
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }

        try:
            response = get_http_client().get(url, headers=headers)
        except httpx.HTTPError as exc:
            logger.error("Supabase profile fetch unreachable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to reach Supabase database",
            ) from exc

        if response.status_code >= 400:
            logger.error("Profile fetch failed: %s %s", response.status_code, response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to load user profile",
            )

        rows = response.json() or []
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "User profile not found. Ensure the users migration "
                    "has been applied and the auth user has a profile row."
                ),
            )

        row = rows[0]
        return UserProfile(
            id=row["id"],
            full_name=row["full_name"],
            email=row["email"],
            role=UserRole(row["role"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


auth_service = AuthService()
