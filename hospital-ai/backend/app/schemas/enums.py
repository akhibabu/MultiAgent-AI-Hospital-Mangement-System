"""Shared enums and domain type aliases."""

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "Admin"
    DOCTOR = "Doctor"
    NURSE = "Nurse"
    RECEPTIONIST = "Receptionist"
