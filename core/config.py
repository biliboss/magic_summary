"""Application configuration helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from shutil import which

APP_ROOT = Path(__file__).resolve().parent.parent


def load_environment(dotenv_path: Optional[Path] = None) -> None:
    """Load environment variables from a `.env` file if present."""
    if dotenv_path is None:
        dotenv_path = APP_ROOT / ".env"
    load_dotenv(dotenv_path)


@dataclass
class OpenAISettings:
    api_key: str
    model_transcription: str = "whisper-1"
    model_summary: str = "gpt-4o-mini"


def get_openai_settings() -> OpenAISettings:
    load_environment()
    from os import getenv

    api_key = getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Please configure it in the .env file."
        )
    model_transcription = getenv("OPENAI_WHISPER_MODEL", OpenAISettings.model_transcription)
    model_summary = getenv("OPENAI_SUMMARY_MODEL", OpenAISettings.model_summary)
    return OpenAISettings(
        api_key=api_key,
        model_transcription=model_transcription,
        model_summary=model_summary,
    )


def get_ffmpeg_path() -> Path:
    """Resolve the ffmpeg executable path.

    Priority order:
    1. `FFMPEG_BIN` environment variable (absolute path).
    2. System PATH lookup via `which`.
    """

    load_environment()
    from os import getenv

    env_path = getenv("FFMPEG_BIN")
    if env_path:
        ffmpeg_path = Path(env_path)
        if not ffmpeg_path.exists():
            raise RuntimeError(
                f"FFMPEG_BIN is set to '{env_path}', but the file does not exist."
            )
        return ffmpeg_path

    discovered = which("ffmpeg")
    if not discovered:
        raise RuntimeError(
            "ffmpeg executable not found. Set FFMPEG_BIN in the environment or add ffmpeg to PATH."
        )
    return Path(discovered)
