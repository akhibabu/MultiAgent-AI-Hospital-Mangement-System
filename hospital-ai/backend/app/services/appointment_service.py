"""Appointment business logic against Supabase PostgREST."""

from datetime import date, datetime, time
from math import ceil
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from fastapi import HTTPException, status

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.appointment import (
    ACTIVE_STATUSES,
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentReschedule,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    AvailableSlot,
    AvailableSlotsResponse,
    DepartmentBrief,
    DoctorBrief,
    PatientBrief,
    VisitType,
)
from app.services.notification_service import notification_service

logger = get_logger("hospital_ai.appointments")

APPOINTMENT_SELECT = (
    "id,appointment_number,patient_id,doctor_id,department_id,"
    "appointment_date,start_time,end_time,status,visit_type,"
    "reason_for_visit,notes,"
    "predicted_wait_time,priority_score,recommended_slot,ai_notes,"
    "created_by,created_at,updated_at"
)

SORTABLE = {
    "appointment_number",
    "appointment_date",
    "start_time",
    "status",
    "visit_type",
    "created_at",
    "updated_at",
}

MIN_DURATION_MINUTES = 5
MAX_DURATION_MINUTES = 480


def _time_to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute + value.second // 60


def _minutes_to_time(minutes: int) -> time:
    minutes = max(0, min(minutes, 23 * 60 + 59))
    return time(hour=minutes // 60, minute=minutes % 60)


def _parse_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    text = str(value)
    if len(text) == 5:
        return time.fromisoformat(text)
    return time.fromisoformat(text[:8])


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value)[:10])


def _times_overlap(
    start_a: time, end_a: time, start_b: time, end_b: time
) -> bool:
    return _time_to_minutes(start_a) < _time_to_minutes(end_b) and _time_to_minutes(
        start_b
    ) < _time_to_minutes(end_a)


def _python_weekday_to_db(d: date) -> int:
    """Python Monday=0 … Sunday=6 — matches doctor_availability.day_of_week."""
    return d.weekday()


class AppointmentService:
    def _headers(self, prefer: Optional[str] = None) -> Dict[str, str]:
        settings = get_settings()
        settings.require_supabase()
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _base_url(self) -> str:
        return f"{get_settings().supabase_url.rstrip('/')}/rest/v1/appointments"

    def _handle_error(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        logger.error("%s failed: %s %s", action, response.status_code, response.text)
        detail = "Appointment operation failed"
        try:
            body = response.json()
            detail = body.get("message") or body.get("error") or detail
        except Exception:  # noqa: BLE001
            pass
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if response.status_code == 409:
            raise HTTPException(status_code=409, detail="Conflict creating appointment")
        if 400 <= response.status_code < 500:
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)

    def _get_json(self, url: str, params: List[tuple[str, str]]) -> Any:
        try:
            response = get_http_client().get(
                url, headers=self._headers(), params=params
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc
        if response.status_code >= 400:
            return None
        return response.json()

    def _ensure_patient(self, patient_id: UUID) -> PatientBrief:
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/patients"
        rows = self._get_json(
            url,
            [
                ("select", "id,patient_number,first_name,last_name"),
                ("id", f"eq.{patient_id}"),
            ],
        )
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=400, detail="Patient not found")
        return PatientBrief.model_validate(rows[0])

    def _load_doctor_row(self, doctor_id: UUID) -> Dict[str, Any]:
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/doctors"
        rows = self._get_json(
            url,
            [
                (
                    "select",
                    "id,doctor_number,first_name,last_name,specialization,"
                    "department_id,availability_status",
                ),
                ("id", f"eq.{doctor_id}"),
            ],
        )
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=400, detail="Doctor not found")
        return rows[0]

    def _load_department(self, department_id: Optional[UUID]) -> Optional[DepartmentBrief]:
        if not department_id:
            return None
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/departments"
        rows = self._get_json(
            url,
            [("select", "id,name"), ("id", f"eq.{department_id}")],
        )
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=400, detail="Department not found")
        return DepartmentBrief.model_validate(rows[0])

    def _load_briefs(
        self, rows: List[Dict[str, Any]]
    ) -> Tuple[
        Dict[str, PatientBrief],
        Dict[str, DoctorBrief],
        Dict[str, DepartmentBrief],
    ]:
        patient_ids = list(
            dict.fromkeys(str(r["patient_id"]) for r in rows if r.get("patient_id"))
        )
        doctor_ids = list(
            dict.fromkeys(str(r["doctor_id"]) for r in rows if r.get("doctor_id"))
        )
        dept_ids = list(
            dict.fromkeys(
                str(r["department_id"]) for r in rows if r.get("department_id")
            )
        )
        settings = get_settings()
        patients: Dict[str, PatientBrief] = {}
        doctors: Dict[str, DoctorBrief] = {}
        departments: Dict[str, DepartmentBrief] = {}

        if patient_ids:
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/patients"
            data = self._get_json(
                url,
                [
                    ("select", "id,patient_number,first_name,last_name"),
                    ("id", f"in.({','.join(patient_ids)})"),
                ],
            )
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        patients[str(row["id"])] = PatientBrief.model_validate(row)

        if doctor_ids:
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/doctors"
            data = self._get_json(
                url,
                [
                    (
                        "select",
                        "id,doctor_number,first_name,last_name,specialization",
                    ),
                    ("id", f"in.({','.join(doctor_ids)})"),
                ],
            )
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        doctors[str(row["id"])] = DoctorBrief.model_validate(row)

        if dept_ids:
            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/departments"
            data = self._get_json(
                url,
                [
                    ("select", "id,name"),
                    ("id", f"in.({','.join(dept_ids)})"),
                ],
            )
            if isinstance(data, list):
                for row in data:
                    if isinstance(row, dict):
                        departments[str(row["id"])] = DepartmentBrief.model_validate(
                            row
                        )

        return patients, doctors, departments

    def _to_response(
        self,
        row: Dict[str, Any],
        patients: Optional[Dict[str, PatientBrief]] = None,
        doctors: Optional[Dict[str, DoctorBrief]] = None,
        departments: Optional[Dict[str, DepartmentBrief]] = None,
    ) -> AppointmentResponse:
        data = dict(row)
        pid = str(data.get("patient_id") or "")
        did = str(data.get("doctor_id") or "")
        deptid = str(data.get("department_id") or "")
        data["patient"] = (patients or {}).get(pid)
        data["doctor"] = (doctors or {}).get(did)
        data["department"] = (departments or {}).get(deptid) if deptid else None
        return AppointmentResponse.model_validate(data)

    def _duration_minutes(self, start: time, end: time) -> int:
        return _time_to_minutes(end) - _time_to_minutes(start)

    def _validate_duration(self, start: time, end: time) -> None:
        duration = self._duration_minutes(start, end)
        if duration < MIN_DURATION_MINUTES:
            raise HTTPException(
                status_code=400,
                detail=f"Appointment must be at least {MIN_DURATION_MINUTES} minutes",
            )
        if duration > MAX_DURATION_MINUTES:
            raise HTTPException(
                status_code=400,
                detail=f"Appointment cannot exceed {MAX_DURATION_MINUTES} minutes",
            )

    def _fetch_availability(self, doctor_id: UUID) -> List[Dict[str, Any]]:
        settings = get_settings()
        url = f"{settings.supabase_url.rstrip('/')}/rest/v1/doctor_availability"
        rows = self._get_json(
            url,
            [
                (
                    "select",
                    "id,doctor_id,day_of_week,start_time,end_time,slot_duration,is_available",
                ),
                ("doctor_id", f"eq.{doctor_id}"),
                ("is_available", "eq.true"),
                ("order", "day_of_week.asc,start_time.asc"),
            ],
        )
        if not isinstance(rows, list):
            return []
        return [r for r in rows if isinstance(r, dict)]

    def _fetch_doctor_appointments_on_date(
        self,
        doctor_id: UUID,
        appointment_date: date,
        exclude_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        params: List[tuple[str, str]] = [
            ("select", "id,start_time,end_time,status"),
            ("doctor_id", f"eq.{doctor_id}"),
            ("appointment_date", f"eq.{appointment_date.isoformat()}"),
            ("status", f"in.({','.join(s.value for s in ACTIVE_STATUSES)})"),
        ]
        if exclude_id:
            params.append(("id", f"neq.{exclude_id}"))
        rows = self._get_json(self._base_url(), params)
        if not isinstance(rows, list):
            return []
        return [r for r in rows if isinstance(r, dict)]

    def _validate_within_availability(
        self,
        doctor_id: UUID,
        appointment_date: date,
        start: time,
        end: time,
    ) -> None:
        windows = self._fetch_availability(doctor_id)
        day = _python_weekday_to_db(appointment_date)
        day_windows = [w for w in windows if int(w["day_of_week"]) == day]
        if not day_windows:
            raise HTTPException(
                status_code=400,
                detail="Doctor has no availability configured for this day",
            )
        start_m = _time_to_minutes(start)
        end_m = _time_to_minutes(end)
        for window in day_windows:
            w_start = _time_to_minutes(_parse_time(window["start_time"]))
            w_end = _time_to_minutes(_parse_time(window["end_time"]))
            if start_m >= w_start and end_m <= w_end:
                return
        raise HTTPException(
            status_code=400,
            detail="Selected time is outside the doctor's available hours",
        )

    def _assert_no_overlap(
        self,
        doctor_id: UUID,
        appointment_date: date,
        start: time,
        end: time,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        existing = self._fetch_doctor_appointments_on_date(
            doctor_id, appointment_date, exclude_id=exclude_id
        )
        for row in existing:
            if _times_overlap(
                start,
                end,
                _parse_time(row["start_time"]),
                _parse_time(row["end_time"]),
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Double booking detected: overlapping appointment exists for this doctor",
                )

    def _validate_booking(
        self,
        *,
        doctor_id: UUID,
        appointment_date: date,
        start: time,
        end: time,
        exclude_id: Optional[UUID] = None,
        skip_availability: bool = False,
    ) -> None:
        self._validate_duration(start, end)
        doctor = self._load_doctor_row(doctor_id)
        if doctor.get("availability_status") == "On Leave":
            raise HTTPException(
                status_code=400,
                detail="Doctor is on leave and cannot be booked",
            )
        if not skip_availability:
            self._validate_within_availability(
                doctor_id, appointment_date, start, end
            )
        self._assert_no_overlap(
            doctor_id, appointment_date, start, end, exclude_id=exclude_id
        )

    def get_available_slots(
        self, doctor_id: UUID, appointment_date: date
    ) -> AvailableSlotsResponse:
        self._load_doctor_row(doctor_id)
        windows = self._fetch_availability(doctor_id)
        available_days = sorted({int(w["day_of_week"]) for w in windows})
        day = _python_weekday_to_db(appointment_date)
        day_windows = [w for w in windows if int(w["day_of_week"]) == day]
        if not day_windows:
            return AvailableSlotsResponse(
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                day_of_week=day,
                available_days=available_days,
                slots=[],
                message="Doctor is not available on this day",
            )

        booked = self._fetch_doctor_appointments_on_date(doctor_id, appointment_date)
        slots: List[AvailableSlot] = []
        for window in day_windows:
            w_start = _time_to_minutes(_parse_time(window["start_time"]))
            w_end = _time_to_minutes(_parse_time(window["end_time"]))
            duration = int(window.get("slot_duration") or 30)
            if duration < MIN_DURATION_MINUTES:
                duration = 30
            cursor = w_start
            while cursor + duration <= w_end:
                slot_start = _minutes_to_time(cursor)
                slot_end = _minutes_to_time(cursor + duration)
                conflict = False
                for row in booked:
                    if _times_overlap(
                        slot_start,
                        slot_end,
                        _parse_time(row["start_time"]),
                        _parse_time(row["end_time"]),
                    ):
                        conflict = True
                        break
                if not conflict:
                    slots.append(AvailableSlot(start_time=slot_start, end_time=slot_end))
                cursor += duration

        return AvailableSlotsResponse(
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            day_of_week=day,
            available_days=available_days,
            slots=slots,
            message=None if slots else "No open slots for this date",
        )

    def list_appointments(
        self,
        *,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        doctor_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        department_id: Optional[UUID] = None,
        status_filter: Optional[AppointmentStatus] = None,
        visit_type: Optional[VisitType] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        sort_by: str = "appointment_date",
        sort_order: str = "desc",
    ) -> AppointmentListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10
        if sort_by not in SORTABLE:
            sort_by = "appointment_date"
        order = "desc" if sort_order.lower() == "desc" else "asc"

        params: List[tuple[str, str]] = [
            ("select", APPOINTMENT_SELECT),
            ("order", f"{sort_by}.{order},start_time.{order}"),
        ]
        if doctor_id:
            params.append(("doctor_id", f"eq.{doctor_id}"))
        if patient_id:
            params.append(("patient_id", f"eq.{patient_id}"))
        if department_id:
            params.append(("department_id", f"eq.{department_id}"))
        if status_filter:
            params.append(("status", f"eq.{status_filter.value}"))
        if visit_type:
            params.append(("visit_type", f"eq.{visit_type.value}"))
        if date_from:
            params.append(("appointment_date", f"gte.{date_from.isoformat()}"))
        if date_to:
            params.append(("appointment_date", f"lte.{date_to.isoformat()}"))

        if search:
            tokens = [t for t in search.strip().replace(",", " ").split() if t]
            if tokens:
                or_parts: List[str] = []
                for token in tokens:
                    safe = (
                        token.replace("\\", "\\\\")
                        .replace("*", "\\*")
                        .replace(",", "\\,")
                    )
                    or_parts.extend(
                        [
                            f"appointment_number.ilike.*{safe}*",
                            f"reason_for_visit.ilike.*{safe}*",
                            f"notes.ilike.*{safe}*",
                        ]
                    )
                params.append(("or", f"({','.join(or_parts)})"))

        offset = (page - 1) * page_size
        headers = self._headers(prefer="count=exact")
        headers["Range-Unit"] = "items"
        headers["Range"] = f"{offset}-{offset + page_size - 1}"

        try:
            response = get_http_client().get(
                self._base_url(), headers=headers, params=params
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "list_appointments")
        total = 0
        cr = response.headers.get("content-range", "")
        if "/" in cr:
            try:
                total = int(cr.split("/")[-1])
            except ValueError:
                total = 0

        rows = response.json()
        if not isinstance(rows, list):
            logger.error("Unexpected appointments payload: %s", rows)
            raise HTTPException(
                status_code=502,
                detail="Unexpected response from database while listing appointments",
            )
        dict_rows = [r for r in rows if isinstance(r, dict)]
        patients, doctors, departments = self._load_briefs(dict_rows)
        items = [
            self._to_response(r, patients, doctors, departments) for r in dict_rows
        ]
        total_pages = ceil(total / page_size) if page_size and total else 0
        return AppointmentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_appointment(self, appointment_id: UUID) -> AppointmentResponse:
        try:
            response = get_http_client().get(
                self._base_url(),
                headers=self._headers(),
                params=[
                    ("select", APPOINTMENT_SELECT),
                    ("id", f"eq.{appointment_id}"),
                ],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "get_appointment")
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=404, detail="Appointment not found")
        row = rows[0]
        if not isinstance(row, dict):
            raise HTTPException(status_code=502, detail="Unexpected appointment payload")
        patients, doctors, departments = self._load_briefs([row])
        return self._to_response(row, patients, doctors, departments)

    def create_appointment(
        self, payload: AppointmentCreate, created_by: UUID
    ) -> AppointmentResponse:
        self._ensure_patient(payload.patient_id)
        doctor_row = self._load_doctor_row(payload.doctor_id)
        department_id = payload.department_id
        if department_id is None and doctor_row.get("department_id"):
            department_id = UUID(str(doctor_row["department_id"]))
        if department_id:
            self._load_department(department_id)

        # Emergency visits may book outside availability windows
        skip_avail = payload.visit_type == VisitType.EMERGENCY
        self._validate_booking(
            doctor_id=payload.doctor_id,
            appointment_date=payload.appointment_date,
            start=payload.start_time,
            end=payload.end_time,
            skip_availability=skip_avail,
        )

        body = payload.model_dump(mode="json")
        body["department_id"] = str(department_id) if department_id else None
        body["created_by"] = str(created_by)
        try:
            response = get_http_client().post(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "create_appointment")
        rows = response.json() or []
        if not rows:
            raise HTTPException(
                status_code=502, detail="Appointment created but no data returned"
            )
        created = self.get_appointment(UUID(rows[0]["id"]))
        notification_service.appointment_created(
            appointment_id=created.id,
            appointment_number=created.appointment_number,
            patient_id=created.patient_id,
            doctor_id=created.doctor_id,
        )
        notification_service.doctor_assigned(
            appointment_id=created.id,
            appointment_number=created.appointment_number,
            patient_id=created.patient_id,
            doctor_id=created.doctor_id,
        )
        return created

    def update_appointment(
        self, appointment_id: UUID, payload: AppointmentUpdate
    ) -> AppointmentResponse:
        existing = self.get_appointment(appointment_id)
        body = payload.model_dump(mode="json", exclude_unset=True)
        if not body:
            return existing

        doctor_id = UUID(str(body.get("doctor_id", existing.doctor_id)))
        appointment_date = _parse_date(
            body.get("appointment_date", existing.appointment_date)
        )
        start = (
            _parse_time(body["start_time"])
            if "start_time" in body
            else existing.start_time
        )
        end = _parse_time(body["end_time"]) if "end_time" in body else existing.end_time
        visit_type = body.get("visit_type", existing.visit_type.value)
        if isinstance(visit_type, VisitType):
            visit_type = visit_type.value

        schedule_changed = any(
            k in body
            for k in ("doctor_id", "appointment_date", "start_time", "end_time")
        )
        new_status = body.get("status")
        if schedule_changed and new_status is None:
            # Mark as rescheduled when time/doctor changes while still active
            if existing.status in ACTIVE_STATUSES:
                body["status"] = AppointmentStatus.RESCHEDULED.value

        if "patient_id" in body:
            self._ensure_patient(UUID(str(body["patient_id"])))
        if "department_id" in body and body["department_id"]:
            self._load_department(UUID(str(body["department_id"])))

        if schedule_changed or new_status in (
            AppointmentStatus.SCHEDULED.value,
            AppointmentStatus.RESCHEDULED.value,
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.RESCHEDULED,
        ):
            effective_status = body.get("status", existing.status.value)
            if isinstance(effective_status, AppointmentStatus):
                effective_status = effective_status.value
            if effective_status in {s.value for s in ACTIVE_STATUSES}:
                skip_avail = visit_type == VisitType.EMERGENCY.value
                self._validate_booking(
                    doctor_id=doctor_id,
                    appointment_date=appointment_date,
                    start=start,
                    end=end,
                    exclude_id=appointment_id,
                    skip_availability=skip_avail,
                )

        try:
            response = get_http_client().patch(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{appointment_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc

        self._handle_error(response, "update_appointment")
        rows = response.json() or []
        if not rows:
            raise HTTPException(status_code=404, detail="Appointment not found")
        updated = self.get_appointment(appointment_id)
        if updated.status == AppointmentStatus.CANCELLED and existing.status != (
            AppointmentStatus.CANCELLED
        ):
            notification_service.appointment_cancelled(
                appointment_id=updated.id,
                appointment_number=updated.appointment_number,
                patient_id=updated.patient_id,
                doctor_id=updated.doctor_id,
            )
        return updated

    def reschedule_appointment(
        self, appointment_id: UUID, payload: AppointmentReschedule
    ) -> AppointmentResponse:
        existing = self.get_appointment(appointment_id)
        if existing.status == AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=400, detail="Cannot reschedule a cancelled appointment"
            )
        if existing.status == AppointmentStatus.COMPLETED:
            raise HTTPException(
                status_code=400, detail="Cannot reschedule a completed appointment"
            )
        skip_avail = existing.visit_type == VisitType.EMERGENCY
        self._validate_booking(
            doctor_id=existing.doctor_id,
            appointment_date=payload.appointment_date,
            start=payload.start_time,
            end=payload.end_time,
            exclude_id=appointment_id,
            skip_availability=skip_avail,
        )
        body: Dict[str, Any] = {
            "appointment_date": payload.appointment_date.isoformat(),
            "start_time": payload.start_time.isoformat(),
            "end_time": payload.end_time.isoformat(),
            "status": AppointmentStatus.RESCHEDULED.value,
        }
        if payload.notes is not None:
            body["notes"] = payload.notes
        try:
            response = get_http_client().patch(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{appointment_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc
        self._handle_error(response, "reschedule_appointment")
        return self.get_appointment(appointment_id)

    def update_status(
        self, appointment_id: UUID, payload: AppointmentStatusUpdate
    ) -> AppointmentResponse:
        existing = self.get_appointment(appointment_id)
        body: Dict[str, Any] = {"status": payload.status.value}
        if payload.notes is not None:
            body["notes"] = payload.notes
        try:
            response = get_http_client().patch(
                self._base_url(),
                headers=self._headers(prefer="return=representation"),
                params=[("id", f"eq.{appointment_id}")],
                json=body,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc
        self._handle_error(response, "update_status")
        updated = self.get_appointment(appointment_id)
        if (
            payload.status == AppointmentStatus.CANCELLED
            and existing.status != AppointmentStatus.CANCELLED
        ):
            notification_service.appointment_cancelled(
                appointment_id=updated.id,
                appointment_number=updated.appointment_number,
                patient_id=updated.patient_id,
                doctor_id=updated.doctor_id,
            )
        return updated

    def delete_appointment(self, appointment_id: UUID) -> None:
        existing = self.get_appointment(appointment_id)
        try:
            response = get_http_client().delete(
                self._base_url(),
                headers=self._headers(),
                params=[("id", f"eq.{appointment_id}")],
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503, detail="Unable to reach Supabase"
            ) from exc
        self._handle_error(response, "delete_appointment")
        notification_service.appointment_cancelled(
            appointment_id=existing.id,
            appointment_number=existing.appointment_number,
            patient_id=existing.patient_id,
            doctor_id=existing.doctor_id,
            meta={"reason": "deleted"},
        )
        logger.info("Deleted appointment %s", appointment_id)


appointment_service = AppointmentService()
