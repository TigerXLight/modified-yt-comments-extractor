"""Local WebRTC VAD helpers for blank speech-interval transcript scaffolds."""

from __future__ import annotations

import shutil
import subprocess
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence


DEFAULT_VAD_SAMPLE_RATE = 16000
DEFAULT_VAD_FRAME_MS = 30


@dataclass(frozen=True)
class SpeechInterval:
    """A local speech interval with no transcript text."""

    start_seconds: float
    end_seconds: float


def _frame_bytes(sample_rate: int, frame_ms: int) -> int:
    return int(sample_rate * (frame_ms / 1000.0) * 2)


def _merge_intervals(
    intervals: Sequence[SpeechInterval],
    *,
    merge_gap_seconds: float,
) -> tuple[SpeechInterval, ...]:
    merged: list[SpeechInterval] = []
    for interval in sorted(intervals, key=lambda item: (item.start_seconds, item.end_seconds)):
        if not merged:
            merged.append(interval)
            continue
        previous = merged[-1]
        if interval.start_seconds - previous.end_seconds <= merge_gap_seconds:
            merged[-1] = SpeechInterval(
                start_seconds=previous.start_seconds,
                end_seconds=max(previous.end_seconds, interval.end_seconds),
            )
        else:
            merged.append(interval)
    return tuple(merged)


def _frame_rms(frame: bytes) -> float:
    if len(frame) < 2:
        return 0.0
    usable = frame[: len(frame) - (len(frame) % 2)]
    if not usable:
        return 0.0
    values = struct.unpack("<" + "h" * (len(usable) // 2), usable)
    if not values:
        return 0.0
    return (sum(float(value) * float(value) for value in values) / len(values)) ** 0.5


def _split_long_intervals(
    intervals: Sequence[SpeechInterval],
    *,
    max_interval_seconds: float,
) -> tuple[SpeechInterval, ...]:
    if max_interval_seconds <= 0:
        return tuple(intervals)
    split: list[SpeechInterval] = []
    for interval in intervals:
        duration = interval.end_seconds - interval.start_seconds
        if duration <= max_interval_seconds:
            split.append(interval)
            continue
        start = interval.start_seconds
        while start < interval.end_seconds:
            end = min(interval.end_seconds, start + max_interval_seconds)
            split.append(SpeechInterval(start_seconds=start, end_seconds=end))
            start = end
    return tuple(split)


def detect_speech_intervals_from_pcm(
    pcm_bytes: bytes,
    *,
    sample_rate: int = DEFAULT_VAD_SAMPLE_RATE,
    frame_ms: int = DEFAULT_VAD_FRAME_MS,
    aggressiveness: int = 2,
    min_speech_ms: int = 180,
    padding_ms: int = 90,
    merge_gap_ms: int = 180,
    max_interval_seconds: float = 8.0,
    rms_floor: float = 120.0,
    progress_callback: Optional[Callable[[float], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> tuple[SpeechInterval, ...]:
    """Detect local speech intervals from mono 16-bit PCM bytes.

    The returned intervals intentionally contain no recognized text. They are
    suitable for editable blank subtitle scaffolds only.
    """

    if sample_rate not in {8000, 16000, 32000, 48000}:
        raise ValueError("sample_rate must be one of WebRTC VAD's supported rates")
    if frame_ms not in {10, 20, 30}:
        raise ValueError("frame_ms must be 10, 20, or 30")

    try:
        import webrtcvad  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised when dependency missing
        raise RuntimeError(
            "webrtcvad-wheels==2.0.14 is required for local speech interval detection."
        ) from exc

    vad = webrtcvad.Vad(max(0, min(3, int(aggressiveness))))
    frame_size = _frame_bytes(sample_rate, frame_ms)
    if frame_size <= 0 or not pcm_bytes:
        return ()

    total_frames = len(pcm_bytes) // frame_size
    if total_frames <= 0:
        return ()

    min_speech_frames = max(1, int(round(min_speech_ms / frame_ms)))
    padding_seconds = max(0.0, padding_ms / 1000.0)
    raw_intervals: list[SpeechInterval] = []
    active_start_frame: Optional[int] = None
    last_speech_frame: Optional[int] = None

    for index in range(total_frames):
        if cancel_check and cancel_check():
            raise RuntimeError("speech_interval_detection_cancelled")
        frame = pcm_bytes[index * frame_size : (index + 1) * frame_size]
        is_speech = _frame_rms(frame) >= float(rms_floor) and vad.is_speech(frame, sample_rate)
        if is_speech:
            if active_start_frame is None:
                active_start_frame = index
            last_speech_frame = index
        elif active_start_frame is not None and last_speech_frame is not None:
            quiet_frames = index - last_speech_frame
            if quiet_frames * frame_ms >= merge_gap_ms:
                speech_frames = last_speech_frame - active_start_frame + 1
                if speech_frames >= min_speech_frames:
                    raw_intervals.append(
                        SpeechInterval(
                            start_seconds=max(
                                0.0,
                                active_start_frame * frame_ms / 1000.0 - padding_seconds,
                            ),
                            end_seconds=(last_speech_frame + 1) * frame_ms / 1000.0
                            + padding_seconds,
                        )
                    )
                active_start_frame = None
                last_speech_frame = None
        if progress_callback and (index % 50 == 0 or index == total_frames - 1):
            progress_callback((index + 1) / total_frames)

    if active_start_frame is not None and last_speech_frame is not None:
        speech_frames = last_speech_frame - active_start_frame + 1
        if speech_frames >= min_speech_frames:
            raw_intervals.append(
                SpeechInterval(
                    start_seconds=max(
                        0.0,
                        active_start_frame * frame_ms / 1000.0 - padding_seconds,
                    ),
                    end_seconds=(last_speech_frame + 1) * frame_ms / 1000.0 + padding_seconds,
                )
            )

    merged = _merge_intervals(
        raw_intervals,
        merge_gap_seconds=max(0.0, merge_gap_ms / 1000.0),
    )
    return _split_long_intervals(
        merged,
        max_interval_seconds=max(0.0, float(max_interval_seconds)),
    )


def pcm_bytes_from_media_file(
    media_path: str,
    *,
    sample_rate: int = DEFAULT_VAD_SAMPLE_RATE,
    ffmpeg_path: str = "ffmpeg",
    timeout_seconds: int = 600,
) -> bytes:
    """Convert a local media file to mono s16le PCM using FFmpeg stdout."""

    source = Path(media_path).expanduser()
    if not source.exists():
        raise FileNotFoundError("media file not found")

    ffmpeg = shutil.which(ffmpeg_path) if ffmpeg_path == "ffmpeg" else ffmpeg_path
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for speech interval detection.")

    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "pipe:1",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        raise RuntimeError("FFmpeg could not create PCM audio for speech interval detection.")
    return bytes(result.stdout or b"")


def detect_speech_intervals_for_media_file(
    media_path: str,
    *,
    sample_rate: int = DEFAULT_VAD_SAMPLE_RATE,
    frame_ms: int = DEFAULT_VAD_FRAME_MS,
    aggressiveness: int = 2,
    max_interval_seconds: float = 8.0,
    rms_floor: float = 120.0,
    progress_callback: Optional[Callable[[float], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> tuple[SpeechInterval, ...]:
    """Detect blank local speech intervals for a media file."""

    pcm = pcm_bytes_from_media_file(media_path, sample_rate=sample_rate)
    return detect_speech_intervals_from_pcm(
        pcm,
        sample_rate=sample_rate,
        frame_ms=frame_ms,
        aggressiveness=aggressiveness,
        max_interval_seconds=max_interval_seconds,
        rms_floor=rms_floor,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )
