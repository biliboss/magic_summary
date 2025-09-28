"""Domain models for transcripts and summaries."""
from __future__ import annotations

from datetime import timedelta
from typing import List

from pydantic import BaseModel, Field, validator


class TranscriptSegment(BaseModel):
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_timestamp_label(self) -> str:
        return format_timestamp(self.start)


class TopicHighlight(BaseModel):
    # Allow longer titles and quotes as the new prompt requests more detail.
    title: str = Field(..., max_length=200)
    timestamp: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    quote: str = Field(..., max_length=500)


class TopicSummary(BaseModel):
    title: str
    timestamp: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    description: str
    # Optional short sentence describing the impact/importance of the topic.
    impact_assessment: str | None = None
    highlights: List[TopicHighlight] = Field(default_factory=list)


class VideoSummary(BaseModel):
    topics: List[TopicSummary] = Field(default_factory=list)

    @property
    def total_topics(self) -> int:
        return len(self.topics)


class SummaryMetadata(BaseModel):
    prompt_version: str | None = None
    regenerated_at: str | None = None
    backend_model: str | None = None
    extra: dict = Field(default_factory=dict)


class ProcessingStatus(BaseModel):
    status: str
    progress: float = Field(0.0, ge=0.0, le=1.0)
    message: str | None = None


def format_timestamp(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    minutes, secs = divmod(td.seconds, 60)
    return f"{minutes:02d}:{secs:02d}"
