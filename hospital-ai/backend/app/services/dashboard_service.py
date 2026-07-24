"""Dashboard aggregation + global search."""

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.database.http import get_http_client
from app.schemas.dashboard import (
    ActivityItem,
    ChartSeries,
    DashboardCharts,
    DashboardStatistics,
    GlobalSearchHit,
    GlobalSearchResponse,
    RecentActivitiesResponse,
    ResourceSummaryResponse,
    UpcomingAppointmentItem,
    UpcomingAppointmentsResponse,
)
from app.services.resource_service import resource_service

logger = get_logger("hospital_ai.dashboard")


class DashboardService:
    def _headers(self) -> Dict[str, str]:
        settings = get_settings()
        settings.require_supabase()
        return {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }

    def _base(self) -> str:
        return get_settings().supabase_url.rstrip("/")

    def _count(self, table: str, filters: Optional[List[tuple[str, str]]] = None) -> int:
        params: List[tuple[str, str]] = [("select", "id")]
        if filters:
            params.extend(filters)
        headers = self._headers()
        headers["Prefer"] = "count=exact"
        headers["Range-Unit"] = "items"
        headers["Range"] = "0-0"
        try:
            response = get_http_client().get(
                f"{self._base()}/rest/v1/{table}",
                headers=headers,
                params=params,
            )
        except httpx.HTTPError:
            return 0
        if response.status_code >= 400:
            return 0
        cr = response.headers.get("content-range", "")
        if "/" in cr:
            try:
                return int(cr.split("/")[-1])
            except ValueError:
                return 0
        return 0

    def _get(
        self, table: str, params: List[tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        try:
            response = get_http_client().get(
                f"{self._base()}/rest/v1/{table}",
                headers=self._headers(),
                params=params,
            )
        except httpx.HTTPError:
            return []
        if response.status_code >= 400:
            return []
        rows = response.json()
        return rows if isinstance(rows, list) else []

    def statistics(self) -> DashboardStatistics:
        today = date.today().isoformat()
        total_patients = self._count("patients")
        total_doctors = self._count("doctors")
        todays_appointments = self._count(
            "appointments", [("appointment_date", f"eq.{today}")]
        )
        total_departments = self._count("departments")
        medical_records = self._count("medical_records")

        resources = resource_service.all_rows()
        available_beds = 0
        icu_total = 0
        icu_available = 0
        available_resources = 0
        for row in resources:
            if not isinstance(row, dict):
                continue
            avail = int(row.get("available_quantity") or 0)
            qty = int(row.get("quantity") or 0)
            available_resources += avail
            rtype = row.get("resource_type")
            if rtype == "Bed":
                available_beds += avail
            elif rtype == "ICU Bed":
                icu_total += qty
                icu_available += avail
        icu_used = max(icu_total - icu_available, 0)
        icu_pct = round((icu_used / icu_total) * 100, 1) if icu_total else 0.0

        return DashboardStatistics(
            total_patients=total_patients,
            total_doctors=total_doctors,
            todays_appointments=todays_appointments,
            available_beds=available_beds,
            icu_occupancy_pct=icu_pct,
            total_departments=total_departments,
            medical_records_uploaded=medical_records,
            available_resources=available_resources,
        )

    def charts(self) -> DashboardCharts:
        # Appointments per day (last 7 days)
        appointments_per_day: List[ChartSeries] = []
        for i in range(6, -1, -1):
            d = date.today() - timedelta(days=i)
            count = self._count(
                "appointments", [("appointment_date", f"eq.{d.isoformat()}")]
            )
            appointments_per_day.append(
                ChartSeries(label=d.strftime("%a %d"), value=float(count))
            )

        # Appointment status distribution
        status_dist: List[ChartSeries] = []
        for status in ("Scheduled", "Completed", "Cancelled", "No Show", "Rescheduled"):
            status_dist.append(
                ChartSeries(
                    label=status,
                    value=float(
                        self._count("appointments", [("status", f"eq.{status}")])
                    ),
                )
            )

        # Doctor distribution by specialization (top rows)
        doctors = self._get(
            "doctors",
            [("select", "specialization"), ("limit", "200")],
        )
        by_spec: Dict[str, int] = defaultdict(int)
        for row in doctors:
            if isinstance(row, dict):
                by_spec[str(row.get("specialization") or "Other")] += 1
        doctor_distribution = [
            ChartSeries(label=k, value=float(v))
            for k, v in sorted(by_spec.items(), key=lambda x: -x[1])[:8]
        ]

        # Patients per department — approximate via doctors' departments + patient count split
        # Prefer counting patients is not linked to dept; use doctor dept distribution as proxy
        # and also show department doctor counts as "Patients Per Department" alternative:
        # Use medical records linked? Better: departments with doctor counts labeled as staff density
        # Spec says Patients Per Department — patients table may not have department_id.
        # Use appointments joined mentally: count appointments by department_id.
        appts = self._get(
            "appointments",
            [
                ("select", "department_id"),
                ("department_id", "not.is.null"),
                ("limit", "500"),
            ],
        )
        dept_counts: Dict[str, int] = defaultdict(int)
        dept_ids = list(
            {
                str(r["department_id"])
                for r in appts
                if isinstance(r, dict) and r.get("department_id")
            }
        )
        dept_names: Dict[str, str] = {}
        if dept_ids:
            depts = self._get(
                "departments",
                [
                    ("select", "id,name"),
                    ("id", f"in.({','.join(dept_ids)})"),
                ],
            )
            for d in depts:
                if isinstance(d, dict):
                    dept_names[str(d["id"])] = d["name"]
        for row in appts:
            if isinstance(row, dict) and row.get("department_id"):
                name = dept_names.get(str(row["department_id"]), "Unknown")
                dept_counts[name] += 1
        if not dept_counts:
            # Fallback: department list with zeros + patient total on first
            all_depts = self._get("departments", [("select", "name"), ("limit", "20")])
            patients_per_department = [
                ChartSeries(label=str(d.get("name")), value=0.0)
                for d in all_depts
                if isinstance(d, dict)
            ] or [ChartSeries(label="Unassigned", value=float(self._count("patients")))]
        else:
            patients_per_department = [
                ChartSeries(label=k, value=float(v))
                for k, v in sorted(dept_counts.items(), key=lambda x: -x[1])[:8]
            ]

        # Bed utilization
        resources = resource_service.all_rows()
        bed_total = bed_avail = icu_total = icu_avail = 0
        for row in resources:
            if not isinstance(row, dict):
                continue
            qty = int(row.get("quantity") or 0)
            avail = int(row.get("available_quantity") or 0)
            if row.get("resource_type") == "Bed":
                bed_total += qty
                bed_avail += avail
            elif row.get("resource_type") == "ICU Bed":
                icu_total += qty
                icu_avail += avail
        bed_utilization = [
            ChartSeries(label="Beds available", value=float(bed_avail)),
            ChartSeries(label="Beds occupied", value=float(max(bed_total - bed_avail, 0))),
            ChartSeries(label="ICU available", value=float(icu_avail)),
            ChartSeries(label="ICU occupied", value=float(max(icu_total - icu_avail, 0))),
        ]

        # Monthly patient registration (last 6 months)
        monthly: List[ChartSeries] = []
        today = date.today()
        for i in range(5, -1, -1):
            month = today.month - i
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            count = self._count(
                "patients",
                [
                    ("created_at", f"gte.{start.isoformat()}T00:00:00Z"),
                    ("created_at", f"lte.{end.isoformat()}T23:59:59Z"),
                ],
            )
            monthly.append(
                ChartSeries(label=start.strftime("%b %Y"), value=float(count))
            )

        return DashboardCharts(
            appointments_per_day=appointments_per_day,
            patients_per_department=patients_per_department,
            doctor_distribution=doctor_distribution,
            bed_utilization=bed_utilization,
            monthly_patient_registration=monthly,
            appointment_status_distribution=status_dist,
        )

    def recent_activities(self) -> RecentActivitiesResponse:
        patients = self._get(
            "patients",
            [
                ("select", "id,patient_number,first_name,last_name,created_at"),
                ("order", "created_at.desc"),
                ("limit", "5"),
            ],
        )
        doctors = self._get(
            "doctors",
            [
                ("select", "id,doctor_number,first_name,last_name,created_at"),
                ("order", "created_at.desc"),
                ("limit", "5"),
            ],
        )
        records = self._get(
            "medical_records",
            [
                ("select", "id,title,record_type,created_at,updated_at"),
                ("order", "created_at.desc"),
                ("limit", "5"),
            ],
        )
        updated = self._get(
            "medical_records",
            [
                ("select", "id,title,record_type,created_at,updated_at"),
                ("order", "updated_at.desc"),
                ("limit", "5"),
            ],
        )
        today = date.today().isoformat()
        todays = self._get(
            "appointments",
            [
                (
                    "select",
                    "id,appointment_number,appointment_date,start_time,status,created_at",
                ),
                ("appointment_date", f"eq.{today}"),
                ("order", "start_time.asc"),
                ("limit", "8"),
            ],
        )

        def patient_items(rows: List[Dict[str, Any]]) -> List[ActivityItem]:
            return [
                ActivityItem(
                    id=str(r["id"]),
                    type="patient",
                    title=f"{r.get('first_name')} {r.get('last_name')}",
                    subtitle=str(r.get("patient_number") or ""),
                    timestamp=str(r.get("created_at") or ""),
                    link=f"/patients/{r['id']}",
                )
                for r in rows
                if isinstance(r, dict)
            ]

        def doctor_items(rows: List[Dict[str, Any]]) -> List[ActivityItem]:
            return [
                ActivityItem(
                    id=str(r["id"]),
                    type="doctor",
                    title=f"Dr. {r.get('first_name')} {r.get('last_name')}",
                    subtitle=str(r.get("doctor_number") or ""),
                    timestamp=str(r.get("created_at") or ""),
                    link=f"/doctors/{r['id']}",
                )
                for r in rows
                if isinstance(r, dict)
            ]

        def record_items(
            rows: List[Dict[str, Any]], *, ts_field: str
        ) -> List[ActivityItem]:
            return [
                ActivityItem(
                    id=str(r["id"]),
                    type="medical_record",
                    title=str(r.get("title") or "Record"),
                    subtitle=str(r.get("record_type") or ""),
                    timestamp=str(r.get(ts_field) or ""),
                    link=f"/medical-records/{r['id']}",
                )
                for r in rows
                if isinstance(r, dict)
            ]

        return RecentActivitiesResponse(
            new_patients=patient_items(patients),
            new_doctors=doctor_items(doctors),
            recent_medical_records=record_items(records, ts_field="created_at"),
            todays_appointments=[
                ActivityItem(
                    id=str(r["id"]),
                    type="appointment",
                    title=str(r.get("appointment_number") or "Appointment"),
                    subtitle=f"{r.get('start_time', '')} · {r.get('status', '')}",
                    timestamp=str(r.get("created_at") or ""),
                    link=f"/appointments/{r['id']}",
                )
                for r in todays
                if isinstance(r, dict)
            ],
            recently_updated_records=record_items(updated, ts_field="updated_at"),
        )

    def upcoming_appointments(self) -> UpcomingAppointmentsResponse:
        today = date.today().isoformat()
        rows = self._get(
            "appointments",
            [
                (
                    "select",
                    "id,appointment_number,patient_id,doctor_id,"
                    "appointment_date,start_time,status,visit_type",
                ),
                ("appointment_date", f"gte.{today}"),
                ("status", "in.(Scheduled,Rescheduled)"),
                ("order", "appointment_date.asc,start_time.asc"),
                ("limit", "10"),
            ],
        )
        patient_ids = list(
            {str(r["patient_id"]) for r in rows if isinstance(r, dict) and r.get("patient_id")}
        )
        doctor_ids = list(
            {str(r["doctor_id"]) for r in rows if isinstance(r, dict) and r.get("doctor_id")}
        )
        patients: Dict[str, str] = {}
        doctors: Dict[str, str] = {}
        if patient_ids:
            for p in self._get(
                "patients",
                [
                    ("select", "id,first_name,last_name"),
                    ("id", f"in.({','.join(patient_ids)})"),
                ],
            ):
                if isinstance(p, dict):
                    patients[str(p["id"])] = f"{p.get('first_name')} {p.get('last_name')}"
        if doctor_ids:
            for d in self._get(
                "doctors",
                [
                    ("select", "id,first_name,last_name"),
                    ("id", f"in.({','.join(doctor_ids)})"),
                ],
            ):
                if isinstance(d, dict):
                    doctors[str(d["id"])] = (
                        f"Dr. {d.get('first_name')} {d.get('last_name')}"
                    )
        items = [
            UpcomingAppointmentItem(
                id=str(r["id"]),
                appointment_number=str(r.get("appointment_number") or ""),
                patient_name=patients.get(str(r.get("patient_id")), "—"),
                doctor_name=doctors.get(str(r.get("doctor_id")), "—"),
                appointment_date=str(r.get("appointment_date") or ""),
                start_time=str(r.get("start_time") or "")[:5],
                status=str(r.get("status") or ""),
                visit_type=str(r.get("visit_type") or ""),
            )
            for r in rows
            if isinstance(r, dict)
        ]
        return UpcomingAppointmentsResponse(items=items, total=len(items))

    def resource_summary(self) -> ResourceSummaryResponse:
        rows = resource_service.all_rows()
        by_type: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"total_quantity": 0, "available_quantity": 0}
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            t = str(row.get("resource_type") or "Other")
            by_type[t]["total_quantity"] += int(row.get("quantity") or 0)
            by_type[t]["available_quantity"] += int(row.get("available_quantity") or 0)
        items = [
            {
                "resource_type": k,
                "total_quantity": v["total_quantity"],
                "available_quantity": v["available_quantity"],
                "in_use": max(v["total_quantity"] - v["available_quantity"], 0),
            }
            for k, v in sorted(by_type.items())
        ]
        beds = by_type.get("Bed", {"total_quantity": 0, "available_quantity": 0})
        icu = by_type.get("ICU Bed", {"total_quantity": 0, "available_quantity": 0})
        ot = by_type.get("Operation Theatre", {"total_quantity": 0, "available_quantity": 0})
        vent = by_type.get("Ventilator", {"total_quantity": 0, "available_quantity": 0})
        lab = by_type.get("Laboratory", {"total_quantity": 0, "available_quantity": 0})
        return ResourceSummaryResponse(
            items=items,
            total_beds=beds["total_quantity"],
            available_beds=beds["available_quantity"],
            total_icu=icu["total_quantity"],
            available_icu=icu["available_quantity"],
            operation_theatres=ot["total_quantity"],
            ventilators_available=vent["available_quantity"],
            laboratories=lab["total_quantity"],
        )

    def global_search(self, query: str) -> GlobalSearchResponse:
        q = (query or "").strip()
        if len(q) < 2:
            return GlobalSearchResponse(
                query=q,
                patients=[],
                doctors=[],
                departments=[],
                appointments=[],
                medical_records=[],
                total=0,
            )
        safe = q.replace("\\", "\\\\").replace("*", "\\*").replace(",", "\\,")

        patients_rows = self._get(
            "patients",
            [
                ("select", "id,patient_number,first_name,last_name"),
                (
                    "or",
                    f"(first_name.ilike.*{safe}*,last_name.ilike.*{safe}*,"
                    f"patient_number.ilike.*{safe}*)",
                ),
                ("limit", "8"),
            ],
        )
        doctors_rows = self._get(
            "doctors",
            [
                ("select", "id,doctor_number,first_name,last_name,specialization"),
                (
                    "or",
                    f"(first_name.ilike.*{safe}*,last_name.ilike.*{safe}*,"
                    f"doctor_number.ilike.*{safe}*,specialization.ilike.*{safe}*)",
                ),
                ("limit", "8"),
            ],
        )
        depts = self._get(
            "departments",
            [
                ("select", "id,name"),
                ("name", f"ilike.*{safe}*"),
                ("limit", "8"),
            ],
        )
        appts = self._get(
            "appointments",
            [
                ("select", "id,appointment_number,status,appointment_date"),
                (
                    "or",
                    f"(appointment_number.ilike.*{safe}*,reason_for_visit.ilike.*{safe}*)",
                ),
                ("limit", "8"),
            ],
        )
        records = self._get(
            "medical_records",
            [
                ("select", "id,title,record_type"),
                (
                    "or",
                    f"(title.ilike.*{safe}*,diagnosis.ilike.*{safe}*,notes.ilike.*{safe}*)",
                ),
                ("limit", "8"),
            ],
        )

        patients = [
            GlobalSearchHit(
                id=str(r["id"]),
                category="Patients",
                title=f"{r.get('first_name')} {r.get('last_name')}",
                subtitle=str(r.get("patient_number") or ""),
                link=f"/patients/{r['id']}",
            )
            for r in patients_rows
            if isinstance(r, dict)
        ]
        doctors = [
            GlobalSearchHit(
                id=str(r["id"]),
                category="Doctors",
                title=f"Dr. {r.get('first_name')} {r.get('last_name')}",
                subtitle=str(r.get("specialization") or r.get("doctor_number") or ""),
                link=f"/doctors/{r['id']}",
            )
            for r in doctors_rows
            if isinstance(r, dict)
        ]
        departments = [
            GlobalSearchHit(
                id=str(r["id"]),
                category="Departments",
                title=str(r.get("name") or ""),
                subtitle=None,
                link="/departments",
            )
            for r in depts
            if isinstance(r, dict)
        ]
        appointments = [
            GlobalSearchHit(
                id=str(r["id"]),
                category="Appointments",
                title=str(r.get("appointment_number") or ""),
                subtitle=f"{r.get('appointment_date')} · {r.get('status')}",
                link=f"/appointments/{r['id']}",
            )
            for r in appts
            if isinstance(r, dict)
        ]
        medical_records = [
            GlobalSearchHit(
                id=str(r["id"]),
                category="Medical Records",
                title=str(r.get("title") or ""),
                subtitle=str(r.get("record_type") or ""),
                link=f"/medical-records/{r['id']}",
            )
            for r in records
            if isinstance(r, dict)
        ]
        total = (
            len(patients)
            + len(doctors)
            + len(departments)
            + len(appointments)
            + len(medical_records)
        )
        return GlobalSearchResponse(
            query=q,
            patients=patients,
            doctors=doctors,
            departments=departments,
            appointments=appointments,
            medical_records=medical_records,
            total=total,
        )


dashboard_service = DashboardService()
