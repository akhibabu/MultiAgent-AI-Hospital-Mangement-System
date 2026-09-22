"""Scheduling Agent Stage 1: doctor assignment."""
from __future__ import annotations
import re
from typing import Any, Dict, List
from .models import DoctorCandidate, DoctorAssignmentResult

SPECIALTY_HINTS = {
    "cardiology": {"heart","cardiac","chest","palpitation","hypertension","coronary"},
    "neurology": {"stroke","cva","seizure","neurological","headache","migraine","weakness"},
    "pulmonology": {"lung","respiratory","asthma","copd","dyspnea","breath","pneumonia"},
    "endocrinology": {"diabetes","glucose","thyroid","insulin","endocrine"},
    "gastroenterology": {"stomach","abdominal","liver","hepatitis","gastric","bowel"},
    "orthopedics": {"fracture","bone","joint","knee","back","spine","musculoskeletal"},
    "dermatology": {"skin","rash","eczema","dermatitis"},
    "nephrology": {"kidney","renal","dialysis"},
    "oncology": {"cancer","tumor","oncology","malignancy"},
    "pediatrics": {"child","pediatric","infant","newborn"},
}

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]{3,}", text.lower()))

class DoctorAssignmentEngine:
    def assign(self, *, doctors: List[Dict[str, Any]], workload: Dict[str, int], department_names: Dict[str, str], preferred_doctor_id: str | None, requested_department_id: str | None, requested_department_name: str | None, preferred_specialists: List[str], clinical_text: str, emergency_level: str, visit_type: str) -> DoctorAssignmentResult:
        patient_tokens = _tokens(clinical_text)
        scored: List[DoctorCandidate] = []
        emergency_boost = {"Critical": 18, "Urgent": 10, "Semi-Urgent": 4, "Routine": 0}.get(emergency_level, 0)
        for d in doctors:
            did = str(d["id"]); status = str(d.get("availability_status") or "Available")
            specialization = str(d.get("specialization") or "General Medicine")
            spec_tokens = _tokens(specialization)
            score = 0.0; reasons=[]
            if status == "Available": score += 25; reasons.append("Doctor is marked Available.")
            elif status == "Busy": score += 5; reasons.append("Doctor is marked Busy, so workload is considered.")
            else: score -= 100; reasons.append("Doctor is on leave and excluded from normal booking.")
            if requested_department_id and str(d.get("department_id") or "") == requested_department_id:
                score += 22; reasons.append("Recommended department matches.")
            if requested_department_name and requested_department_name.lower() in str(department_names.get(str(d.get("department_id"))) or "").lower():
                score += 18; reasons.append("Recommended department matches the available department.")
            specialist_tokens = [t for t in _tokens(" ".join(preferred_specialists)) if len(t) >= 5]
            specialization_tokens = _tokens(specialization)
            if any(a[:5] == b[:5] for a in specialist_tokens for b in specialization_tokens):
                score += 20
                reasons.append("Specialist recommendation from prior agents matches this doctor.")
            if preferred_doctor_id and did == preferred_doctor_id:
                score += 30; reasons.append("Preferred doctor requested.")
            hint_score = 0
            key = specialization.lower()
            for hint, words in SPECIALTY_HINTS.items():
                if hint in key and patient_tokens & words:
                    hint_score = 24; break
            if hint_score:
                score += hint_score; reasons.append("Specialization matches the patient's clinical/reason text.")
            exp = int(d.get("experience_years") or 0)
            score += min(10.0, exp * 0.5)
            load = int(workload.get(did, 0))
            score -= min(20.0, load * 0.75)
            if load <= 2: reasons.append("Low upcoming workload.")
            if emergency_boost:
                score += emergency_boost
                reasons.append(f"{emergency_level} emergency priority is incorporated into assignment.")
            if visit_type == "Emergency":
                score += 8; reasons.append("Emergency visit receives scheduling priority.")
            scored.append(DoctorCandidate(
                doctor_id=did, doctor_name=f"Dr. {d.get('first_name','')} {d.get('last_name','')}".strip(),
                specialization=specialization, department_id=str(d.get("department_id")) if d.get("department_id") else None,
                department_name=department_names.get(str(d.get("department_id"))) if d.get("department_id") else None,
                availability_status=status, workload_count=load, score=round(score,1), reasons=reasons[:8]
            ))
        eligible=[c for c in scored if c.availability_status != "On Leave"]
        eligible.sort(key=lambda x:(x.score, -x.workload_count), reverse=True)
        selected=eligible[0] if eligible else None
        return DoctorAssignmentResult(
            selected_doctor_id=selected.doctor_id if selected else None,
            selected_doctor_name=selected.doctor_name if selected else None,
            selection_score=selected.score if selected else 0.0,
            candidates=eligible[:8],
            rationale=(selected.reasons if selected else ["No bookable doctor candidate was found."])[:8]
        )
