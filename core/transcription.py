"""Transcription service using OpenAI Whisper API."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Callable

from openai import OpenAI

from .config import get_openai_settings
from .models import TranscriptSegment, ProcessingStatus

StatusCallback = Callable[[ProcessingStatus], None]


class TranscriptionService:
    def __init__(self, client: OpenAI | None = None):
        settings = get_openai_settings()
        self._client = client or OpenAI(api_key=settings.api_key)
        self._model = settings.model_transcription

    def transcribe(self, video_path: Path, status_cb: StatusCallback | None = None) -> list[TranscriptSegment]:
        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=0.1, message="Upload do áudio"))

        audio_input = self._prepare_audio(video_path)

        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=0.4, message="Chamando Whisper"))

        response = self._client.audio.transcriptions.create(
            model=self._model,
            file=audio_input,
            response_format="verbose_json",
            temperature=0.0,
        )

        segments = [
            TranscriptSegment(start=seg.start, end=seg.end, text=seg.text)
            for seg in response.segments
        ]

        if status_cb:
            status_cb(ProcessingStatus(status="transcribing", progress=1.0, message="Transcrição concluída"))

        return segments

    def _prepare_audio(self, video_path: Path):
        # TODO: implement audio extraction using ffmpeg/ffprobe
        raise NotImplementedError("Audio extraction not yet implemented")
