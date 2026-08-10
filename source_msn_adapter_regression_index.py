"""Create a compact regression index for MSN adapter source, docs and tests."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


CATEGORIES = {
    "core": [
        "source_msn_adapter_manifest.py",
        "source_msn_adapter_readiness.py",
        "source_msn_adapter_release_report.py",
        "source_msn_adapter_final_validator.py",
        "source_msn_adapter_total_package.py",
        "source_msn_adapter_completion_cli.py",
        "source_msn_adapter_closeout_orchestrator.py",
    ],
    "media": [
        "source_msn_adapter_media_download_cli.py",
    ],
    "operator_validation": [
        "source_msn_adapter_manual_validation.py",
        "source_msn_adapter_done_gate.py",
        "source_msn_adapter_operator_smoke_pack.py",
        "source_msn_adapter_acceptance_suite.py",
        "source_msn_adapter_live_acceptance_pack.py",
        "source_msn_adapter_operator_final_runner.py",
        "source_msn_adapter_live_result_reconciler.py",
        "source_msn_adapter_goal_matrix.py",
    ],
}


@dataclass
class RegressionIndexEntry:
    category: str
    path: str
    present: bool
    companion_test: str | None
    companion_test_present: bool


@dataclass
class RegressionIndex:
    generated_at_utc: str
    repo_root: str
    status: str
    present_count: int
    missing_count: int
    entries: list[RegressionIndexEntry]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _test_name(path: str) -> str:
    if path.endswith(".py"):
        return path[:-3] + "_test.py"
    return ""


def build_regression_index(repo_root: Path) -> RegressionIndex:
    repo_root = repo_root.resolve()
    entries: list[RegressionIndexEntry] = []
    for category, paths in CATEGORIES.items():
        for rel in paths:
            test = _test_name(rel)
            entries.append(RegressionIndexEntry(
                category=category,
                path=rel,
                present=(repo_root / rel).exists(),
                companion_test=test or None,
                companion_test_present=bool(test and (repo_root / test).exists()),
            ))
    present = sum(1 for entry in entries if entry.present)
    missing = len(entries) - present
    status = "PASS" if missing == 0 else "PARTIAL"
    return RegressionIndex(_now(), str(repo_root), status, present, missing, entries)


def write_regression_index(index: RegressionIndex, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MSN_SOURCE_ADAPTER_REGRESSION_INDEX.json"
    md_path = output_dir / "MSN_SOURCE_ADAPTER_REGRESSION_INDEX.md"
    json_path.write_text(json.dumps(asdict(index), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# MSN Source Adapter Regression Index",
        "",
        f"- Generated: `{index.generated_at_utc}`",
        f"- Status: `{index.status}`",
        f"- Present modules: `{index.present_count}`",
        f"- Missing modules: `{index.missing_count}`",
        "",
        "| Category | Module | Present | Test | Test present |",
        "|---|---|---:|---|---:|",
    ]
    for entry in index.entries:
        lines.append(
            f"| `{entry.category}` | `{entry.path}` | `{entry.present}` | `{entry.companion_test or '—'}` | `{entry.companion_test_present}` |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MSN source adapter regression index.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default="reports")
    args = parser.parse_args(argv)
    index = build_regression_index(Path(args.repo_root))
    json_path, md_path = write_regression_index(index, Path(args.output))
    print(f"MSN regression index status: {index.status}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
