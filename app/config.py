import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "ServiceNow AI Incident Assigner"
    PORT: int = 8000
    RESOLVED_INC_EXCEL_FILE: str = "servicenow-diversion_inc-dumps.xlsx"

    # Database Settings
    DATABASE_URL: str = "sqlite:///./incident_assignment.db"

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_TEXT_MODEL: str = "qwen3:1.7b"  # Fast local model
    OLLAMA_EMBED_MODEL: str = "qwen3-embedding:4b"  # Native embedding model

    # LangSmith Settings (read from .env / process env automatically by pydantic-settings)
    LANGSMITH_TRACING: str = "True"
    LANGSMITH_ENDPOINT: str = ""
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = ""

    # ChromaDB Settings
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "resolved_incidents"

    # ServiceNow Settings
    SERVICENOW_URL: str = os.getenv("SERVICENOW_URL")
    SERVICENOW_USER: str = os.getenv("SERVICENOW_USER")
    SERVICENOW_PASSWORD: str = os.getenv("SERVICENOW_PASSWORD")

    # Confidence Score Threshold (Below this will require Human Review)
    CONFIDENCE_THRESHOLD: float = 70.0

    # Use pydantic-settings v2 config: load .env from the same directory as this file.
    # Pydantic-settings automatically reads from BOTH the .env file and the process
    # environment, with process environment taking precedence.
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


# -------------------------------------------------------------------
# Mirror LangSmith / ServiceNow settings into os.environ
# -------------------------------------------------------------------
# pydantic-settings reads values from .env into the Settings object, but
# the LangSmith SDK (and most third-party libs) only look at os.environ.
# Without this, even a perfectly loaded .env produces zero traces.
# Only set keys that are non-empty so we don't clobber unrelated env vars.
def _export_to_env(settings_obj, keys):
    for key in keys:
        value = getattr(settings_obj, key, None)
        if value not in (None, ""):
            os.environ[key] = str(value)


_export_to_env(
    settings,
    [
        "LANGSMITH_TRACING",
        "LANGSMITH_ENDPOINT",
        "LANGSMITH_API_KEY",
        "LANGSMITH_PROJECT",
    ],
)
