"""Process scanned PDFs / image documents via page rasterization + OCR."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.ai.document_processing.ocr_processor import OCRProcessResult, OCRProcessor
from app.ai.document_processing.pdf_extractor import PDFTextExtractor
from app.core.logging import get_logger

logger = get_logger("hospital_ai.document.scanned")


@dataclass
class ScannedProcessResult:
    text: str
    confidence: float
    language: str
    library_used: str
    fallback_used: bool
    page_count: int
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    images_meta: List[dict] = field(default_factory=list)


class ScannedDocumentProcessor:
    """
    Convert scanned PDF pages (or image bytes) into OCR text.

    PDF → PNG pages (PyMuPDF / pdf2image) → OCRProcessor (Paddle → Tesseract)
    """

    def __init__(
        self,
        *,
        pdf_extractor: Optional[PDFTextExtractor] = None,
        ocr_processor: Optional[OCRProcessor] = None,
    ) -> None:
        self._pdf = pdf_extractor or PDFTextExtractor()
        self._ocr = ocr_processor or OCRProcessor()

    def process_scanned_pdf(self, file_bytes: bytes) -> ScannedProcessResult:
        logs: List[str] = []
        errors: List[str] = []
        logs.append("Treating PDF as scanned — converting pages to images")
        try:
            page_images, render_logs = self._pdf.render_pages_as_png(file_bytes)
            logs.extend(render_logs)
        except RuntimeError as exc:
            errors.append(str(exc))
            return ScannedProcessResult(
                text="",
                confidence=0.0,
                language="unknown",
                library_used="none",
                fallback_used=True,
                page_count=0,
                logs=logs,
                errors=errors,
            )

        if not page_images:
            errors.append("No pages could be rendered from the PDF")
            return ScannedProcessResult(
                text="",
                confidence=0.0,
                language="unknown",
                library_used="none",
                fallback_used=True,
                page_count=0,
                logs=logs,
                errors=errors,
            )

        try:
            ocr = self._ocr.process_pages(page_images)
        except RuntimeError as exc:
            errors.append(str(exc))
            return ScannedProcessResult(
                text="",
                confidence=0.0,
                language="unknown",
                library_used="none",
                fallback_used=True,
                page_count=len(page_images),
                logs=logs,
                errors=errors,
                images_meta=[
                    {"page_number": i + 1, "format": "png"}
                    for i in range(len(page_images))
                ],
            )

        logs.extend(ocr.logs)
        errors.extend(ocr.errors)
        return ScannedProcessResult(
            text=ocr.text,
            confidence=ocr.confidence,
            language=ocr.language,
            library_used=ocr.library_used,
            fallback_used=ocr.fallback_used,
            page_count=len(page_images),
            logs=logs,
            errors=errors,
            images_meta=[
                {"page_number": i + 1, "format": "png"}
                for i in range(len(page_images))
            ],
        )

    def process_image(self, file_bytes: bytes) -> ScannedProcessResult:
        logs: List[str] = ["Running OCR on image document"]
        errors: List[str] = []
        try:
            ocr: OCRProcessResult = self._ocr.process_image(file_bytes)
        except RuntimeError as exc:
            return ScannedProcessResult(
                text="",
                confidence=0.0,
                language="unknown",
                library_used="none",
                fallback_used=True,
                page_count=1,
                logs=logs,
                errors=[str(exc)],
                images_meta=[{"page_number": 1, "format": "image"}],
            )

        logs.extend(ocr.logs)
        errors.extend(ocr.errors)
        return ScannedProcessResult(
            text=ocr.text,
            confidence=ocr.confidence,
            language=ocr.language,
            library_used=ocr.library_used,
            fallback_used=ocr.fallback_used,
            page_count=1,
            logs=logs,
            errors=errors,
            images_meta=[{"page_number": 1, "format": "image"}],
        )
