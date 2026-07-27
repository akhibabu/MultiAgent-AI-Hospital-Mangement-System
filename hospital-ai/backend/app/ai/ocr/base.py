"""
OCR provider interface — Strategy Pattern.

OCR converts documents into machine-readable text only.
It MUST NOT identify diseases, medications, symptoms, or diagnoses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Provenance:
    """Every OCR artifact must carry provenance."""

    source_document: str
    file_name: str
    document_type: str
    page_number: int
    ocr_provider: str
    extraction_time: str
    confidence_score: float
    processing_job_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_document": self.source_document,
            "file_name": self.file_name,
            "document_type": self.document_type,
            "page_number": self.page_number,
            "ocr_provider": self.ocr_provider,
            "extraction_time": self.extraction_time,
            "confidence_score": self.confidence_score,
            "processing_job": self.processing_job_id,
        }


@dataclass
class OCRTable:
    page_number: int
    rows: List[List[str]]
    confidence: float
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "rows": self.rows,
            "confidence": self.confidence,
            "provenance": self.provenance,
        }


@dataclass
class OCRImageMeta:
    page_number: int
    width: Optional[int]
    height: Optional[int]
    format: Optional[str]
    byte_size: int
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "format": self.format,
            "byte_size": self.byte_size,
            "provenance": self.provenance,
        }


@dataclass
class OCRExtractionResult:
    """Full OCR output — text + tables + images + language + confidence."""

    raw_text: str
    tables: List[OCRTable]
    images: List[OCRImageMeta]
    detected_language: str
    confidence: float
    provider: str
    page_count: int
    processing_time_ms: int
    provenance: Provenance
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "tables": [t.to_dict() for t in self.tables],
            "images": [i.to_dict() for i in self.images],
            "detected_language": self.detected_language,
            "confidence": self.confidence,
            "provider": self.provider,
            "page_count": self.page_count,
            "processing_time_ms": self.processing_time_ms,
            "provenance": self.provenance.to_dict(),
            "metadata": self.metadata,
        }


class OCRProvider(ABC):
    """
    Provider-independent OCR interface.

    Adapters: Stub (complete), Tesseract, PaddleOCR, Google Vision, Azure.
    """

    name: str

    @abstractmethod
    def extract_text(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> str:
        """Return raw OCR text only (no medical interpretation)."""

    @abstractmethod
    def extract_tables(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> List[OCRTable]:
        """Return tabular regions as raw cell strings."""

    @abstractmethod
    def extract_images(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> List[OCRImageMeta]:
        """Return image / page metadata (not pixel payloads)."""

    @abstractmethod
    def detect_language(
        self,
        *,
        text: str,
    ) -> str:
        """Detect language code (e.g. en, hi, unknown)."""

    @abstractmethod
    def get_confidence(self) -> float:
        """Last extraction confidence in [0, 1]."""

    def run(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
        provenance: Provenance,
    ) -> OCRExtractionResult:
        """Template method: full extraction using Strategy methods."""
        started = datetime.utcnow()
        text = self.extract_text(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        tables = self.extract_tables(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        images = self.extract_images(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        language = self.detect_language(text=text)
        confidence = self.get_confidence()
        elapsed = int((datetime.utcnow() - started).total_seconds() * 1000)

        provenance.confidence_score = confidence
        provenance.extraction_time = datetime.utcnow().isoformat() + "Z"
        provenance.ocr_provider = self.name

        for table in tables:
            if not table.provenance:
                table.provenance = provenance.to_dict()
        for image in images:
            if not image.provenance:
                image.provenance = provenance.to_dict()

        return OCRExtractionResult(
            raw_text=text,
            tables=tables,
            images=images,
            detected_language=language,
            confidence=confidence,
            provider=self.name,
            page_count=max(1, len(images) or 1),
            processing_time_ms=elapsed,
            provenance=provenance,
            metadata={"content_type": content_type, "byte_size": len(file_bytes)},
        )


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
