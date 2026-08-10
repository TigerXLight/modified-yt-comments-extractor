from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PYTHON = "python"


@dataclass(frozen=True)
class OperatorCommand:
    step: int
    label: str
    command: str
    output_dir: str
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OperatorQuickstart:
    generated_at_utc: str
    root: str
    out: str
    python_executable: str
    target_url: str
    decision_boundary: str
    commands: list[OperatorCommand]
    required_manual_file: str
    warnings: list[str]

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _quote_cmd(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _cmd(python_executable: str, module: str, root: Path, out: Path, extra: list[str] | None = None) -> str:
    parts = [_quote_cmd(python_executable), module, "--root", _quote_cmd(str(root)), "--out", _quote_cmd(str(out))]
    if extra:
        parts.extend(extra)
    return " ".join(parts)


def build_quickstart(root: Path, out: Path, python_executable: str = DEFAULT_PYTHON, target_url: str = "") -> OperatorQuickstart:
    root = root.resolve()
    out = out.resolve()
    manual_file = root / "MSN_LIVE_EVIDENCE_RESULT.json"
    commands: list[OperatorCommand] = []

    commands.append(OperatorCommand(
        1,
        "Generate fillable live evidence template",
        _cmd(python_executable, "source_msn_adapter_live_evidence_template.py", root, root / "live_evidence_template"),
        str(root / "live_evidence_template"),
        ["Fill the resulting template from actual MSN validation before expecting final COMPLETE."],
    ))
    commands.append(OperatorCommand(2, "Run operator final runner", _cmd(python_executable, "source_msn_adapter_operator_final_runner.py", root, root / "operator_final"), str(root / "operator_final")))
    commands.append(OperatorCommand(3, "Reconcile manual/live evidence", _cmd(python_executable, "source_msn_adapter_live_result_reconciler.py", root, root / "live_reconciliation"), str(root / "live_reconciliation"), [f"Looks for live evidence such as {manual_file.name} when present."]))
    commands.append(OperatorCommand(4, "Run release promotion gate", _cmd(python_executable, "source_msn_adapter_release_promotion.py", root, root / "release_promotion"), str(root / "release_promotion"), ["This must remain blocked/pending unless positive live evidence is present."]))
    commands.append(OperatorCommand(5, "Run final promotion closeout", _cmd(python_executable, "source_msn_adapter_final_promotion_closeout.py", root, root / "promotion_closeout"), str(root / "promotion_closeout")))
    commands.append(OperatorCommand(6, "Build certification bundle", _cmd(python_executable, "source_msn_adapter_certification_bundle.py", root, root / "final_certification"), str(root / "final_certification")))
    commands.append(OperatorCommand(7, "Build hash-indexed certification archive", _cmd(python_executable, "source_msn_adapter_certification_archive.py", root, root / "certification_archive", ["--zip"]), str(root / "certification_archive")))

    return OperatorQuickstart(
        generated_at_utc=_now(),
        root=str(root),
        out=str(out),
        python_executable=python_executable,
        target_url=target_url,
        decision_boundary="No real MSN COMPLETE/CERTIFIED state is allowed without positive manual/live evidence.",
        commands=commands,
        required_manual_file=str(manual_file),
        warnings=[
            "This quickstart does not perform a live MSN capture.",
            "Generated templates are not positive live evidence.",
            "Keep MSN republisher, visible publisher/source, visible media credit, and original source status separate.",
        ],
    )


def write_quickstart(bundle: OperatorQuickstart) -> dict[str, Path]:
    out = Path(bundle.out)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "MSN_SOURCE_ADAPTER_OPERATOR_QUICKSTART.json"
    md_path = out / "MSN_SOURCE_ADAPTER_OPERATOR_QUICKSTART.md"
    cmd_path = out / "MSN_SOURCE_ADAPTER_OPERATOR_COMMANDS.cmd"

    json_path.write_text(json.dumps(bundle.to_json_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# MSN Source Adapter Operator Quickstart", "", f"Generated UTC: `{bundle.generated_at_utc}`", f"Root: `{bundle.root}`", "",
        "## Decision boundary", "", bundle.decision_boundary, "", "## Commands", "",
    ]
    for item in bundle.commands:
        lines.extend([f"### {item.step}. {item.label}", "", "```cmd", item.command, "```", "", f"Output: `{item.output_dir}`", ""])
        for note in item.notes:
            lines.append(f"- {note}")
        if item.notes:
            lines.append("")
    lines.extend(["## Required manual/live evidence file", "", f"`{bundle.required_manual_file}`", "", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in bundle.warnings)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd_lines = ["@echo off", "setlocal", "echo MSN source adapter final operator command sequence", "echo This script does not create positive live evidence by itself.", "echo."]
    for item in bundle.commands:
        cmd_lines.extend([f"echo [{item.step}/7] {item.label}", item.command, "if errorlevel 1 exit /b %errorlevel%", "echo."])
    cmd_lines.extend(["echo Operator quickstart sequence finished.", "endlocal"])
    cmd_path.write_text("\r\n".join(cmd_lines) + "\r\n", encoding="utf-8")
    return {"json": json_path, "markdown": md_path, "cmd": cmd_path}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate final MSN adapter operator commands for one output folder.")
    parser.add_argument("--root", required=True, help="Existing MSN output/capture folder")
    parser.add_argument("--out", required=True, help="Output folder for generated quickstart files")
    parser.add_argument("--python", default=DEFAULT_PYTHON, help="Python executable to write into generated commands")
    parser.add_argument("--target-url", default="", help="Optional MSN URL being validated")
    args = parser.parse_args(argv)
    bundle = build_quickstart(Path(args.root), Path(args.out), args.python, args.target_url)
    paths = write_quickstart(bundle)
    print("MSN operator quickstart written:")
    for key, path in paths.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
