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
    title: str = Field(..., max_length=120)
    timestamp: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    quote: str = Field(..., max_length=280)


class TopicSummary(BaseModel):
    title: str
    timestamp: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    description: str
    highlights: List[TopicHighlight] = Field(default_factory=list)


class VideoSummary(BaseModel):
    topics: List[TopicSummary] = Field(default_factory=list)

    @property
    def total_topics(self) -> int:
        return len(self.topics)


class ProcessingStatus(BaseModel):
    status: str
    progress: float = Field(0.0, ge=0.0, le=1.0)
    message: str | None = None


def format_timestamp(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    minutes, secs = divmod(td.seconds, 60)
    return f"{minutes:02d}:{secs:02d}"
