"""Summarization service using OpenAI + instructor for structured outputs."""
from __future__ import annotations

from typing import Sequence

from instructor import from_openai
from openai import OpenAI

from .config import get_openai_settings
from .models import TranscriptSegment, VideoSummary, format_timestamp


HIGHLIGHT_PROMPT = (
    "You are an expert product analyst summarizing usability feedback videos.\n"
    "Analyze the provided transcript segments and produce structured insights for product and engineering teams."
)


class SummarizationService:
    def __init__(self, client: OpenAI | None = None):
        settings = get_openai_settings()
        base_client = client or OpenAI(api_key=settings.api_key)
        self._client = from_openai(base_client)
        self._model = settings.model_summary

    def summarize(self, segments: Sequence[TranscriptSegment]) -> VideoSummary:
        if not segments:
            return VideoSummary(topics=[])

        transcript_as_text = "\n".join(
            f"[{format_timestamp(seg.start)}] {seg.text.strip()}" for seg in segments if seg.text.strip()
        )

        user_prompt = (
            f"{HIGHLIGHT_PROMPT}\n\n"
            "Instructions:\n"
            "- Identify the most critical UX or technical issues raised.\n"
            "- Return between 3 and 6 topics. Each topic should include a title, timestamp, description, and highlights.\n"
            "- Each highlight must contain a short title, the timestamp in MM:SS, and a direct quote (<=120 characters).\n"
            "- Focus on actionable problems or suggestions relevant to product/engineering.\n"
            "- Rely only on the transcript provided; do not fabricate details.\n\n"
            f"Transcript:\n{transcript_as_text}"
        )

        response: VideoSummary = self._client.chat.completions.create(
            model=self._model,
            temperature=0.2,
            response_model=VideoSummary,
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured insights from UX feedback videos.",
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        return response
