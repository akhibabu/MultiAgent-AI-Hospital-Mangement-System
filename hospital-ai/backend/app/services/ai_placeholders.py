"""Placeholder AI / RAG services — interfaces only, no implementation."""

from typing import Any, Optional, Protocol
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger("hospital_ai.ai_placeholders")


class OCRService(Protocol):
    """Future OCR pipeline for medical documents."""

    def extract_text(self, *, document_id: UUID, storage_path: str) -> str: ...

    def enqueue(self, *, document_id: UUID, storage_path: str) -> str: ...


class EmbeddingService(Protocol):
    """Future embedding generation for RAG indexing."""

    def embed_text(self, text: str) -> list[float]: ...

    def embed_document(self, *, document_id: UUID) -> str: ...


class VectorIndexService(Protocol):
    """Future vector store upsert / search."""

    def upsert(self, *, embedding_id: str, vector: list[float], metadata: dict[str, Any]) -> None: ...

    def search(self, *, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]: ...


class MedicalSummaryService(Protocol):
    """Future clinical summarization over a medical record."""

    def summarize_record(self, *, record_id: UUID) -> str: ...


class PlaceholderOCRService:
    """Stub OCRService — dependency injection point only."""

    def extract_text(self, *, document_id: UUID, storage_path: str) -> str:
        logger.info(
            "[placeholder] OCRService.extract_text document=%s path=%s",
            document_id,
            storage_path,
        )
        return ""

    def enqueue(self, *, document_id: UUID, storage_path: str) -> str:
        logger.info(
            "[placeholder] OCRService.enqueue document=%s path=%s",
            document_id,
            storage_path,
        )
        return "pending"


class PlaceholderEmbeddingService:
    """Stub EmbeddingService — dependency injection point only."""

    def embed_text(self, text: str) -> list[float]:
        logger.info("[placeholder] EmbeddingService.embed_text chars=%s", len(text))
        return []

    def embed_document(self, *, document_id: UUID) -> str:
        logger.info("[placeholder] EmbeddingService.embed_document %s", document_id)
        return ""


class PlaceholderVectorIndexService:
    """Stub VectorIndexService — dependency injection point only."""

    def upsert(
        self,
        *,
        embedding_id: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> None:
        logger.info(
            "[placeholder] VectorIndexService.upsert id=%s dims=%s meta=%s",
            embedding_id,
            len(vector),
            metadata,
        )

    def search(
        self, *, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        logger.info(
            "[placeholder] VectorIndexService.search dims=%s top_k=%s",
            len(query_vector),
            top_k,
        )
        return []


class PlaceholderMedicalSummaryService:
    """Stub MedicalSummaryService — dependency injection point only."""

    def summarize_record(self, *, record_id: UUID) -> str:
        logger.info("[placeholder] MedicalSummaryService.summarize_record %s", record_id)
        return ""


# Default injectable singletons (swap with real implementations later)
ocr_service: OCRService = PlaceholderOCRService()
embedding_service: EmbeddingService = PlaceholderEmbeddingService()
vector_index_service: VectorIndexService = PlaceholderVectorIndexService()
medical_summary_service: MedicalSummaryService = PlaceholderMedicalSummaryService()


def get_ocr_service() -> OCRService:
    return ocr_service


def get_embedding_service() -> EmbeddingService:
    return embedding_service


def get_vector_index_service() -> VectorIndexService:
    return vector_index_service


def get_medical_summary_service() -> MedicalSummaryService:
    return medical_summary_service
