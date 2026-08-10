"""Validate manual/live MSN adapter evidence before any COMPLETE claim.

This module is deliberately no-network.  It scans an existing MSN output folder
for filled operator/manual/live validation evidence and normalises that evidence
into a small decision report.  It does not perform a live capture and it refuses
to treat no-network fixture success as proof of real MSN completion.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


POSITIVE = {"pass", "passed", "ok", "true", "yes", "accepted", "complete", "completed", "validated", "success"}
NEGATIVE = {"fail", "failed", "false", "no", "blocked", "reject", "rejected", "missing", "error"}
REQUIRED_CHECKS = (
    "article_extraction",
    "comments_profile_extraction",
    "offline_viewer_archive",
    "media_registration",
    "source_chain_review",
)
OPTIONAL_CHECKS = (
    "video_stream_status",
    "downloaded_media_hashes",
    "warc_wacz_status",
    "profile_stats",
)


@dataclass
class EvidenceFile:
    path: str
    status: str = "UNKNOWN"
    operator_decision: str = ""
    target_url: str = ""
    observed_at: str = ""
    checks: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class LiveEvidenceValidation:
    generated_at_utc: str
    root: str
    status: str
    summary: str
    evidence_files: list[EvidenceFile] = field(default_factory=list)
    accepted_file: str = ""
    accepted_target_url: str = ""
    accepted_observed_at: str = ""
    required_checks: dict[str, str] = field(default_factory=dict)
    optional_checks: dict[str, str] = field(default_factory=dict)
    missing_required_checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalise_status(value: Any) -> str:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if value is None:
        return "UNKNOWN"
    text = str(value).strip().lower()
    if not text:
        return "UNKNOWN"
    if text in POSITIVE:
        return "PASS"
    if text in NEGATIVE:
        return "FAIL"
    if "pass" in text or "accept" in text or "valid" in text or "complete" in text:
        return "PASS"
    if "fail" in text or "block" in text or "missing" in text or "reject" in text:
        return "FAIL"
    if "partial" in text or "review" in text or "pending" in text:
        return "PARTIAL"
    return str(value).strip().upper().replace(" ", "_")


def _flatten_keys(data: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_keys(value, new_prefix)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            new_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            yield from _flatten_keys(value, new_prefix)
    else:
        yield prefix, data


def _first_text(data: Any, names: Iterable[str]) -> str:
    wanted = {n.lower() for n in names}
    for key, value in _flatten_keys(data):
        leaf = key.split(".")[-1].split("[")[0].lower()
        if leaf in wanted and value not in (None, ""):
            return str(value)
    return ""


def _extract_checks(data: Any) -> dict[str, str]:
    checks: dict[str, str] = {}

    def add(name: str, value: Any) -> None:
        safe = str(name).strip().lower().replace(" ", "_").replace("-", "_")
        if safe:
            checks[safe] = _normalise_status(value)

    if isinstance(data, dict):
        raw_checks = data.get("checks") or data.get("manual_checks") or data.get("live_checks")
        if isinstance(raw_checks, dict):
            for name, value in raw_checks.items():
                if isinstance(value, dict):
                    add(name, value.get("status", value.get("result", value.get("passed"))))
                else:
                    add(name, value)
        elif isinstance(raw_checks, list):
            for entry in raw_checks:
                if isinstance(entry, dict):
                    name = entry.get("name") or entry.get("check") or entry.get("id")
                    if name:
                        add(str(name), entry.get("status", entry.get("result", entry.get("passed"))))

        for key, value in data.items():
            key_norm = str(key).strip().lower().replace(" ", "_").replace("-", "_")
            for required in REQUIRED_CHECKS + OPTIONAL_CHECKS:
                if key_norm == required or key_norm.endswith("_" + required):
                    add(required, value)

    for key, value in _flatten_keys(data):
        leaf = key.split(".")[-1].split("[")[0].lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "article": "article_extraction",
            "article_extracted": "article_extraction",
            "comments": "comments_profile_extraction",
            "comments_exported": "comments_profile_extraction",
            "profiles": "comments_profile_extraction",
            "profiles_exported": "comments_profile_extraction",
            "offline_viewer": "offline_viewer_archive",
            "archive": "offline_viewer_archive",
            "media": "media_registration",
            "media_registered": "media_registration",
            "source_chain": "source_chain_review",
            "source_role": "source_chain_review",
            "source_review": "source_chain_review",
            "video": "video_stream_status",
            "video_status": "video_stream_status",
            "hashes": "downloaded_media_hashes",
            "media_hashes": "downloaded_media_hashes",
            "profile_stats": "profile_stats",
        }
        if leaf in aliases and aliases[leaf] not in checks:
            checks[aliases[leaf]] = _normalise_status(value)
    return checks


def _file_score(path: Path) -> int:
    name = path.name.lower()
    score = 0
    for token in ("live", "manual", "acceptance", "validation", "result", "filled", "complete"):
        if token in name:
            score += 2
    if "template" in name:
        score -= 3
    if "report" in name:
        score -= 1
    return score


def find_candidate_evidence_files(root: Path) -> list[Path]:
    patterns = (
        "*LIVE*ACCEPTANCE*RESULT*.json",
        "*MANUAL*VALIDATION*RESULT*.json",
        "*MSN*LIVE*RESULT*.json",
        "*MSN*MANUAL*RESULT*.json",
        "*MSN*ACCEPTANCE*RESULT*.json",
    )
    candidates: set[Path] = set()
    if root.exists():
        for pattern in patterns:
            candidates.update(path for path in root.rglob(pattern) if path.is_file())
    return sorted(candidates, key=lambda p: (-_file_score(p), str(p).lower()))


def _parse_evidence_file(path: Path, root: Path) -> EvidenceFile:
    try:
        data = _safe_read_json(path)
    except Exception as exc:  # pragma: no cover - defensive
        return EvidenceFile(path=str(path.relative_to(root)), status="UNREADABLE", notes=[f"Could not read JSON: {exc}"])

    checks = _extract_checks(data)
    decision = _first_text(data, ["operator_decision", "decision", "status", "result", "overall_status", "final_status"])
    status = _normalise_status(decision)
    target_url = _first_text(data, ["target_url", "source_url", "url", "msn_url"])
    observed_at = _first_text(data, ["observed_at", "validated_at", "capture_time_utc", "checked_at", "completed_at"])
    notes: list[str] = []

    if "template" in path.name.lower():
        notes.append("Filename looks like an unfilled template; evidence must be confirmed by content.")
    if not checks:
        notes.append("No machine-readable check statuses found.")

    return EvidenceFile(
        path=str(path.relative_to(root)),
        status=status,
        operator_decision=decision,
        target_url=target_url,
        observed_at=observed_at,
        checks=checks,
        notes=notes,
    )


def validate_live_evidence(root: str | Path) -> LiveEvidenceValidation:
    root_path = Path(root).expanduser().resolve()
    warnings: list[str] = []
    next_actions: list[str] = []
    evidence_files = [_parse_evidence_file(path, root_path) for path in find_candidate_evidence_files(root_path)]

    if not root_path.exists():
        return LiveEvidenceValidation(
            generated_at_utc=_now(),
            root=str(root_path),
            status="INSUFFICIENT_EVIDENCE",
            summary="Root folder does not exist.",
            warnings=["The requested MSN output folder was not found."],
            next_actions=["Run the operator final runner against a real MSN output folder, then add the filled live/manual result JSON."],
        )

    if not evidence_files:
        return LiveEvidenceValidation(
            generated_at_utc=_now(),
            root=str(root_path),
            status="NO_LIVE_EVIDENCE",
            summary="No filled manual/live acceptance result JSON was found.",
            warnings=["No real MSN COMPLETE claim is allowed without positive manual/live evidence."],
            next_actions=["Fill the generated MSN live acceptance result JSON after a manual/live operator check."],
        )

    accepted: EvidenceFile | None = None
    best_required: dict[str, str] = {}
    best_optional: dict[str, str] = {}
    for evidence in evidence_files:
        required = {name: evidence.checks.get(name, "UNKNOWN") for name in REQUIRED_CHECKS}
        optional = {name: evidence.checks.get(name, "UNKNOWN") for name in OPTIONAL_CHECKS}
        missing = [name for name, status in required.items() if status != "PASS"]
        if evidence.status == "PASS" and not missing:
            accepted = evidence
            best_required = required
            best_optional = optional
            break
        if not best_required:
            best_required = required
            best_optional = optional

    if accepted:
        if not accepted.target_url:
            warnings.append("Positive evidence found but target URL is blank; keep folder-level source URL records for audit.")
        if not accepted.observed_at:
            warnings.append("Positive evidence found but observed/validated timestamp is blank.")
        return LiveEvidenceValidation(
            generated_at_utc=_now(),
            root=str(root_path),
            status="LIVE_EVIDENCE_ACCEPTED",
            summary="Positive filled manual/live MSN evidence was found and all required checks passed.",
            evidence_files=evidence_files,
            accepted_file=accepted.path,
            accepted_target_url=accepted.target_url,
            accepted_observed_at=accepted.observed_at,
            required_checks=best_required,
            optional_checks=best_optional,
            warnings=warnings,
            next_actions=["The release promotion gate may mark MSN COMPLETE if the no-network reports are also non-failing."],
        )

    any_fail = any(e.status == "FAIL" or any(v == "FAIL" for v in e.checks.values()) for e in evidence_files)
    missing_required = [name for name, status in best_required.items() if status != "PASS"]
    status = "LIVE_EVIDENCE_REJECTED" if any_fail else "LIVE_EVIDENCE_INCOMPLETE"
    summary = "Manual/live evidence exists but does not pass all required checks."
    return LiveEvidenceValidation(
        generated_at_utc=_now(),
        root=str(root_path),
        status=status,
        summary=summary,
        evidence_files=evidence_files,
        required_checks=best_required,
        optional_checks=best_optional,
        missing_required_checks=missing_required,
        warnings=["Do not promote MSN to COMPLETE while required live checks are missing or failing."],
        next_actions=["Review the live/manual evidence JSON and rerun the operator final runner after correcting failed areas."],
    )


def write_live_evidence_report(report: LiveEvidenceValidation, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_VALIDATION.json"
    md_path = out / "MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_VALIDATION.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# MSN Source Adapter Live Evidence Validation",
        "",
        f"Status: **{report.status}**",
        "",
        report.summary,
        "",
        f"Root: `{report.root}`",
        f"Generated: `{report.generated_at_utc}`",
        "",
        "## Required checks",
    ]
    if report.required_checks:
        for name, status in report.required_checks.items():
            lines.append(f"- {name}: {status}")
    else:
        lines.append("- No required check evidence was found.")
    if report.evidence_files:
        lines.extend(["", "## Evidence files"])
        for evidence in report.evidence_files:
            lines.append(f"- `{evidence.path}` — {evidence.status}")
    if report.warnings:
        lines.extend(["", "## Warnings"])
        for warning in report.warnings:
            lines.append(f"- {warning}")
    if report.next_actions:
        lines.extend(["", "## Next actions"])
        for action in report.next_actions:
            lines.append(f"- {action}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate filled manual/live MSN evidence without network access.")
    parser.add_argument("--root", required=True, help="Existing MSN output folder to scan")
    parser.add_argument("--out-dir", default=None, help="Output report directory; defaults to <root>/reports")
    args = parser.parse_args(argv)
    root = Path(args.root)
    out_dir = Path(args.out_dir) if args.out_dir else root / "reports"
    report = validate_live_evidence(root)
    json_path, md_path = write_live_evidence_report(report, out_dir)
    print(f"MSN live evidence validation status: {report.status}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0 if report.status in {"LIVE_EVIDENCE_ACCEPTED", "NO_LIVE_EVIDENCE", "LIVE_EVIDENCE_INCOMPLETE"} else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
