import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/running.db")
    CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]

    STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
    STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
    STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN", "")
    STRAVA_VERIFY_TOKEN = os.getenv("STRAVA_VERIFY_TOKEN", "")
    STRAVA_ATHLETE_ID = os.getenv("STRAVA_ATHLETE_ID", "")
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
