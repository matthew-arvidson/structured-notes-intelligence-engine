"""
Centralized environment configuration.

All env vars are loaded here once. If a required variable is missing the app
raises immediately on import — no silent failures, no hardcoded defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Return the env var value or raise a clear error if it is not set."""
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in all values."
        )
    return value


def _optional(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


# ─── Azure OpenAI ─────────────────────────────────────────────────────────────
AZURE_OPENAI_API_KEY: str = _require("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT: str = _require("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION: str = _optional("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_OPENAI_CHAT_DEPLOYMENT: str = _require("AZURE_OPENAI_CHAT_DEPLOYMENT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = _require("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

# ─── Azure PostgreSQL ─────────────────────────────────────────────────────────
AZURE_PG_HOST: str = _require("AZURE_PG_HOST")
AZURE_PG_DATABASE: str = _require("AZURE_PG_DATABASE")
AZURE_PG_USER: str = _require("AZURE_PG_USER")
AZURE_PG_PASSWORD: str = _require("AZURE_PG_PASSWORD")
AZURE_PG_PORT: int = int(_optional("AZURE_PG_PORT", "5432"))

# ─── ChromaDB ─────────────────────────────────────────────────────────────────
CHROMA_PATH: str = _optional("CHROMA_PATH", "./chroma_db")
CHROMA_HOST: str = _optional("CHROMA_HOST", "")          # blank = local mode
CHROMA_PORT: int = int(_optional("CHROMA_PORT", "8000"))
CHROMA_COLLECTION: str = _optional("CHROMA_COLLECTION", "term_sheets")

# ─── App ──────────────────────────────────────────────────────────────────────
API_PORT: int = int(_optional("API_PORT", "3001"))
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in _optional("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
]
LOG_LEVEL: str = _optional("LOG_LEVEL", "INFO")
