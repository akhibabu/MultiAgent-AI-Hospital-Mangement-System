"""Dashboard + global search REST API."""

from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser
from app.schemas.dashboard import (
    DashboardCharts,
    DashboardStatistics,
    GlobalSearchResponse,
    RecentActivitiesResponse,
    ResourceSummaryResponse,
    UpcomingAppointmentsResponse,
)
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
search_router = APIRouter(tags=["search"])


@router.get("/statistics", response_model=DashboardStatistics)
def get_statistics(_current_user: CurrentUser) -> DashboardStatistics:
    return dashboard_service.statistics()


@router.get("/charts", response_model=DashboardCharts)
def get_charts(_current_user: CurrentUser) -> DashboardCharts:
    return dashboard_service.charts()


@router.get("/recent-activities", response_model=RecentActivitiesResponse)
def get_recent_activities(_current_user: CurrentUser) -> RecentActivitiesResponse:
    return dashboard_service.recent_activities()


@router.get("/upcoming-appointments", response_model=UpcomingAppointmentsResponse)
def get_upcoming_appointments(
    _current_user: CurrentUser,
) -> UpcomingAppointmentsResponse:
    return dashboard_service.upcoming_appointments()


@router.get("/resource-summary", response_model=ResourceSummaryResponse)
def get_resource_summary(_current_user: CurrentUser) -> ResourceSummaryResponse:
    return dashboard_service.resource_summary()


@search_router.get("/search", response_model=GlobalSearchResponse)
def global_search(
    _current_user: CurrentUser,
    q: str = Query(..., min_length=1, max_length=100),
) -> GlobalSearchResponse:
    return dashboard_service.global_search(q)
