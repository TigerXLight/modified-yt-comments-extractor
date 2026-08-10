from __future__ import annotations

"""MSN source adapter release-candidate lock.

This module is intentionally no-network.  It does not claim that a live MSN page
worked unless a positive manual/live result is supplied.  Its job is to freeze the
repo-side MSN adapter components, hash the evidence files that exist, and produce
an operator-readable lock report showing what remains to move from release
candidate to live-complete.
"""

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


STATUS_PRESENT = "PRESENT"
STATUS_MISSING = "MISSING"
STATE_COMPLETE_WITH_LIVE_EVIDENCE = "COMPLETE_WITH_LIVE_EVIDENCE"
STATE_RC_LOCKED_PENDING_LIVE_EVIDENCE = "RC_LOCKED_PENDING_LIVE_EVIDENCE"
STATE_PARTIAL = "PARTIAL"
STATE_BLOCKED = "BLOCKED"

EXPECTED_REPO_ARTIFACTS: tuple[str, ...] = (
    "source_msn_adapter_manifest.py",
    "source_msn_adapter_readiness.py",
    "source_msn_adapter_release_report.py",
    "source_msn_adapter_final_validator.py",
    "source_msn_adapter_media_download_cli.py",
    "source_msn_adapter_total_package.py",
    "source_msn_adapter_completion_cli.py",
    "source_msn_adapter_manual_validation.py",
    "source_msn_adapter_done_gate.py",
    "source_msn_adapter_operator_smoke_pack.py",
    "source_msn_adapter_acceptance_suite.py",
    "source_msn_adapter_live_acceptance_pack.py",
    "source_msn_adapter_operator_final_runner.py",
    "source_msn_adapter_live_result_reconciler.py",
    "source_msn_adapter_closeout_orchestrator.py",
    "source_msn_adapter_goal_matrix.py",
    "source_msn_adapter_final_lock.py",
    "source_msn_adapter_regression_index.py",
    "source_msn_adapter_evidence_pack_index.py",
    "source_msn_adapter_final_evidence_seal.py",
    "source_msn_adapter_completion_snapshot.py",
    "MSN_SOURCE_ADAPTER_FINAL_STATE_LOCK.md",
    "MSN_SOURCE_ADAPTER_FINAL_LOCK.md",
    "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.md",
    "MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.md",
)

CORE_CAPABILITIES: tuple[str, ...] = (
    "article_extraction",
    "comments_profile_extraction",
    "offline_webpage_viewer_and_archive",
    "media_discovery_and_download_registration",
    "video_candidate_status_recording",
    "source_role_and_primary_source_status",
    "msn_republisher_visible_publisher_original_source_separation",
    "readiness_release_final_validation",
    "operator_smoke_and_live_acceptance_pack",
    "final_lock_evidence_pack_snapshot",
)

LIVE_POSITIVE_TERMS = {"complete", "pass", "passed", "accepted", "verified", "true", "yes"}
LIVE_NEGATIVE_TERMS = {"fail", "failed", "blocked", "false", "no", "partial"}


@dataclass(frozen=True)
class RepoArtifactCheck:
    path: str
    status: str
    sha256: str | None = None
    size_bytes: int | None = None


@dataclass(frozen=True)
class CapabilityDecision:
    capability: str
    status: str
    evidence: str


@dataclass(frozen=True)
class ReleaseCandidateLock:
    generated_at_utc: str
    repo_root: str
    state: str
    repo_artifacts_present: int
    repo_artifacts_expected: int
    live_evidence_status: str
    artifact_checks: list[RepoArtifactCheck] = field(default_factory=list)
    capability_decisions: list[CapabilityDecision] = field(default_factory=list)
    missing_artifacts: list[str] = field(default_factory=list)
    operator_actions: list[str] = field(default_factory=list)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _flatten_values(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _flatten_values(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _flatten_values(item)
    elif value is not None:
        yield str(value)


def _manual_live_status(path: Path | None) -> str:
    if path is None:
        return "MISSING_MANUAL_LIVE_RESULT"
    if not path.exists():
        return "MISSING_MANUAL_LIVE_RESULT"
    try:
        if path.suffix.lower() == ".json":
            tokens = {token.lower() for token in _flatten_values(_read_json(path))}
        else:
            tokens = set(path.read_text(encoding="utf-8", errors="replace").lower().replace("_", " ").split())
    except Exception as exc:  # pragma: no cover - defensive operator path
        return f"UNREADABLE_MANUAL_LIVE_RESULT:{exc.__class__.__name__}"
    if tokens & LIVE_NEGATIVE_TERMS:
        return "MANUAL_LIVE_RESULT_REQUIRES_REVIEW"
    if tokens & LIVE_POSITIVE_TERMS:
        return "POSITIVE_MANUAL_LIVE_EVIDENCE_PRESENT"
    return "MANUAL_LIVE_RESULT_AMBIGUOUS"


def check_repo_artifacts(repo_root: Path) -> list[RepoArtifactCheck]:
    checks: list[RepoArtifactCheck] = []
    for rel in EXPECTED_REPO_ARTIFACTS:
        path = repo_root / rel
        if path.exists() and path.is_file():
            checks.append(
                RepoArtifactCheck(
                    path=rel,
                    status=STATUS_PRESENT,
                    sha256=_sha256_file(path),
                    size_bytes=path.stat().st_size,
                )
            )
        else:
            checks.append(RepoArtifactCheck(path=rel, status=STATUS_MISSING))
    return checks


def build_release_candidate_lock(
    repo_root: Path,
    output_dir: Path | None = None,
    manual_live_result: Path | None = None,
) -> ReleaseCandidateLock:
    repo_root = repo_root.resolve()
    artifact_checks = check_repo_artifacts(repo_root)
    missing = [item.path for item in artifact_checks if item.status != STATUS_PRESENT]
    present_count = len(artifact_checks) - len(missing)
    live_status = _manual_live_status(manual_live_result)

    capability_status = "PASS" if not missing else "PARTIAL"
    capability_evidence = (
        "All expected repo-side MSN adapter files are present."
        if not missing
        else "Some repo-side MSN adapter files are missing."
    )
    capability_decisions = [
        CapabilityDecision(capability=name, status=capability_status, evidence=capability_evidence)
        for name in CORE_CAPABILITIES
    ]

    if missing:
        state = STATE_PARTIAL
    elif live_status == "POSITIVE_MANUAL_LIVE_EVIDENCE_PRESENT":
        state = STATE_COMPLETE_WITH_LIVE_EVIDENCE
    elif live_status.startswith("UNREADABLE"):
        state = STATE_BLOCKED
    else:
        state = STATE_RC_LOCKED_PENDING_LIVE_EVIDENCE

    actions: list[str] = []
    if missing:
        actions.append("Restore or implement the missing MSN adapter files listed in missing_artifacts.")
    if live_status != "POSITIVE_MANUAL_LIVE_EVIDENCE_PRESENT":
        actions.append("Run the operator smoke/live acceptance pack on a named MSN article and attach the positive result before calling live MSN COMPLETE.")
    actions.append("Keep source-role separation: MSN republisher, visible publisher/source credit, and original source are not interchangeable.")

    lock = ReleaseCandidateLock(
        generated_at_utc=_utc_now(),
        repo_root=str(repo_root),
        state=state,
        repo_artifacts_present=present_count,
        repo_artifacts_expected=len(artifact_checks),
        live_evidence_status=live_status,
        artifact_checks=artifact_checks,
        capability_decisions=capability_decisions,
        missing_artifacts=missing,
        operator_actions=actions,
    )
    if output_dir is not None:
        write_release_candidate_lock(lock, output_dir)
    return lock


def _markdown(lock: ReleaseCandidateLock) -> str:
    lines = [
        "# MSN Source Adapter Release Candidate Lock",
        "",
        f"Generated UTC: `{lock.generated_at_utc}`",
        f"State: **{lock.state}**",
        f"Repo artifacts: `{lock.repo_artifacts_present}/{lock.repo_artifacts_expected}`",
        f"Live evidence status: `{lock.live_evidence_status}`",
        "",
        "## Decision rule",
        "",
        "Do not mark real MSN COMPLETE unless positive manual/live evidence is present. No-network fixtures can lock the release candidate, but they cannot prove current live MSN behaviour.",
        "",
        "## Capability matrix",
        "",
        "| Capability | Status | Evidence |",
        "|---|---:|---|",
    ]
    for item in lock.capability_decisions:
        lines.append(f"| {item.capability} | {item.status} | {item.evidence} |")
    lines.extend(["", "## Missing artifacts", ""])
    if lock.missing_artifacts:
        lines.extend(f"- `{item}`" for item in lock.missing_artifacts)
    else:
        lines.append("None.")
    lines.extend(["", "## Operator actions", ""])
    lines.extend(f"- {action}" for action in lock.operator_actions)
    lines.extend(["", "## Artifact SHA256 index", ""])
    for item in lock.artifact_checks:
        if item.sha256:
            lines.append(f"- `{item.path}` — `{item.sha256}` ({item.size_bytes} bytes)")
        else:
            lines.append(f"- `{item.path}` — {item.status}")
    lines.append("")
    return "\n".join(lines)


def write_release_candidate_lock(lock: ReleaseCandidateLock, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK.md"
    csv_path = output_dir / "MSN_SOURCE_ADAPTER_RELEASE_CANDIDATE_LOCK_ARTIFACTS.csv"
    json_path.write_text(json.dumps(asdict(lock), indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_markdown(lock), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "status", "sha256", "size_bytes"])
        writer.writeheader()
        for item in lock.artifact_checks:
            writer.writerow(asdict(item))
    return {"json": str(json_path), "markdown": str(md_path), "csv": str(csv_path)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MSN release-candidate lock reports.")
    parser.add_argument("--repo-root", default=".", help="Repository root to inspect.")
    parser.add_argument("--output-dir", default="msn_release_candidate_lock", help="Directory for report outputs.")
    parser.add_argument("--manual-live-result", default=None, help="Optional filled live/manual result JSON or Markdown.")
    args = parser.parse_args(argv)
    manual = Path(args.manual_live_result) if args.manual_live_result else None
    lock = build_release_candidate_lock(Path(args.repo_root), Path(args.output_dir), manual)
    print(f"MSN release-candidate lock state: {lock.state}")
    print(f"Repo artifacts: {lock.repo_artifacts_present}/{lock.repo_artifacts_expected}")
    return 0 if lock.state != STATE_BLOCKED else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
