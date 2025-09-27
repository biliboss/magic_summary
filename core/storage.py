"""Persistence helpers for cached transcripts."""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .models import TranscriptSegment

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "transcripts"


@dataclass(frozen=True)
class TranscriptFingerprint:
    size: int
    mtime_ns: int

    @classmethod
    def from_path(cls, path: Path) -> "TranscriptFingerprint":
        stat = path.stat()
        return cls(size=stat.st_size, mtime_ns=int(stat.st_mtime_ns))

    def to_dict(self) -> dict[str, int]:
        return {"size": self.size, "mtime_ns": self.mtime_ns}

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "TranscriptFingerprint":
        return cls(size=int(data["size"]), mtime_ns=int(data["mtime_ns"]))


def _ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _fingerprint_path(video_path: Path) -> Path:
    fingerprint = TranscriptFingerprint.from_path(video_path)
    payload = f"{video_path.resolve()}::{fingerprint.size}::{fingerprint.mtime_ns}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return _ensure_cache_dir() / f"{digest}.json"


def load_transcript(video_path: Path) -> list[TranscriptSegment] | None:
    cache_path = _fingerprint_path(video_path)
    if not cache_path.exists():
        return None

    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        cache_path.unlink(missing_ok=True)
        return None

    try:
        stored_fp = TranscriptFingerprint.from_dict(payload["fingerprint"])
    except (KeyError, TypeError, ValueError):
        cache_path.unlink(missing_ok=True)
        return None

    current_fp = TranscriptFingerprint.from_path(video_path)
    if stored_fp != current_fp:
        cache_path.unlink(missing_ok=True)
        return None

    segments_data = payload.get("segments", [])
    try:
        return [TranscriptSegment.model_validate(seg) for seg in segments_data]
    except Exception:
        cache_path.unlink(missing_ok=True)
        return None


def save_transcript(video_path: Path, segments: Sequence[TranscriptSegment]) -> None:
    cache_path = _fingerprint_path(video_path)
    fingerprint = TranscriptFingerprint.from_path(video_path)
    data = {
        "video": str(video_path.resolve()),
        "fingerprint": fingerprint.to_dict(),
        "segments": [seg.model_dump() for seg in segments],
    }
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def transcript_to_text(segments: Iterable[TranscriptSegment]) -> str:
    lines: list[str] = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        lines.append(text)
    return "\n".join(lines)
