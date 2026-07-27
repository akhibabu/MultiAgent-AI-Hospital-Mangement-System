"""OCR Provider Factory — pluggable Strategy selection."""

from __future__ import annotations

from typing import Dict, Type

from app.ai.ocr.adapters import (
    AzureOCRAdapter,
    GoogleVisionOCRAdapter,
    PaddleOCRAdapter,
    StubOCRAdapter,
    TesseractOCRAdapter,
)
from app.ai.ocr.base import OCRProvider
from app.core.logging import get_logger

logger = get_logger("hospital_ai.ocr.factory")


class OCRProviderFactory:
    """
    Factory Pattern for OCR providers.

    Register new adapters without modifying callers.
    """

    _registry: Dict[str, Type[OCRProvider]] = {
        "stub": StubOCRAdapter,
        "tesseract": TesseractOCRAdapter,
        "paddle": PaddleOCRAdapter,
        "paddleocr": PaddleOCRAdapter,
        "google_vision": GoogleVisionOCRAdapter,
        "google": GoogleVisionOCRAdapter,
        "azure": AzureOCRAdapter,
    }

    @classmethod
    def register(cls, name: str, provider_cls: Type[OCRProvider]) -> None:
        cls._registry[name.strip().lower()] = provider_cls
        logger.info("Registered OCR provider '%s'", name)

    @classmethod
    def create(cls, name: str | None = None) -> OCRProvider:
        from app.config import get_settings

        settings = get_settings()
        key = (name or settings.ocr_provider or "stub").strip().lower()
        provider_cls = cls._registry.get(key)
        if not provider_cls:
            raise ValueError(
                f"Unknown OCR_PROVIDER '{key}'. "
                f"Available: {', '.join(sorted(set(cls._registry)))}"
            )

        if provider_cls is GoogleVisionOCRAdapter:
            return GoogleVisionOCRAdapter(settings.google_vision_api_key)
        if provider_cls is AzureOCRAdapter:
            return AzureOCRAdapter(settings.azure_ocr_endpoint, settings.azure_ocr_key)
        return provider_cls()


def get_ocr_provider(name: str | None = None) -> OCRProvider:
    """Backward-compatible factory entrypoint."""
    return OCRProviderFactory.create(name)
