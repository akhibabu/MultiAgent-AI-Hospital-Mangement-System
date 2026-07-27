"""Extract embedded selectable text from digital PDFs (not OCR)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from app.core.logging import get_logger

logger = get_logger("hospital_ai.document.pdf")


@dataclass
class PDFExtractResult:
    text: str
    page_count: int
    library_used: str
    fallback_used: bool
    logs: List[str] = field(default_factory=list)
    encrypted: bool = False
    corrupted: bool = False
    error: str | None = None


class PDFTextExtractor:
    """
    Primary: PyMuPDF (fitz)
    Fallback: pdfplumber

    Never returns PDF object streams / binary as text.
    """

    def extract(self, file_bytes: bytes) -> PDFExtractResult:
        logs: List[str] = []

        if not file_bytes or len(file_bytes) < 8:
            return PDFExtractResult(
                text="",
                page_count=0,
                library_used="none",
                fallback_used=False,
                logs=["File too small to be a valid PDF"],
                corrupted=True,
                error="Corrupted or empty PDF",
            )

        if b"/Encrypt" in file_bytes[:12000]:
            logs.append("PDF appears encrypted")
            return PDFExtractResult(
                text="",
                page_count=0,
                library_used="none",
                fallback_used=False,
                logs=logs,
                encrypted=True,
                error="Encrypted PDFs are not supported. Upload an unlocked PDF.",
            )

        text, pages, lib = self._extract_pymupdf(file_bytes, logs)
        fallback = False
        if not (text or "").strip():
            logs.append("PyMuPDF returned empty text — trying pdfplumber")
            alt, alt_pages, alt_lib = self._extract_pdfplumber(file_bytes, logs)
            if (alt or "").strip():
                text, pages, lib = alt, alt_pages, alt_lib
                fallback = True
            elif lib == "none":
                text, pages, lib = alt, alt_pages, alt_lib
                fallback = True

        return PDFExtractResult(
            text=text or "",
            page_count=max(1, pages) if pages else 0,
            library_used=lib,
            fallback_used=fallback,
            logs=logs,
        )

    def render_pages_as_png(
        self, file_bytes: bytes, *, max_pages: int = 30, dpi: int = 200
    ) -> Tuple[List[bytes], List[str]]:
        """Rasterize PDF pages for OCR (PyMuPDF primary; pdf2image optional)."""
        logs: List[str] = []
        try:
            return self._render_pymupdf(file_bytes, max_pages=max_pages, dpi=dpi, logs=logs)
        except Exception as primary_exc:  # noqa: BLE001
            logs.append(f"PyMuPDF rasterize failed: {primary_exc}")
            try:
                return self._render_pdf2image(
                    file_bytes, max_pages=max_pages, dpi=dpi, logs=logs
                )
            except Exception as fallback_exc:  # noqa: BLE001
                logs.append(f"pdf2image rasterize failed: {fallback_exc}")
                raise RuntimeError(
                    "Unable to convert PDF pages to images for OCR. "
                    "Install pymupdf, or pdf2image with Poppler."
                ) from fallback_exc

    def _render_pymupdf(
        self,
        file_bytes: bytes,
        *,
        max_pages: int,
        dpi: int,
        logs: List[str],
    ) -> Tuple[List[bytes], List[str]]:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError(
                "PyMuPDF (pymupdf) is required to OCR scanned PDFs."
            ) from exc

        images: List[bytes] = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        try:
            zoom = dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            count = min(doc.page_count, max_pages)
            logs.append(f"Rasterizing {count} PDF page(s) at {dpi} DPI via PyMuPDF")
            for i in range(count):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                images.append(pix.tobytes("png"))
        finally:
            doc.close()
        return images, logs

    def _render_pdf2image(
        self,
        file_bytes: bytes,
        *,
        max_pages: int,
        dpi: int,
        logs: List[str],
    ) -> Tuple[List[bytes], List[str]]:
        import io

        from pdf2image import convert_from_bytes

        pages = convert_from_bytes(
            file_bytes, dpi=dpi, first_page=1, last_page=max_pages
        )
        logs.append(f"Rasterizing {len(pages)} PDF page(s) via pdf2image")
        images: List[bytes] = []
        for page in pages:
            buf = io.BytesIO()
            page.save(buf, format="PNG")
            images.append(buf.getvalue())
        return images, logs

    def _extract_pymupdf(
        self, file_bytes: bytes, logs: List[str]
    ) -> Tuple[str, int, str]:
        try:
            import fitz
        except ImportError:
            logs.append("PyMuPDF not installed")
            return "", 0, "none"

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            parts: List[str] = []
            try:
                if getattr(doc, "is_encrypted", False):
                    logs.append("PyMuPDF reports encrypted document")
                    return "", 0, "none"
                for page in doc:
                    parts.append(page.get_text("text") or "")
                text = "\n\n".join(parts)
                logs.append(
                    f"PyMuPDF extracted {len(text)} chars from {doc.page_count} page(s)"
                )
                return text, doc.page_count, "pymupdf"
            finally:
                doc.close()
        except Exception as exc:  # noqa: BLE001
            logs.append(f"PyMuPDF failed: {exc}")
            logger.warning("PyMuPDF extract failed: %s", exc)
            return "", 0, "none"

    def _extract_pdfplumber(
        self, file_bytes: bytes, logs: List[str]
    ) -> Tuple[str, int, str]:
        try:
            import io

            import pdfplumber
        except ImportError:
            logs.append("pdfplumber not installed")
            return "", 0, "none"

        try:
            parts: List[str] = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    parts.append(page.extract_text() or "")
                text = "\n\n".join(parts)
                logs.append(
                    f"pdfplumber extracted {len(text)} chars from {len(pdf.pages)} page(s)"
                )
                return text, len(pdf.pages), "pdfplumber"
        except Exception as exc:  # noqa: BLE001
            logs.append(f"pdfplumber failed: {exc}")
            logger.warning("pdfplumber extract failed: %s", exc)
            return "", 0, "none"
