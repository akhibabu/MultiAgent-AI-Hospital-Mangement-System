"""Document processing models — readable text only, never PDF binary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class QualityReport:
    passed: bool
    confidence: float
    character_count: int
    word_count: int
    page_count: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class DocumentProcessingResult:
    """Final output of Stage 3 — clean text for Medical Entity Recognition."""

    raw_extracted_text: str
    clean_text: str
    document_type: str  # digital_pdf | scanned_pdf | image | unknown
    processing_method: str  # embedded_text | ocr
    ocr_provider: Optional[str]  # paddleocr | tesseract | None
    library_used: str
    fallback_used: bool
    language: str
    confidence: float
    processing_time_ms: int
    page_count: int
    character_count: int
    word_count: int
    status: str  # Completed | Failed | Partial
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    images_meta: List[Dict[str, Any]] = field(default_factory=list)
    quality: Optional[QualityReport] = None

    @property
    def readable_text(self) -> str:
        """Alias used by NER consumers — always cleaned text."""
        return self.clean_text

    @property
    def extraction_method(self) -> str:
        """Backward-compatible alias for processing_method."""
        return self.processing_method

    @property
    def document_status(self) -> str:
        return self.status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_extracted_text": self.raw_extracted_text,
            "clean_text": self.clean_text,
            "document_type": self.document_type,
            "processing_method": self.processing_method,
            "ocr_provider": self.ocr_provider,
            "library_used": self.library_used,
            "fallback_used": self.fallback_used,
            "language": self.language,
            "confidence": self.confidence,
            "processing_time_ms": self.processing_time_ms,
            "page_count": self.page_count,
            "character_count": self.character_count,
            "word_count": self.word_count,
            "status": self.status,
            "error_message": self.error_message,
            "warnings": self.warnings,
            "logs": self.logs,
            "errors": self.errors,
            "tables": self.tables,
            "images_meta": self.images_meta,
        }
