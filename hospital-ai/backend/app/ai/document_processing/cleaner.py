"""Clean extracted document text into human-readable medical report paragraphs."""

from __future__ import annotations

import re


_PDF_GARBAGE = (
    "%PDF-",
    " endobj",
    "endobj\n",
    "/FlateDecode",
    "/FontDescriptor",
    "/Type /Page",
    "xref\n",
    "trailer",
    "startxref",
    "stream\r",
    "stream\n",
)

# Common OCR artifact characters to strip when isolated
_OCR_NOISE = re.compile(r"[|_=~`^]{3,}")
_BROKEN_WORD = re.compile(r"(\w)-\n(\w)")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_NON_PRINTABLE = re.compile(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\u024F\u0900-\u097F]")


class DocumentCleaner:
    """Normalize and sanitize extracted text for clinical staff + NER."""

    def looks_like_pdf_binary(self, text: str) -> bool:
        if not text or not text.strip():
            return False
        sample = text[:4000]
        hits = sum(1 for marker in _PDF_GARBAGE if marker in sample)
        printable = sum(1 for ch in sample if ch.isprintable() or ch in "\n\r\t")
        ratio = printable / max(1, len(sample))
        return hits >= 2 or ratio < 0.55

    def clean(self, text: str) -> str:
        if not text:
            return ""

        if self.looks_like_pdf_binary(text):
            return ""

        lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append("")
                continue
            if self._is_pdf_syntax_line(stripped):
                continue
            lines.append(stripped)

        text = "\n".join(lines)
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Merge hyphenated line-breaks (OCR / PDF wrap artifacts)
        text = _BROKEN_WORD.sub(r"\1\2", text)

        # Remove long OCR noise runs
        text = _OCR_NOISE.sub(" ", text)
        text = _NON_PRINTABLE.sub("", text)

        cleaned_lines: list[str] = []
        for line in text.split("\n"):
            line = _MULTI_SPACE.sub(" ", line).strip()
            if not line:
                cleaned_lines.append("")
                continue
            # Drop lines that are mostly non-letter noise
            alnum = len(re.findall(r"[A-Za-z0-9\u0900-\u097F]", line))
            if alnum < max(1, len(line) // 5) and len(line) > 12:
                continue
            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)
        text = _MULTI_NEWLINE.sub("\n\n", text).strip()

        # Soft paragraph formatting for label: value medical layouts
        text = self._format_medical_labels(text)
        return text.strip()

    def _is_pdf_syntax_line(self, stripped: str) -> bool:
        lower = stripped.lower()
        if stripped.startswith("%PDF"):
            return True
        if re.match(r"^\d+\s+\d+\s+obj\b", stripped):
            return True
        if stripped in {"stream", "endstream", "endobj", "xref", "trailer"}:
            return True
        if stripped.startswith("<<") or stripped.startswith(">>"):
            return True
        if "/FlateDecode" in stripped or "/FontDescriptor" in stripped:
            return True
        if re.match(r"^/\w+", stripped) and len(stripped.split()) <= 4:
            return True
        if lower.startswith("startxref"):
            return True
        return False

    def _format_medical_labels(self, text: str) -> str:
        """
        Promote 'Label: value' onto clearer lines when jammed together.
        Conservative — does not invent content.
        """
        labels = (
            "Patient Name",
            "Age",
            "Gender",
            "Sex",
            "Diagnosis",
            "Medication",
            "Medications",
            "Blood Pressure",
            "Recommendation",
            "Chief Complaint",
            "History",
            "Allergies",
            "Doctor",
            "Date",
        )
        out = text
        for label in labels:
            # Ensure label starts on its own line when preceded by other text
            out = re.sub(
                rf"(?<!\n)({re.escape(label)}\s*:)",
                r"\n\1",
                out,
                flags=re.IGNORECASE,
            )
        return _MULTI_NEWLINE.sub("\n\n", out).strip()
