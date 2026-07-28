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

    # AI / Intake Agent providers (adapters selected by name)
    ocr_provider: str = Field(default="stub", alias="OCR_PROVIDER")
    llm_provider: str = Field(default="stub", alias="LLM_PROVIDER")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-haiku-latest", alias="ANTHROPIC_MODEL")
    ollama_base_url: str = Field(default="http://127.0.0.1:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2", alias="OLLAMA_MODEL")
    google_vision_api_key: str = Field(default="", alias="GOOGLE_VISION_API_KEY")
    azure_ocr_endpoint: str = Field(default="", alias="AZURE_OCR_ENDPOINT")
    azure_ocr_key: str = Field(default="", alias="AZURE_OCR_KEY")

    # Diagnosis Agent (clinical decision support — assists, never replaces, a physician)
    diagnosis_engine: str = Field(default="rule_based", alias="DIAGNOSIS_ENGINE")

    # Research Agent (evidence enrichment providers)
    research_provider: str = Field(default="mock", alias="RESEARCH_PROVIDER")
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
