from __future__ import annotations
import time

import hashlib
import inspect
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



def _asr_ffmpeg_audio_filter_chain(audio_filter: Optional[str]) -> Optional[str]:
    """Return a safe FFmpeg audio filter chain for ASR probe preprocessing."""
    key = (audio_filter or "").strip().lower()

    filters = {
        "loudnorm": "loudnorm=I=-16:TP=-1.5:LRA=11",
        "speech_clean": "highpass=f=80,lowpass=f=7800,dynaudnorm=f=150:g=15",
        "voice_eq": "highpass=f=100,lowpass=f=7600,equalizer=f=3000:t=q:w=1.0:g=3,dynaudnorm=f=150:g=12",
        "denoise": "afftdn=nf=-25,highpass=f=80,lowpass=f=7800",
        "denoise_loudnorm": "afftdn=nf=-25,highpass=f=80,lowpass=f=7800,loudnorm=I=-16:TP=-1.5:LRA=11",
    }

    return filters.get(key)

def _make_probe_audio_clip(media_path: Path, probe_seconds: int, audio_filter: Optional[str] = None) -> Path:
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

    filter_chain = _asr_ffmpeg_audio_filter_chain(audio_filter)

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-t",
        str(probe_seconds),
        "-i",
        media_path.resolve().as_posix(),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
    ]

    if filter_chain:
        command.extend(["-af", filter_chain])

    command.append(tmp_path.resolve().as_posix())

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


def _mean(values: List[float]) -> Optional[float]:
    values = [float(value) for value in values if value is not None]

    if not values:
        return None

    return sum(values) / len(values)


def _quality_score(
    avg_logprob_mean: Optional[float],
    compression_ratio_mean: Optional[float],
    no_speech_prob_mean: Optional[float],
    text_chars: int,
    segment_count: int,
) -> float:
    """Return a rough score for comparing probe candidates without a reference transcript."""
    score = 0.0

    if avg_logprob_mean is not None:
        score += avg_logprob_mean * 100.0

    if compression_ratio_mean is not None:
        score -= max(0.0, compression_ratio_mean - 2.4) * 20.0

    if no_speech_prob_mean is not None:
        score -= no_speech_prob_mean * 20.0

    if segment_count <= 0 or text_chars <= 0:
        score -= 100.0

    # Tiny reward for producing usable text, but not enough to beat confidence.
    score += min(text_chars, 600) / 200.0

    return score


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
    condition_on_previous_text: Optional[bool] = None,
    hotwords: Optional[str] = None,
    audio_filter: Optional[str] = None,
) -> Tuple[List[TranscriptSegment], Dict[str, Any]]:
    """
    Transcribe a local audio/video file with faster-whisper.

    If probe_seconds is provided, only the first N seconds are extracted with
    FFmpeg and transcribed. This is intended for quality checks before full ASR.
    """
    path = Path(media_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    is_probe = bool(probe_seconds and int(probe_seconds) > 0)
    probe_clip_path: Optional[Path] = None
    transcribe_path = path
    asr_started_at = time.perf_counter()

    try:
        if is_probe:
            probe_clip_path = _make_probe_audio_clip(path, int(probe_seconds or 60), audio_filter=audio_filter)
            transcribe_path = probe_clip_path

        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )

        transcribe_kwargs: Dict[str, Any] = {
            "language": language,
            "initial_prompt": initial_prompt,
            "beam_size": beam_size,
            "vad_filter": vad_filter,
        }

        if condition_on_previous_text is not None:
            transcribe_kwargs["condition_on_previous_text"] = condition_on_previous_text

        if hotwords:
            transcribe_kwargs["hotwords"] = hotwords

        # faster-whisper versions differ. Only pass options supported by the
        # installed WhisperModel.transcribe signature.
        try:
            supported_args = set(inspect.signature(model.transcribe).parameters)
            transcribe_kwargs = {
                key: value
                for key, value in transcribe_kwargs.items()
                if key in supported_args
            }
        except Exception:
            transcribe_kwargs.pop("hotwords", None)
            transcribe_kwargs.pop("condition_on_previous_text", None)

        whisper_segments, info = model.transcribe(
            str(transcribe_path),
            **transcribe_kwargs,
        )

        transcript_segments: List[TranscriptSegment] = []
        avg_logprobs: List[float] = []
        compression_ratios: List[float] = []
        no_speech_probs: List[float] = []
        text_chars = 0

        for segment in whisper_segments:
            text = (segment.text or "").strip()

            avg_logprob = getattr(segment, "avg_logprob", None)
            compression_ratio = getattr(segment, "compression_ratio", None)
            no_speech_prob = getattr(segment, "no_speech_prob", None)

            if avg_logprob is not None:
                avg_logprobs.append(float(avg_logprob))

            if compression_ratio is not None:
                compression_ratios.append(float(compression_ratio))

            if no_speech_prob is not None:
                no_speech_probs.append(float(no_speech_prob))

            if not text:
                continue

            text_chars += len(text)

            transcript_segments.append(
                TranscriptSegment(
                    speaker=speaker_name,
                    start=_seconds_to_timestamp(segment.start),
                    end=_seconds_to_timestamp(segment.end),
                    text=text,
                )
            )

        avg_logprob_mean = _mean(avg_logprobs)
        compression_ratio_mean = _mean(compression_ratios)
        no_speech_prob_mean = _mean(no_speech_probs)

        elapsed_seconds = max(0.0, time.perf_counter() - asr_started_at)
        duration_for_speed = None

        try:
            duration_for_speed = float(getattr(info, "duration", None) or 0.0)
        except Exception:
            duration_for_speed = None

        if not duration_for_speed and is_probe:
            try:
                duration_for_speed = float(probe_seconds or 0)
            except Exception:
                duration_for_speed = None

        realtime_speed = None

        if elapsed_seconds > 0 and duration_for_speed and duration_for_speed > 0:
            realtime_speed = duration_for_speed / elapsed_seconds

        metadata: Dict[str, Any] = {
            "source_file": str(path),
            "source_file_name": path.name,
            "source_file_size_bytes": path.stat().st_size,
            "source_file_sha256": _sha256_file(path),
            "transcribed_file": str(transcribe_path),
            "is_probe": is_probe,
            "probe_seconds": int(probe_seconds or 0) if is_probe else 0,
            "audio_filter": audio_filter or "",
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
            "condition_on_previous_text": condition_on_previous_text,
            "hotwords": hotwords,
            "segment_count": len(transcript_segments),
            "avg_logprob_mean": avg_logprob_mean,
            "compression_ratio_mean": compression_ratio_mean,
            "no_speech_prob_mean": no_speech_prob_mean,
            "quality_score": _quality_score(
                avg_logprob_mean=avg_logprob_mean,
                compression_ratio_mean=compression_ratio_mean,
                no_speech_prob_mean=no_speech_prob_mean,
                text_chars=text_chars,
                segment_count=len(transcript_segments),
            ),
            "elapsed_seconds": elapsed_seconds,
            "duration_for_speed_seconds": duration_for_speed,
            "processing_speed_x_realtime": realtime_speed,
        }

        return transcript_segments, metadata

    finally:
        if probe_clip_path is not None:
            try:
                probe_clip_path.unlink(missing_ok=True)
            except Exception:
                pass
