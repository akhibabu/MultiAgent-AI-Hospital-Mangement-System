"""
OCR engine Strategy + Factory.

Primary: PaddleOCR
Fallback: Tesseract
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

from app.core.logging import get_logger

logger = get_logger("hospital_ai.document.ocr_engines")


@dataclass
class EngineOCRResult:
    text: str
    confidence: float
    language: str
    provider: str
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class OCREngine(ABC):
    """Strategy interface for an OCR engine."""

    name: str

    @abstractmethod
    def available(self) -> bool:
        """True when the engine can run in this environment."""

    @abstractmethod
    def recognize(self, image_bytes: bytes, *, lang: str = "en") -> EngineOCRResult:
        """OCR a single image (PNG/JPEG bytes)."""


class PaddleOCREngine(OCREngine):
    """Primary OCR engine — PaddleOCR."""

    name = "paddleocr"

    def __init__(self) -> None:
        self._ocr = None
        self._init_error: Optional[str] = None

    def available(self) -> bool:
        try:
            self._ensure()
            return self._ocr is not None
        except Exception:  # noqa: BLE001
            return False

    def _ensure(self):
        if self._ocr is not None:
            return self._ocr
        if self._init_error:
            raise RuntimeError(self._init_error)
        try:
            from paddleocr import PaddleOCR  # type: ignore
        except ImportError as exc:
            self._init_error = (
                "PaddleOCR is not installed. "
                "Install with: pip install paddleocr paddlepaddle"
            )
            raise RuntimeError(self._init_error) from exc

        try:
            # use_angle_cls helps rotated hospital scans; show_log noise off
            try:
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    show_log=False,
                    use_gpu=False,
                )
            except TypeError:
                # Newer paddleocr versions changed kwargs
                self._ocr = PaddleOCR(lang="en")
            return self._ocr
        except Exception as exc:  # noqa: BLE001
            self._init_error = f"PaddleOCR failed to initialize: {exc}"
            logger.warning(self._init_error)
            raise RuntimeError(self._init_error) from exc

    def recognize(self, image_bytes: bytes, *, lang: str = "en") -> EngineOCRResult:
        import io
        import tempfile
        from pathlib import Path

        from PIL import Image

        logs: List[str] = []
        errors: List[str] = []
        ocr = self._ensure()

        image = Image.open(io.BytesIO(image_bytes))
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        # PaddleOCR accepts file path most reliably across versions
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            path = Path(tmp.name)
            image.save(path, format="PNG")

        try:
            try:
                raw = ocr.ocr(str(path), cls=True)
            except TypeError:
                raw = ocr.ocr(str(path))
        finally:
            try:
                path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass

        lines: List[str] = []
        scores: List[float] = []

        # paddleocr returns list[list[[box], (text, score)]] or dict in newer APIs
        pages = raw if isinstance(raw, list) else [raw]
        for page in pages:
            if page is None:
                continue
            if isinstance(page, dict):
                # PP-Structure / new API shape
                rec_texts = page.get("rec_texts") or page.get("texts") or []
                rec_scores = page.get("rec_scores") or page.get("scores") or []
                for t, s in zip(rec_texts, rec_scores or [0.9] * len(rec_texts)):
                    if t:
                        lines.append(str(t))
                        try:
                            scores.append(float(s))
                        except (TypeError, ValueError):
                            scores.append(0.85)
                continue
            for item in page:
                if not item:
                    continue
                try:
                    _box, pair = item
                    text, score = pair[0], float(pair[1])
                except (ValueError, TypeError, IndexError):
                    continue
                if text:
                    lines.append(str(text))
                    scores.append(score)

        text = "\n".join(lines)
        confidence = sum(scores) / len(scores) if scores else (0.55 if text else 0.0)
        logs.append(
            f"PaddleOCR produced {len(text)} chars "
            f"({len(lines)} lines, confidence≈{confidence:.2f})"
        )
        return EngineOCRResult(
            text=text,
            confidence=float(confidence),
            language="en" if lang.startswith("en") else lang,
            provider=self.name,
            logs=logs,
            errors=errors,
        )


class TesseractOCREngine(OCREngine):
    """Fallback OCR engine — Tesseract."""

    name = "tesseract"

    def available(self) -> bool:
        try:
            import pytesseract
            from PIL import Image  # noqa: F401

            # Probe binary
            try:
                pytesseract.get_tesseract_version()
            except Exception:  # noqa: BLE001
                return False
            return True
        except ImportError:
            return False

    def recognize(self, image_bytes: bytes, *, lang: str = "en") -> EngineOCRResult:
        import io

        import pytesseract
        from PIL import Image

        logs: List[str] = []
        errors: List[str] = []
        tess_lang = "eng" if lang.startswith("en") else lang

        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            data = pytesseract.image_to_data(
                image, lang=tess_lang, output_type=pytesseract.Output.DICT
            )
            confs = [
                int(c)
                for c in data.get("conf", [])
                if str(c).lstrip("-").isdigit() and int(c) >= 0
            ]
            confidence = (sum(confs) / len(confs) / 100.0) if confs else 0.5
            text = pytesseract.image_to_string(image, lang=tess_lang) or ""
            logs.append(
                f"Tesseract OCR produced {len(text)} chars "
                f"(confidence≈{confidence:.2f})"
            )
            return EngineOCRResult(
                text=text,
                confidence=float(confidence),
                language="en" if tess_lang.startswith("eng") else tess_lang,
                provider=self.name,
                logs=logs,
                errors=errors,
            )
        except pytesseract.TesseractNotFoundError as exc:
            msg = (
                "Tesseract binary not found on PATH. "
                "Install Tesseract-OCR or ensure PaddleOCR is available."
            )
            errors.append(msg)
            raise RuntimeError(msg) from exc


class OCRProviderFactory:
    """
    Factory — Strategy Pattern.

    Prefers PaddleOCR; automatically falls back to Tesseract.
    """

    _registry: Dict[str, Type[OCREngine]] = {
        "paddleocr": PaddleOCREngine,
        "tesseract": TesseractOCREngine,
    }

    @classmethod
    def register(cls, name: str, engine_cls: Type[OCREngine]) -> None:
        cls._registry[name] = engine_cls

    @classmethod
    def create(cls, preferred: Optional[str] = None) -> OCREngine:
        order: List[str]
        if preferred and preferred in cls._registry:
            order = [preferred] + [n for n in ("paddleocr", "tesseract") if n != preferred]
        else:
            order = ["paddleocr", "tesseract"]

        errors: List[str] = []
        for name in order:
            engine_cls = cls._registry[name]
            engine = engine_cls()
            try:
                if engine.available():
                    logger.info("OCR engine selected: %s", name)
                    return engine
                errors.append(f"{name}: not available")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {exc}")

        raise RuntimeError(
            "No OCR engine available. Install PaddleOCR "
            "(pip install paddlepaddle paddleocr) or Tesseract "
            "(pytesseract + system binary). "
            f"Details: {'; '.join(errors)}"
        )

    @classmethod
    def create_with_fallback(cls) -> tuple[OCREngine, List[str]]:
        """
        Return (primary_or_fallback_engine, logs).
        Tries Paddle first; on failure returns Tesseract.
        """
        logs: List[str] = []
        paddle = PaddleOCREngine()
        try:
            if paddle.available():
                logs.append("Using PaddleOCR as primary OCR engine")
                return paddle, logs
            logs.append("PaddleOCR not available — falling back to Tesseract")
        except Exception as exc:  # noqa: BLE001
            logs.append(f"PaddleOCR unavailable ({exc}) — falling back to Tesseract")

        tess = TesseractOCREngine()
        if tess.available():
            logs.append("Using Tesseract OCR as fallback engine")
            return tess, logs

        raise RuntimeError(
            "Neither PaddleOCR nor Tesseract is available. "
            "Install paddleocr/paddlepaddle, or install Tesseract-OCR."
        )
