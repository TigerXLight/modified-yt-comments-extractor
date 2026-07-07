from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


PROJECT_DIR = Path(__file__).resolve().parent
WHISPERCPP_ROOT = Path(os.environ.get("WHISPERCPP_ROOT", r"C:\whisper.cpp"))
WHISPERCPP_CLI = Path(
    os.environ.get(
        "WHISPERCPP_CLI",
        str(WHISPERCPP_ROOT / "build-vulkan" / "bin" / "Release" / "whisper-cli.exe"),
    )
)
TIMEOUT_SECONDS = int(os.environ.get("WHISPERCPP_MATRIX_TIMEOUT", "90"))
PROBE_SECONDS = float(os.environ.get("WHISPERCPP_MATRIX_PROBE_SECONDS", "30"))
OUT_DIR = PROJECT_DIR / "whispercpp_matrix_out"
OUT_DIR.mkdir(exist_ok=True)

TERMS = "Kingman, ZoneX, Freckelston, Shadowsmith, Nicolas Cage, Caltheris, Nyxara"

PROMPTS: Dict[str, str] = {
    "unprompted": "",
    "short_terms": f"Names and terms that may appear: {TERMS}.",
    "phrase_prompt": (
        f"Names and terms that may appear: {TERMS}. "
        "Likely phrases: I've cleared the Nicolas Cage event. "
        "What are you, like, trying to insinuate? "
        "We need more Caltheris content."
    ),
}

SEGMENT_FLAGS: Dict[str, List[str]] = {
    "base": [],
    "max_len_80": ["--max-len", "80"],
    "max_len_80_split_words": ["--max-len", "80", "--split-on-word"],
    "no_context": ["--no-context"],
}

MODELS = ["large-v3", "large-v3-turbo"]


def find_model(model_name: str) -> Optional[Path]:
    candidates = [
        WHISPERCPP_ROOT / f"ggml-{model_name}.bin",
        WHISPERCPP_ROOT / "models" / f"ggml-{model_name}.bin",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


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


def reference_accuracy(reference: str, candidate: str) -> float:
    ref_words = normalize_text(reference)
    cand_words = normalize_text(candidate)

    if not ref_words:
        return 0.0

    distance = levenshtein(ref_words, cand_words)
    return max(0.0, 100.0 * (1.0 - distance / max(1, len(ref_words))))


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
            left = line.split("-->", 1)[0].strip()
            start_seconds = timestamp_to_seconds(left)
            include_current_block = (
                max_seconds is None
                or start_seconds is None
                or start_seconds < max_seconds
            )
            continue

        if not include_current_block:
            continue

        line = re.sub(r"^\[[^\]]+\]\s*", "", line)
        pieces.append(line)

    return " ".join(pieces)


def prepare_probe_audio(input_path: Path) -> Path:
    if input_path.suffix.lower() == ".wav":
        return input_path

    probe_path = OUT_DIR / f"matrix_probe_{int(PROBE_SECONDS)}s.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-t",
        str(PROBE_SECONDS),
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(probe_path),
    ]

    print("Preparing 30s probe WAV...")
    subprocess.run(cmd, check=True)

    return probe_path


def default_input_path() -> Optional[Path]:
    local_probe = PROJECT_DIR / "whisperx_probe_30s.wav"

    if local_probe.exists():
        return local_probe

    common_short = Path(
        r"T:\References\to go\Media\Sexual offences\sexual harrashment\Indirect\June 2026\YouTube\28 Jun - Frecklston - White\short\short.mp4"
    )

    if common_short.exists():
        return common_short

    return None


def run_case(
    case_name: str,
    model_path: Path,
    wav_path: Path,
    prompt: str,
    flags: List[str],
    reference_text: str,
) -> Dict[str, object]:
    output_base = OUT_DIR / case_name

    for suffix in [".txt", ".srt", ".json", ".vtt"]:
        try:
            output_base.with_suffix(suffix).unlink(missing_ok=True)
        except Exception:
            pass

    cmd = [
        str(WHISPERCPP_CLI),
        "-m",
        str(model_path),
        "-f",
        str(wav_path),
        "-l",
        "en",
        "-otxt",
        "-osrt",
        "-of",
        str(output_base),
    ]

    if prompt:
        cmd += ["--prompt", prompt]

    cmd += flags

    started = time.perf_counter()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(WHISPERCPP_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
        )
        elapsed = time.perf_counter() - started
    except subprocess.TimeoutExpired:
        return {
            "case": case_name,
            "ok": False,
            "elapsed": TIMEOUT_SECONDS,
            "accuracy": 0.0,
            "error": f"TIMEOUT after {TIMEOUT_SECONDS}s",
            "text": "",
        }

    txt_path = output_base.with_suffix(".txt")

    if txt_path.exists():
        text = txt_path.read_text(encoding="utf-8", errors="replace").strip()
    else:
        text = (result.stdout or "").strip()

    acc = reference_accuracy(reference_text, text) if reference_text else 0.0

    return {
        "case": case_name,
        "ok": result.returncode == 0,
        "elapsed": elapsed,
        "accuracy": acc,
        "error": (result.stderr or result.stdout or "").strip()[-1000:] if result.returncode != 0 else "",
        "text": text,
    }


def main() -> int:
    if not WHISPERCPP_CLI.exists():
        print(f"ERROR: whisper-cli not found: {WHISPERCPP_CLI}")
        return 1

    if len(sys.argv) >= 2:
        input_path = Path(sys.argv[1])
    else:
        input_path = default_input_path()

    if not input_path or not input_path.exists():
        print("ERROR: No input found.")
        print('Run with: python RUN_WHISPERCPP_MATRIX.py "path\\to\\short.mp4" short_eng.txt')
        return 1

    if len(sys.argv) >= 3:
        reference_path = Path(sys.argv[2])
    else:
        reference_path = PROJECT_DIR / "short_eng.txt"

    reference_text = read_reference(reference_path, max_seconds=PROBE_SECONDS) if reference_path.exists() else ""

    if not reference_text:
        print("WARNING: No reference transcript found, so accuracy will be 0.00.")

    wav_path = prepare_probe_audio(input_path)

    model_paths: Dict[str, Path] = {}

    for model_name in MODELS:
        model_path = find_model(model_name)

        if model_path:
            model_paths[model_name] = model_path
        else:
            print(f"SKIP: missing model {model_name}. Expected ggml-{model_name}.bin in C:\\whisper.cpp or C:\\whisper.cpp\\models")

    if not model_paths:
        print("ERROR: No whisper.cpp models found.")
        return 1

    results: List[Dict[str, object]] = []

    for model_name, model_path in model_paths.items():
        for prompt_name, prompt in PROMPTS.items():
            for segment_name, flags in SEGMENT_FLAGS.items():
                case_name = f"{model_name}__{prompt_name}__{segment_name}".replace(" ", "_")
                print(f"RUN {case_name}")
                result = run_case(case_name, model_path, wav_path, prompt, flags, reference_text)
                results.append(result)

                status = "OK" if result["ok"] else "FAIL"
                print(
                    f"  {status} accuracy={result['accuracy']:.2f}% "
                    f"elapsed={result['elapsed']:.2f}s"
                )

    results_sorted = sorted(
        results,
        key=lambda r: (float(r["accuracy"]), -float(r["elapsed"])),
        reverse=True,
    )

    summary_lines = []
    summary_lines.append("WHISPER.CPP MATRIX SUMMARY")
    summary_lines.append("=" * 80)
    summary_lines.append(f"Input: {input_path}")
    summary_lines.append(f"Probe WAV: {wav_path}")
    summary_lines.append(f"Reference: {reference_path if reference_path.exists() else 'NONE'}")
    summary_lines.append(f"Timeout per case: {TIMEOUT_SECONDS}s")
    summary_lines.append(f"Reference scoring window: first {PROBE_SECONDS:g}s")
    summary_lines.append("")

    for idx, result in enumerate(results_sorted, start=1):
        summary_lines.append(
            f"{idx:02d}. {result['case']} | "
            f"ok={result['ok']} | "
            f"accuracy={result['accuracy']:.2f}% | "
            f"elapsed={result['elapsed']:.2f}s"
        )

        if result["error"]:
            summary_lines.append(f"    error: {result['error']}")

        preview = " ".join(str(result["text"]).split())[:500]
        summary_lines.append(f"    transcript: {preview}")
        summary_lines.append("")

    summary_path = PROJECT_DIR / "WHISPERCPP_MATRIX_SUMMARY.txt"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")

    print("")
    print("\n".join(summary_lines[:40]))
    print("")
    print(f"Wrote: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())