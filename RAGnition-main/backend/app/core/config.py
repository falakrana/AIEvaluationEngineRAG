"""
Application settings loaded from environment variables / .env file.
All paths use pathlib so the app runs on Linux, macOS, and Windows alike.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ---- LLM / Embeddings ------------------------------------------------
    google_api_key: str = ""
    gemini_model: str = "models/gemini-2.5-flash"
    embedding_model: str = "models/gemini-embedding-2"
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"

    # ---- Chunking --------------------------------------------------------
    chunk_size: int = 800
    chunk_overlap: int = 150

    # ---- Retrieval -------------------------------------------------------
    top_k: int = 5

    # ---- Storage ---------------------------------------------------------
    # Resolved relative to the backend/ directory at startup.
    storage_dir: Path = Path("./storage")

    # ---- Server ----------------------------------------------------------
    cors_origins: List[str] = ["http://localhost:5173"]
    max_file_size_mb: int = 50

    # ---- Derived (not from env) ------------------------------------------
    @property
    def upload_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.storage_dir / "chroma"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        """Accept either a JSON array string or a real list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback: single origin as plain string
                return [v]
        return v

    def ensure_dirs(self) -> None:
        """Create storage directories if they do not exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    settings = Settings()
    settings.ensure_dirs()
    return settings
