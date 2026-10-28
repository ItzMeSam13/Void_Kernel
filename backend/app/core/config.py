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

    # ── Audio / Whisper (Module 4) ───────────────────────────────────
    WHISPER_MODEL_SIZE: str = "small"
    WHISPER_DEVICE: str = "auto"
    WHISPER_COMPUTE_TYPE: str = "default"
    WHISPER_DOWNLOAD_ROOT: str | None = None

    # ── Synthetic Audio / Wav2Vec2 (Module 4) ─────────────────────────
    DEEPFAKE_AUDIO_MODEL_ID: str = "mo-thecreator/Deepfake-audio-detection"
    DEEPFAKE_AUDIO_DEVICE: str = "auto"
    DEEPFAKE_AUDIO_THRESHOLD: float = 0.65
    DEEPFAKE_AUDIO_WINDOW_SEC: float = 5.0
    DEEPFAKE_AUDIO_OVERLAP_SEC: float = 1.0

    # ── Cache ─────────────────────────────────────────────────────────
    RESULT_CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 7  # 7 days


settings = Settings()
