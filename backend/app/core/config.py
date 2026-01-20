from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env.local")


def _split_csv(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.2")
    cors_origins: list[str] = _split_csv(
        os.getenv("CORS_ORIGINS"),
        ["http://localhost:3000", "http://127.0.0.1:3000"],
    )
    demo_script_path: str = os.getenv("DEMO_SCRIPT_PATH", "app/demo/demo_script.json")
    storage_dir: str = os.getenv("MEETING_STORAGE_DIR", "meetings")


settings = Settings()
