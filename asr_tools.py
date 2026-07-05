from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
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


def _make_probe_audio_clip(media_path: Path, probe_seconds: int) -> Path:
    """Create a temporary WAV containing the first probe_seconds of media."""
    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg is required for ASR probe mode. "
            "Install FFmpeg or run a full ASR transcription instead."
        )

    probe_seconds = max(1, int(probe_seconds))

    tmp = tempfile.NamedTemporaryFile(
        prefix="ytce_asr_probe_",
        suffix=".wav",
        delete=False,
    )
    tmp_path = Path(tmp.name)
    tmp.close()

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-t",
        str(probe_seconds),
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(tmp_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

        error_text = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "Could not create ASR probe clip with FFmpeg."
            + (f"\n\n{error_text}" if error_text else "")
        )

    return tmp_path


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
    probe_seconds: Optional[int] = None,
) -> Tuple[List[TranscriptSegment], Dict[str, Any]]:
    """
    Transcribe a local audio/video file with faster-whisper.

    If probe_seconds is provided, only the first N seconds are extracted with
    FFmpeg and transcribed. This is intended for quick quality checks before
    full transcription.

    This does not perform speaker diarization.
    All generated segments are assigned to speaker_name.
    """
    path = Path(media_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    is_probe = bool(probe_seconds and int(probe_seconds) > 0)
    probe_clip_path: Optional[Path] = None
    transcribe_path = path

    try:
        if is_probe:
            probe_clip_path = _make_probe_audio_clip(path, int(probe_seconds or 60))
            transcribe_path = probe_clip_path

        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )

        whisper_segments, info = model.transcribe(
            str(transcribe_path),
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
            "transcribed_file": str(transcribe_path),
            "is_probe": is_probe,
            "probe_seconds": int(probe_seconds or 0) if is_probe else 0,
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

    finally:
        if probe_clip_path is not None:
            try:
                probe_clip_path.unlink(missing_ok=True)
            except Exception:
                pass
