from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

EXPECTED_FILES = (
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
)

EXPECTED_DOCS = (
    "MSN_SOURCE_ADAPTER_READINESS_GATE.md",
    "MSN_SOURCE_ADAPTER_RELEASE_VALIDATION.md",
    "MSN_SOURCE_ADAPTER_FINAL_VALIDATION.md",
    "MSN_MEDIA_DOWNLOAD_WORKFLOW.md",
    "MSN_SOURCE_ADAPTER_TOTAL_PACKAGE.md",
    "MSN_SOURCE_ADAPTER_COMPLETION_RUNBOOK.md",
    "MSN_SOURCE_ADAPTER_MANUAL_VALIDATION_INTAKE.md",
    "MSN_SOURCE_ADAPTER_DONE_GATE.md",
    "MSN_SOURCE_ADAPTER_GOAL_STATUS.md",
    "MSN_SOURCE_ADAPTER_OPERATOR_SMOKE_PACK.md",
    "MSN_SOURCE_ADAPTER_ACCEPTANCE_SUITE.md",
    "MSN_SOURCE_ADAPTER_LIVE_ACCEPTANCE_PACK.md",
    "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_RUNNER.md",
    "MSN_SOURCE_ADAPTER_LIVE_RESULT_RECONCILER.md",
    "MSN_SOURCE_ADAPTER_COMPLETION_DECISION_MATRIX.md",
    "MSN_SOURCE_ADAPTER_CLOSEOUT_ORCHESTRATOR.md",
    "MSN_SOURCE_ADAPTER_FINAL_STATE_LOCK.md",
    "MSN_SOURCE_ADAPTER_FINAL_LOCK.md",
    "MSN_SOURCE_ADAPTER_REGRESSION_INDEX.md",
    "MSN_SOURCE_ADAPTER_EVIDENCE_PACK_INDEX.md",
    "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_COMMANDS.md",
    "MSN_SOURCE_ADAPTER_FINAL_EVIDENCE_SEAL.md",
)

@dataclass
class SnapshotEntry:
    path: str
    present: bool
    kind: str

@dataclass
class CompletionSnapshot:
    status: str
    present_count: int
    expected_count: int
    missing: list[str]
    entries: list[SnapshotEntry] = field(default_factory=list)


def build_completion_snapshot(repo: Path, output_dir: Path | None = None) -> CompletionSnapshot:
    repo = repo.resolve()
    output_dir = (output_dir or repo / "msn_completion_snapshot").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[SnapshotEntry] = []
    for name in EXPECTED_FILES:
        entries.append(SnapshotEntry(path=name, present=(repo / name).exists(), kind="python"))
    for name in EXPECTED_DOCS:
        entries.append(SnapshotEntry(path=name, present=(repo / name).exists(), kind="documentation"))
    missing = [e.path for e in entries if not e.present]
    present_count = len(entries) - len(missing)
    status = "PASS" if not missing else "PARTIAL"
    snapshot = CompletionSnapshot(status=status, present_count=present_count, expected_count=len(entries), missing=missing, entries=entries)
    _write_outputs(snapshot, output_dir)
    return snapshot


def _write_outputs(snapshot: CompletionSnapshot, output_dir: Path) -> None:
    json_path = output_dir / "MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.md"
    json_path.write_text(json.dumps(asdict(snapshot), indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# MSN Source Adapter Completion Snapshot",
        "",
        f"Status: **{snapshot.status}**",
        f"Present: **{snapshot.present_count}/{snapshot.expected_count}**",
        "",
        "## Expected implementation/docs files",
        "",
        "| Kind | Path | Present |",
        "| --- | --- | --- |",
    ]
    for entry in snapshot.entries:
        lines.append(f"| {entry.kind} | `{entry.path}` | {'yes' if entry.present else 'no'} |")
    if snapshot.missing:
        lines.extend(["", "## Missing", ""])
        lines.extend(f"- `{name}`" for name in snapshot.missing)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a static completion snapshot for the MSN adapter toolchain.")
    parser.add_argument("repo", type=Path, nargs="?", default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    snapshot = build_completion_snapshot(args.repo, args.output_dir)
    print("MSN completion snapshot status:", snapshot.status)
    print(f"Present: {snapshot.present_count}/{snapshot.expected_count}")
    if snapshot.missing:
        print("Missing:", ", ".join(snapshot.missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
