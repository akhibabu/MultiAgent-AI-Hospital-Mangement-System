"""Research Agent — Step 6: Recommendation Generation."""

from __future__ import annotations

from typing import List

from app.ai.research.models import RankedEvidence, ResearchRecommendation


class RecommendationGenerator:
    """Synthesizes ranked evidence into clinician-friendly recommendations."""

    def generate(
        self, condition: str, evidence: List[RankedEvidence]
    ) -> ResearchRecommendation:
        condition_evidence = [e for e in evidence if e.condition == condition]

        literature = [e for e in condition_evidence if e.evidence_type == "pubmed"]
        guidelines = [e for e in condition_evidence if e.evidence_type == "guideline"]
        trials = [e for e in condition_evidence if e.evidence_type == "clinical_trial"]

        high_count = sum(1 for e in condition_evidence if e.evidence_level == "High")
        confidence_score = round(
            min(
                0.95,
                (sum(e.confidence for e in condition_evidence) / len(condition_evidence))
                if condition_evidence
                else 0.3,
            ),
            3,
        )

        highlights: List[str] = []
        if trials:
            highlights.append(
                f"{len(trials)} related clinical trial(s) identified, "
                f"{sum(1 for t in trials if 'Completed' in t.source or True)} referenced."
            )
        if high_count:
            highlights.append(f"{high_count} high-quality evidence source(s) support this condition.")
        if not condition_evidence:
            highlights.append("No evidence retrieved for this condition from configured providers.")

        recommended_tests = list(
            dict.fromkeys(
                g.title.split(" for ")[0] for g in guidelines
            )
        )[:3]

        evidence_summary = (
            f"{len(literature)} literature source(s), {len(trials)} clinical trial(s), "
            f"and {len(guidelines)} guideline(s) reviewed for {condition}."
        )

        return ResearchRecommendation(
            condition=condition,
            supporting_literature=[l.title for l in literature[:5]],
            clinical_guidelines=[g.title for g in guidelines[:5]],
            evidence_summary=evidence_summary,
            recommended_diagnostic_tests=recommended_tests,
            research_highlights=highlights,
            confidence_score=confidence_score,
        )
