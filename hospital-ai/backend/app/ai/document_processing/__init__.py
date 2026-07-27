"""Intelligent document processing for Intake Agent Stage 3."""

from app.ai.document_processing.classifier import DocumentClassifier
from app.ai.document_processing.cleaner import DocumentCleaner
from app.ai.document_processing.ocr_engines import OCRProviderFactory
from app.ai.document_processing.ocr_processor import OCRProcessor
from app.ai.document_processing.pdf_extractor import PDFTextExtractor
from app.ai.document_processing.quality import QualityChecker
from app.ai.document_processing.scanned_processor import ScannedDocumentProcessor
from app.ai.document_processing.service import (
    DocumentProcessingService,
    DocumentProcessorFactory,
)

__all__ = [
    "DocumentClassifier",
    "DocumentCleaner",
    "DocumentProcessingService",
    "DocumentProcessorFactory",
    "OCRProcessor",
    "OCRProviderFactory",
    "PDFTextExtractor",
    "QualityChecker",
    "ScannedDocumentProcessor",
]
