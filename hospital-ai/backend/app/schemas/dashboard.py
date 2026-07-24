"""Dashboard analytics schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DashboardStatistics(BaseModel):
    total_patients: int = 0
    total_doctors: int = 0
    todays_appointments: int = 0
    available_beds: int = 0
    icu_occupancy_pct: float = 0.0
    total_departments: int = 0
    medical_records_uploaded: int = 0
    available_resources: int = 0


class ChartSeries(BaseModel):
    label: str
    value: float


class DashboardCharts(BaseModel):
    appointments_per_day: List[ChartSeries]
    patients_per_department: List[ChartSeries]
    doctor_distribution: List[ChartSeries]
    bed_utilization: List[ChartSeries]
    monthly_patient_registration: List[ChartSeries]
    appointment_status_distribution: List[ChartSeries]


class ActivityItem(BaseModel):
    id: str
    type: str
    title: str
    subtitle: Optional[str] = None
    timestamp: str
    link: Optional[str] = None


class RecentActivitiesResponse(BaseModel):
    new_patients: List[ActivityItem]
    new_doctors: List[ActivityItem]
    recent_medical_records: List[ActivityItem]
    todays_appointments: List[ActivityItem]
    recently_updated_records: List[ActivityItem]


class UpcomingAppointmentItem(BaseModel):
    id: str
    appointment_number: str
    patient_name: str
    doctor_name: str
    appointment_date: str
    start_time: str
    status: str
    visit_type: str


class UpcomingAppointmentsResponse(BaseModel):
    items: List[UpcomingAppointmentItem]
    total: int


class ResourceSummaryResponse(BaseModel):
    items: List[Dict[str, Any]]
    total_beds: int
    available_beds: int
    total_icu: int
    available_icu: int
    operation_theatres: int
    ventilators_available: int
    laboratories: int


class GlobalSearchHit(BaseModel):
    id: str
    category: str
    title: str
    subtitle: Optional[str] = None
    link: str


class GlobalSearchResponse(BaseModel):
    query: str
    patients: List[GlobalSearchHit]
    doctors: List[GlobalSearchHit]
    departments: List[GlobalSearchHit]
    appointments: List[GlobalSearchHit]
    medical_records: List[GlobalSearchHit]
    total: int
