"""
AI Orchestrator — the single entry point for every AI/LLM request in the
Hospital AI system.

No AI Agent (Intake, Diagnosis, Research, Prescription, Medical Report)
talks to an LLM provider (Groq, Ollama, OpenAI, Gemini, Anthropic) directly.
Every agent calls exactly one method:

    from app.ai.orchestrator import get_orchestrator

    response = get_orchestrator().run(
        agent="diagnosis",
        task="differential_diagnosis",
        patient_id=patient_id,
        response_model=SomeSchema,
    )

See `app/ai/orchestrator/orchestrator.py` for the full contract.
"""
from __future__ import annotations

from app.ai.orchestrator.orchestrator import (
    AIOrchestrator,
    AIOrchestratorError,
    get_orchestrator,
)

__all__ = ["AIOrchestrator", "AIOrchestratorError", "get_orchestrator"]
