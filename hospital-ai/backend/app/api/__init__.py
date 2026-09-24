"""API router aggregation."""

from fastapi import APIRouter

from app.routes import (
    ai_health,
    ai_orchestrator,
    announcements,
    appointments,
    auth,
    availability,
    dashboard,
    departments,
    diagnosis,
    doctors,
    emergency,
    health,
    intake,
    medical_records,
    medical_report,
    patients,
    prescription,
    research,
    resource_allocation,
    validation,
    resources,
    scheduling,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(doctors.router)
api_router.include_router(departments.router)
api_router.include_router(availability.router)
api_router.include_router(appointments.router)
api_router.include_router(medical_records.router)
api_router.include_router(resources.router)
api_router.include_router(announcements.router)
api_router.include_router(announcements.notifications_router)
api_router.include_router(dashboard.router)
api_router.include_router(dashboard.search_router)
api_router.include_router(intake.router)
api_router.include_router(diagnosis.router)
api_router.include_router(research.router)
api_router.include_router(prescription.router)
api_router.include_router(medical_report.router)
api_router.include_router(emergency.router)
api_router.include_router(scheduling.router)
api_router.include_router(resource_allocation.router)
api_router.include_router(validation.router)
api_router.include_router(ai_orchestrator.router)
api_router.include_router(ai_health.router)
