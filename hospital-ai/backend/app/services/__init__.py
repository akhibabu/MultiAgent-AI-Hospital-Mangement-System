"""Business services."""

from app.services.appointment_service import AppointmentService, appointment_service
from app.services.availability_service import AvailabilityService, availability_service
from app.services.department_service import DepartmentService, department_service
from app.services.doctor_service import DoctorService, doctor_service
from app.services.medical_record_service import MedicalRecordService, medical_record_service
from app.services.medical_storage_service import MedicalStorageService, medical_storage_service
from app.services.notification_service import NotificationService, notification_service
from app.services.patient_service import PatientService, patient_service

__all__ = [
    "AppointmentService",
    "AvailabilityService",
    "DepartmentService",
    "DoctorService",
    "MedicalRecordService",
    "MedicalStorageService",
    "NotificationService",
    "PatientService",
    "appointment_service",
    "availability_service",
    "department_service",
    "doctor_service",
    "medical_record_service",
    "medical_storage_service",
    "notification_service",
    "patient_service",
]
