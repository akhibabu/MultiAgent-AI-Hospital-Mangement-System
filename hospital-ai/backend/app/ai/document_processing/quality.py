"""Quality gates for extracted document text before persistence."""

from __future__ import annotations

import re
from typing import List

from app.ai.document_processing.cleaner import DocumentCleaner
from app.ai.document_processing.models import QualityReport


MIN_READABLE_CHARS = 50
LOW_CONFIDENCE_THRESHOLD = 0.70


class QualityChecker:
    """
    Validate extraction quality before saving.

    Failed  → fewer than MIN_READABLE_CHARS readable characters, or PDF binary.
    Warning → confidence below 70%.
    """

    def __init__(self, cleaner: DocumentCleaner | None = None) -> None:
        self._cleaner = cleaner or DocumentCleaner()

    def evaluate(
        self,
        *,
        clean_text: str,
        confidence: float,
        page_count: int,
    ) -> QualityReport:
        warnings: List[str] = []
        errors: List[str] = []

        if self._cleaner.looks_like_pdf_binary(clean_text):
            errors.append(
                "Extracted content looked like PDF internals, not readable text."
            )
            return QualityReport(
                passed=False,
                confidence=0.0,
                character_count=0,
                word_count=0,
                page_count=max(1, page_count),
                warnings=warnings,
                errors=errors,
            )

        text = (clean_text or "").strip()
        char_count = len(re.findall(r"[A-Za-z0-9\u0900-\u097F]", text))
        word_count = len(re.findall(r"[A-Za-z0-9\u0900-\u097F]+", text))

        if char_count < MIN_READABLE_CHARS:
            errors.append(
                f"Extraction produced only {char_count} readable characters "
                f"(minimum {MIN_READABLE_CHARS}). "
                "The document may be empty, corrupted, or unscannable."
            )
            return QualityReport(
                passed=False,
                confidence=float(confidence or 0.0),
                character_count=char_count,
                word_count=word_count,
                page_count=max(1, page_count),
                warnings=warnings,
                errors=errors,
            )

        conf = float(confidence or 0.0)
        if conf < LOW_CONFIDENCE_THRESHOLD:
            warnings.append(
                f"Extraction confidence is {(conf * 100):.0f}% "
                f"(below {int(LOW_CONFIDENCE_THRESHOLD * 100)}%). "
                "Please review the text before Medical Entity Recognition."
            )

        return QualityReport(
            passed=True,
            confidence=conf,
            character_count=char_count,
            word_count=word_count,
            page_count=max(1, page_count),
            warnings=warnings,
            errors=errors,
        )
