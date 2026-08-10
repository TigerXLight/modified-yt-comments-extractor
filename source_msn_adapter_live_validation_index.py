from __future__ import annotations

import argparse
import csv
import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

STATUS_READY_FOR_LIVE_EVIDENCE = "READY_FOR_LIVE_EVIDENCE"
STATUS_LIVE_EVIDENCE_PRESENT = "LIVE_EVIDENCE_PRESENT"
STATUS_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE = "COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE"
STATUS_PROMOTION_BLOCKED = "PROMOTION_BLOCKED"
STATUS_INSUFFICIENT_OUTPUT = "INSUFFICIENT_OUTPUT"

POSITIVE_WORDS = {"pass", "passed", "yes", "true", "ok", "complete", "verified", "positive", "success"}
NEGATIVE_WORDS = {"fail", "failed", "no", "false", "blocked", "missing", "partial", "unknown"}


@dataclass(frozen=True)
class ValidationCheck:
    key: str
    label: str
    status: str
    evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class LiveValidationIndex:
    input_root: str
    output_dir: str
    status: str
    required_positive_live_keys: List[str]
    checks: List[ValidationCheck]
    manual_live_evidence_files: List[str]
    positive_live_evidence: bool
    blocking_reasons: List[str]
    next_actions: List[str]


def _as_dict(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    return obj


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_read_text(path: Path, limit: int = 120_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _iter_files(root: Path, max_files: int = 8000) -> List[Path]:
    if not root.exists():
        return []
    files: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file():
            files.append(p)
            if len(files) >= max_files:
                break
    return files


def _match_files(files: Iterable[Path], *needles: str, suffixes: Optional[Iterable[str]] = None) -> List[Path]:
    lowered = [n.lower() for n in needles if n]
    suffix_set = {s.lower() for s in suffixes} if suffixes else None
    out: List[Path] = []
    for p in files:
        name = p.name.lower()
        path_text = str(p).lower()
        if suffix_set and p.suffix.lower() not in suffix_set:
            continue
        if all(n in path_text or n in name for n in lowered):
            out.append(p)
    return out


def _rel(root: Path, paths: Iterable[Path]) -> List[str]:
    result: List[str] = []
    for p in paths:
        try:
            result.append(str(p.relative_to(root)))
        except Exception:
            result.append(str(p))
    return sorted(result)


def _truthy(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in POSITIVE_WORDS:
            return True
        if v in NEGATIVE_WORDS:
            return False
    return None


def _deep_find_key(data: Any, wanted: str) -> List[Any]:
    found: List[Any] = []
    if isinstance(data, dict):
        for k, v in data.items():
            if str(k).lower() == wanted.lower():
                found.append(v)
            found.extend(_deep_find_key(v, wanted))
    elif isinstance(data, list):
        for item in data:
            found.extend(_deep_find_key(item, wanted))
    return found


def _read_manual_live_evidence(files: Iterable[Path]) -> Dict[str, Any]:
    combined: Dict[str, Any] = {}
    for p in files:
        if p.suffix.lower() == ".json":
            data = _safe_read_json(p)
            if isinstance(data, dict):
                combined[p.name] = data
        elif p.suffix.lower() in {".md", ".txt"}:
            text = _safe_read_text(p)
            combined[p.name] = {"text": text}
    return combined


def _has_positive_manual_live_evidence(manual_data: Dict[str, Any], required_keys: List[str]) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    if not manual_data:
        return False, ["No manual/live evidence file found."]

    flattened_text = json.dumps(manual_data, ensure_ascii=False).lower()
    if "failed" in flattened_text or "promotion_blocked" in flattened_text:
        reasons.append("Manual/live evidence contains an explicit failure/block marker.")

    missing: List[str] = []
    for key in required_keys:
        values: List[Any] = []
        for data in manual_data.values():
            values.extend(_deep_find_key(data, key))
        truths = [_truthy(v) for v in values]
        if not values:
            if key.replace("_", " ") in flattened_text and any(w in flattened_text for w in POSITIVE_WORDS):
                continue
            missing.append(key)
        elif not any(t is True for t in truths):
            missing.append(key)
    if missing:
        reasons.append("Required positive live keys missing or not positive: " + ", ".join(missing))

    explicit_overall = []
    for data in manual_data.values():
        for key in ("overall_status", "final_status", "status", "promotion_status"):
            explicit_overall.extend(_deep_find_key(data, key))
    if explicit_overall:
        if any(str(v).strip().upper() == STATUS_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE for v in explicit_overall):
            pass
        elif not any(_truthy(v) is True for v in explicit_overall):
            reasons.append("No explicit positive overall manual/live status found.")

    return not reasons, reasons


def build_live_validation_index(input_root: Path, output_dir: Optional[Path] = None) -> LiveValidationIndex:
    root = input_root.resolve()
    out = (output_dir or (root / "reports")).resolve()
    files = _iter_files(root)

    groups = {
        "article": _match_files(files, "article", suffixes={".html", ".md", ".json", ".txt"}),
        "comments": _match_files(files, "comment", suffixes={".json", ".html", ".md", ".txt", ".csv"}),
        "profiles": _match_files(files, "profile", suffixes={".json", ".html", ".md", ".txt", ".csv"}),
        "offline_viewer": _match_files(files, "viewer", suffixes={".html", ".cmd", ".md", ".json"}) + _match_files(files, "rendered-page", suffixes={".html"}),
        "warc": _match_files(files, "warc", suffixes={".warc", ".gz", ".json", ".md"}),
        "wacz": _match_files(files, "wacz", suffixes={".wacz", ".json", ".md"}),
        "media": _match_files(files, "media", suffixes={".json", ".csv", ".md"}) + _match_files(files, "image", suffixes={".json", ".csv", ".md", ".jpg", ".jpeg", ".png", ".webp"}) + _match_files(files, "video", suffixes={".json", ".csv", ".md", ".mp4", ".m3u8", ".mpd"}),
        "source_chain": _match_files(files, "source", "chain", suffixes={".json", ".md", ".csv"}) + _match_files(files, "provenance", suffixes={".json", ".md", ".csv"}),
        "final_reports": _match_files(files, "final", "validation", suffixes={".json", ".md", ".csv"}) + _match_files(files, "acceptance", suffixes={".json", ".md", ".csv"}) + _match_files(files, "certification", suffixes={".json", ".md", ".csv"}),
    }

    manual_live = []
    for p in files:
        lower = str(p).lower()
        if ("live" in lower or "manual" in lower) and ("evidence" in lower or "acceptance" in lower or "validation" in lower) and p.suffix.lower() in {".json", ".md", ".txt"}:
            manual_live.append(p)

    required_live_keys = [
        "article_extracted",
        "comments_exported",
        "profiles_exported",
        "offline_viewer_verified",
        "archive_verified",
        "media_reviewed",
        "source_chain_reviewed",
    ]
    manual_data = _read_manual_live_evidence(manual_live)
    positive_live, live_reasons = _has_positive_manual_live_evidence(manual_data, required_live_keys)

    checks: List[ValidationCheck] = []
    for key, label in [
        ("article", "Article extraction artifacts"),
        ("comments", "Comments export artifacts"),
        ("profiles", "Profile export artifacts"),
        ("offline_viewer", "Offline viewer/rendered page artifacts"),
        ("warc", "WARC/archive artifacts"),
        ("wacz", "WACZ/ReplayWeb artifacts"),
        ("media", "Media/image/video artifacts"),
        ("source_chain", "Source-chain/provenance artifacts"),
        ("final_reports", "Final reports / acceptance / certification artifacts"),
    ]:
        evidence = _rel(root, groups.get(key, []))[:25]
        checks.append(ValidationCheck(
            key=key,
            label=label,
            status="PASS" if evidence else "MISSING",
            evidence=evidence,
            notes=[] if evidence else ["No matching artifacts found in scanned output folder."],
        ))

    manual_evidence_rel = _rel(root, manual_live)[:50]
    checks.append(ValidationCheck(
        key="manual_live_evidence",
        label="Manual/live evidence file",
        status="PASS" if positive_live else ("PRESENT_BUT_NOT_POSITIVE" if manual_live else "MISSING"),
        evidence=manual_evidence_rel,
        notes=live_reasons,
    ))

    missing_core = [c.key for c in checks if c.key not in {"manual_live_evidence", "wacz"} and c.status == "MISSING"]
    blocking: List[str] = []
    if missing_core:
        blocking.append("Missing core artifacts: " + ", ".join(missing_core))
    if not positive_live:
        blocking.extend(live_reasons)

    if positive_live and not missing_core:
        status = STATUS_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE
    elif missing_core and not files:
        status = STATUS_INSUFFICIENT_OUTPUT
    elif manual_live and not positive_live:
        status = STATUS_PROMOTION_BLOCKED
    else:
        status = STATUS_READY_FOR_LIVE_EVIDENCE

    next_actions = []
    if status == STATUS_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE:
        next_actions.append("Archive the output folder and keep the live-evidence file with the final certification bundle.")
    else:
        next_actions.append("Run the final live MSN operator sequence on a real MSN output folder.")
        next_actions.append("Fill the live evidence result template with positive evidence only after manual review.")
        next_actions.append("Re-run this live validation index after the live evidence file is present.")

    return LiveValidationIndex(
        input_root=str(root),
        output_dir=str(out),
        status=status,
        required_positive_live_keys=required_live_keys,
        checks=checks,
        manual_live_evidence_files=manual_evidence_rel,
        positive_live_evidence=positive_live,
        blocking_reasons=blocking,
        next_actions=next_actions,
    )


def write_live_validation_index(report: LiveValidationIndex) -> Dict[str, str]:
    out = Path(report.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_LIVE_VALIDATION_INDEX.json"
    md_path = out / "MSN_SOURCE_ADAPTER_LIVE_VALIDATION_INDEX.md"
    csv_path = out / "MSN_SOURCE_ADAPTER_LIVE_VALIDATION_INDEX.csv"

    json_path.write_text(json.dumps(_as_dict(report), indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# MSN Source Adapter Live Validation Index",
        "",
        f"Status: **{report.status}**",
        "",
        f"Input root: `{report.input_root}`",
        "",
        "## Checks",
        "",
        "| Key | Status | Evidence count |",
        "|---|---:|---:|",
    ]
    for c in report.checks:
        md_lines.append(f"| {c.key} | {c.status} | {len(c.evidence)} |")
    md_lines.extend(["", "## Blocking reasons", ""])
    if report.blocking_reasons:
        md_lines.extend(f"- {r}" for r in report.blocking_reasons)
    else:
        md_lines.append("- None")
    md_lines.extend(["", "## Next actions", ""])
    md_lines.extend(f"- {a}" for a in report.next_actions)
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "label", "status", "evidence_count", "notes"])
        writer.writeheader()
        for c in report.checks:
            writer.writerow({
                "key": c.key,
                "label": c.label,
                "status": c.status,
                "evidence_count": len(c.evidence),
                "notes": "; ".join(c.notes),
            })

    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build an MSN source-adapter live validation index for an output folder.")
    parser.add_argument("--input", required=True, help="Existing MSN output folder to scan.")
    parser.add_argument("--output", default=None, help="Directory for reports. Defaults to <input>/reports.")
    args = parser.parse_args(argv)
    report = build_live_validation_index(Path(args.input), Path(args.output) if args.output else None)
    paths = write_live_validation_index(report)
    print("MSN live validation index status:", report.status)
    print("JSON:", paths["json"])
    print("Markdown:", paths["markdown"])
    print("CSV:", paths["csv"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
