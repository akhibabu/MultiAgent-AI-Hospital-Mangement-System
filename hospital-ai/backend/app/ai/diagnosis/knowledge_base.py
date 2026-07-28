"""
Rule-based clinical knowledge base for the Diagnosis Agent.

Deterministic, transparent mapping used by the rule-based differential
strategy. Not a source of medical truth — a decision-support heuristic that
must always be reviewed by a physician.
"""

from __future__ import annotations

from typing import Any, Dict, List, NamedTuple, Optional


class ConditionProfile(NamedTuple):
    condition: str
    body_system: str
    symptoms: List[str]
    labs: List[str]
    vital_signals: List[str]
    risk_category: Optional[str]
    specialists: List[str]
    department: str
    diagnostic_tests: List[str]
    imaging: List[str]
    severity_weight: float


CONDITION_PROFILES: List[ConditionProfile] = [
    ConditionProfile(
        condition="Type 2 Diabetes Mellitus",
        body_system="Endocrine",
        symptoms=["fatigue", "increased thirst", "frequent urination", "blurred vision", "weight loss"],
        labs=["glucose", "hba1c", "blood sugar"],
        vital_signals=["blood glucose"],
        risk_category="Diabetes Risk",
        specialists=["Endocrinologist", "General Physician"],
        department="Endocrinology",
        diagnostic_tests=["Fasting blood glucose", "HbA1c", "Oral glucose tolerance test"],
        imaging=[],
        severity_weight=0.6,
    ),
    ConditionProfile(
        condition="Hypertension",
        body_system="Cardiovascular",
        symptoms=["headache", "dizziness", "blurred vision", "chest pain", "shortness of breath"],
        labs=["creatinine", "cholesterol"],
        vital_signals=["blood pressure"],
        risk_category="Cardiovascular Risk",
        specialists=["Cardiologist", "General Physician"],
        department="Cardiology",
        diagnostic_tests=["Basic metabolic panel", "Lipid panel", "ECG"],
        imaging=["Echocardiogram"],
        severity_weight=0.65,
    ),
    ConditionProfile(
        condition="Coronary Artery Disease",
        body_system="Cardiovascular",
        symptoms=["chest pain", "shortness of breath", "fatigue", "palpitations", "sweating"],
        labs=["troponin", "cholesterol", "ck-mb"],
        vital_signals=["blood pressure", "heart rate"],
        risk_category="Cardiovascular Risk",
        specialists=["Cardiologist", "Emergency Department"],
        department="Cardiology",
        diagnostic_tests=["Troponin", "Lipid panel", "ECG"],
        imaging=["Echocardiogram", "Coronary CT angiography"],
        severity_weight=0.85,
    ),
    ConditionProfile(
        condition="Asthma / Reactive Airway Disease",
        body_system="Respiratory",
        symptoms=["cough", "wheezing", "shortness of breath", "chest tightness"],
        labs=[],
        vital_signals=["oxygen saturation", "respiratory rate"],
        risk_category="Respiratory Risk",
        specialists=["Pulmonologist", "General Physician"],
        department="Pulmonology",
        diagnostic_tests=["Spirometry", "Peak flow measurement"],
        imaging=["Chest X-ray"],
        severity_weight=0.55,
    ),
    ConditionProfile(
        condition="Pneumonia / Respiratory Infection",
        body_system="Respiratory",
        symptoms=["fever", "cough", "shortness of breath", "chest pain", "fatigue"],
        labs=["wbc", "crp"],
        vital_signals=["temperature", "oxygen saturation", "respiratory rate"],
        risk_category="Respiratory Risk",
        specialists=["Pulmonologist", "General Physician"],
        department="Pulmonology",
        diagnostic_tests=["CBC", "CRP", "Sputum culture"],
        imaging=["Chest X-ray"],
        severity_weight=0.7,
    ),
    ConditionProfile(
        condition="Chronic Kidney Disease",
        body_system="Renal",
        symptoms=["fatigue", "swelling", "decreased urination", "nausea"],
        labs=["creatinine", "egfr", "bun"],
        vital_signals=["blood pressure"],
        risk_category="General Health Risk",
        specialists=["Nephrologist", "General Physician"],
        department="Nephrology",
        diagnostic_tests=["Serum creatinine", "eGFR", "Urinalysis"],
        imaging=["Renal ultrasound"],
        severity_weight=0.7,
    ),
    ConditionProfile(
        condition="Urinary Tract Infection",
        body_system="Genitourinary",
        symptoms=["burning urination", "frequent urination", "fever", "abdominal pain"],
        labs=["wbc", "urinalysis"],
        vital_signals=["temperature"],
        risk_category="General Health Risk",
        specialists=["General Physician", "Urologist"],
        department="General Medicine",
        diagnostic_tests=["Urinalysis", "Urine culture"],
        imaging=[],
        severity_weight=0.4,
    ),
    ConditionProfile(
        condition="Anemia",
        body_system="Hematologic",
        symptoms=["fatigue", "weakness", "pale skin", "shortness of breath", "dizziness"],
        labs=["hemoglobin", "hematocrit", "ferritin"],
        vital_signals=["heart rate"],
        risk_category="General Health Risk",
        specialists=["General Physician", "Hematologist"],
        department="Hematology",
        diagnostic_tests=["CBC", "Iron studies", "Ferritin"],
        imaging=[],
        severity_weight=0.45,
    ),
    ConditionProfile(
        condition="Thyroid Disorder",
        body_system="Endocrine",
        symptoms=["fatigue", "weight change", "palpitations", "tremor", "cold intolerance", "heat intolerance"],
        labs=["tsh", "t3", "t4"],
        vital_signals=["heart rate"],
        risk_category="General Health Risk",
        specialists=["Endocrinologist"],
        department="Endocrinology",
        diagnostic_tests=["TSH", "Free T4", "Free T3"],
        imaging=["Thyroid ultrasound"],
        severity_weight=0.4,
    ),
    ConditionProfile(
        condition="Gastritis / Peptic Ulcer Disease",
        body_system="Gastrointestinal",
        symptoms=["abdominal pain", "nausea", "vomiting", "bloating", "loss of appetite"],
        labs=["h pylori"],
        vital_signals=[],
        risk_category="General Health Risk",
        specialists=["Gastroenterologist", "General Physician"],
        department="Gastroenterology",
        diagnostic_tests=["H. pylori test", "Stool occult blood"],
        imaging=["Upper GI endoscopy"],
        severity_weight=0.4,
    ),
    ConditionProfile(
        condition="Migraine / Neurological Headache Disorder",
        body_system="Neurological",
        symptoms=["headache", "nausea", "blurred vision", "sensitivity to light", "dizziness"],
        labs=[],
        vital_signals=["blood pressure"],
        risk_category="Neurological Risk",
        specialists=["Neurologist", "General Physician"],
        department="Neurology",
        diagnostic_tests=["Neurological exam"],
        imaging=["MRI brain (if red flags present)"],
        severity_weight=0.35,
    ),
    ConditionProfile(
        condition="Sepsis / Systemic Infection",
        body_system="Emergency",
        symptoms=["fever", "confusion", "rapid breathing", "low blood pressure", "rapid heart rate"],
        labs=["wbc", "lactate", "crp"],
        vital_signals=["temperature", "blood pressure", "heart rate", "respiratory rate"],
        risk_category="Emergency Risk",
        specialists=["Emergency Department", "General Physician"],
        department="Emergency Medicine",
        diagnostic_tests=["Blood culture", "Lactate", "CBC"],
        imaging=["Chest X-ray"],
        severity_weight=0.95,
    ),
]


def get_condition_profile(condition: str) -> Optional[ConditionProfile]:
    for profile in CONDITION_PROFILES:
        if profile.condition == condition:
            return profile
    return None


class ConditionKnowledgeBase:
    """Read-only accessor over the static condition profile table."""

    def all_profiles(self) -> List[ConditionProfile]:
        return list(CONDITION_PROFILES)

    def get(self, condition: str) -> Optional[ConditionProfile]:
        return get_condition_profile(condition)

    def match_symptom(self, symptom: str) -> List[ConditionProfile]:
        s = symptom.strip().lower()
        return [p for p in CONDITION_PROFILES if any(s in sym or sym in s for sym in p.symptoms)]

    def typical_drugs_for(self, condition: str) -> List[str]:
        """Analysis-only lookup used by the Research Agent (never prescribed)."""
        return _TYPICAL_DRUG_CLASSES.get(condition, [])


_TYPICAL_DRUG_CLASSES: Dict[str, List[str]] = {
    "Type 2 Diabetes Mellitus": ["Metformin", "Insulin", "SGLT2 inhibitors"],
    "Hypertension": ["ACE inhibitors", "Calcium channel blockers", "Thiazide diuretics"],
    "Coronary Artery Disease": ["Statins", "Aspirin", "Beta blockers"],
    "Asthma / Reactive Airway Disease": ["Inhaled corticosteroids", "Bronchodilators"],
    "Pneumonia / Respiratory Infection": ["Beta-lactam antibiotics", "Macrolide antibiotics"],
    "Chronic Kidney Disease": ["ACE inhibitors", "Phosphate binders"],
    "Urinary Tract Infection": ["Fluoroquinolones", "Nitrofurantoin"],
    "Anemia": ["Iron supplements", "Vitamin B12 supplements"],
    "Thyroid Disorder": ["Levothyroxine", "Antithyroid agents"],
    "Gastritis / Peptic Ulcer Disease": ["Proton pump inhibitors", "H2 blockers"],
    "Migraine / Neurological Headache Disorder": ["Triptans", "NSAIDs"],
    "Sepsis / Systemic Infection": ["Broad-spectrum antibiotics", "IV fluids"],
}


def any_metadata() -> Dict[str, Any]:
    return {"condition_count": len(CONDITION_PROFILES)}
