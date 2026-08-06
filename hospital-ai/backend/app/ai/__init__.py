"""
AI package — Intake Agent, OCR provider, pipelines, and the AI
Orchestrator (the single entry point for every LLM request; see
`app/ai/orchestrator/`).

`app/ai/llm/providers.py` is deprecated — every agent's LLM calls now go
through `app.ai.orchestrator.get_orchestrator()` instead.
"""

from app.ai.intake.agent import IntakeAgent, intake_agent
from app.ai.ocr.providers import OCRProvider, get_ocr_provider
from app.ai.orchestrator import AIOrchestrator, get_orchestrator

__all__ = [
    "IntakeAgent",
    "intake_agent",
    "OCRProvider",
    "get_ocr_provider",
    "AIOrchestrator",
    "get_orchestrator",
]
