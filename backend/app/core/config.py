"""
Application configuration via pydantic-settings.
All secrets come from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── App ───────────────────────────────────────────────────────────
    APP_NAME: str = "Void Kernel — Multimodal Misinformation Detector"
    DEBUG: bool = False

    # ── Redis / ARQ (job queue + SHA-256 result cache) ────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Supabase ──────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # ── Gemini ────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # ── Tavily ────────────────────────────────────────────────────────
    TAVILY_API_KEY: str = ""

    # ── Google Fact Check API ─────────────────────────────────────────
    GOOGLE_FACT_CHECK_API_KEY: str = ""

    # ── Feature flags ─────────────────────────────────────────────────
    ENABLE_SERPAPI_REVERSE_IMAGE: bool = False
    SERPAPI_KEY: str = ""

    # ── Cache ─────────────────────────────────────────────────────────
    RESULT_CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days


settings = Settings()
