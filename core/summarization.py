"""Summarization service using OpenAI + instructor for structured outputs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from instructor import from_openai
from openai import OpenAI

from .config import get_openai_settings
from .models import TranscriptSegment, VideoSummary, SummaryMetadata, format_timestamp


HIGHLIGHT_PROMPT = (
    "You are an expert product analyst summarizing usability feedback videos.\n"
    "Transform the provided transcript segments into a structured `VideoSummary`.\n\n"
    "Guidelines:\n"
    "- Do not limit the number of topics; include as many as needed.\n"
    "- Each topic (`TopicSummary`) must have: title (<=120 chars), timestamp (MM:SS), description, and highlights[].\n"
    "- Each highlight (`TopicHighlight`) must have: title (<=120 chars), timestamp (MM:SS), quote (<=280 chars).\n"
    "- If the same issue appears multiple times, merge into one topic and include multiple highlights.\n"
    "- Order topics chronologically by their first occurrence.\n"
    "- Quotes must be literal from the transcript (truncate with … if needed).\n"
    "- Focus on actionable UX/technical problems or suggestions relevant to product/engineering.\n"
    "- Do not invent details beyond the transcript.\n"
    "- Use the transcript’s language.\n"
)

PROMPT_VERSION = "2025-09-27"


class SummarizationService:
    def __init__(self, client: OpenAI | None = None):
        settings = get_openai_settings()
        base_client = client or OpenAI(api_key=settings.api_key)
        self._client = from_openai(base_client)
        self._model = settings.model_summary
        self._temperature = settings.summary_temperature
        self._prompt_version = PROMPT_VERSION

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    def summarize(self, segments: Sequence[TranscriptSegment]) -> VideoSummary:
        if not segments:
            return VideoSummary(topics=[])

        transcript_as_text = "\n".join(
            f"[{format_timestamp(seg.start)}] {seg.text.strip()}"
            for seg in segments
            if seg.text.strip()
        )

        user_prompt = f"{HIGHLIGHT_PROMPT}\n\nTranscript:\n{transcript_as_text}"

        create_kwargs: dict = {
            "model": self._model,
            "response_model": VideoSummary,
            "messages": [
                {
                    "role": "system",
                    "content": "You return only valid JSON that matches the `VideoSummary` schema.",
                },
                {"role": "user", "content": user_prompt},
            ],
        }
        if self._temperature is not None:
            create_kwargs["temperature"] = self._temperature

        response: VideoSummary = self._client.chat.completions.create(**create_kwargs)
        return response

    def build_metadata(self) -> SummaryMetadata:
        return SummaryMetadata(
            prompt_version=self._prompt_version,
            regenerated_at=datetime.now(timezone.utc).isoformat(),
            backend_model=self._model,
        )
