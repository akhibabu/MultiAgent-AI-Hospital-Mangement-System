"""Backward-compatible re-exports for legacy imports."""

from app.ai.ocr.base import OCRExtractionResult as OCRResult
from app.ai.ocr.base import OCRProvider
from app.ai.ocr.factory import OCRProviderFactory, get_ocr_provider

__all__ = ["OCRProvider", "OCRResult", "OCRProviderFactory", "get_ocr_provider"]
