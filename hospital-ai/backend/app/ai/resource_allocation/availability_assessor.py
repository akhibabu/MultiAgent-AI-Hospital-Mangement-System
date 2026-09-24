"""Assess available hospital resources without mutating inventory."""
from __future__ import annotations

from typing import Dict, List, Optional

from app.ai.resource_allocation.models import (
    MatchedResource,
    ResourceAllocationItem,
    ResourceRequirement,
)


class AvailabilityAssessor:
    AVAILABLE_STATUSES = {"available", "ready", "free", "active", "on duty"}

    def assess(
        self,
        *,
        requirements: List[ResourceRequirement],
        resources: List[Dict],
        doctors: List[Dict],
        selected_doctor_id: Optional[str] = None,
        preferred_specialists: Optional[List[str]] = None,
    ) -> List[ResourceAllocationItem]:
        outputs: List[ResourceAllocationItem] = []
        preferred_specialists = preferred_specialists or []
        for req in requirements:
            if (
                req.resource_type is None
                and req.requirement.lower() == "specialist staff"
            ):
                outputs.append(
                    self._assess_staff(
                        req, doctors, selected_doctor_id, preferred_specialists
                    )
                )
                continue

            candidates = [
                row
                for row in resources
                if str(row.get("resource_type") or "").strip().lower()
                == str(req.resource_type or "").strip().lower()
                and _is_available(row.get("status"))
                and int(row.get("available_quantity") or 0) > 0
            ]
            matched = [
                MatchedResource(
                    resource_id=str(row.get("id")),
                    resource_name=str(
                        row.get("resource_name") or req.requirement
                    ),
                    resource_type=str(
                        row.get("resource_type") or req.resource_type or ""
                    ),
                    available_quantity=int(row.get("available_quantity") or 0),
                    location=row.get("location"),
                )
                for row in candidates
                if row.get("id")
            ]
            available = sum(item.available_quantity for item in matched)
            allocated = min(req.required_quantity, available)
            shortage = max(req.required_quantity - allocated, 0)
            status = (
                "Allocated"
                if shortage == 0
                else "Partially Allocated"
                if allocated
                else "Unavailable"
            )
            outputs.append(
                ResourceAllocationItem(
                    requirement=req.requirement,
                    resource_type=req.resource_type,
                    required_quantity=req.required_quantity,
                    available_quantity=available,
                    allocated_quantity=allocated,
                    shortage_quantity=shortage,
                    status=status,
                    priority=req.priority,
                    source=req.source,
                    rationale=req.rationale,
                    matched_resources=matched,
                )
            )
        return outputs

    def _assess_staff(
        self,
        req: ResourceRequirement,
        doctors: List[Dict],
        selected_doctor_id: Optional[str],
        preferred_specialists: List[str],
    ) -> ResourceAllocationItem:
        available_doctors = [
            d for d in doctors if _is_available(d.get("availability_status"))
        ]
        candidates: List[Dict] = []

        # Prefer the doctor already selected by Scheduling, because that
        # assignment was derived from the same patient-specific clinical context.
        if selected_doctor_id:
            candidates.extend(
                d for d in available_doctors if str(d.get("id")) == selected_doctor_id
            )

        specialist_terms = [
            term.strip().lower()
            for term in preferred_specialists
            if term and term.strip()
        ]
        if specialist_terms:
            candidates.extend(
                d
                for d in available_doctors
                if _specialist_matches(
                    str(d.get("specialization") or ""), specialist_terms
                )
            )

        deduped: List[Dict] = []
        seen = set()
        for doctor in candidates:
            doctor_id = str(doctor.get("id") or "")
            if doctor_id and doctor_id not in seen:
                seen.add(doctor_id)
                deduped.append(doctor)

        matched = [
            MatchedResource(
                resource_id=str(d.get("id")),
                resource_name=(
                    f"Dr. {str(d.get('first_name') or '').strip()} "
                    f"{str(d.get('last_name') or '').strip()}"
                ).strip(),
                resource_type="Specialist Staff",
                available_quantity=1,
            )
            for d in deduped
        ]
        available = len(matched)
        allocated = min(req.required_quantity, available)
        shortage = max(req.required_quantity - allocated, 0)
        return ResourceAllocationItem(
            requirement=req.requirement,
            resource_type=None,
            required_quantity=req.required_quantity,
            available_quantity=available,
            allocated_quantity=allocated,
            shortage_quantity=shortage,
            status=(
                "Allocated"
                if shortage == 0
                else "Partially Allocated"
                if allocated
                else "Unavailable"
            ),
            priority=req.priority,
            source=req.source,
            rationale=req.rationale,
            matched_resources=matched,
        )


def _specialist_matches(specialization: str, terms: List[str]) -> bool:
    spec = specialization.strip().lower()
    if not spec:
        return False
    aliases = {
        "cardiologist": "cardiology",
        "neurologist": "neurology",
        "neurosurgeon": "neurosurgery",
        "orthopedist": "orthopedics",
        "oncologist": "oncology",
        "dermatologist": "dermatology",
        "gastroenterologist": "gastroenterology",
        "pulmonologist": "pulmonology",
        "nephrologist": "nephrology",
    }
    for term in terms:
        normalized = aliases.get(term, term)
        if normalized in spec or spec in normalized:
            return True
    return False


def _is_available(status: object) -> bool:
    if status is None:
        return True
    return str(status).strip().lower() in AvailabilityAssessor.AVAILABLE_STATUSES
