"""
DocumentProcessingService — intelligent hospital document text extraction.

Digital PDF  → embedded text (PyMuPDF / pdfplumber)
Scanned PDF  → page images → PaddleOCR (Tesseract fallback)
Image        → PaddleOCR (Tesseract fallback)

Never returns PDF binary / object streams.
"""

from __future__ import annotations

import re
import time
from typing import List, Optional

from app.ai.document_processing.classifier import DocumentClassifier
from app.ai.document_processing.cleaner import DocumentCleaner
from app.ai.document_processing.models import DocumentProcessingResult
from app.ai.document_processing.ocr_processor import OCRProcessor
from app.ai.document_processing.pdf_extractor import PDFTextExtractor
from app.ai.document_processing.quality import QualityChecker
from app.ai.document_processing.scanned_processor import ScannedDocumentProcessor
from app.core.logging import get_logger

logger = get_logger("hospital_ai.document.service")

# Below this many alphanumeric chars → treat PDF as scanned.
MIN_EMBEDDED_TEXT_CHARS = 40


class DocumentProcessingService:
    """Orchestrates classification → extraction/OCR → clean → quality check."""

    def __init__(
        self,
        *,
        classifier: Optional[DocumentClassifier] = None,
        pdf_extractor: Optional[PDFTextExtractor] = None,
        scanned_processor: Optional[ScannedDocumentProcessor] = None,
        ocr_processor: Optional[OCRProcessor] = None,
        cleaner: Optional[DocumentCleaner] = None,
        quality_checker: Optional[QualityChecker] = None,
    ) -> None:
        self._classifier = classifier or DocumentClassifier()
        self._pdf = pdf_extractor or PDFTextExtractor()
        self._ocr = ocr_processor or OCRProcessor()
        self._scanned = scanned_processor or ScannedDocumentProcessor(
            pdf_extractor=self._pdf,
            ocr_processor=self._ocr,
        )
        self._cleaner = cleaner or DocumentCleaner()
        self._quality = quality_checker or QualityChecker(cleaner=self._cleaner)

    def process(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> DocumentProcessingResult:
        started = time.perf_counter()
        logs: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        classification = self._classifier.classify(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        logs.append(
            f"Detected file kind: {classification.file_kind} ({file_name})"
        )

        try:
            if classification.file_kind == "pdf":
                result = self._process_pdf(file_bytes, logs, errors)
            elif classification.file_kind == "image":
                result = self._process_image(file_bytes, logs, errors)
            else:
                errors.append(
                    f"Unsupported document type. "
                    f"Upload a PDF, PNG, JPG, or JPEG file."
                )
                result = self._failed(
                    document_type="unknown",
                    processing_method="none",
                    library_used="none",
                    logs=logs,
                    errors=errors,
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Document processing failed")
            errors.append(self._friendly_error(exc))
            result = self._failed(
                document_type="unknown",
                processing_method="none",
                library_used="none",
                logs=logs,
                errors=errors,
            )

        # Clean + quality gate
        raw = result.raw_extracted_text or ""
        if self._cleaner.looks_like_pdf_binary(raw):
            logs.append("Rejected output that looked like PDF internals")
            raw = ""
            errors.append(
                "Extracted content looked like PDF binary, not readable text."
            )

        clean = self._cleaner.clean(raw)
        quality = self._quality.evaluate(
            clean_text=clean,
            confidence=result.confidence,
            page_count=result.page_count,
        )
        warnings.extend(quality.warnings)
        errors.extend(quality.errors)

        result.raw_extracted_text = raw
        result.clean_text = clean
        result.character_count = quality.character_count
        result.word_count = quality.word_count
        result.page_count = quality.page_count
        result.confidence = quality.confidence if quality.passed else result.confidence
        result.warnings = warnings
        result.quality = quality
        result.logs = logs + list(result.logs or [])
        result.errors = list(dict.fromkeys(errors + list(result.errors or [])))
        result.processing_time_ms = int((time.perf_counter() - started) * 1000)
        result.language = self._detect_language(clean) or result.language

        if not quality.passed:
            result.status = "Failed"
            result.error_message = "; ".join(quality.errors) or "Extraction quality check failed"
        elif result.status != "Failed":
            result.status = "Completed"
            result.error_message = None

        return result

    def _process_pdf(
        self, file_bytes: bytes, logs: List[str], errors: List[str]
    ) -> DocumentProcessingResult:
        extracted = self._pdf.extract(file_bytes)
        logs.extend(extracted.logs)

        if extracted.encrypted:
            errors.append(extracted.error or "Encrypted PDFs are not supported")
            return self._failed(
                document_type="digital_pdf",
                processing_method="embedded_text",
                library_used=extracted.library_used,
                logs=[],
                errors=errors,
                page_count=extracted.page_count or 0,
            )

        if extracted.corrupted:
            errors.append(extracted.error or "Corrupted PDF")
            return self._failed(
                document_type="unknown",
                processing_method="none",
                library_used="none",
                logs=[],
                errors=errors,
            )

        cleaned_probe = self._cleaner.clean(extracted.text)
        alnum = len(re.findall(r"[A-Za-z0-9\u0900-\u097F]", cleaned_probe))

        if alnum >= MIN_EMBEDDED_TEXT_CHARS and not self._cleaner.looks_like_pdf_binary(
            cleaned_probe
        ):
            logs.append("Using embedded PDF text extraction (no OCR)")
            return DocumentProcessingResult(
                raw_extracted_text=extracted.text,
                clean_text="",  # filled by process()
                document_type="digital_pdf",
                processing_method="embedded_text",
                ocr_provider=None,
                library_used=extracted.library_used,
                fallback_used=extracted.fallback_used,
                language=self._detect_language(cleaned_probe),
                confidence=0.94 if extracted.library_used == "pymupdf" else 0.90,
                processing_time_ms=0,
                page_count=extracted.page_count or 1,
                character_count=0,
                word_count=0,
                status="Completed",
                logs=[],
                errors=[],
            )

        # --- Scanned PDF OCR disabled for now ---
        # When re-enabled: rasterize pages → PaddleOCR / Tesseract → merge text.
        logs.append(
            f"Embedded text insufficient ({alnum} readable chars) — "
            "scanned PDF OCR is currently disabled"
        )
        errors.append(
            "This PDF has little or no selectable text (likely scanned). "
            "Scanned PDF extraction is disabled for now. "
            "Please upload a digital (text) PDF, or a PNG/JPG image instead."
        )
        return self._failed(
            document_type="scanned_pdf",
            processing_method="ocr",
            library_used=extracted.library_used or "none",
            logs=[],
            errors=errors,
            page_count=extracted.page_count or 1,
            fallback_used=False,
        )

        # scanned = self._scanned.process_scanned_pdf(file_bytes)
        # logs.extend(scanned.logs)
        # errors.extend(scanned.errors)
        #
        # if scanned.errors and not (scanned.text or "").strip():
        #     return self._failed(
        #         document_type="scanned_pdf",
        #         processing_method="ocr",
        #         library_used=scanned.library_used,
        #         logs=[],
        #         errors=errors,
        #         page_count=scanned.page_count,
        #         ocr_provider=scanned.library_used
        #         if scanned.library_used in {"paddleocr", "tesseract"}
        #         else None,
        #         fallback_used=scanned.fallback_used,
        #     )
        #
        # return DocumentProcessingResult(
        #     raw_extracted_text=scanned.text,
        #     clean_text="",
        #     document_type="scanned_pdf",
        #     processing_method="ocr",
        #     ocr_provider=scanned.library_used
        #     if scanned.library_used in {"paddleocr", "tesseract"}
        #     else scanned.library_used,
        #     library_used=f"pymupdf+{scanned.library_used}",
        #     fallback_used=scanned.fallback_used,
        #     language=scanned.language,
        #     confidence=scanned.confidence,
        #     processing_time_ms=0,
        #     page_count=scanned.page_count or 1,
        #     character_count=0,
        #     word_count=0,
        #     status="Completed",
        #     logs=[],
        #     errors=[],
        #     images_meta=scanned.images_meta,
        # )

    def _process_image(
        self, file_bytes: bytes, logs: List[str], errors: List[str]
    ) -> DocumentProcessingResult:
        logs.append("Image document — OCR path")
        scanned = self._scanned.process_image(file_bytes)
        logs.extend(scanned.logs)
        errors.extend(scanned.errors)

        if scanned.errors and not (scanned.text or "").strip():
            return self._failed(
                document_type="image",
                processing_method="ocr",
                library_used=scanned.library_used,
                logs=[],
                errors=errors,
                page_count=1,
                ocr_provider=scanned.library_used
                if scanned.library_used in {"paddleocr", "tesseract"}
                else None,
                fallback_used=scanned.fallback_used,
            )

        return DocumentProcessingResult(
            raw_extracted_text=scanned.text,
            clean_text="",
            document_type="image",
            processing_method="ocr",
            ocr_provider=scanned.library_used,
            library_used=scanned.library_used,
            fallback_used=scanned.fallback_used,
            language=scanned.language,
            confidence=scanned.confidence,
            processing_time_ms=0,
            page_count=1,
            character_count=0,
            word_count=0,
            status="Completed",
            logs=[],
            errors=[],
            images_meta=scanned.images_meta,
        )

    def _failed(
        self,
        *,
        document_type: str,
        processing_method: str,
        library_used: str,
        logs: List[str],
        errors: List[str],
        page_count: int = 0,
        ocr_provider: Optional[str] = None,
        fallback_used: bool = False,
    ) -> DocumentProcessingResult:
        return DocumentProcessingResult(
            raw_extracted_text="",
            clean_text="",
            document_type=document_type,
            processing_method=processing_method,
            ocr_provider=ocr_provider,
            library_used=library_used,
            fallback_used=fallback_used,
            language="unknown",
            confidence=0.0,
            processing_time_ms=0,
            page_count=page_count,
            character_count=0,
            word_count=0,
            status="Failed",
            error_message="; ".join(errors) if errors else "Document processing failed",
            logs=logs,
            errors=errors,
        )

    def _detect_language(self, text: str) -> str:
        if not text or not text.strip():
            return "unknown"
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(1, len(text))
        return "en" if ascii_ratio > 0.8 else "unknown"

    def _friendly_error(self, exc: Exception) -> str:
        msg = str(exc)
        if "Encrypt" in msg or "encrypted" in msg.lower():
            return "Encrypted PDFs are not supported. Upload an unlocked PDF."
        if "Unsupported" in msg:
            return "Unsupported file type. Please upload PDF, PNG, JPG, or JPEG."
        if "Tesseract" in msg or "PaddleOCR" in msg or "OCR" in msg:
            return msg
        return f"Document processing failed: {msg}"


class DocumentProcessorFactory:
    """Factory for DocumentProcessingService (easy DI / testing)."""

    @staticmethod
    def create() -> DocumentProcessingService:
        return DocumentProcessingService()
