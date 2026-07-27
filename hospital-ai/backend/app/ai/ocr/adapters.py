"""OCR provider adapters — Strategy implementations."""

from __future__ import annotations

import re
from typing import List, Optional

from app.ai.ocr.base import OCRImageMeta, OCRProvider, OCRTable


class StubOCRAdapter(OCRProvider):
    """
    Default provider — delegates to DocumentProcessingService.

    Digital PDFs → embedded text (PyMuPDF / pdfplumber).
    Scanned PDFs / images → Tesseract OCR.
    Never returns raw PDF object streams as text.
    """

    name = "stub"

    def __init__(self) -> None:
        self._last_confidence = 0.0
        self._last_result = None
        from app.ai.document_processing import DocumentProcessorFactory

        self._documents = DocumentProcessorFactory.create()

    def _process(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ):
        result = self._documents.process(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        self._last_result = result
        self._last_confidence = float(result.confidence or 0.0)
        return result

    def extract_text(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> str:
        result = self._process(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        return result.clean_text or result.raw_extracted_text or ""

    def extract_tables(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> List[OCRTable]:
        result = self._last_result or self._process(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        tables_out: List[OCRTable] = []
        for t in result.tables or []:
            if isinstance(t, dict):
                tables_out.append(
                    OCRTable(
                        page_number=int(t.get("page_number") or 1),
                        rows=t.get("rows") or [],
                        confidence=float(t.get("confidence") or self._last_confidence),
                    )
                )
        if tables_out:
            return tables_out
        # Heuristic fallback from readable text
        text = result.readable_text or ""
        rows: List[List[str]] = []
        for line in text.splitlines():
            if "|" in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) >= 2:
                    rows.append(cells)
            elif "\t" in line:
                cells = [c.strip() for c in line.split("\t") if c.strip()]
                if len(cells) >= 2:
                    rows.append(cells)
        if not rows:
            return []
        return [
            OCRTable(
                page_number=1,
                rows=rows[:50],
                confidence=self._last_confidence,
            )
        ]

    def extract_images(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> List[OCRImageMeta]:
        result = self._last_result or self._process(
            file_bytes=file_bytes,
            content_type=content_type,
            file_name=file_name,
        )
        metas = result.images_meta or []
        if metas:
            return [
                OCRImageMeta(
                    page_number=int(m.get("page_number") or i + 1),
                    width=m.get("width"),
                    height=m.get("height"),
                    format=str(m.get("format") or "unknown"),
                    byte_size=int(m.get("byte_size") or 0),
                )
                for i, m in enumerate(metas)
                if isinstance(m, dict)
            ]
        pages = max(1, int(result.page_count or 1))
        fmt = "pdf" if "pdf" in (content_type or "").lower() else "image"
        return [
            OCRImageMeta(
                page_number=i + 1,
                width=None,
                height=None,
                format=fmt,
                byte_size=0,
            )
            for i in range(pages)
        ]

    def detect_language(self, *, text: str) -> str:
        if self._last_result and self._last_result.language:
            return self._last_result.language
        sample = (text or "").lower()
        if not sample.strip():
            return "unknown"
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        ascii_ratio = sum(1 for c in sample if ord(c) < 128) / max(1, len(sample))
        return "en" if ascii_ratio > 0.85 else "unknown"

    def get_confidence(self) -> float:
        return float(self._last_confidence)


class TesseractOCRAdapter(OCRProvider):
    """Tesseract adapter — uses pytesseract when installed; otherwise fails clearly."""

    name = "tesseract"

    def __init__(self) -> None:
        self._last_confidence = 0.0

    def _engine(self):
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
            import io

            return pytesseract, Image, io
        except ImportError as exc:
            raise RuntimeError(
                "Tesseract adapter requires pytesseract and Pillow. "
                "Install them or set OCR_PROVIDER=stub."
            ) from exc

    def extract_text(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> str:
        pytesseract, Image, io = self._engine()
        if "pdf" in (content_type or "").lower():
            raise RuntimeError(
                "Tesseract adapter does not rasterize PDFs in this build. "
                "Convert to PNG/JPEG or use OCR_PROVIDER=stub."
            )
        image = Image.open(io.BytesIO(file_bytes))
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        confs = [int(c) for c in data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
        self._last_confidence = (sum(confs) / len(confs) / 100.0) if confs else 0.5
        return pytesseract.image_to_string(image) or ""

    def extract_tables(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> List[OCRTable]:
        text = self.extract_text(
            file_bytes=file_bytes, content_type=content_type, file_name=file_name
        )
        rows = [
            [c.strip() for c in line.split() if c.strip()]
            for line in text.splitlines()
            if len(line.split()) >= 3
        ]
        if not rows:
            return []
        return [OCRTable(page_number=1, rows=rows[:40], confidence=self._last_confidence)]

    def extract_images(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> List[OCRImageMeta]:
        try:
            _, Image, io = self._engine()
            image = Image.open(io.BytesIO(file_bytes))
            return [
                OCRImageMeta(
                    page_number=1,
                    width=image.width,
                    height=image.height,
                    format=image.format,
                    byte_size=len(file_bytes),
                )
            ]
        except Exception:  # noqa: BLE001
            return [
                OCRImageMeta(
                    page_number=1,
                    width=None,
                    height=None,
                    format=None,
                    byte_size=len(file_bytes),
                )
            ]

    def detect_language(self, *, text: str) -> str:
        return "en" if text and text.strip() else "unknown"

    def get_confidence(self) -> float:
        return float(self._last_confidence)


class PaddleOCRAdapter(OCRProvider):
    name = "paddle"

    def __init__(self) -> None:
        self._last_confidence = 0.0

    def extract_text(self, *, file_bytes: bytes, content_type: str, file_name: str) -> str:
        raise RuntimeError(
            "PaddleOCR adapter is registered but not connected. "
            "Install paddleocr and wire the engine, or set OCR_PROVIDER=stub."
        )

    def extract_tables(self, *, file_bytes: bytes, content_type: str, file_name: str) -> List[OCRTable]:
        raise RuntimeError("PaddleOCR adapter not connected")

    def extract_images(self, *, file_bytes: bytes, content_type: str, file_name: str) -> List[OCRImageMeta]:
        raise RuntimeError("PaddleOCR adapter not connected")

    def detect_language(self, *, text: str) -> str:
        return "unknown"

    def get_confidence(self) -> float:
        return 0.0


class GoogleVisionOCRAdapter(OCRProvider):
    name = "google_vision"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key
        self._last_confidence = 0.0

    def extract_text(self, *, file_bytes: bytes, content_type: str, file_name: str) -> str:
        if not self.api_key:
            raise RuntimeError("GOOGLE_VISION_API_KEY is not configured")
        raise RuntimeError(
            "Google Vision adapter is registered but not connected. "
            "Wire Vision REST API or set OCR_PROVIDER=stub."
        )

    def extract_tables(self, *, file_bytes: bytes, content_type: str, file_name: str) -> List[OCRTable]:
        raise RuntimeError("Google Vision adapter not connected")

    def extract_images(self, *, file_bytes: bytes, content_type: str, file_name: str) -> List[OCRImageMeta]:
        raise RuntimeError("Google Vision adapter not connected")

    def detect_language(self, *, text: str) -> str:
        return "unknown"

    def get_confidence(self) -> float:
        return 0.0


class AzureOCRAdapter(OCRProvider):
    name = "azure"

    def __init__(self, endpoint: str = "", api_key: str = "") -> None:
        self.endpoint = (endpoint or "").rstrip("/")
        self.api_key = api_key
        self._last_confidence = 0.0

    def extract_text(self, *, file_bytes: bytes, content_type: str, file_name: str) -> str:
        if not self.endpoint or not self.api_key:
            raise RuntimeError("AZURE_OCR_ENDPOINT / AZURE_OCR_KEY not configured")
        raise RuntimeError(
            "Azure OCR adapter is registered but not connected. "
            "Wire Read API or set OCR_PROVIDER=stub."
        )

    def extract_tables(self, *, file_bytes: bytes, content_type: str, file_name: str) -> List[OCRTable]:
        raise RuntimeError("Azure OCR adapter not connected")

    def extract_images(self, *, file_bytes: bytes, content_type: str, file_name: str) -> List[OCRImageMeta]:
        raise RuntimeError("Azure OCR adapter not connected")

    def detect_language(self, *, text: str) -> str:
        return "unknown"

    def get_confidence(self) -> float:
        return 0.0
