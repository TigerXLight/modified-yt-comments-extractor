from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from asr_runtime_paths import add_ffmpeg7_shared_dll_directory


add_ffmpeg7_shared_dll_directory()


PROJECT_DIR = Path(__file__).resolve().parent
PROVIDER = "DmlExecutionProvider"
PROBE_SECONDS = 30
PROBE_WAV = PROJECT_DIR / "directml_probe_30s.wav"
SUMMARY_PATH = PROJECT_DIR / "DIRECTML_WHISPER_MATRIX_SUMMARY.txt"

DEFAULT_MEDIA_PATH = Path(
    r"T:\References\to go\Media\Sexual offences\sexual harrashment\Indirect\June 2026\YouTube\28 Jun - Frecklston - White\short\short.mp4"
)
DEFAULT_REFERENCE_PATH = Path(
    r"T:\References\to go\Media\Sexual offences\sexual harrashment\Indirect\June 2026\YouTube\28 Jun - Frecklston - White\short\short_eng.txt"
)

MODELS: List[Dict[str, str]] = [
    {
        "model_id": "openai/whisper-base.en",
        "cache_dir": "directml_whisper_base_en_onnx",
    },
    {
        "model_id": "openai/whisper-small.en",
        "cache_dir": "directml_whisper_small_en_onnx",
    },
]


def log(message: str = "") -> None:
    print(message, flush=True)


def normalize_text(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\d+:\d+(?::\d+)?(?:\.\d+)?", " ", text)
    text = re.sub(r"[^a-z0-9']+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.split()


def levenshtein(a: List[str], b: List[str]) -> int:
    if not a:
        return len(b)

    if not b:
        return len(a)

    prev = list(range(len(b) + 1))

    for i, aw in enumerate(a, start=1):
        cur = [i]

        for j, bw in enumerate(b, start=1):
            cur.append(
                min(
                    prev[j] + 1,
                    cur[j - 1] + 1,
                    prev[j - 1] + (0 if aw == bw else 1),
                )
            )

        prev = cur

    return prev[-1]


def word_error_rate(reference: str, candidate: str) -> float:
    ref_words = normalize_text(reference)
    cand_words = normalize_text(candidate)

    if not ref_words:
        return 1.0

    return levenshtein(ref_words, cand_words) / max(1, len(ref_words))


def reference_accuracy(reference: str, candidate: str) -> float:
    return max(0.0, 100.0 * (1.0 - word_error_rate(reference, candidate)))


def timestamp_to_seconds(value: str) -> Optional[float]:
    value = value.strip().replace(",", ".")
    parts = value.split(":")

    try:
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds

        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
    except ValueError:
        return None

    return None


def read_reference(path: Path, max_seconds: Optional[float] = None) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    pieces = []
    include_current_block = True

    for line in raw.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.isdigit():
            continue

        if "-->" in line:
            left, right = line.split("-->", 1)
            start_seconds = timestamp_to_seconds(left)
            end_seconds = timestamp_to_seconds(right.strip().split()[0])
            # Keep the 30s scorer strict by skipping subtitle fragments that
            # cross the probe boundary.
            include_current_block = (
                max_seconds is None
                or start_seconds is None
                or end_seconds is None
                or (start_seconds < max_seconds and end_seconds <= max_seconds)
            )
            continue

        if not include_current_block:
            continue

        line = re.sub(r"^\[[^\]]+\]\s*", "", line)
        pieces.append(line)

    return " ".join(pieces)


def ensure_probe_wav(media_path: Path) -> Path:
    if PROBE_WAV.exists() and PROBE_WAV.stat().st_size > 0:
        log(f"Reusing probe WAV: {PROBE_WAV}")
        return PROBE_WAV

    ffmpeg = shutil.which("ffmpeg")

    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to create directml_probe_30s.wav.")

    if not media_path.exists():
        raise FileNotFoundError(f"Probe media not found: {media_path}")

    log(f"Creating {PROBE_SECONDS}s probe WAV: {PROBE_WAV}")

    command = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-t",
        str(PROBE_SECONDS),
        "-i",
        str(media_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(PROBE_WAV),
    ]

    subprocess.run(command, check=True)
    return PROBE_WAV


def load_wav_mono_16k(path: Path):
    import wave

    import numpy as np

    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frame_count = wav.getnframes()
        raw = wav.readframes(frame_count)

    if sample_rate != 16000:
        raise ValueError(f"Expected 16000 Hz WAV, got {sample_rate} Hz: {path}")

    if channels != 1:
        raise ValueError(f"Expected mono WAV, got {channels} channels: {path}")

    if sample_width == 2:
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sample_width == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported WAV sample width {sample_width}: {path}")

    return audio


def cache_has_onnx_files(cache_dir: Path) -> bool:
    return cache_dir.exists() and any(cache_dir.rglob("*.onnx"))


def load_or_export_model(model_id: str, cache_dir: Path):
    from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
    from transformers import AutoProcessor

    if cache_has_onnx_files(cache_dir):
        log(f"Loading cached ONNX model from: {cache_dir}")
        processor = AutoProcessor.from_pretrained(cache_dir)
        model = ORTModelForSpeechSeq2Seq.from_pretrained(
            cache_dir,
            provider=PROVIDER,
        )
        return processor, model

    log(f"Exporting ONNX model for {model_id} into: {cache_dir}")
    processor = AutoProcessor.from_pretrained(model_id)
    model = ORTModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        export=True,
        provider=PROVIDER,
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    processor.save_pretrained(cache_dir)
    model.save_pretrained(cache_dir)
    return processor, model


def transcribe_with_directml(model_id: str, cache_dir: Path, audio) -> Dict[str, object]:
    started = time.perf_counter()
    processor, model = load_or_export_model(model_id, cache_dir)

    log(f"Preparing input features for {model_id}")
    inputs = processor(
        audio,
        sampling_rate=16000,
        return_tensors="pt",
    )

    generate_kwargs = {}

    try:
        forced_decoder_ids = processor.get_decoder_prompt_ids(
            language="en",
            task="transcribe",
        )

        if forced_decoder_ids:
            generate_kwargs["forced_decoder_ids"] = forced_decoder_ids
    except Exception:
        pass

    log(f"Generating transcript with {PROVIDER}: {model_id}")
    generated_ids = model.generate(
        input_features=inputs.input_features,
        **generate_kwargs,
    )
    transcript = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True,
    )[0].strip()

    elapsed = time.perf_counter() - started

    return {
        "model_id": model_id,
        "cache_dir": str(cache_dir),
        "elapsed": elapsed,
        "transcript": transcript,
    }


def run_case(model_config: Dict[str, str], audio, reference_text: str) -> Dict[str, object]:
    model_id = model_config["model_id"]
    cache_dir = PROJECT_DIR / model_config["cache_dir"]

    log("")
    log(f"RUN {model_id}")

    try:
        result = transcribe_with_directml(model_id, cache_dir, audio)
        wer = word_error_rate(reference_text, str(result["transcript"]))
        accuracy = reference_accuracy(reference_text, str(result["transcript"]))
        result.update(
            {
                "ok": True,
                "wer": wer,
                "accuracy": accuracy,
                "error": "",
            }
        )
        log(f"OK {model_id}: accuracy={accuracy:.2f}% WER={wer * 100.0:.2f}% elapsed={result['elapsed']:.2f}s")
        return result
    except Exception as exc:
        log(f"FAIL {model_id}: {exc}")
        return {
            "model_id": model_id,
            "cache_dir": str(cache_dir),
            "ok": False,
            "elapsed": 0.0,
            "wer": 1.0,
            "accuracy": 0.0,
            "transcript": "",
            "error": str(exc),
        }


def build_summary(
    media_path: Path,
    reference_path: Path,
    reference_text: str,
    results: List[Dict[str, object]],
) -> str:
    lines = []
    lines.append("DIRECTML WHISPER MATRIX SUMMARY")
    lines.append("=" * 80)
    lines.append(f"Provider: {PROVIDER}")
    lines.append(f"Media: {media_path}")
    lines.append(f"Probe WAV: {PROBE_WAV}")
    lines.append(f"Reference: {reference_path}")
    lines.append(f"Reference scoring window: first {PROBE_SECONDS}s")
    lines.append(f"Reference words: {len(normalize_text(reference_text))}")
    lines.append("")

    results_sorted = sorted(
        results,
        key=lambda item: (float(item["accuracy"]), -float(item["elapsed"])),
        reverse=True,
    )

    for idx, result in enumerate(results_sorted, start=1):
        lines.append(
            f"{idx:02d}. {result['model_id']} | "
            f"ok={result['ok']} | "
            f"accuracy={float(result['accuracy']):.2f}% | "
            f"WER={float(result['wer']) * 100.0:.2f}% | "
            f"elapsed={float(result['elapsed']):.2f}s | "
            f"cache={result['cache_dir']}"
        )

        if result["error"]:
            lines.append(f"    error: {result['error']}")

        preview = " ".join(str(result["transcript"]).split())[:800]
        lines.append(f"    transcript: {preview}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    import sys

    media_path = Path(sys.argv[1]) if len(sys.argv) >= 2 else DEFAULT_MEDIA_PATH
    reference_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else DEFAULT_REFERENCE_PATH

    log("DirectML Whisper matrix runner")
    log(f"Provider: {PROVIDER}")
    log("Models: openai/whisper-base.en, openai/whisper-small.en")

    if not reference_path.exists():
        log(f"ERROR: Reference transcript not found: {reference_path}")
        return 1

    reference_text = read_reference(reference_path, max_seconds=PROBE_SECONDS)

    if not reference_text:
        log(f"ERROR: Reference transcript has no text in first {PROBE_SECONDS}s: {reference_path}")
        return 1

    try:
        import onnxruntime as ort

        providers = list(ort.get_available_providers())
    except Exception as exc:
        log(f"ERROR: Could not inspect ONNX Runtime providers: {exc}")
        return 1

    log(f"Available ONNX Runtime providers: {providers}")

    if PROVIDER not in providers:
        log(f"ERROR: {PROVIDER} is not available.")
        return 1

    wav_path = ensure_probe_wav(media_path)
    log(f"Loading probe audio: {wav_path}")
    audio = load_wav_mono_16k(wav_path)
    log(f"Audio samples: {len(audio)}")

    results = []

    for model_config in MODELS:
        results.append(run_case(model_config, audio, reference_text))

    summary = build_summary(
        media_path=media_path,
        reference_path=reference_path,
        reference_text=reference_text,
        results=results,
    )
    SUMMARY_PATH.write_text(summary + "\n", encoding="utf-8")

    log("")
    log(summary)
    log("")
    log(f"Wrote: {SUMMARY_PATH}")

    return 0 if any(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
