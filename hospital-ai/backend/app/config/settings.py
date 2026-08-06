"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central runtime configuration for the API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Hospital AI API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(
        default="",
        alias="SUPABASE_SERVICE_ROLE_KEY",
    )
    supabase_jwt_secret: str = Field(default="", alias="SUPABASE_JWT_SECRET")
    # Set false on machines with corporate SSL inspection (local only).
    supabase_ssl_verify: bool = Field(default=True, alias="SUPABASE_SSL_VERIFY")

    # Intake Agent — OCR provider (unrelated to the AI Orchestrator)
    ocr_provider: str = Field(default="stub", alias="OCR_PROVIDER")
    google_vision_api_key: str = Field(default="", alias="GOOGLE_VISION_API_KEY")
    azure_ocr_endpoint: str = Field(default="", alias="AZURE_OCR_ENDPOINT")
    azure_ocr_key: str = Field(default="", alias="AZURE_OCR_KEY")

    # ------------------------------------------------------------------
    # AI Orchestrator — the ONLY place any agent's LLM/model config lives.
    # No AI Agent talks to a provider directly; every agent calls
    # `AIOrchestrator.run(agent=..., task=..., ...)`.
    #
    # The provider *fleet* (which providers exist, their priority in the
    # failover chain, their models, capabilities, and pricing) is declared in
    # `backend/providers.yaml`, not here. These settings hold the credentials
    # that file interpolates, plus runtime knobs.
    # ------------------------------------------------------------------
    # Preferred primary provider. This is a *preference*, not a lock: if it
    # is unavailable the Provider Orchestrator automatically fails over to
    # the next provider in providers.yaml. `stub` is the one exception and
    # pins the system offline for tests/local dev.
    ai_provider: str = Field(default="groq", alias="AI_PROVIDER")

    # Groq — priority 1. Free API key: https://console.groq.com/keys
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL"
    )

    # Google Gemini — priority 2. Free key: https://aistudio.google.com/apikey
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    # OpenRouter — priority 3. Free key: https://openrouter.ai/keys
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")

    # HuggingFace Inference — priority 4. Free token:
    # https://huggingface.co/settings/tokens
    huggingface_api_key: str = Field(default="", alias="HUGGINGFACE_API_KEY")

    # Ollama — optional local runtime. Enable in providers.yaml.
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")

    # Model Router — one model setting per requesting agent. Adding a new
    # agent = one new setting + one entry in ModelRouter._MODEL_SETTING_MAP.
    # Defaults target Groq's hosted Llama 3.3; override per-agent for A/B
    # testing or to point a specific agent at a different provider's model.
    intake_model: str = Field(default="llama-3.3-70b-versatile", alias="INTAKE_MODEL")
    diagnosis_model: str = Field(default="llama-3.3-70b-versatile", alias="DIAGNOSIS_MODEL")
    research_model: str = Field(default="llama-3.3-70b-versatile", alias="RESEARCH_MODEL")
    prescription_model: str = Field(
        default="llama-3.3-70b-versatile", alias="PRESCRIPTION_MODEL"
    )
    report_model: str = Field(default="llama-3.3-70b-versatile", alias="REPORT_MODEL")

    # Generation defaults (per-call overridable)
    ai_temperature: float = Field(default=0.2, alias="TEMPERATURE")
    # Completion reservation. Providers meter `prompt + max_tokens` against one
    # per-request ceiling, so this is subtracted from the prompt budget whether
    # or not the model uses it — on Groq's free tier 4096 left under 2 000
    # tokens for the prompt. Agent responses are structured JSON measured at
    # 200-700 tokens, so this is still generous.
    ai_max_tokens: int = Field(default=2048, alias="MAX_TOKENS")
    # Per-request network timeout (seconds) — passed to every provider's generate()/stream().
    ai_timeout_seconds: float = Field(default=120.0, alias="TIMEOUT")

    # Cache Manager
    ai_cache_ttl_seconds: int = Field(default=300, alias="AI_CACHE_TTL_SECONDS")

    # Retry Handler — exponential backoff
    ai_max_retries: int = Field(default=3, alias="AI_MAX_RETRIES")
    ai_retry_base_delay_ms: int = Field(default=500, alias="AI_RETRY_BASE_DELAY_MS")

    # Conversation Memory — recent turns included per orchestrator call
    ai_memory_turns: int = Field(default=5, alias="AI_MEMORY_TURNS")

    # Token optimization — compress patient context before each provider call
    # (dedupe history, trim timelines, compact the knowledge graph, and drop
    # the replayed prompt text from conversation memory).
    ai_context_compression: bool = Field(default=True, alias="AI_CONTEXT_COMPRESSION")

    # Request Queue — bounds simultaneous provider calls so a burst of agent
    # runs queues instead of stampeding a provider's concurrency limit.
    ai_max_concurrent_requests: int = Field(
        default=4, alias="AI_MAX_CONCURRENT_REQUESTS"
    )
    ai_queue_wait_timeout_seconds: float = Field(
        default=60.0, alias="AI_QUEUE_WAIT_TIMEOUT_SECONDS"
    )

    # Automatic failover master switch. Off = single-provider behavior
    # (useful when reproducing a provider-specific bug).
    ai_failover_enabled: bool = Field(default=True, alias="AI_FAILOVER_ENABLED")

    # Paid providers — implemented and pluggable; enable them in
    # providers.yaml (`openai.enabled: true`, etc.) once a key is set.
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")

    # Reserved for a future live PubMed / ClinicalTrials.gov integration.
    # The Research Agent's LLM-backed providers do not call these yet.
    pubmed_api_key: str = Field(default="", alias="PUBMED_API_KEY")
    clinical_trials_api_key: str = Field(default="", alias="CLINICAL_TRIALS_API_KEY")

    @property
    def cors_origins_list(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    def require_supabase(self) -> None:
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", self.supabase_url),
                ("SUPABASE_ANON_KEY", self.supabase_anon_key),
                ("SUPABASE_SERVICE_ROLE_KEY", self.supabase_service_role_key),
                ("SUPABASE_JWT_SECRET", self.supabase_jwt_secret),
            )
            if not value or value.startswith("your-") or "YOUR_PROJECT" in value
        ]
        if missing:
            raise RuntimeError(
                "Missing or placeholder Supabase settings: "
                + ", ".join(missing)
                + ". Copy backend/.env.example to backend/.env and fill values "
                "from the Supabase dashboard."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
