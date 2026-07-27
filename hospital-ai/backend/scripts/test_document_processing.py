"""
Smoke test: DocumentProcessingService on digital PDF, scanned PDF, JPG, PNG.

Usage (from hospital-ai/backend):
  .venv\\Scripts\\python.exe scripts/test_document_processing.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import fitz
from PIL import Image, ImageDraw, ImageFont

from app.ai.document_processing import DocumentProcessorFactory
from app.ai.document_processing.ocr_engines import (
    OCREngine,
    OCRProviderFactory,
    EngineOCRResult,
)


REPORT_LINES = [
    "Apollo Hospital",
    "Patient Name: John Doe",
    "Age: 58",
    "Gender: Male",
    "Diagnosis: Pneumonia",
    "Medication: Azithromycin",
    "Blood Pressure: 145/92",
    "Recommendation: Follow-up after one week.",
]


class FakeOCREngine(OCREngine):
    """Deterministic OCR for environments without Paddle/Tesseract."""

    name = "fake_ocr"

    def available(self) -> bool:
        return True

    def recognize(self, image_bytes: bytes, *, lang: str = "en") -> EngineOCRResult:
        return EngineOCRResult(
            text="\n".join(REPORT_LINES),
            confidence=0.91,
            language="en",
            provider=self.name,
            logs=["FakeOCREngine recognized sample medical report"],
        )


def make_digital_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in REPORT_LINES:
        page.insert_text((72, y), line, fontsize=12)
        y += 18
    data = doc.tobytes()
    doc.close()
    return data


def make_report_image(fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (900, 700), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    y = 40
    for line in REPORT_LINES:
        draw.text((40, y), line, fill=(0, 0, 0), font=font)
        y += 48
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def make_scanned_pdf() -> bytes:
    """Image-only PDF (no selectable text layer)."""
    png = make_report_image("PNG")
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=png)
    data = doc.tobytes()
    doc.close()
    return data


def run_case(label: str, file_bytes: bytes, content_type: str, file_name: str) -> bool:
    svc = DocumentProcessorFactory.create()
    result = svc.process(
        file_bytes=file_bytes,
        content_type=content_type,
        file_name=file_name,
    )
    text = result.clean_text or ""
    ok = (
        result.status == "Completed"
        and "Apollo" in text
        and "John Doe" in text
        and not text.strip().startswith("%PDF")
        and "endobj" not in text
        and "/FlateDecode" not in text
    )
    print("=" * 60)
    print(f"CASE: {label}")
    print(f"  document_type     = {result.document_type}")
    print(f"  processing_method = {result.processing_method}")
    print(f"  ocr_provider      = {result.ocr_provider}")
    print(f"  library_used      = {result.library_used}")
    print(f"  fallback_used     = {result.fallback_used}")
    print(f"  confidence        = {result.confidence:.2f}")
    print(f"  status            = {result.status}")
    print(f"  chars/words       = {result.character_count}/{result.word_count}")
    print(f"  pages             = {result.page_count}")
    print(f"  warnings          = {result.warnings}")
    print(f"  errors            = {result.errors}")
    print("  clean_text preview:")
    print("  " + text[:400].replace("\n", "\n  "))
    print(f"  PASS={ok}")
    return ok


def main() -> int:
    # Prefer real OCR; if none available, register FakeOCR so pipeline still tested.
    from app.ai.document_processing.ocr_engines import (
        PaddleOCREngine,
        TesseractOCREngine,
    )

    has_real = PaddleOCREngine().available() or TesseractOCREngine().available()
    if not has_real:
        print(
            "NOTE: PaddleOCR/Tesseract unavailable — using FakeOCREngine "
            "to verify scanned/image pipeline wiring."
        )
        OCRProviderFactory.register("fake_ocr", FakeOCREngine)
        # Monkey-patch create_with_fallback to prefer fake when real engines missing
        original = OCRProviderFactory.create_with_fallback

        def _fallback():
            try:
                return original()
            except RuntimeError:
                return FakeOCREngine(), ["Using FakeOCREngine for smoke test"]

        OCRProviderFactory.create_with_fallback = staticmethod(_fallback)  # type: ignore

    results = [
        run_case(
            "1. Digital PDF",
            make_digital_pdf(),
            "application/pdf",
            "digital_report.pdf",
        ),
        run_case(
            "2. Scanned PDF",
            make_scanned_pdf(),
            "application/pdf",
            "scanned_report.pdf",
        ),
        run_case(
            "3. JPG report",
            make_report_image("JPEG"),
            "image/jpeg",
            "report.jpg",
        ),
        run_case(
            "4. PNG report",
            make_report_image("PNG"),
            "image/png",
            "report.png",
        ),
    ]
    passed = sum(1 for r in results if r)
    print("=" * 60)
    print(f"RESULT: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
