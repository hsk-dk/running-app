import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Europe/Copenhagen")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/running.db")
    CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]

    # Who is the caller? "none": a single local user (development, or one-person use behind nothing).
    # "proxy": identity comes from the Authentik forward-auth headers, accepted only from TRUSTED_PROXIES.
    AUTH_MODE = os.getenv("AUTH_MODE", "none").lower()
    TRUSTED_PROXIES = [x.strip() for x in os.getenv("TRUSTED_PROXIES", "").split(",") if x.strip()]
    AUTH_ADMIN_GROUPS = [x.strip() for x in os.getenv("AUTH_ADMIN_GROUPS", "homelab-admins").split(",") if x.strip()]
    AUTH_FAMILY_GROUPS = [x.strip() for x in os.getenv("AUTH_FAMILY_GROUPS", "homelab-family").split(",") if x.strip()]
    # The Authentik username that owns the data that existed before users were added. Empty: the first admin to sign in.
    AUTH_OWNER_USERNAME = os.getenv("AUTH_OWNER_USERNAME", "")
    # Signs the OAuth state. If empty, a random key is generated at start (state then dies on restart).
    APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "")
    # Family members can choose to share an overview or their runs with each other. Switch off to disable.
    FAMILY_SHARING_ENABLED = os.getenv("FAMILY_SHARING_ENABLED", "true").lower() in ("1", "true", "yes")

    STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
    STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
    STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN", "")
    STRAVA_VERIFY_TOKEN = os.getenv("STRAVA_VERIFY_TOKEN", "")
    STRAVA_ATHLETE_ID = os.getenv("STRAVA_ATHLETE_ID", "")
    STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "")
    SMASHRUN_CLIENT_ID = os.getenv("SMASHRUN_CLIENT_ID", "")
    SMASHRUN_CLIENT_SECRET = os.getenv("SMASHRUN_CLIENT_SECRET", "")
    SMASHRUN_REDIRECT_URI = os.getenv("SMASHRUN_REDIRECT_URI", "")
    STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL = os.getenv("STRAVA_PUSH_SUBSCRIPTION_CALLBACK_URL", "")

    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_API_URL = os.getenv(
        "LLM_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
    )
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")


settings = Settings()
