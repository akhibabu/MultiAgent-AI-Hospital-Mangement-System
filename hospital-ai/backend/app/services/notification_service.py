"""Placeholder notification service — no email/SMS delivery yet."""

from typing import Any, Dict, Optional
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger("hospital_ai.notifications")


class NotificationService:
    """
    Stub for future notification channels (email, SMS, push).

    Methods log intent only; they do not send messages.
    """

    def appointment_created(
        self,
        *,
        appointment_id: UUID,
        appointment_number: str,
        patient_id: UUID,
        doctor_id: UUID,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        logger.info(
            "[placeholder] Appointment Created — %s (%s) patient=%s doctor=%s meta=%s",
            appointment_number,
            appointment_id,
            patient_id,
            doctor_id,
            meta or {},
        )

    def appointment_cancelled(
        self,
        *,
        appointment_id: UUID,
        appointment_number: str,
        patient_id: UUID,
        doctor_id: UUID,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        logger.info(
            "[placeholder] Appointment Cancelled — %s (%s) patient=%s doctor=%s meta=%s",
            appointment_number,
            appointment_id,
            patient_id,
            doctor_id,
            meta or {},
        )

    def appointment_reminder(
        self,
        *,
        appointment_id: UUID,
        appointment_number: str,
        patient_id: UUID,
        doctor_id: UUID,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        logger.info(
            "[placeholder] Appointment Reminder — %s (%s) patient=%s doctor=%s meta=%s",
            appointment_number,
            appointment_id,
            patient_id,
            doctor_id,
            meta or {},
        )

    def doctor_assigned(
        self,
        *,
        appointment_id: UUID,
        appointment_number: str,
        patient_id: UUID,
        doctor_id: UUID,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        logger.info(
            "[placeholder] Doctor Assigned — %s (%s) patient=%s doctor=%s meta=%s",
            appointment_number,
            appointment_id,
            patient_id,
            doctor_id,
            meta or {},
        )


notification_service = NotificationService()
