"""Tests for local WebRTC VAD speech interval helpers."""

from __future__ import annotations

import math
import struct

from speech_interval_vad import (
    DEFAULT_VAD_FRAME_MS,
    DEFAULT_VAD_SAMPLE_RATE,
    SpeechInterval,
    _merge_intervals,
    _split_long_intervals,
    detect_speech_intervals_from_pcm,
)


def _tone_pcm(seconds: float, *, amplitude: int = 12000) -> bytes:
    sample_count = int(DEFAULT_VAD_SAMPLE_RATE * seconds)
    values = []
    for index in range(sample_count):
        sample = int(amplitude * math.sin(2.0 * math.pi * 220.0 * index / DEFAULT_VAD_SAMPLE_RATE))
        values.append(struct.pack("<h", sample))
    return b"".join(values)


def _silence_pcm(seconds: float) -> bytes:
    return b"\x00\x00" * int(DEFAULT_VAD_SAMPLE_RATE * seconds)


def test_merge_intervals_is_deterministic() -> None:
    intervals = (
        SpeechInterval(2.0, 3.0),
        SpeechInterval(0.0, 1.0),
        SpeechInterval(1.1, 1.6),
    )
    merged = _merge_intervals(intervals, merge_gap_seconds=0.2)
    assert merged == (
        SpeechInterval(0.0, 1.6),
        SpeechInterval(2.0, 3.0),
    )


def test_detect_speech_intervals_from_pcm_returns_blank_timing_scaffold() -> None:
    pcm = _silence_pcm(0.3) + _tone_pcm(0.8) + _silence_pcm(0.4)
    intervals = detect_speech_intervals_from_pcm(
        pcm,
        frame_ms=DEFAULT_VAD_FRAME_MS,
        aggressiveness=1,
        min_speech_ms=90,
    )
    assert intervals
    assert intervals[0].start_seconds >= 0.0
    assert intervals[0].end_seconds > intervals[0].start_seconds


def test_detect_speech_intervals_can_be_cancelled() -> None:
    calls = {"count": 0}

    def cancel_check() -> bool:
        calls["count"] += 1
        return calls["count"] > 3

    pcm = _tone_pcm(2.0)
    try:
        detect_speech_intervals_from_pcm(pcm, cancel_check=cancel_check)
    except RuntimeError as error:
        assert str(error) == "speech_interval_detection_cancelled"
    else:
        raise AssertionError("expected cancellation")


def test_split_long_intervals_bounds_fast_vad_blocks() -> None:
    split = _split_long_intervals(
        (SpeechInterval(0.0, 20.5),),
        max_interval_seconds=8.0,
    )
    assert split == (
        SpeechInterval(0.0, 8.0),
        SpeechInterval(8.0, 16.0),
        SpeechInterval(16.0, 20.5),
    )


def test_high_rms_floor_filters_low_energy_vad_frames() -> None:
    pcm = _tone_pcm(0.8, amplitude=800)
    intervals = detect_speech_intervals_from_pcm(
        pcm,
        frame_ms=DEFAULT_VAD_FRAME_MS,
        aggressiveness=1,
        min_speech_ms=90,
        rms_floor=100000.0,
    )
    assert intervals == ()


if __name__ == "__main__":
    test_merge_intervals_is_deterministic()
    test_detect_speech_intervals_from_pcm_returns_blank_timing_scaffold()
    test_detect_speech_intervals_can_be_cancelled()
    test_split_long_intervals_bounds_fast_vad_blocks()
    test_high_rms_floor_filters_low_energy_vad_frames()
    print("speech_interval_vad_test.py passed")
