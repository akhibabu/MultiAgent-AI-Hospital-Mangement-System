"""Bridge medical document uploads → Intake Agent (sole OCR/NER entrypoint)."""

from __future__ import annotations

import threading
from uuid import UUID

from app.ai.intake.agent import intake_agent
from app.core.logging import get_logger

logger = get_logger("hospital_ai.intake.bridge")


class IntakeOCRBridge:
    """
    Replaces placeholder OCR enqueue.

    Only the Intake Agent may read raw documents and run OCR/entity extraction.
    Upload remains non-blocking; processing runs in a background thread.
    """

    def extract_text(self, *, document_id: UUID, storage_path: str) -> str:
        result = intake_agent.process_document(document_id=document_id)
        return (result.get("ocr") or {}).get("text_preview") or ""

    def enqueue(self, *, document_id: UUID, storage_path: str) -> str:
        logger.info(
            "Enqueueing Intake Agent for document=%s path=%s",
            document_id,
            storage_path,
        )

        def _run() -> None:
            try:
                intake_agent.process_document(document_id=document_id)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Background Intake failed for document=%s", document_id
                )

        threading.Thread(
            target=_run,
            name=f"intake-{document_id}",
            daemon=True,
        ).start()
        return "queued"


intake_ocr_bridge = IntakeOCRBridge()
