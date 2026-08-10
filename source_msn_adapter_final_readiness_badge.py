
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

POSITIVE_COMPLETION_STATES = {"COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE", "COMPLETE", "PROMOTED_COMPLETE"}
BLOCKED_STATES = {"PROMOTION_BLOCKED", "BLOCKED", "FAILED", "FAIL"}
PENDING_STATES = {"RC_LOCKED_PENDING_LIVE_EVIDENCE", "READY_FOR_LIVE_EVIDENCE", "CONFIDENT_WITH_MANUAL_REVIEW", "INSUFFICIENT_EVIDENCE"}

@dataclass(frozen=True)
class BadgeSignal:
    name: str
    status: str
    path: str = ""
    detail: str = ""

@dataclass(frozen=True)
class FinalReadinessBadge:
    badge: str
    complete_allowed: bool
    positive_live_evidence_found: bool
    signal_count: int
    signals: list[BadgeSignal]
    notes: list[str]

def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _walk_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.json"))

def _string_values(obj: Any) -> Iterable[str]:
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _string_values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _string_values(value)
    elif isinstance(obj, str):
        yield obj

def _detect_signal(path: Path, data: dict[str, Any]) -> BadgeSignal | None:
    text_values = [v.strip() for v in _string_values(data) if v.strip()]
    upper_values = {v.upper() for v in text_values}
    joined = " ".join(sorted(upper_values))
    if any(state in upper_values or state in joined for state in POSITIVE_COMPLETION_STATES):
        return BadgeSignal("positive_live_completion", "PASS", str(path), "Positive completion state found")
    if any(state in upper_values or state in joined for state in BLOCKED_STATES):
        return BadgeSignal("blocked_or_failed", "FAIL", str(path), "Blocked/failure state found")
    if any(state in upper_values or state in joined for state in PENDING_STATES):
        return BadgeSignal("pending_live_evidence", "PARTIAL", str(path), "Pending/manual-review state found")
    if "LIVE" in joined and "EVIDENCE" in joined and ("TRUE" in joined or "PASS" in joined):
        return BadgeSignal("live_evidence_hint", "PARTIAL", str(path), "Live evidence wording found but no final completion state")
    return None

def build_final_readiness_badge(root: Path) -> FinalReadinessBadge:
    signals: list[BadgeSignal] = []
    for path in _walk_json_files(root):
        data = _read_json(path)
        if isinstance(data, dict):
            signal = _detect_signal(path, data)
            if signal:
                signals.append(signal)
    positive = any(s.name == "positive_live_completion" and s.status == "PASS" for s in signals)
    blocked = any(s.status == "FAIL" for s in signals)
    pending = any(s.status == "PARTIAL" for s in signals)
    notes = [
        "No-network self-tests are not enough to claim live MSN completion.",
        "The COMPLETE badge requires a positive manual/live evidence result.",
    ]
    if positive and not blocked:
        badge = "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
        complete_allowed = True
    elif blocked:
        badge = "PROMOTION_BLOCKED"
        complete_allowed = False
    elif pending or signals:
        badge = "RC_LOCKED_PENDING_LIVE_EVIDENCE"
        complete_allowed = False
    else:
        badge = "READY_FOR_LIVE_EVIDENCE"
        complete_allowed = False
        notes.append("No live-evidence or promotion reports were detected in the supplied folder.")
    return FinalReadinessBadge(badge, complete_allowed, positive, len(signals), signals, notes)

def write_badge_outputs(report: FinalReadinessBadge, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_READINESS_BADGE.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_READINESS_BADGE.md"
    csv_path = output_dir / "MSN_SOURCE_ADAPTER_FINAL_READINESS_BADGE.csv"
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# MSN Source Adapter Final Readiness Badge", "",
        f"Badge: `{report.badge}`",
        f"Complete allowed: `{str(report.complete_allowed).lower()}`",
        f"Positive live evidence found: `{str(report.positive_live_evidence_found).lower()}`",
        f"Signals: `{report.signal_count}`", "", "## Notes",
    ]
    lines += [f"- {note}" for note in report.notes]
    lines += ["", "## Signals"]
    if report.signals:
        for signal in report.signals:
            lines.append(f"- `{signal.status}` `{signal.name}` - {signal.detail} ({signal.path})")
    else:
        lines.append("- No live/promotion signals found.")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["name", "status", "path", "detail"])
        writer.writeheader()
        for signal in report.signals:
            writer.writerow(asdict(signal))
    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build conservative final readiness badge for MSN adapter outputs.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    report = build_final_readiness_badge(Path(args.root))
    paths = write_badge_outputs(report, Path(args.output_dir))
    print("MSN final readiness badge:", report.badge)
    print("JSON:", paths["json"])
    print("Markdown:", paths["markdown"])
    print("CSV:", paths["csv"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
