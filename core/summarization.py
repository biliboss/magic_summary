"""Summarization service using OpenAI + instructor for structured outputs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from instructor import from_openai
from openai import OpenAI

from .config import get_openai_settings
from .models import TranscriptSegment, VideoSummary, SummaryMetadata, format_timestamp


# The prompt now explicitly asks the model to provide richer, more technical detail and longer
# descriptions. It also relaxes the strict character limits for titles while still keeping them
# concise, and it adds a request for a brief “impact assessment” for each topic. This helps the
# generated summary capture all technical aspects and produce a larger, more useful output.
HIGHLIGHT_PROMPT = (
    "You are an expert product analyst summarizing usability feedback videos.\n"
    "Transform the provided transcript segments into a structured `VideoSummary`.\n\n"
    "Guidelines:\n"
    "- Include **all** relevant topics; do not limit the number of topics.\n"
    "- Each topic (`TopicSummary`) must contain:\n"
    "  * title (up to 200 characters)\n"
    "  * timestamp (MM:SS) of the first occurrence\n"
    "  * a **detailed description** (up to 800 characters) that explains the problem, its technical context, and any suggested solution.\n"
    "  * an optional **impact assessment** (short sentence) describing why this issue matters for the product/engineering team.\n"
    "  * highlights[]\n"
    "- Each highlight (`TopicHighlight`) must contain:\n"
    "  * title (up to 200 characters)\n"
    "  * timestamp (MM:SS)\n"
    "  * quote (up to 500 characters) – verbatim from the transcript, truncate with … if needed.\n"
    "- If the same issue appears multiple times, merge it into a single topic and include all relevant highlights.\n"
    "- Order topics chronologically by their first occurrence.\n"
    "- Quotes must be literal from the transcript.\n"
    "- Focus on actionable UX/technical problems, performance bottlenecks, integration issues, and concrete suggestions.\n"
    "- Do **not** fabricate information; stay strictly within the provided transcript.\n"
    "- Respond **only** with valid JSON matching the `VideoSummary` schema.\n"
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
            # Request a larger token budget to allow the model to generate richer, more detailed summaries.
            "max_tokens": 2500,
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
