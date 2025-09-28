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
    api_key: str | None = None
    transcription_backend: str = "local"
    model_transcription: str = "whisper-1"
    model_summary: str = "gpt-4o-mini-2024-07-18"  # 128k context window
    summary_temperature: float | None = None
    local_model_name: str = "base"
    local_device: str = "cpu"  # Forçado para CPU para evitar erros de CUDA no Windows
    local_compute_type: str = "float32"  # Forçado para float32, compatível sem CUDA
    local_download_root: str | None = None

def get_openai_settings() -> OpenAISettings:
    load_environment()
    from os import getenv

    api_key = getenv("OPENAI_API_KEY")
    model_transcription = getenv("OPENAI_WHISPER_MODEL", OpenAISettings.model_transcription)
    model_summary = getenv("OPENAI_SUMMARY_MODEL", OpenAISettings.model_summary)
    summary_temperature_env = getenv("OPENAI_SUMMARY_TEMPERATURE")

    backend_env = getenv("TRANSCRIPTION_BACKEND")
    transcription_backend = (
        backend_env.lower() if backend_env else OpenAISettings.transcription_backend
    )

    if transcription_backend == "openai" and not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Please configure it in the .env file."
        )
    if transcription_backend not in {"openai", "local"}:
        raise RuntimeError(
            "TRANSCRIPTION_BACKEND inválido. Use 'openai' ou 'local'."
        )

    local_model_name = getenv("LOCAL_WHISPER_MODEL", OpenAISettings.local_model_name)
    local_device = getenv("LOCAL_WHISPER_DEVICE", OpenAISettings.local_device)
    local_compute_type = getenv("LOCAL_WHISPER_COMPUTE", OpenAISettings.local_compute_type)
    local_download_root = getenv("LOCAL_WHISPER_CACHE", None)

    # Força CPU se backend local e qualquer indício de auto ou GPU problemática
    if transcription_backend == "local":
        if local_device.lower() in {"auto", "cuda"}:
            local_device = "cpu"
            local_compute_type = "float32"
        # Verificação adicional: se não há CUDA_VISIBLE_DEVICES, força CPU
        if getenv("CUDA_VISIBLE_DEVICES") is None:
            local_device = "cpu"
            local_compute_type = "float32"

    summary_temperature = None
    if summary_temperature_env:
        try:
            summary_temperature = float(summary_temperature_env)
        except ValueError as exc:
            raise RuntimeError(
                "OPENAI_SUMMARY_TEMPERATURE deve ser um número (float)."
            ) from exc

    return OpenAISettings(
        api_key=api_key,
        model_transcription=model_transcription,
        model_summary=model_summary,
        transcription_backend=transcription_backend,
        summary_temperature=summary_temperature,
        local_model_name=local_model_name,
        local_device=local_device,
        local_compute_type=local_compute_type,
        local_download_root=local_download_root,
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
