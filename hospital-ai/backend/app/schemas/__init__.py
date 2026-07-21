"""Pydantic schemas package."""

from app.schemas.auth import (
    AuthTokens,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    UserProfile,
)
from app.schemas.enums import UserRole
from app.schemas.patient import (
    BloodGroup,
    PatientAIExtensions,
    PatientCreate,
    PatientGender,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)

__all__ = [
    "AuthTokens",
    "BloodGroup",
    "LoginRequest",
    "LoginResponse",
    "MessageResponse",
    "PatientAIExtensions",
    "PatientCreate",
    "PatientGender",
    "PatientListResponse",
    "PatientResponse",
    "PatientUpdate",
    "UserProfile",
    "UserRole",
]
