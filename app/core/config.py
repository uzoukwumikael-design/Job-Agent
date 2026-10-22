from functools import lru_cache
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.xai_api_key = os.getenv("XAI_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai")  # openai | xai | ollama | gemini
        self.llm_model = os.getenv("LLM_MODEL", "gpt-4o")
        self.llm_base_url = os.getenv("LLM_BASE_URL") or None
        self.app_secret_key = os.getenv("APP_SECRET_KEY", "dev-secret-change-me")
        self.debug = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.data_dir = os.getenv("DATA_DIR", "data")
        self.project_root = Path(__file__).resolve().parents[2]

        default_sqlite = f"sqlite:///{self.project_root / self.data_dir / 'app.db'}"
        self.database_url = os.getenv("DATABASE_URL", default_sqlite)

        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.linkedin_client_id = os.getenv("LINKEDIN_CLIENT_ID")
        self.linkedin_client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        self.oauth_redirect_base = os.getenv("OAUTH_REDIRECT_BASE", "http://localhost:8000")

        self.scan_cron_hours = os.getenv("SCAN_CRON_HOURS", "6,18")
        self.enable_scheduler = os.getenv("ENABLE_SCHEDULER", "true").lower() in ("1", "true", "yes")

        # Alerts
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.smtp_host = os.getenv("SMTP_HOST")
        self.alert_from_email = os.getenv("ALERT_FROM_EMAIL", "alerts@jobagent.local")
        self.default_alert_min_score = float(os.getenv("DEFAULT_ALERT_MIN_SCORE", "4.0"))

    @property
    def data_path(self) -> Path:
        p = self.project_root / self.data_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def master_path(self) -> Path:
        p = self.data_path / "master"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def jobs_path(self) -> Path:
        p = self.data_path / "jobs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def tailored_path(self) -> Path:
        p = self.data_path / "tailored"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def tracker_path(self) -> Path:
        p = self.data_path / "tracker"
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
