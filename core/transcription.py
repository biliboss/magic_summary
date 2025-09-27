"""Transcription service using OpenAI Whisper API."""
from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Callable, Tuple

import subprocess

from openai import OpenAI

from .config import get_openai_settings, get_ffmpeg_path
from .models import TranscriptSegment, ProcessingStatus

StatusCallback = Callable[[ProcessingStatus], None]


class TranscriptionService:
    def __init__(self, client: OpenAI | None = None):
        settings = get_openai_settings()
        self._client = client or OpenAI(api_key=settings.api_key)
        self._model = settings.model_transcription

    def transcribe(self, video_path: Path, status_cb: StatusCallback | None = None) -> list[TranscriptSegment]:
        if not video_path.exists():
            raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=0.1, message="Upload do áudio"))

        audio_input, temp_path = self._prepare_audio(video_path)

        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=0.4, message="Chamando Whisper"))

        try:
            response = self._client.audio.transcriptions.create(
                model=self._model,
                file=audio_input,
                response_format="verbose_json",
                temperature=0.0,
            )
        finally:
            audio_input.close()
            temp_path.unlink(missing_ok=True)

        segments = [
            TranscriptSegment(start=seg.start, end=seg.end, text=seg.text)
            for seg in response.segments
        ]

        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=1.0, message="Transcrição concluída"))

        return segments

    def _prepare_audio(self, video_path: Path) -> Tuple[BinaryIO, Path]:
        """Extract the audio track as a temporary WAV file and return an open handle and its path."""

        ffmpeg_bin = get_ffmpeg_path()
        temp_file = NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Extract audio track as WAV (16-bit PCM) which Whisper accepts.
        cmd = [
            str(ffmpeg_bin),
            "-y",
            "-i",
            str(video_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(temp_path),
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError("Falha ao extrair áudio com ffmpeg") from exc

        audio_handle = temp_path.open("rb")
        return audio_handle, temp_path
