"""OCRProcessor — runs PaddleOCR (primary) / Tesseract (fallback) on images."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.ai.document_processing.ocr_engines import (
    EngineOCRResult,
    OCREngine,
    OCRProviderFactory,
)
from app.core.logging import get_logger

logger = get_logger("hospital_ai.document.ocr_processor")


@dataclass
class OCRProcessResult:
    text: str
    confidence: float
    language: str
    library_used: str
    fallback_used: bool
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class OCRProcessor:
    """
    Facade over OCR engines.

    Primary: PaddleOCR
    Fallback: Tesseract (automatic if Paddle fails mid-run)
    """

    def __init__(self, engine: Optional[OCREngine] = None) -> None:
        self._engine = engine
        self._engine_logs: List[str] = []

    def _get_engine(self) -> OCREngine:
        if self._engine is None:
            self._engine, self._engine_logs = OCRProviderFactory.create_with_fallback()
        return self._engine

    def process_image(self, image_bytes: bytes, *, lang: str = "en") -> OCRProcessResult:
        logs: List[str] = list(self._engine_logs)
        errors: List[str] = []
        fallback_used = False

        engine = self._get_engine()
        logs.extend(self._engine_logs)
        self._engine_logs = []

        try:
            result = engine.recognize(image_bytes, lang=lang)
            logs.extend(result.logs)
            return OCRProcessResult(
                text=result.text,
                confidence=result.confidence,
                language=result.language,
                library_used=result.provider,
                fallback_used=result.provider != "paddleocr",
                logs=logs,
                errors=errors,
            )
        except Exception as primary_exc:  # noqa: BLE001
            logs.append(f"{engine.name} failed: {primary_exc}")
            if engine.name == "paddleocr":
                logs.append("Attempting Tesseract fallback")
                try:
                    fallback = OCRProviderFactory.create(preferred="tesseract")
                    result = fallback.recognize(image_bytes, lang=lang)
                    logs.extend(result.logs)
                    fallback_used = True
                    self._engine = fallback
                    return OCRProcessResult(
                        text=result.text,
                        confidence=result.confidence,
                        language=result.language,
                        library_used=result.provider,
                        fallback_used=True,
                        logs=logs,
                        errors=errors,
                    )
                except Exception as fb_exc:  # noqa: BLE001
                    errors.append(str(fb_exc))
                    raise RuntimeError(
                        f"OCR failed (PaddleOCR and Tesseract). "
                        f"Paddle: {primary_exc}; Tesseract: {fb_exc}"
                    ) from fb_exc
            errors.append(str(primary_exc))
            raise RuntimeError(f"OCR failed: {primary_exc}") from primary_exc

    def process_pages(
        self, page_images: List[bytes], *, lang: str = "en"
    ) -> OCRProcessResult:
        logs: List[str] = []
        errors: List[str] = []
        parts: List[str] = []
        confidences: List[float] = []
        library = "none"
        fallback_used = False

        for idx, img in enumerate(page_images, start=1):
            logs.append(f"OCR page {idx}/{len(page_images)}")
            result = self.process_image(img, lang=lang)
            logs.extend(result.logs)
            errors.extend(result.errors)
            if result.text.strip():
                parts.append(result.text.strip())
            confidences.append(result.confidence)
            library = result.library_used
            fallback_used = fallback_used or result.fallback_used

        text = "\n\n".join(parts)
        confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return OCRProcessResult(
            text=text,
            confidence=float(confidence),
            language="en",
            library_used=library,
            fallback_used=fallback_used,
            logs=logs,
            errors=errors,
        )
