from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from faster_whisper import WhisperModel

from transcript_tools import TranscriptSegment



def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return SHA-256 hash for a local file."""
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    if seconds is None:
        seconds = 0.0

    total_ms = int(round(float(seconds) * 1000))

    hours = total_ms // 3_600_000
    total_ms %= 3_600_000

    minutes = total_ms // 60_000
    total_ms %= 60_000

    secs = total_ms // 1000
    ms = total_ms % 1000

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def transcribe_media_file(
    media_path: str,
    model_name: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    speaker_name: str = "ASR",
    language: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    vad_filter: bool = True,
    beam_size: int = 5,
) -> Tuple[List[TranscriptSegment], Dict[str, Any]]:
    """
    Transcribe a local audio/video file with faster-whisper.

    This does not perform speaker diarization.
    All generated segments are assigned to speaker_name.
    """
    path = Path(media_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )

    whisper_segments, info = model.transcribe(
        str(path),
        language=language,
        initial_prompt=initial_prompt,
        beam_size=beam_size,
        vad_filter=vad_filter,
    )

    transcript_segments: List[TranscriptSegment] = []

    for segment in whisper_segments:
        text = (segment.text or "").strip()

        if not text:
            continue

        transcript_segments.append(
            TranscriptSegment(
                speaker=speaker_name,
                start=_seconds_to_timestamp(segment.start),
                end=_seconds_to_timestamp(segment.end),
                text=text,
            )
        )

    metadata: Dict[str, Any] = {
        "source_file": str(path),
        "source_file_name": path.name,
        "source_file_size_bytes": path.stat().st_size,
        "source_file_sha256": _sha256_file(path),
        "model_name": model_name,
        "device": device,
        "compute_type": compute_type,
        "speaker_name": speaker_name,
        "requested_language": language,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "initial_prompt": initial_prompt,
        "duration": getattr(info, "duration", None),
        "duration_after_vad": getattr(info, "duration_after_vad", None),
        "vad_filter": vad_filter,
        "beam_size": beam_size,
        "segment_count": len(transcript_segments),
    }

    return transcript_segments, metadata