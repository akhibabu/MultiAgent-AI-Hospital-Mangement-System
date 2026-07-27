"""
Patient Risk Profiling — Intake Agent Stage 5.

Clinical decision-support only.
Does NOT diagnose, prescribe, or replace physician judgment.
Estimates risk from recognized entities and patient history.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.ai.ner.extractor import ExtractedMedicalEntities, VitalEntity, LabValueEntity


# ---------------------------------------------------------------------------
# Levels & categories
# ---------------------------------------------------------------------------

RISK_LEVELS = ("Very Low", "Low", "Moderate", "High", "Critical")

RISK_CATEGORIES = (
    "General Health Risk",
    "Cardiovascular Risk",
    "Diabetes Risk",
    "Respiratory Risk",
    "Neurological Risk",
    "Emergency Risk",
    "Medication Interaction Risk",
    "Hospital Readmission Risk",
)


def score_to_level(score: float) -> str:
    s = max(0.0, min(100.0, float(score)))
    if s >= 76:
        return "Critical"
    if s >= 51:
        return "High"
    if s >= 31:
        return "Moderate"
    if s >= 16:
        return "Low"
    return "Very Low"


def level_rank(level: str) -> int:
    try:
        return RISK_LEVELS.index(level)
    except ValueError:
        return 0


class CategoryRisk(BaseModel):
    """Single risk category assessment."""

    name: str
    level: str = "Very Low"
    score: float = 0.0
    reason: str = ""
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.7
    factors: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class RiskAlert(BaseModel):
    severity: str  # info | warning | critical
    message: str
    category: Optional[str] = None


class PatientRiskAssessment(BaseModel):
    """Full Stage 5 output — multi-category risk profile."""

    overall_level: str = "Very Low"
    overall_score: float = 0.0
    overall_confidence: float = 0.7
    categories: List[CategoryRisk] = Field(default_factory=list)
    top_risk_factors: List[str] = Field(default_factory=list)
    important_findings: List[str] = Field(default_factory=list)
    alerts: List[RiskAlert] = Field(default_factory=list)
    distribution: Dict[str, int] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    disclaimer: str = (
        "Clinical decision-support estimate only. "
        "Does not diagnose, prescribe, or replace physician judgment."
    )
    suggested_next_stage: str = "Patient Knowledge Graph"
    source: str = "rule_based_risk_profiler"
    assessed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


# Backward-compatible shim used by legacy intake pipeline
class PatientRiskProfile(BaseModel):
    risk_level: str = "Low Risk"
    risk_factors: List[str] = Field(default_factory=list)
    reasoning: str = ""
    score: int = 0


class RiskLevel:
    """Legacy level strings."""

    LOW = "Low Risk"
    MEDIUM = "Medium Risk"
    HIGH = "High Risk"


# ---------------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------------


class RiskProfiler:
    """
    Modular rule-based risk profiler.

    Consumes NER entities + optional history/age.
    Produces category risks with reasons and evidence.
    """

    def assess(
        self,
        entities: ExtractedMedicalEntities,
        *,
        allergies: Optional[List[str]] = None,
        age_years: Optional[int] = None,
        medical_history: Optional[Dict[str, Any]] = None,
        timeline: Optional[List[Any]] = None,
    ) -> PatientRiskAssessment:
        diseases = [d.lower() for d in entities.diseases]
        symptoms = [s.lower() for s in entities.symptoms]
        conditions = diseases + [c.lower() for c in entities.medical_conditions]
        med_names = [m.name.lower() for m in entities.medications]
        all_allergies = list(allergies or []) + list(entities.allergies)
        history = medical_history or {}

        # Merge history hints (non-authoritative)
        hist_conditions = [
            str(x).lower()
            for x in (
                history.get("previous_diagnoses")
                or history.get("conditions")
                or []
            )
            if x
        ]
        hist_meds = [
            str(x).lower()
            for x in (history.get("medications") or [])
            if x
        ]
        hist_allergies = [
            str(x).lower()
            for x in (history.get("allergies") or [])
            if x
        ]
        conditions = list(dict.fromkeys(conditions + hist_conditions))
        med_names = list(dict.fromkeys(med_names + hist_meds))
        all_allergies = list(
            dict.fromkeys(
                [a for a in all_allergies if a]
                + [a.title() for a in hist_allergies]
            )
        )

        categories = [
            self._cardiovascular(entities, conditions, symptoms),
            self._diabetes(entities, conditions, med_names),
            self._respiratory(entities, conditions, symptoms),
            self._neurological(entities, conditions, symptoms),
            self._emergency(entities, conditions, symptoms),
            self._medication_interaction(
                entities, med_names, all_allergies
            ),
            self._readmission(
                entities, conditions, symptoms, age_years, timeline
            ),
            self._general_health(
                entities, conditions, symptoms, age_years, all_allergies
            ),
        ]

        # Overall = weighted blend favoring highest acuity categories
        weights = {
            "Emergency Risk": 1.4,
            "Cardiovascular Risk": 1.2,
            "Respiratory Risk": 1.1,
            "Neurological Risk": 1.1,
            "Diabetes Risk": 1.0,
            "Medication Interaction Risk": 0.9,
            "Hospital Readmission Risk": 0.9,
            "General Health Risk": 0.8,
        }
        weighted = 0.0
        wsum = 0.0
        for cat in categories:
            w = weights.get(cat.name, 1.0)
            weighted += cat.score * w
            wsum += w
        overall_score = round(weighted / wsum if wsum else 0.0, 1)
        overall_level = score_to_level(overall_score)

        # Confidence: more populated categories → higher
        filled = sum(1 for c in categories if c.score >= 10 or c.evidence)
        conf = round(min(0.92, 0.55 + filled * 0.04), 3)
        avg_cat_conf = (
            sum(c.confidence for c in categories) / len(categories)
            if categories
            else 0.7
        )
        overall_confidence = round((conf + avg_cat_conf) / 2, 3)

        # Top factors / findings
        factor_rows: List[Tuple[float, str]] = []
        findings: List[str] = []
        for cat in sorted(categories, key=lambda c: c.score, reverse=True):
            for f in cat.factors[:3]:
                factor_rows.append((cat.score, f"{cat.name}: {f}"))
            if cat.level in {"High", "Critical"} and cat.reason:
                findings.append(f"{cat.name} — {cat.reason}")
            elif cat.evidence and cat.score >= 25:
                findings.append(f"{cat.name}: {cat.evidence[0]}")

        factor_rows.sort(key=lambda x: x[0], reverse=True)
        top_factors = []
        seen = set()
        for _, f in factor_rows:
            if f.lower() in seen:
                continue
            seen.add(f.lower())
            top_factors.append(f)
            if len(top_factors) >= 8:
                break

        alerts = self._build_alerts(categories, overall_level)
        distribution = {lvl: 0 for lvl in RISK_LEVELS}
        for cat in categories:
            distribution[cat.level] = distribution.get(cat.level, 0) + 1

        timeline_events = self._build_timeline(
            categories, overall_level, overall_score, timeline
        )

        return PatientRiskAssessment(
            overall_level=overall_level,
            overall_score=overall_score,
            overall_confidence=overall_confidence,
            categories=categories,
            top_risk_factors=top_factors,
            important_findings=findings[:8]
            or ["No high-acuity risk triggers matched from recognized entities."],
            alerts=alerts,
            distribution=distribution,
            timeline=timeline_events,
        )

    def profile(
        self,
        entities: ExtractedMedicalEntities,
        *,
        allergies: Optional[List[str]] = None,
        age_years: Optional[int] = None,
    ) -> PatientRiskProfile:
        """Legacy single-score profile for older callers."""
        assessment = self.assess(
            entities, allergies=allergies, age_years=age_years
        )
        legacy = {
            "Very Low": RiskLevel.LOW,
            "Low": RiskLevel.LOW,
            "Moderate": RiskLevel.MEDIUM,
            "High": RiskLevel.HIGH,
            "Critical": RiskLevel.HIGH,
        }.get(assessment.overall_level, RiskLevel.LOW)
        return PatientRiskProfile(
            risk_level=legacy,
            risk_factors=assessment.top_risk_factors,
            reasoning="; ".join(assessment.important_findings[:4]),
            score=int(round(assessment.overall_score)),
        )

    # ----- category scorers -----

    def _cardiovascular(
        self,
        entities: ExtractedMedicalEntities,
        conditions: List[str],
        symptoms: List[str],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        cardio_dx = [
            ("myocardial infarction", 35, "History of myocardial infarction"),
            ("heart failure", 30, "Heart failure documented"),
            ("coronary artery disease", 25, "Coronary artery disease"),
            ("hypertension", 18, "History of hypertension"),
            ("stroke", 28, "Prior stroke / CVA"),
        ]
        for term, pts, label in cardio_dx:
            if any(term in c for c in conditions):
                score += pts
                factors.append(label)
                evidence.append(label)
                reasons.append(label)

        if any("chest pain" in s for s in symptoms):
            score += 22
            factors.append("Chest pain")
            evidence.append("Symptom: chest pain")
            reasons.append("Chest pain raises cardiovascular acuity")

        for vital in entities.vitals:
            bp = self._parse_bp(vital)
            if bp:
                sys, dia = bp
                if sys >= 180 or dia >= 120:
                    score += 30
                    factors.append(f"Critical BP {vital.value}")
                    evidence.append(f"Blood pressure {vital.value}")
                    reasons.append("Blood pressure critically elevated")
                elif sys >= 140 or dia >= 90:
                    score += 18
                    factors.append(f"Elevated BP {vital.value}")
                    evidence.append(f"Blood pressure {vital.value}")
                    reasons.append("Blood pressure above normal range")
            hr = self._parse_float(vital.value) if self._is_hr(vital) else None
            if hr is not None and (hr >= 120 or hr <= 45):
                score += 14
                factors.append(f"Abnormal HR {vital.value}")
                evidence.append(f"Heart rate {vital.value}")

        score = min(100.0, score)
        reason = (
            reasons[0]
            if reasons
            else "No major cardiovascular risk signals from recognized entities."
        )
        if len(reasons) > 1:
            reason = f"{reasons[0]}. {reasons[1]}."
        return CategoryRisk(
            name="Cardiovascular Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reason,
            evidence=evidence[:6],
            factors=factors,
            confidence=0.82 if evidence else 0.6,
        )

    def _diabetes(
        self,
        entities: ExtractedMedicalEntities,
        conditions: List[str],
        med_names: List[str],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        if any("diabetes" in c for c in conditions):
            score += 25
            factors.append("Diabetes documented")
            evidence.append("Recognized disease: diabetes")
            reasons.append("Documented diabetes increases metabolic risk")

        if any(m in med_names for m in ("metformin", "insulin", "glipizide", "sitagliptin")):
            score += 10
            factors.append("Glucose-lowering medication")
            evidence.append("Diabetes-related medication recognized")

        for lab in entities.lab_values:
            if "hba1c" in lab.name.lower():
                val = self._parse_float(lab.value)
                if val is not None:
                    if val >= 9:
                        score += 28
                        factors.append(f"HbA1c {lab.value}")
                        evidence.append(f"HbA1c {lab.value}")
                        reasons.append("HbA1c indicates poor glycemic control")
                    elif val >= 7:
                        score += 16
                        factors.append(f"HbA1c {lab.value}")
                        evidence.append(f"HbA1c {lab.value}")
                        reasons.append("HbA1c above target range")
            if "glucose" in lab.name.lower():
                val = self._parse_float(lab.value)
                if val is not None and val >= 200:
                    score += 18
                    factors.append(f"Glucose {lab.value}")
                    evidence.append(f"Glucose {lab.value}")

        score = min(100.0, score)
        reason = reasons[0] if reasons else "No significant diabetes risk signals."
        return CategoryRisk(
            name="Diabetes Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reason,
            evidence=evidence[:6],
            factors=factors,
            confidence=0.8 if evidence else 0.58,
        )

    def _respiratory(
        self,
        entities: ExtractedMedicalEntities,
        conditions: List[str],
        symptoms: List[str],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        for term, pts, label in (
            ("pneumonia", 28, "Pneumonia"),
            ("copd", 22, "COPD"),
            ("asthma", 14, "Asthma"),
            ("tuberculosis", 20, "Tuberculosis"),
            ("bronchitis", 12, "Bronchitis"),
        ):
            if any(term in c for c in conditions):
                score += pts
                factors.append(label)
                evidence.append(label)
                reasons.append(f"{label} documented")

        for s in ("shortness of breath", "dyspnea", "cough", "wheeze"):
            if any(s in sx for sx in symptoms):
                score += 12
                factors.append(s.title())
                evidence.append(f"Symptom: {s}")

        for vital in entities.vitals:
            if "spo2" in vital.name.lower():
                val = self._parse_float(vital.value.replace("%", ""))
                if val is not None:
                    if val < 90:
                        score += 32
                        factors.append(f"Critical SpO2 {vital.value}")
                        evidence.append(f"SpO2 {vital.value}")
                        reasons.append("Hypoxemia increases respiratory risk")
                    elif val < 94:
                        score += 18
                        factors.append(f"Low SpO2 {vital.value}")
                        evidence.append(f"SpO2 {vital.value}")
                        reasons.append("Oxygen saturation below normal")

        score = min(100.0, score)
        reason = reasons[0] if reasons else "No major respiratory risk signals."
        return CategoryRisk(
            name="Respiratory Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reason,
            evidence=evidence[:6],
            factors=factors,
            confidence=0.8 if evidence else 0.58,
        )

    def _neurological(
        self,
        entities: ExtractedMedicalEntities,
        conditions: List[str],
        symptoms: List[str],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        for term, pts, label in (
            ("stroke", 32, "Stroke"),
            ("seizure", 22, "Seizure disorder"),
            ("migraine", 8, "Migraine"),
            ("parkinson", 18, "Parkinson disease"),
        ):
            if any(term in c for c in conditions):
                score += pts
                factors.append(label)
                evidence.append(label)
                reasons.append(f"{label} documented")

        for s in ("dizziness", "weakness", "confusion", "headache", "seizure"):
            if any(s in sx for sx in symptoms):
                score += 10
                factors.append(s.title())
                evidence.append(f"Symptom: {s}")

        score = min(100.0, score)
        reason = reasons[0] if reasons else "No major neurological risk signals."
        return CategoryRisk(
            name="Neurological Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reason,
            evidence=evidence[:6],
            factors=factors,
            confidence=0.78 if evidence else 0.55,
        )

    def _emergency(
        self,
        entities: ExtractedMedicalEntities,
        conditions: List[str],
        symptoms: List[str],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        emergency_terms = (
            ("sepsis", 40, "Sepsis"),
            ("myocardial infarction", 38, "Acute coronary syndrome risk"),
            ("stroke", 36, "Stroke"),
            ("anaphylaxis", 40, "Anaphylaxis"),
        )
        for term, pts, label in emergency_terms:
            if any(term in c for c in conditions):
                score += pts
                factors.append(label)
                evidence.append(label)
                reasons.append(f"{label} raises emergency acuity")

        if any("chest pain" in s for s in symptoms) and any(
            "shortness of breath" in s or "dyspnea" in s for s in symptoms
        ):
            score += 25
            factors.append("Chest pain with dyspnea")
            evidence.append("Combined chest pain + shortness of breath")
            reasons.append("Combined cardiopulmonary symptoms elevate emergency risk")

        for vital in entities.vitals:
            bp = self._parse_bp(vital)
            if bp and (bp[0] >= 180 or bp[0] <= 85):
                score += 20
                factors.append(f"Unstable BP {vital.value}")
                evidence.append(f"BP {vital.value}")
            if "spo2" in vital.name.lower():
                val = self._parse_float(vital.value.replace("%", ""))
                if val is not None and val < 90:
                    score += 28
                    factors.append(f"Critical SpO2 {vital.value}")
                    evidence.append(f"SpO2 {vital.value}")
                    reasons.append("Critical hypoxemia")

        score = min(100.0, score)
        reason = reasons[0] if reasons else "No emergency-level triggers matched."
        return CategoryRisk(
            name="Emergency Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reason,
            evidence=evidence[:6],
            factors=factors,
            confidence=0.84 if evidence else 0.55,
        )

    def _medication_interaction(
        self,
        entities: ExtractedMedicalEntities,
        med_names: List[str],
        allergies: List[str],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        if len(med_names) >= 5:
            score += 22
            factors.append("Polypharmacy (≥5 medications)")
            evidence.append(f"{len(med_names)} medications recognized")
            reasons.append("Polypharmacy increases interaction and adverse-event risk")
        elif len(med_names) >= 3:
            score += 10
            factors.append("Multiple medications")
            evidence.append(f"{len(med_names)} medications recognized")

        # Simple interaction pairs (recognition aid only)
        pairs = [
            ({"warfarin", "aspirin"}, "Anticoagulant + antiplatelet combination"),
            ({"warfarin", "ibuprofen"}, "Warfarin with NSAID"),
            ({"metformin", "contrast"}, "Metformin with contrast exposure"),
        ]
        med_set = set(med_names)
        for pair, label in pairs:
            if pair.issubset(med_set):
                score += 20
                factors.append(label)
                evidence.append(label)
                reasons.append(label)

        allergy_lower = [a.lower() for a in allergies]
        for med in med_names:
            for allergy in allergy_lower:
                if allergy and allergy in med:
                    score += 28
                    factors.append(f"Possible allergy conflict: {allergy}")
                    evidence.append(f"Allergy {allergy} vs medication {med}")
                    reasons.append(
                        "Medication may conflict with documented allergy"
                    )

        if allergies:
            score += 5
            factors.append("Documented allergies")
            evidence.append("Allergy history present")

        score = min(100.0, score)
        reason = (
            reasons[0]
            if reasons
            else "No major medication interaction signals from recognized entities."
        )
        return CategoryRisk(
            name="Medication Interaction Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reason,
            evidence=evidence[:6],
            factors=factors,
            confidence=0.75 if evidence else 0.55,
        )

    def _readmission(
        self,
        entities: ExtractedMedicalEntities,
        conditions: List[str],
        symptoms: List[str],
        age_years: Optional[int],
        timeline: Optional[List[Any]],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        chronic = (
            "heart failure",
            "copd",
            "chronic kidney disease",
            "diabetes",
            "pneumonia",
        )
        for term in chronic:
            if any(term in c for c in conditions):
                score += 12
                factors.append(term.title())
                evidence.append(f"Chronic/acute condition: {term}")

        if age_years is not None and age_years >= 65:
            score += 12
            factors.append("Age ≥ 65")
            evidence.append(f"Age {age_years}")
            reasons.append("Advanced age elevates readmission risk")

        if len(entities.medications) >= 5:
            score += 10
            factors.append("Complex medication regimen")

        if timeline and len(timeline) >= 4:
            score += 8
            factors.append("Frequent care encounters")
            evidence.append(f"{len(timeline)} timeline events")
            reasons.append("Multiple recent encounters may indicate instability")

        if any("fever" in s or "weakness" in s for s in symptoms):
            score += 6
            factors.append("Ongoing symptoms")

        score = min(100.0, score)
        if not reasons and evidence:
            reasons.append(
                "Chronic conditions and care pattern suggest elevated readmission risk"
            )
        reason = reasons[0] if reasons else "Readmission risk signals are limited."
        return CategoryRisk(
            name="Hospital Readmission Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reason,
            evidence=evidence[:6],
            factors=factors,
            confidence=0.72 if evidence else 0.55,
        )

    def _general_health(
        self,
        entities: ExtractedMedicalEntities,
        conditions: List[str],
        symptoms: List[str],
        age_years: Optional[int],
        allergies: List[str],
    ) -> CategoryRisk:
        score = 0.0
        evidence: List[str] = []
        factors: List[str] = []
        reasons: List[str] = []

        score += min(30.0, len(conditions) * 6)
        if conditions:
            evidence.append(f"{len(conditions)} recognized condition(s)")
            factors.append("Multiple conditions" if len(conditions) > 1 else conditions[0].title())

        score += min(20.0, len(symptoms) * 4)
        if symptoms:
            evidence.append(f"{len(symptoms)} symptom(s)")
            factors.extend([s.title() for s in symptoms[:3]])

        if age_years is not None and age_years >= 65:
            score += 10
            factors.append("Age ≥ 65")
            evidence.append(f"Age {age_years}")

        if allergies:
            score += 4
            factors.append("Allergies documented")

        if entities.procedures:
            score += min(12.0, len(entities.procedures) * 4)
            evidence.append(f"{len(entities.procedures)} procedure(s)")

        if score >= 20:
            reasons.append(
                "Combined clinical entities indicate elevated general health risk"
            )
        else:
            reasons.append("Limited general health risk signals from current data")

        score = min(100.0, score)
        return CategoryRisk(
            name="General Health Risk",
            level=score_to_level(score),
            score=round(score, 1),
            reason=reasons[0],
            evidence=evidence[:6],
            factors=factors[:8],
            confidence=0.7 if evidence else 0.55,
        )

    # ----- helpers -----

    def _build_alerts(
        self, categories: List[CategoryRisk], overall_level: str
    ) -> List[RiskAlert]:
        alerts: List[RiskAlert] = []
        if overall_level == "Critical":
            alerts.append(
                RiskAlert(
                    severity="critical",
                    message=(
                        "Overall health risk is Critical. "
                        "Prompt clinician review is advised."
                    ),
                )
            )
        elif overall_level == "High":
            alerts.append(
                RiskAlert(
                    severity="warning",
                    message=(
                        "Overall health risk is High. "
                        "Review risk cards and evidence carefully."
                    ),
                )
            )

        for cat in categories:
            if cat.level == "Critical":
                alerts.append(
                    RiskAlert(
                        severity="critical",
                        message=f"{cat.name}: {cat.reason}",
                        category=cat.name,
                    )
                )
            elif cat.level == "High":
                alerts.append(
                    RiskAlert(
                        severity="warning",
                        message=f"{cat.name}: {cat.reason}",
                        category=cat.name,
                    )
                )

        alerts.append(
            RiskAlert(
                severity="info",
                message=(
                    "Decision-support only — does not diagnose or prescribe. "
                    "Clinical judgment required."
                ),
            )
        )
        return alerts[:10]

    def _build_timeline(
        self,
        categories: List[CategoryRisk],
        overall_level: str,
        overall_score: float,
        timeline: Optional[List[Any]],
    ) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        events: List[Dict[str, Any]] = [
            {
                "at": now,
                "label": "Risk profile assessed",
                "detail": f"Overall {overall_level} ({overall_score:.0f})",
                "level": overall_level,
            }
        ]
        for cat in sorted(categories, key=lambda c: c.score, reverse=True)[:4]:
            if cat.score >= 15:
                events.append(
                    {
                        "at": now,
                        "label": cat.name,
                        "detail": cat.reason,
                        "level": cat.level,
                        "score": cat.score,
                    }
                )
        if timeline:
            for item in timeline[-3:]:
                if isinstance(item, dict):
                    events.append(
                        {
                            "at": item.get("at") or item.get("date") or now,
                            "label": str(
                                item.get("title")
                                or item.get("event")
                                or "Prior encounter"
                            ),
                            "detail": str(item.get("status") or item.get("detail") or ""),
                            "level": "info",
                        }
                    )
        return events

    def _parse_float(self, value: str) -> Optional[float]:
        try:
            cleaned = re.sub(r"[^\d.]+", "", str(value).split()[0])
            return float(cleaned) if cleaned else None
        except (ValueError, IndexError):
            return None

    def _parse_bp(self, vital: VitalEntity) -> Optional[Tuple[float, float]]:
        if "bp" not in vital.name.lower() and "blood pressure" not in vital.name.lower():
            return None
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", str(vital.value))
        if not m:
            return None
        return float(m.group(1)), float(m.group(2))

    def _is_hr(self, vital: VitalEntity) -> bool:
        n = vital.name.lower()
        return n in {"hr", "heart rate", "pulse"} or "heart rate" in n


risk_profiler = RiskProfiler()
