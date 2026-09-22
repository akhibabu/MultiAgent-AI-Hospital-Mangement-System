"""Cross-agent context for the Scheduling Agent.

Scheduling never asks the patient to decide clinical treatment, surgery, or
doctor assignment. It reads the latest persisted outputs of upstream agents.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.emergency_repository import EmergencyResultRepository
from app.repositories.medical_report_repository import GeneratedMedicalReportRepository
from app.repositories.prescription_repository import PrescriptionResultRepository

NEGATIVE_SURGERY = re.compile(r"(?:no|not|without|does not|doesn't|do not|don't)\s+(?:require\s+|recommend\s+|need\s+)?(?:for\s+)?(?:surgery|surgical intervention|operation|operative procedure)", re.I)
SURGERY = re.compile(r"(?:(?:recommend(?:ed)?|require(?:d)?|need(?:s|ed)?|plan(?:ned)?|schedule(?:d)?|indicat(?:e|ed|es)).{0,90}(?:surgery|surgical intervention|operation|operative procedure))|(?:(?:surgery|surgical intervention|operation|operative procedure).{0,90}(?:recommend(?:ed)?|require(?:d)?|needed|planned|schedule(?:d)?|indicat(?:e|ed|es)))", re.I|re.S)

class SchedulingSourceContext:
    def __init__(self) -> None:
        self.diagnosis = DiagnosisResultRepository()
        self.emergency = EmergencyResultRepository()
        self.prescription = PrescriptionResultRepository()
        self.medical_report = GeneratedMedicalReportRepository()

    def load(self, patient_id: UUID) -> Dict[str, Any]:
        return {
            "diagnosis": self.diagnosis.get_latest_for_patient(patient_id),
            "emergency": self.emergency.get_latest_for_patient(patient_id),
            "prescription": self.prescription.get_latest_for_patient(patient_id),
            "medical_report": self.medical_report.get_latest_for_patient(patient_id),
        }

    @staticmethod
    def derive(src: Dict[str, Any]) -> Dict[str, Any]:
        d, e, p, r = (src.get("diagnosis") or {}, src.get("emergency") or {},
                      src.get("prescription") or {}, src.get("medical_report") or {})
        tp=(d.get("treatment_path_json") or {}); cds=(d.get("clinical_decision_support_json") or {})
        sev=(d.get("severity_assessment_json") or {})
        ep=(p.get("treatment_plan_json") or {}); pv=(p.get("validation_summary_json") or {})
        rn=(r.get("doctor_notes_json") or {}); rr=(r.get("referral_letter_json") or {})
        rp=(r.get("patient_report_json") or {}); rs=(r.get("clinical_summary_json") or {})
        pri=(e.get("patient_priority_json") or {}); tri=(e.get("triage_classification_json") or {}); icu=(e.get("icu_requirement_json") or {})

        specialists=_unique([*(tp.get("recommended_specialists") or []),*(ep.get("recommended_specialists") or []),rr.get("receiving_specialist") or ""])
        department=str(tp.get("recommended_department") or "").strip() or None
        priority_level=str(pri.get("priority_level") or "").strip() or "Routine"
        priority_score=_num(pri.get("priority_score"))
        triage=str(tri.get("category") or "").strip() or None
        urgency=str(tp.get("urgency") or "").strip() or "Routine"

        structured_surgery=bool(tp.get("surgery_required") or ep.get("surgery_required"))
        evidence=_surgery_evidence([
            ("Diagnosis Treatment Path",tp.get("notes")),
            ("Diagnosis Clinical Notes",cds.get("clinical_notes")),
            ("Prescription Emergency Advice",ep.get("emergency_advice")),
            ("Medical Report Doctor Plan",rn.get("plan")),
            ("Medical Report Referral",rr.get("requested_evaluation")),
        ])

        follow=str(ep.get("follow_up_interval") or "").strip() or str(rp.get("follow_up") or "").strip() or str((r.get("discharge_summary_json") or {}).get("follow_up") or "").strip()
        visit_type="Emergency" if priority_level in {"Critical","Urgent"} or triage in {"Critical","Urgent"} or urgency in {"Critical","Urgent"} else ("Follow Up" if follow else "Consultation")
        text_parts=[
            *_strings(d.get("target_conditions_json")),
            *_strings(d.get("differential_diagnoses_json"),"condition"),
            *_strings(cds.get("possible_diagnoses")),
            tp.get("recommended_department") or "", tp.get("notes") or "",
            *_strings(tp.get("recommended_specialists")),
            *_strings(ep.get("recommended_lab_tests")),
            *_strings(ep.get("recommended_imaging")),
            *_strings(ep.get("medication_plan")),
            rn.get("assessment") or "", rn.get("plan") or "",
            rs.get("diagnosis_summary") or "", rr.get("requested_evaluation") or "",
        ]
        return {
            "source_ids": {
                "diagnosis_result_id": str(d.get("id")) if d.get("id") else None,
                "emergency_result_id": str(e.get("id")) if e.get("id") else None,
                "prescription_result_id": str(p.get("id")) if p.get("id") else None,
                "medical_report_result_id": str(r.get("id")) if r.get("id") else None,
            },
            "sources_available": {"diagnosis":bool(d),"emergency":bool(e),"prescription":bool(p),"medical_report":bool(r)},
            "department":department,"specialists":specialists,"visit_type":visit_type,
            "emergency_priority_level":priority_level,"emergency_priority_score":priority_score,
            "emergency_triage":triage,"icu_signal":str(icu.get("signal") or "Low"),
            "severity_level":str(sev.get("level") or "").strip() or None,
            "urgency":urgency,"clinical_text":" ".join(str(x) for x in text_parts if x).strip(),
            "surgery_required":structured_surgery or bool(evidence),"surgery_evidence":evidence,
            "surgery_duration_minutes":_duration(tp.get("surgery_duration_minutes") or ep.get("surgery_duration_minutes")),
            "follow_up_text":follow,
            "recommended_tests":_unique([*_strings(tp.get("diagnostic_tests")),*_strings(ep.get("recommended_lab_tests"))]),
            "recommended_imaging":_unique([*_strings(tp.get("imaging")),*_strings(ep.get("recommended_imaging"))]),
            "medications":_unique(_strings(ep.get("medication_plan"))),
            "validation_status":str(pv.get("approval_status") or "").strip() or None,
        }

def _surgery_evidence(items: List[tuple[str,Any]]) -> List[str]:
    out=[]
    for source,value in items:
        vals=value if isinstance(value,list) else [value]
        for raw in vals:
            s=str(raw or "").strip()
            if not s or NEGATIVE_SURGERY.search(s): continue
            m=SURGERY.search(s)
            if m: out.append(f"{source}: {m.group(0).strip()[:300]}")
    return out[:6]
def _strings(value:Any,key:Optional[str]=None)->List[str]:
    if not isinstance(value,list): return []
    out=[]
    for x in value:
        if key and isinstance(x,dict): x=x.get(key)
        if x is not None and str(x).strip(): out.append(str(x).strip())
    return out
def _unique(values:List[Any])->List[str]:
    out=[]; seen=set()
    for x in values:
        s=str(x or "").strip()
        if s and s.lower() not in seen: out.append(s); seen.add(s.lower())
    return out
def _num(value:Any)->float:
    try: return round(float(value or 0),1)
    except (TypeError,ValueError): return 0.0


def _duration(value: Any) -> int:
    try:
        n = int(float(value))
        return n if 30 <= n <= 480 else 0
    except (TypeError, ValueError):
        return 0
