"""Build Scheduling Agent context from prior agent outputs."""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from uuid import UUID
from app.repositories.diagnosis_repository import DiagnosisResultRepository
from app.repositories.emergency_repository import EmergencyResultRepository
from app.repositories.medical_report_repository import GeneratedMedicalReportRepository
from app.repositories.prescription_repository import PrescriptionResultRepository

_NEGATIVE_SURGERY = re.compile(r"(?:no|not|without|does not|doesn't|do not|don't)\s+(?:require\s+|recommend\s+|need\s+)?(?:for\s+)?(?:surgery|surgical intervention|operation|operative procedure)", re.I)
_SURGERY = re.compile(r"(?:(?:recommend(?:ed)?|require(?:d)?|need(?:s|ed)?|plan(?:ned)?|schedule(?:d)?|indicat(?:e|ed|es)).{0,90}(?:surgery|surgical intervention|operation|operative procedure))|(?:(?:surgery|surgical intervention|operation|operative procedure).{0,90}(?:recommend(?:ed)?|require(?:d)?|needed|planned|schedule(?:d)?|indicat(?:e|ed|es)))", re.I|re.S)

class SchedulingSourceContext:
    """Read-only cross-agent context used to drive scheduling."""
    def __init__(self)->None:
        self.diagnosis_repo=DiagnosisResultRepository()
        self.emergency_repo=EmergencyResultRepository()
        self.prescription_repo=PrescriptionResultRepository()
        self.medical_report_repo=GeneratedMedicalReportRepository()
    def load(self,patient_id:UUID)->Dict[str,Any]:
        return {"diagnosis":self.diagnosis_repo.get_latest_for_patient(patient_id),
                "emergency":self.emergency_repo.get_latest_for_patient(patient_id),
                "prescription":self.prescription_repo.get_latest_for_patient(patient_id),
                "medical_report":self.medical_report_repo.get_latest_for_patient(patient_id)}
    @staticmethod
    def derive(source:Dict[str,Any])->Dict[str,Any]:
        diagnosis=source.get("diagnosis") or {}; emergency=source.get("emergency") or {}
        prescription=source.get("prescription") or {}; report=source.get("medical_report") or {}
        tp=diagnosis.get("treatment_path_json") or {}; cds=diagnosis.get("clinical_decision_support_json") or {}
        sev=diagnosis.get("severity_assessment_json") or {}; pp=prescription.get("treatment_plan_json") or {}
        validation=prescription.get("validation_summary_json") or {}; cs=report.get("clinical_summary_json") or {}
        notes=report.get("doctor_notes_json") or {}; discharge=report.get("discharge_summary_json") or {}
        referral=report.get("referral_letter_json") or {}; patient_report=report.get("patient_report_json") or {}
        priority=emergency.get("patient_priority_json") or {}; triage=emergency.get("triage_classification_json") or {}; icu=emergency.get("icu_requirement_json") or {}
        specialists=_unique([*(tp.get("recommended_specialists") or []),*(pp.get("recommended_specialists") or []),referral.get("receiving_specialist") or ""])
        department=str(tp.get("recommended_department") or "").strip() or None
        priority_level=str(priority.get("priority_level") or "").strip() or "Routine"
        priority_score=_number(priority.get("priority_score"))
        triage_category=str(triage.get("category") or "").strip() or None
        urgency=str(tp.get("urgency") or "").strip() or priority_level or "Routine"
        clinical_parts=[*_strings(diagnosis.get("target_conditions_json")),*_strings(diagnosis.get("differential_diagnoses_json"),"condition"),*_strings(cds.get("possible_diagnoses")),*_strings(tp.get("recommended_specialists")),tp.get("notes") or "",*_strings(pp.get("recommended_lab_tests")),*_strings(pp.get("recommended_imaging")),*_strings(pp.get("medication_plan")),notes.get("assessment") or "",notes.get("plan") or "",cs.get("diagnosis_summary") or "",referral.get("requested_evaluation") or "",discharge.get("admission_reason") or ""]
        surgery_evidence=_surgery_evidence([
            ("Diagnosis Treatment Path",tp.get("notes")),("Diagnosis Clinical Notes",cds.get("clinical_notes")),
            ("Prescription Emergency Advice",pp.get("emergency_advice")),("Medical Report Doctor Plan",notes.get("plan")),
            ("Medical Report Referral",referral.get("requested_evaluation"))])
        follow_text=str(pp.get("follow_up_interval") or "").strip() or str(patient_report.get("follow_up") or "").strip() or str(discharge.get("follow_up") or "").strip()
        visit_type="Emergency" if priority_level in {"Critical","Urgent"} or triage_category in {"Critical","Urgent"} else ("Follow Up" if follow_text else "Consultation")
        return {
            "source_ids":{"diagnosis_result_id":str(diagnosis.get("id")) if diagnosis.get("id") else None,"emergency_result_id":str(emergency.get("id")) if emergency.get("id") else None,"prescription_result_id":str(prescription.get("id")) if prescription.get("id") else None,"medical_report_result_id":str(report.get("id")) if report.get("id") else None},
            "sources_available":{"diagnosis":bool(diagnosis),"emergency":bool(emergency),"prescription":bool(prescription),"medical_report":bool(report)},
            "department":department,"specialists":specialists,"urgency":urgency,"visit_type":visit_type,
            "emergency_priority_level":priority_level,"emergency_priority_score":priority_score,
            "emergency_triage":triage_category,"icu_signal":str(icu.get("signal") or "Low"),"severity_level":str(sev.get("level") or "").strip() or None,
            "clinical_text":" ".join(str(x) for x in clinical_parts if x).strip(),
            "surgery_required":bool(surgery_evidence),"surgery_evidence":surgery_evidence,
            "surgery_duration_minutes":120 if surgery_evidence else 0,"follow_up_text":follow_text,
            "recommended_tests":_unique([*_strings(tp.get("diagnostic_tests")),*_strings(pp.get("recommended_lab_tests"))]),
            "recommended_imaging":_unique([*_strings(tp.get("imaging")),*_strings(pp.get("recommended_imaging"))]),
            "medications":_unique(_strings(pp.get("medication_plan"))),
            "validation_status":str(validation.get("approval_status") or "").strip() or None
        }

def _surgery_evidence(items:List[tuple[str,Any]])->List[str]:
    out=[]
    for source,value in items:
        vals=value if isinstance(value,list) else [value]
        for raw in vals:
            text=str(raw or "").strip()
            if not text or _NEGATIVE_SURGERY.search(text): continue
            match=_SURGERY.search(text)
            if match: out.append(f"{source}: {match.group(0).strip()[:300]}")
    return out[:6]
def _strings(value:Any,key:Optional[str]=None)->List[str]:
    if not isinstance(value,list): return []
    out=[]
    for item in value:
        if key and isinstance(item,dict): item=item.get(key)
        if item is not None and str(item).strip(): out.append(str(item).strip())
    return out
def _unique(items:List[Any])->List[str]:
    out=[]; seen=set()
    for item in items:
        v=str(item or "").strip()
        if v and v.lower() not in seen: out.append(v); seen.add(v.lower())
    return out
def _number(value:Any)->float:
    try: return round(float(value or 0),1)
    except (TypeError,ValueError): return 0.0
