from __future__ import annotations

"""Completion ledger for the MSN source adapter.

The ledger is a stable human-readable index of what was added, why it exists, and
which command/report family owns each decision.  It is no-network and safe to run
inside the development tree or against a copied evidence folder.
"""

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class LedgerEntry:
    layer: str
    owned_by: str
    purpose: str
    completion_role: str


@dataclass(frozen=True)
class CompletionLedger:
    generated_at_utc: str
    entries: list[LedgerEntry] = field(default_factory=list)
    non_negotiable_rules: list[str] = field(default_factory=list)


LEDGER_ENTRIES: tuple[LedgerEntry, ...] = (
    LedgerEntry("manifest", "source_msn_adapter_manifest.py", "preserve article/comment/media/source-chain facts", "core bundle metadata"),
    LedgerEntry("readiness", "source_msn_adapter_readiness.py", "report PASS/PARTIAL/FAIL readiness", "pre-release gate"),
    LedgerEntry("release-report", "source_msn_adapter_release_report.py", "human-readable release evidence", "release review"),
    LedgerEntry("final-validator", "source_msn_adapter_final_validator.py", "validate existing output folder", "operator validation"),
    LedgerEntry("media-download", "source_msn_adapter_media_download_cli.py", "inventory/download-status/hash media candidates", "media completion"),
    LedgerEntry("total-package", "source_msn_adapter_total_package.py", "join article/comments/archive/media/reports", "operator package"),
    LedgerEntry("manual-intake", "source_msn_adapter_manual_validation.py", "record manual live evidence", "human evidence intake"),
    LedgerEntry("done-gate", "source_msn_adapter_done_gate.py", "decide whether goals are satisfied", "completion gate"),
    LedgerEntry("acceptance-suite", "source_msn_adapter_acceptance_suite.py", "produce acceptance JSON/MD/CSV", "acceptance evidence"),
    LedgerEntry("operator-final", "source_msn_adapter_operator_final_runner.py", "chain reports for one output folder", "final operator command"),
    LedgerEntry("live-reconciler", "source_msn_adapter_live_result_reconciler.py", "join no-network and manual live results", "live truth boundary"),
    LedgerEntry("closeout", "source_msn_adapter_closeout_orchestrator.py", "closeout reports/actions", "roadmap closeout"),
    LedgerEntry("final-lock", "source_msn_adapter_final_lock.py", "lock final repo/evidence state", "regression guard"),
    LedgerEntry("evidence-seal", "source_msn_adapter_final_evidence_seal.py", "seal final evidence artifacts", "evidence integrity"),
    LedgerEntry("completion-snapshot", "source_msn_adapter_completion_snapshot.py", "snapshot current completion state", "handoff continuity"),
    LedgerEntry("release-candidate-lock", "source_msn_adapter_release_candidate_lock.py", "freeze repo-side RC and live-evidence boundary", "RC lock"),
)

RULES: tuple[str, ...] = (
    "Do not call live MSN COMPLETE unless positive manual/live evidence exists.",
    "MSN republisher status must stay separate from visible publisher/source credit and original-source proof.",
    "Media candidates are not downloaded media unless local path/hash/status confirms the download.",
    "Strict WACZ support must remain labelled honestly if replay support is experimental or partial.",
    "Closed-loop or repeated publisher claims do not become primary source evidence by repetition.",
)


def build_completion_ledger() -> CompletionLedger:
    return CompletionLedger(
        generated_at_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        entries=list(LEDGER_ENTRIES),
        non_negotiable_rules=list(RULES),
    )


def _markdown(ledger: CompletionLedger) -> str:
    lines = [
        "# MSN Source Adapter Completion Ledger",
        "",
        f"Generated UTC: `{ledger.generated_at_utc}`",
        "",
        "## Layers",
        "",
        "| Layer | Owner | Purpose | Completion role |",
        "|---|---|---|---|",
    ]
    for entry in ledger.entries:
        lines.append(f"| {entry.layer} | `{entry.owned_by}` | {entry.purpose} | {entry.completion_role} |")
    lines.extend(["", "## Non-negotiable rules", ""])
    lines.extend(f"- {rule}" for rule in ledger.non_negotiable_rules)
    lines.append("")
    return "\n".join(lines)


def write_completion_ledger(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = build_completion_ledger()
    json_path = output_dir / "MSN_SOURCE_ADAPTER_COMPLETION_LEDGER.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_COMPLETION_LEDGER.md"
    json_path.write_text(json.dumps(asdict(ledger), indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_markdown(ledger), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the MSN completion ledger.")
    parser.add_argument("--output-dir", default="msn_completion_ledger")
    args = parser.parse_args(argv)
    paths = write_completion_ledger(Path(args.output_dir))
    print("MSN completion ledger written:")
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
