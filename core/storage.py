"""Persistence helpers for cached transcripts and summaries."""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from .models import TranscriptSegment, VideoSummary, SummaryMetadata

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "transcripts"
STATE_DIR = Path(__file__).resolve().parent.parent / "data" / "state"
RECENT_VIDEOS_FILE = STATE_DIR / "recent_videos.json"


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


def _ensure_state_dir() -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR


def _fingerprint_path(video_path: Path) -> Path:
    fingerprint = TranscriptFingerprint.from_path(video_path)
    payload = f"{video_path.resolve()}::{fingerprint.size}::{fingerprint.mtime_ns}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return _ensure_cache_dir() / f"{digest}.json"


def _read_cache(video_path: Path) -> tuple[Path, dict[str, Any]]:
    cache_path = _fingerprint_path(video_path)
    if not cache_path.exists():
        return cache_path, {}

    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        cache_path.unlink(missing_ok=True)
        return cache_path, {}

    fingerprint_data = payload.get("fingerprint")
    if not fingerprint_data:
        cache_path.unlink(missing_ok=True)
        return cache_path, {}

    try:
        stored_fp = TranscriptFingerprint.from_dict(fingerprint_data)
    except (KeyError, TypeError, ValueError):
        cache_path.unlink(missing_ok=True)
        return cache_path, {}

    current_fp = TranscriptFingerprint.from_path(video_path)
    if stored_fp != current_fp:
        cache_path.unlink(missing_ok=True)
        return cache_path, {}

    return cache_path, payload


def _prepare_cache(video_path: Path) -> tuple[Path, dict[str, Any], TranscriptFingerprint]:
    cache_path, payload = _read_cache(video_path)
    fingerprint = TranscriptFingerprint.from_path(video_path)
    payload["video"] = str(video_path.resolve())
    payload["fingerprint"] = fingerprint.to_dict()
    return cache_path, payload, fingerprint


def load_transcript(video_path: Path) -> list[TranscriptSegment] | None:
    _, payload = _read_cache(video_path)
    if not payload:
        return None

    segments_data = payload.get("segments", [])
    try:
        return [TranscriptSegment.model_validate(seg) for seg in segments_data]
    except Exception:
        return None


def save_transcript(video_path: Path, segments: Sequence[TranscriptSegment]) -> None:
    cache_path, data, _ = _prepare_cache(video_path)
    data["segments"] = [seg.model_dump() for seg in segments]
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_summary(video_path: Path) -> tuple[VideoSummary | None, SummaryMetadata | None]:
    _, payload = _read_cache(video_path)
    if not payload:
        return None, None

    summary_data = payload.get("summary")
    if not summary_data:
        meta_dict = payload.get("metadata", {}).get("summary")
        if meta_dict:
            try:
                return None, SummaryMetadata.model_validate(meta_dict)
            except Exception:
                return None, None
        return None, None

    try:
        summary = VideoSummary.model_validate(summary_data)
    except Exception:
        meta_dict = payload.get("metadata", {}).get("summary")
        if meta_dict:
            try:
                return None, SummaryMetadata.model_validate(meta_dict)
            except Exception:
                return None, None
        return None, None

    meta_dict = payload.get("metadata", {}).get("summary")
    metadata = None
    if meta_dict:
        try:
            metadata = SummaryMetadata.model_validate(meta_dict)
        except Exception:
            metadata = None
    return summary, metadata


def save_summary(
    video_path: Path,
    summary: VideoSummary,
    *,
    metadata: SummaryMetadata | None = None,
) -> None:
    cache_path, data, _ = _prepare_cache(video_path)
    data["summary"] = summary.model_dump()
    if metadata:
        meta_section = data.setdefault("metadata", {})
        meta_section["summary"] = metadata.model_dump()
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_summary(video_path: Path) -> None:
    cache_path, data = _read_cache(video_path)
    if not data:
        return
    data.pop("summary", None)
    meta = data.get("metadata")
    if isinstance(meta, dict):
        meta.pop("summary", None)
    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache_bundle(
    video_path: Path,
) -> tuple[list[TranscriptSegment] | None, VideoSummary | None, SummaryMetadata | None, dict[str, Any]]:
    cache_path = _fingerprint_path(video_path)
    if not cache_path.exists():
        return None, None, None, {}

    segments = load_transcript(video_path)
    summary, metadata = load_summary(video_path)
    payload = cache_path.read_text(encoding="utf-8")
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError:
        raw = {}
    return segments, summary, metadata, raw


def transcript_to_text(segments: Iterable[TranscriptSegment]) -> str:
    lines: list[str] = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        lines.append(text)
    return "\n".join(lines)


def load_recent_videos(limit: int = 10) -> list[Path]:
    if not RECENT_VIDEOS_FILE.exists():
        return []
    try:
        payload = json.loads(RECENT_VIDEOS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(payload, list):
        return []

    recent_paths: list[Path] = []
    for entry in payload:
        if not isinstance(entry, str):
            continue
        path = Path(entry)
        if path.exists():
            recent_paths.append(path)
        if len(recent_paths) >= limit:
            break
    return recent_paths


def save_recent_videos(paths: Iterable[Path], *, limit: int = 10) -> None:
    _ensure_state_dir()
    unique_paths: list[str] = []
    for path in paths:
        try:
            resolved = str(Path(path).resolve())
        except OSError:
            continue
        if resolved in unique_paths:
            continue
        unique_paths.append(resolved)
        if len(unique_paths) >= limit:
            break

    RECENT_VIDEOS_FILE.write_text(
        json.dumps(unique_paths, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
