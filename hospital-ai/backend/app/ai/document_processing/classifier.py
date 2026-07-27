"""Classify uploaded documents for the document-processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClassificationResult:
    file_kind: str  # pdf | image | unknown
    mime_hint: str
    extension: str


class DocumentClassifier:
    """
    Detect file kind from MIME, filename, and magic bytes.

    Fine-grained digital_pdf vs scanned_pdf is decided later after
    embedded-text probing — this class only classifies the container.
    """

    IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")

    def classify(
        self,
        *,
        file_bytes: bytes,
        content_type: str,
        file_name: str,
    ) -> ClassificationResult:
        name = (file_name or "").lower().strip()
        mime = (content_type or "").lower().strip()
        ext = ""
        if "." in name:
            ext = "." + name.rsplit(".", 1)[-1]

        if (
            "pdf" in mime
            or name.endswith(".pdf")
            or file_bytes[:5] == b"%PDF-"
        ):
            return ClassificationResult(
                file_kind="pdf",
                mime_hint=mime or "application/pdf",
                extension=".pdf",
            )

        if mime.startswith("image/") or name.endswith(self.IMAGE_EXTENSIONS):
            return ClassificationResult(
                file_kind="image",
                mime_hint=mime or f"image/{ext.lstrip('.') or 'jpeg'}",
                extension=ext or ".jpg",
            )

        # Magic-byte fallbacks for mislabeled uploads
        if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return ClassificationResult("image", "image/png", ".png")
        if file_bytes[:3] == b"\xff\xd8\xff":
            return ClassificationResult("image", "image/jpeg", ".jpg")

        return ClassificationResult(
            file_kind="unknown",
            mime_hint=mime or "application/octet-stream",
            extension=ext,
        )

    def display_label(self, document_type: str) -> str:
        return {
            "digital_pdf": "Digital PDF",
            "scanned_pdf": "Scanned PDF",
            "image": "Image",
            "unknown": "Unknown",
        }.get(document_type, document_type or "Document")
