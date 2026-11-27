"""Configuration and environment loading for SCRIPTXT."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

PROMPT_VERSION: Final[str] = "v1.0.0"

SUPPORTED_TONES: Final[tuple[str, ...]] = (
    "Professional",
    "Friendly",
    "Bold",
    "Educational",
    "Inspirational",
    "Witty",
)

SUPPORTED_CHANNELS: Final[tuple[str, ...]] = (
    "LinkedIn",
    "X",
    "Instagram",
    "Blog",
)

SUPPORTED_FORMATS: Final[tuple[str, ...]] = (
    "post",
    "thread",
    "caption",
    "carousel",
    "reel",
    "blog_outline",
)

SUPPORTED_OBJECTIVES: Final[tuple[str, ...]] = (
    "awareness",
    "engagement",
    "education",
    "lead_generation",
)

MAX_TOPIC_LENGTH: Final[int] = 300
MAX_AUDIENCE_LENGTH: Final[int] = 300
MAX_BRAND_VOICE_LENGTH: Final[int] = 1000
MIN_CALENDAR_DAYS: Final[int] = 3
MAX_CALENDAR_DAYS: Final[int] = 14
LINKEDIN_MIN_WORDS: Final[int] = 120
LINKEDIN_MAX_WORDS: Final[int] = 180
X_THREAD_MIN_POSTS: Final[int] = 3
X_THREAD_MAX_POSTS: Final[int] = 7
INSTAGRAM_MAX_CHARS: Final[int] = 2200
MIN_HASHTAGS: Final[int] = 3
MAX_HASHTAGS: Final[int] = 8
DEFAULT_MODEL: Final[str] = "gemini-4-hydrogen"
MODEL_ROUTING_AUTO: Final[str] = "auto"

FREE_TIER_TEXT_MODELS: Final[tuple[str, ...]] = (
    "gemini-4-hydrogen",
    "gemini-3.1-flash-lite",
)

DEFAULT_TASK_MODELS: Final[dict[str, str]] = {
    "linkedin_post": "gemini-4-hydrogen",
    "x_thread": "gemini-3.1-flash-lite",
    "instagram_caption": "gemini-3.1-flash-lite",
    "blog_outline": "gemini-4-hydrogen",
    "content_calendar": "gemini-4-hydrogen",
}


class ConfigurationError(RuntimeError):
    """Raised when required environment configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    gemini_api_key: str
    gemini_model: str = MODEL_ROUTING_AUTO
    request_timeout_seconds: float = 60.0
    prompt_version: str = PROMPT_VERSION


def load_environment(env_path: str | Path | None = None) -> None:
    """Load environment variables from a .env file without overriding existing env vars."""
    load_dotenv(dotenv_path=env_path, override=False)


def get_settings(
    env_path: str | Path | None = None,
    require_api_key: bool = True,
) -> Settings:
    """Return validated runtime settings from environment variables."""
    load_environment(env_path=env_path)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", MODEL_ROUTING_AUTO).strip() or MODEL_ROUTING_AUTO
    timeout_raw = os.getenv("GEMINI_TIMEOUT_SECONDS", "60").strip()

    try:
        timeout = float(timeout_raw)
        if timeout <= 0:
            raise ValueError("Timeout must be positive.")
    except ValueError:
        timeout = 60.0

    placeholders = {"", "MY_GEMINI_API_KEY", "your_api_key_here"}
    if require_api_key and api_key in placeholders:
        raise ConfigurationError(
            "GEMINI_API_KEY is missing or not configured. "
            "Set GEMINI_API_KEY in your environment or .env file."
        )

    return Settings(
        gemini_api_key=api_key,
        gemini_model=model,
        request_timeout_seconds=timeout,
        prompt_version=PROMPT_VERSION,
    )
