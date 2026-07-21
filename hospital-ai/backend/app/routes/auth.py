"""Authentication HTTP routes."""

from fastapi import APIRouter, status

from app.auth.dependencies import AccessToken, CurrentUser
from app.auth.service import auth_service
from app.schemas.auth import LoginRequest, LoginResponse, MessageResponse, UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Email/password login via Supabase Auth",
)
def login(body: LoginRequest) -> LoginResponse:
    return auth_service.login(body.email, body.password)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Invalidate the current Supabase session",
)
def logout(token: AccessToken) -> MessageResponse:
    auth_service.logout(token)
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Return the authenticated user profile and role",
)
def me(current_user: CurrentUser) -> UserProfile:
    return current_user
