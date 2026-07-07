from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_REFERENCE_PATH = Path(
    r"T:\References\to go\Media\Sexual offences\sexual harrashment\Indirect\June 2026\YouTube\28 Jun - Frecklston - White\short\short_eng.txt"
)
DEFAULT_SECONDS = 30.0
SUMMARY_PATH = PROJECT_DIR / "TRANSCRIPT_REFERENCE_SCORE_SUMMARY.txt"

IMPORTANT_TERMS = [
    "Kingman",
    "ZoneX",
    "Shadowsmith",
    "Nicolas Cage",
    "Freckelston",
    "Caltheris",
    "Nyxara",
]


def normalize_text(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"\[[^\]]+\]", " ", text)
    text = re.sub(r"\d+:\d+(?::\d+)?(?:\.\d+)?", " ", text)
    text = re.sub(r"[^a-z0-9']+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.split()


def normalized_string(text: str) -> str:
    return " ".join(normalize_text(text))


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


def parse_timing_line(line: str) -> Optional[tuple[Optional[float], Optional[float]]]:
    if "-->" in line:
        left, right = line.split("-->", 1)
        right_timestamp = right.strip().split()[0] if right.strip() else ""
        return timestamp_to_seconds(left.strip()), timestamp_to_seconds(right_timestamp)

    match = re.match(
        r"^\s*\[?(\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d+)?)\]?\s*(.*)$",
        line,
    )

    if match and match.group(2).strip():
        return timestamp_to_seconds(match.group(1)), None

    return None


def clean_transcript_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^\s*WEBVTT\s*$", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\s*NOTE\b.*$", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^\[[^\]]+\]\s*", "", line)
    line = re.sub(
        r"^\s*\[?\d{1,2}:\d{2}(?::\d{2})?(?:[\.,]\d+)?\]?\s*[-:]*\s*",
        "",
        line,
    )
    return line.strip()


def read_transcript_text(path: Path, max_seconds: Optional[float] = None) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    pieces = []
    include_current_block = True

    for line in raw.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.isdigit():
            continue

        if line.upper() == "WEBVTT" or line.upper().startswith("NOTE"):
            continue

        timing = parse_timing_line(line)

        if timing:
            start_seconds, end_seconds = timing

            # Keep the scoring window strict by skipping subtitle fragments that
            # cross the boundary instead of pulling in after-boundary words.
            if max_seconds is None or start_seconds is None:
                include_current_block = True
            elif end_seconds is None:
                include_current_block = start_seconds < max_seconds
            else:
                include_current_block = start_seconds < max_seconds and end_seconds <= max_seconds

            cleaned_line = clean_transcript_line(line)

            if cleaned_line and "-->" not in line and include_current_block:
                pieces.append(cleaned_line)

            continue

        if not include_current_block:
            continue

        cleaned_line = clean_transcript_line(line)

        if cleaned_line:
            pieces.append(cleaned_line)

    return " ".join(pieces)


def term_checks(candidate_text: str) -> List[Dict[str, str]]:
    candidate_normalized = f" {normalized_string(candidate_text)} "
    checks = []

    for term in IMPORTANT_TERMS:
        term_normalized = f" {normalized_string(term)} "
        checks.append(
            {
                "term": term,
                "status": "FOUND" if term_normalized in candidate_normalized else "MISSING",
            }
        )

    return checks


def score_candidate(
    reference_text: str,
    candidate_path: Path,
    max_seconds: Optional[float],
) -> Dict[str, object]:
    candidate_text = read_transcript_text(candidate_path, max_seconds=max_seconds)
    reference_words = normalize_text(reference_text)
    candidate_words = normalize_text(candidate_text)
    wer = word_error_rate(reference_text, candidate_text)
    accuracy = reference_accuracy(reference_text, candidate_text)
    preview = " ".join(candidate_text.split())[:800]

    return {
        "path": str(candidate_path),
        "reference_words": len(reference_words),
        "candidate_words": len(candidate_words),
        "wer": wer,
        "accuracy": accuracy,
        "preview": preview,
        "term_checks": term_checks(candidate_text),
    }


def format_result(result: Dict[str, object]) -> List[str]:
    lines = []
    lines.append(f"Candidate: {result['path']}")
    lines.append(f"Reference words: {result['reference_words']}")
    lines.append(f"Candidate words: {result['candidate_words']}")
    lines.append(f"WER: {float(result['wer']) * 100.0:.2f}%")
    lines.append(f"Reference accuracy: {float(result['accuracy']):.2f}%")
    lines.append("Important terms:")

    for check in result["term_checks"]:
        lines.append(f"- {check['term']}: {check['status']}")

    lines.append(f"Preview: {result['preview']}")
    return lines


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score candidate transcripts against a strict reference transcript window.",
    )
    parser.add_argument(
        "--reference",
        default=str(DEFAULT_REFERENCE_PATH),
        help="Reference transcript path.",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=DEFAULT_SECONDS,
        help="Strict scoring window in seconds.",
    )
    parser.add_argument(
        "candidates",
        nargs="+",
        help="Candidate transcript files to score.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    reference_path = Path(args.reference)
    max_seconds = float(args.seconds)

    if not reference_path.exists():
        print(f"ERROR: Reference transcript not found: {reference_path}")
        return 1

    reference_text = read_transcript_text(reference_path, max_seconds=max_seconds)

    if not reference_text:
        print(f"ERROR: Reference transcript has no text in first {max_seconds:g}s: {reference_path}")
        return 1

    all_lines = []
    all_lines.append("TRANSCRIPT REFERENCE SCORE SUMMARY")
    all_lines.append("=" * 80)
    all_lines.append(f"Reference: {reference_path}")
    all_lines.append(f"Strict scoring window: first {max_seconds:g}s")
    all_lines.append(f"Reference words: {len(normalize_text(reference_text))}")
    all_lines.append("")

    exit_code = 0

    for candidate_arg in args.candidates:
        candidate_path = Path(candidate_arg)

        if not candidate_path.exists():
            exit_code = 1
            lines = [
                f"Candidate: {candidate_path}",
                "ERROR: candidate transcript not found.",
            ]
        else:
            result = score_candidate(reference_text, candidate_path, max_seconds=max_seconds)
            lines = format_result(result)

        for line in lines:
            print(line)

        print("")
        all_lines.extend(lines)
        all_lines.append("")

    SUMMARY_PATH.write_text("\n".join(all_lines), encoding="utf-8")
    print(f"Wrote: {SUMMARY_PATH}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
