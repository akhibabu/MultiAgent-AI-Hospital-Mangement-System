"""
Medical Entity Recognition — structured extraction for Intake Stage 4.

Recognizes and categorizes medical information from cleaned document text.
Does NOT diagnose, predict severity, or recommend treatment.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class MedicationEntity(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None


class LabValueEntity(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None


class VitalEntity(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None


class MedicalEntity(BaseModel):
    """Canonical entity record for persistence + UI highlighting."""

    type: str
    value: str
    confidence: float = 0.8
    source_document: Optional[str] = None
    page: int = 1
    sentence: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    extraction_time: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class ExtractedMedicalEntities(BaseModel):
    """Grouped NER output + flat entity list for highlighting."""

    diseases: List[str] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    medications: List[MedicationEntity] = Field(default_factory=list)
    dosages: List[str] = Field(default_factory=list)
    frequencies: List[str] = Field(default_factory=list)
    lab_values: List[LabValueEntity] = Field(default_factory=list)
    lab_tests: List[str] = Field(default_factory=list)
    vitals: List[VitalEntity] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    body_parts: List[str] = Field(default_factory=list)
    medical_devices: List[str] = Field(default_factory=list)
    doctor_names: List[str] = Field(default_factory=list)
    hospital_names: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    follow_up_dates: List[str] = Field(default_factory=list)
    medical_conditions: List[str] = Field(default_factory=list)
    medical_codes: List[str] = Field(default_factory=list)
    entities: List[MedicalEntity] = Field(default_factory=list)
    confidence: float = 0.0
    source: str = "rule_based_ner"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    def statistics(self) -> Dict[str, int]:
        return {
            "disease_count": len(self.diseases),
            "medication_count": len(self.medications),
            "symptom_count": len(self.symptoms),
            "allergy_count": len(self.allergies),
            "vital_count": len(self.vitals),
            "lab_value_count": len(self.lab_values),
            "lab_test_count": len(self.lab_tests),
            "procedure_count": len(self.procedures),
            "dosage_count": len(self.dosages),
            "date_count": len(self.dates),
            "doctor_count": len(self.doctor_names),
            "hospital_count": len(self.hospital_names),
            "body_part_count": len(self.body_parts),
            "total_entities": len(self.entities),
        }

    def summary(self) -> Dict[str, Any]:
        """Structured patient summary buckets (recognition only)."""
        return {
            "conditions": self.diseases or self.medical_conditions,
            "current_medications": [
                {
                    "name": m.name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                }
                for m in self.medications
            ],
            "symptoms": self.symptoms,
            "allergies": self.allergies,
            "recent_tests": self.lab_tests
            + [f"{lv.name}: {lv.value}" + (f" {lv.unit}" if lv.unit else "") for lv in self.lab_values],
            "recent_procedures": self.procedures,
            "vitals": [
                {
                    "name": v.name,
                    "value": v.value,
                    "unit": v.unit,
                }
                for v in self.vitals
            ],
            "follow_up": self.follow_up_dates or self.dates[:3],
            "doctors": self.doctor_names,
            "hospitals": self.hospital_names,
        }


# ---------------------------------------------------------------------------
# Lexicons & patterns
# ---------------------------------------------------------------------------

DISEASE_TERMS = [
    "diabetes",
    "type 2 diabetes",
    "type 2 diabetes mellitus",
    "type 1 diabetes",
    "hypertension",
    "asthma",
    "copd",
    "coronary artery disease",
    "heart failure",
    "chronic kidney disease",
    "pneumonia",
    "anemia",
    "hypothyroidism",
    "hyperthyroidism",
    "hyperlipidemia",
    "stroke",
    "myocardial infarction",
    "tuberculosis",
    "covid-19",
    "influenza",
    "bronchitis",
    "gastritis",
    "arthritis",
    "migraine",
    "sepsis",
    "urinary tract infection",
]

SYMPTOM_TERMS = [
    "fever",
    "cough",
    "fatigue",
    "chest pain",
    "shortness of breath",
    "dyspnea",
    "nausea",
    "vomiting",
    "headache",
    "dizziness",
    "edema",
    "palpitations",
    "abdominal pain",
    "sore throat",
    "chills",
    "sweating",
    "weakness",
    "loss of appetite",
    "weight loss",
    "joint pain",
    "back pain",
]

PROCEDURE_TERMS = [
    "chest x-ray",
    "x-ray",
    "mri",
    "ct scan",
    "ultrasound",
    "ecg",
    "ekg",
    "endoscopy",
    "colonoscopy",
    "biopsy",
    "surgery",
    "echocardiogram",
    "angiography",
    "dialysis",
]

BODY_PART_TERMS = [
    "heart",
    "lung",
    "lungs",
    "liver",
    "kidney",
    "kidneys",
    "brain",
    "stomach",
    "chest",
    "abdomen",
    "spine",
    "knee",
    "shoulder",
    "thyroid",
]

LAB_TEST_TERMS = [
    "complete blood count",
    "cbc",
    "lipid panel",
    "liver function test",
    "lft",
    "kidney function test",
    "renal panel",
    "urine analysis",
    "urinalysis",
    "blood culture",
    "thyroid panel",
]

DEVICE_TERMS = [
    "pacemaker",
    "ventilator",
    "insulin pump",
    "cpap",
    "catheter",
    "stent",
]

KNOWN_MEDS = [
    "metformin",
    "amlodipine",
    "lisinopril",
    "atorvastatin",
    "insulin",
    "azithromycin",
    "amoxicillin",
    "paracetamol",
    "acetaminophen",
    "ibuprofen",
    "aspirin",
    "omeprazole",
    "pantoprazole",
    "losartan",
    "atenolol",
    "warfarin",
    "clopidogrel",
    "prednisone",
    "salbutamol",
    "albuterol",
]

MED_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z\-]+(?:mycin|cillin|pril|sartan|olol|statin|formin|pine|azole|vir)?)\s+"
    r"(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|IU|units?))\b",
    re.IGNORECASE,
)
FREQ_PATTERN = re.compile(
    r"\b(once|twice|thrice|three times|four times)\s+(?:a\s+|per\s+)?(day|daily|week|weekly|"
    r"morning|evening|night)|"
    r"\b(OD|BD|TDS|QID|PRN|HS|bid|tid|qid)\b|"
    r"\bevery\s+\d+\s+(?:hours?|hrs?|days?)\b",
    re.IGNORECASE,
)
LAB_PATTERN = re.compile(
    r"\b(HbA1c|Creatinine|WBC|RBC|Hemoglobin|Haemoglobin|Platelets|Glucose|Sodium|Potassium|"
    r"ALT|AST|Troponin|CRP|ESR|TSH|T3|T4|Urea|BUN|LDL|HDL|Triglycerides)\s*[:=]?\s*"
    r"(\d+(?:\.\d+)?)\s*([%a-zA-Z/^µμ0-9\-]*)",
    re.IGNORECASE,
)
VITAL_PATTERN = re.compile(
    r"\b(BP|Blood Pressure|HR|Heart Rate|Temp|Temperature|SpO2|RR|Respiratory Rate|"
    r"Pulse|Weight|Height)\s*[:=]?\s*"
    r"([\d]+(?:\.\d+)?(?:\s*/\s*[\d]+(?:\.\d+)?)?)\s*"
    r"(%|mmHg|bpm|°[CF]|kg|cm|m)?\b",
    re.IGNORECASE,
)
ICD_PATTERN = re.compile(r"\b([A-TV-Z][0-9]{2}(?:\.[0-9A-TV-Z]{1,4})?)\b")
DATE_PATTERN = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)
FOLLOWUP_PATTERN = re.compile(
    r"(?:follow[\s\-]?up|review|return)\s*(?:after|in|on)?\s*"
    r"((?:one|two|three|1|2|3|\d+)\s+(?:day|days|week|weeks|month|months)|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)
DOCTOR_PATTERN = re.compile(r"\bDr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})")
HOSPITAL_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}\s+(?:Hospital|Clinic|Medical Center|Centre))\b"
)
ALLERGY_PATTERN = re.compile(
    r"(?:allerg(?:y|ies)|allergic to)\s*[:\-]?\s*([A-Za-z0-9,\s\-/]+?)(?:\.|;|\n|$)",
    re.IGNORECASE,
)


class MedicalEntityRecognizer:
    """
    Rule-based medical NER.

    Output is recognition-only — never diagnosis or treatment advice.
    """

    def extract(
        self,
        text: str,
        *,
        source_document: Optional[str] = None,
        page: int = 1,
    ) -> ExtractedMedicalEntities:
        if not (text or "").strip():
            return ExtractedMedicalEntities(confidence=0.0)

        now = datetime.now(timezone.utc).isoformat()
        entities: List[MedicalEntity] = []
        lower = text.lower()

        def add(
            etype: str,
            value: str,
            *,
            start: Optional[int] = None,
            end: Optional[int] = None,
            confidence: float = 0.85,
            metadata: Optional[Dict[str, Any]] = None,
        ) -> None:
            value = (value or "").strip(" .;,\t")
            if not value:
                return
            # Deduplicate by type+normalized value; also skip shorter subsumed terms
            key = (etype.lower(), value.lower())
            if any((e.type.lower(), e.value.lower()) == key for e in entities):
                return
            if etype.lower() in {"disease", "symptom", "medical condition", "body part"}:
                for e in entities:
                    if e.type.lower() != etype.lower():
                        continue
                    if value.lower() in e.value.lower() or e.value.lower() in value.lower():
                        # Keep the longer phrase
                        if len(value) <= len(e.value):
                            return
                        entities.remove(e)
                        break
            span = self._find_span(text, value, start, end)
            sentence = self._sentence_at(text, span[0]) if span[0] is not None else None
            entities.append(
                MedicalEntity(
                    type=etype,
                    value=value,
                    confidence=confidence,
                    source_document=source_document,
                    page=page,
                    sentence=sentence,
                    char_start=span[0],
                    char_end=span[1],
                    extraction_time=now,
                    metadata=metadata or {},
                )
            )

        # Term lists (longest match first)
        for term in sorted(DISEASE_TERMS, key=len, reverse=True):
            if term in lower:
                add("Disease", term.title(), confidence=0.9)

        for term in sorted(SYMPTOM_TERMS, key=len, reverse=True):
            if term in lower:
                add("Symptom", term, confidence=0.82)

        for term in sorted(PROCEDURE_TERMS, key=len, reverse=True):
            if term in lower:
                add("Procedure", term.title(), confidence=0.84)

        for term in sorted(BODY_PART_TERMS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(term)}\b", lower):
                add("Body Part", term.title(), confidence=0.75)

        for term in sorted(LAB_TEST_TERMS, key=len, reverse=True):
            if term in lower:
                add("Lab Test", term.upper() if len(term) <= 3 else term.title(), confidence=0.8)

        for term in sorted(DEVICE_TERMS, key=len, reverse=True):
            if term in lower:
                add("Medical Device", term.title(), confidence=0.8)

        for match in MED_PATTERN.finditer(text):
            name, dosage = match.group(1), match.group(2)
            add(
                "Medication",
                name.title(),
                start=match.start(1),
                end=match.end(1),
                confidence=0.88,
                metadata={"dosage": dosage},
            )
            add(
                "Dosage",
                dosage,
                start=match.start(2),
                end=match.end(2),
                confidence=0.9,
                metadata={"medication": name.title()},
            )

        for med in KNOWN_MEDS:
            if med in lower:
                add("Medication", med.title(), confidence=0.86)

        for match in FREQ_PATTERN.finditer(text):
            freq = match.group(0).strip()
            add(
                "Frequency",
                freq,
                start=match.start(),
                end=match.end(),
                confidence=0.8,
            )

        for match in LAB_PATTERN.finditer(text):
            name, value, unit = match.group(1), match.group(2), (match.group(3) or "").strip()
            display = f"{name}: {value}" + (f" {unit}" if unit else "")
            add(
                "Lab Value",
                display,
                start=match.start(),
                end=match.end(),
                confidence=0.9,
                metadata={"name": name, "value": value, "unit": unit or None},
            )
            add("Lab Test", name, confidence=0.85)

        for match in VITAL_PATTERN.finditer(text):
            name, value, unit = match.group(1), match.group(2), (match.group(3) or "").strip()
            display = f"{name}: {value}" + (f" {unit}" if unit else "")
            add(
                "Vital",
                display,
                start=match.start(),
                end=match.end(),
                confidence=0.92,
                metadata={"name": name, "value": value, "unit": unit or None},
            )

        for match in ICD_PATTERN.finditer(text):
            add(
                "Medical Code",
                match.group(1),
                start=match.start(),
                end=match.end(),
                confidence=0.7,
            )

        for match in DATE_PATTERN.finditer(text):
            add(
                "Date",
                match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.8,
            )

        for match in FOLLOWUP_PATTERN.finditer(text):
            add(
                "Follow-up Date",
                match.group(1).strip(),
                start=match.start(1),
                end=match.end(1),
                confidence=0.85,
            )

        for match in DOCTOR_PATTERN.finditer(text):
            add(
                "Doctor",
                match.group(0),
                start=match.start(),
                end=match.end(),
                confidence=0.88,
            )

        for match in HOSPITAL_PATTERN.finditer(text):
            add(
                "Hospital",
                match.group(1),
                start=match.start(1),
                end=match.end(1),
                confidence=0.9,
            )

        for match in ALLERGY_PATTERN.finditer(text):
            parts = [p.strip() for p in match.group(1).split(",") if p.strip()]
            for part in parts[:5]:
                # Avoid swallowing long sentence fragments
                if len(part) > 40:
                    part = part.split()[0]
                add(
                    "Allergy",
                    part.title(),
                    start=match.start(1),
                    end=match.end(1),
                    confidence=0.8,
                )
        if "penicillin" in lower:
            add("Allergy", "Penicillin", confidence=0.85)

        # Build grouped views from flat entities
        diseases = [e.value for e in entities if e.type == "Disease"]
        symptoms = [e.value for e in entities if e.type == "Symptom"]
        procedures = [e.value for e in entities if e.type == "Procedure"]
        body_parts = [e.value for e in entities if e.type == "Body Part"]
        lab_tests = sorted({e.value for e in entities if e.type == "Lab Test"})
        devices = [e.value for e in entities if e.type == "Medical Device"]
        dosages = [e.value for e in entities if e.type == "Dosage"]
        frequencies = [e.value for e in entities if e.type == "Frequency"]
        allergies = [e.value for e in entities if e.type == "Allergy"]
        doctors = [e.value for e in entities if e.type == "Doctor"]
        hospitals = [e.value for e in entities if e.type == "Hospital"]
        dates = [e.value for e in entities if e.type == "Date"]
        follow_ups = [e.value for e in entities if e.type == "Follow-up Date"]
        codes = [e.value for e in entities if e.type == "Medical Code"]

        medications: List[MedicationEntity] = []
        for e in entities:
            if e.type != "Medication":
                continue
            dosage = (e.metadata or {}).get("dosage")
            # Attach nearest frequency if any
            freq = frequencies[0] if frequencies else None
            medications.append(
                MedicationEntity(name=e.value, dosage=dosage, frequency=freq)
            )

        labs = [
            LabValueEntity(
                name=str((e.metadata or {}).get("name") or e.value),
                value=str((e.metadata or {}).get("value") or ""),
                unit=(e.metadata or {}).get("unit"),
            )
            for e in entities
            if e.type == "Lab Value"
        ]
        vitals = [
            VitalEntity(
                name=str((e.metadata or {}).get("name") or e.value),
                value=str((e.metadata or {}).get("value") or ""),
                unit=(e.metadata or {}).get("unit"),
            )
            for e in entities
            if e.type == "Vital"
        ]

        filled = sum(
            1
            for bucket in (
                diseases,
                symptoms,
                medications,
                labs,
                vitals,
                allergies,
                procedures,
                codes,
            )
            if bucket
        )
        confidence = round(min(0.95, 0.35 + filled * 0.08), 4)
        if entities:
            avg = sum(e.confidence for e in entities) / len(entities)
            confidence = round((confidence + avg) / 2, 4)

        return ExtractedMedicalEntities(
            diseases=diseases,
            symptoms=symptoms,
            medications=medications,
            dosages=sorted(set(dosages)),
            frequencies=sorted(set(frequencies)),
            lab_values=labs,
            lab_tests=lab_tests,
            vitals=vitals,
            allergies=sorted(set(allergies)),
            procedures=procedures,
            body_parts=body_parts,
            medical_devices=devices,
            doctor_names=doctors,
            hospital_names=hospitals,
            dates=dates,
            follow_up_dates=follow_ups,
            medical_conditions=diseases,
            medical_codes=codes,
            entities=entities,
            confidence=confidence,
        )

    def _find_span(
        self,
        text: str,
        value: str,
        start: Optional[int],
        end: Optional[int],
    ) -> Tuple[Optional[int], Optional[int]]:
        if start is not None and end is not None:
            return start, end
        idx = text.lower().find(value.lower())
        if idx < 0:
            return None, None
        return idx, idx + len(value)

    def _sentence_at(self, text: str, pos: Optional[int]) -> Optional[str]:
        if pos is None:
            return None
        # Split on sentence boundaries
        starts = [0]
        for m in re.finditer(r"[.!?\n]+", text):
            starts.append(m.end())
        starts.append(len(text))
        for i in range(len(starts) - 1):
            if starts[i] <= pos < starts[i + 1]:
                return text[starts[i] : starts[i + 1]].strip()[:400]
        return None


medical_entity_recognizer = MedicalEntityRecognizer()
