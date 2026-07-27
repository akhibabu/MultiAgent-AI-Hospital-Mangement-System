"""OCR package — provider interface, adapters, factory."""

from app.ai.ocr.base import OCRExtractionResult, OCRProvider, Provenance
from app.ai.ocr.factory import OCRProviderFactory, get_ocr_provider

__all__ = [
    "OCRProvider",
    "OCRExtractionResult",
    "Provenance",
    "OCRProviderFactory",
    "get_ocr_provider",
]
