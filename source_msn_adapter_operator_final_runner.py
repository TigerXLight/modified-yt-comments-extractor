from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence


SUMMARY_JSON = "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json"
SUMMARY_MD = "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.md"


class StepStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


class OverallStatus(str, Enum):
    CONFIDENT_WITH_MANUAL_REVIEW = "CONFIDENT_WITH_MANUAL_REVIEW"
    PARTIAL_REVIEW_NEEDED = "PARTIAL_REVIEW_NEEDED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class OperatorStep:
    name: str
    description: str
    command: tuple[str, ...]
    report_dir: str
    required: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "command": list(self.command),
            "report_dir": self.report_dir,
            "required": self.required,
        }


@dataclass(frozen=True)
class OperatorStepResult:
    name: str
    description: str
    status: StepStatus
    returncode: int | None
    command: tuple[str, ...]
    report_dir: str
    stdout_tail: str = ""
    stderr_tail: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "returncode": self.returncode,
            "command": list(self.command),
            "report_dir": self.report_dir,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "note": self.note,
        }


@dataclass(frozen=True)
class OperatorFinalSummary:
    root: str
    source_url: str
    output_dir: str
    overall_status: OverallStatus
    steps: tuple[OperatorStepResult, ...]
    required_steps: int
    passed_required_steps: int
    failed_required_steps: int
    warning_steps: int
    skipped_optional_steps: int
    next_actions: tuple[str, ...]
    no_live_capture_started: bool = True

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["overall_status"] = self.overall_status.value
        data["steps"] = [step.to_dict() for step in self.steps]
        return data


def _tail(text: str, limit: int = 2400) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _existing_script_or_none(repo_dir: Path, name: str) -> Path | None:
    path = repo_dir / name
    return path if path.exists() else None


def build_steps(
    *,
    root: Path,
    output_dir: Path,
    source_url: str = "",
    python_exe: str | None = None,
    repo_dir: Path | None = None,
) -> tuple[OperatorStep, ...]:
    """Build the final operator command chain.

    The command chain is intentionally local-only. It validates and packages an
    existing output folder; it does not browse, scrape, or start live capture.
    """

    repo = repo_dir or Path(__file__).resolve().parent
    py = python_exe or sys.executable
    root_s = str(root)
    source_args = ["--source-url", source_url] if source_url else []
    steps: list[OperatorStep] = []

    completion = _existing_script_or_none(repo, "source_msn_adapter_completion_cli.py")
    if completion:
        steps.append(
            OperatorStep(
                name="completion_cli",
                description="Join article, comments/profile, archive/viewer, media registration, and validation outputs into the operator completion folder.",
                command=(
                    py,
                    str(completion),
                    root_s,
                    *source_args,
                    "--output-dir",
                    str(output_dir / "completion"),
                    "--media-dry-run",
                ),
                report_dir=str(output_dir / "completion"),
                required=True,
            )
        )

    final_validator = _existing_script_or_none(repo, "source_msn_adapter_final_validator.py")
    if final_validator:
        steps.append(
            OperatorStep(
                name="final_validation",
                description="Produce the MSN_ADAPTER_FINAL_VALIDATION_REPORT for the existing output folder.",
                command=(
                    py,
                    str(final_validator),
                    root_s,
                    *source_args,
                    "--output-dir",
                    str(output_dir / "final_validation"),
                ),
                report_dir=str(output_dir / "final_validation"),
                required=True,
            )
        )

    done_gate = _existing_script_or_none(repo, "source_msn_adapter_done_gate.py")
    if done_gate:
        steps.append(
            OperatorStep(
                name="done_gate",
                description="Run the final PASS/PARTIAL/FAIL done gate for adapter capabilities.",
                command=(
                    py,
                    str(done_gate),
                    "--bundle-dir",
                    root_s,
                    "--output-dir",
                    str(output_dir / "done_gate"),
                ),
                report_dir=str(output_dir / "done_gate"),
                required=True,
            )
        )

    acceptance = _existing_script_or_none(repo, "source_msn_adapter_acceptance_suite.py")
    if acceptance:
        steps.append(
            OperatorStep(
                name="acceptance_suite",
                description="Write the final acceptance JSON, Markdown, and CSV checks for the existing MSN output folder.",
                command=(
                    py,
                    str(acceptance),
                    "--root",
                    root_s,
                    "--output",
                    str(output_dir / "acceptance"),
                ),
                report_dir=str(output_dir / "acceptance"),
                required=True,
            )
        )

    live_pack = _existing_script_or_none(repo, "source_msn_adapter_live_acceptance_pack.py")
    if live_pack:
        live_command: tuple[str, ...] = (
            py,
            str(live_pack),
            "--output",
            str(output_dir / "live_acceptance_pack"),
            "--output-folder",
            root_s,
        )
        if source_url:
            live_command = (*live_command, "--article-url", source_url)
        steps.append(
            OperatorStep(
                name="live_acceptance_pack",
                description="Generate manual live-acceptance checklist/template files without starting live capture.",
                command=live_command,
                report_dir=str(output_dir / "live_acceptance_pack"),
                required=False,
            )
        )

    smoke_pack = _existing_script_or_none(repo, "source_msn_adapter_operator_smoke_pack.py")
    if smoke_pack and source_url:
        steps.append(
            OperatorStep(
                name="operator_smoke_pack",
                description="Generate an operator smoke pack for a named MSN article URL without executing live capture.",
                command=(
                    py,
                    str(smoke_pack),
                    "--target-url",
                    source_url,
                    "--output-dir",
                    str(output_dir / "operator_smoke_pack"),
                ),
                report_dir=str(output_dir / "operator_smoke_pack"),
                required=False,
            )
        )

    return tuple(steps)


def run_step(step: OperatorStep) -> OperatorStepResult:
    report_dir = Path(step.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(list(step.command), text=True, capture_output=True, check=False)
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        status = StepStatus.FAIL if step.required else StepStatus.WARN
        return OperatorStepResult(
            name=step.name,
            description=step.description,
            status=status,
            returncode=None,
            command=step.command,
            report_dir=step.report_dir,
            stderr_tail=str(exc),
            note="exception while running local report command",
        )

    if completed.returncode == 0:
        status = StepStatus.PASS
        note = "local report command completed"
    elif step.required:
        status = StepStatus.FAIL
        note = "required local report command failed"
    else:
        status = StepStatus.WARN
        note = "optional local report command failed"

    return OperatorStepResult(
        name=step.name,
        description=step.description,
        status=status,
        returncode=completed.returncode,
        command=step.command,
        report_dir=step.report_dir,
        stdout_tail=_tail(completed.stdout),
        stderr_tail=_tail(completed.stderr),
        note=note,
    )


def derive_overall_status(results: Iterable[OperatorStepResult], required_names: Iterable[str]) -> OverallStatus:
    result_by_name = {result.name: result for result in results}
    required = tuple(required_names)
    failed_required = [
        name
        for name in required
        if result_by_name.get(name) is None or result_by_name[name].status == StepStatus.FAIL
    ]
    if failed_required:
        return OverallStatus.BLOCKED
    warnings = [result for result in result_by_name.values() if result.status == StepStatus.WARN]
    if warnings:
        return OverallStatus.PARTIAL_REVIEW_NEEDED
    return OverallStatus.CONFIDENT_WITH_MANUAL_REVIEW


def build_next_actions(results: Sequence[OperatorStepResult]) -> tuple[str, ...]:
    failed = [result.name for result in results if result.status == StepStatus.FAIL]
    warned = [result.name for result in results if result.status == StepStatus.WARN]
    actions: list[str] = []
    if failed:
        actions.append(
            "Fix failed required report steps before treating the MSN adapter output as complete: "
            + ", ".join(failed)
            + "."
        )
    if warned:
        actions.append("Review optional warning steps and generated templates: " + ", ".join(warned) + ".")
    if not failed:
        actions.append(
            "Open the generated Markdown summary and inspect PASS/PARTIAL/FAIL sections for article, comments, archive, media, and source-chain coverage."
        )
        actions.append(
            "Run the manual/live acceptance checklist only when an operator explicitly approves a real MSN article validation run."
        )
    actions.append(
        "Do not treat MSN as the original media source when the visible publisher, visible credit, or first uploader is separate or missing."
    )
    return tuple(actions)


def build_summary(
    *,
    root: Path,
    output_dir: Path,
    source_url: str,
    steps: Sequence[OperatorStep],
    results: Sequence[OperatorStepResult],
) -> OperatorFinalSummary:
    required_names = tuple(step.name for step in steps if step.required)
    required_results = [result for result in results if result.name in required_names]
    passed_required = sum(1 for result in required_results if result.status == StepStatus.PASS)
    failed_required = sum(
        1
        for name in required_names
        if not any(result.name == name and result.status != StepStatus.FAIL for result in results)
    )
    warning_steps = sum(1 for result in results if result.status == StepStatus.WARN)
    skipped_optional = sum(1 for step in steps if not step.required and not any(result.name == step.name for result in results))
    overall = derive_overall_status(results, required_names)
    return OperatorFinalSummary(
        root=str(root),
        source_url=source_url,
        output_dir=str(output_dir),
        overall_status=overall,
        steps=tuple(results),
        required_steps=len(required_names),
        passed_required_steps=passed_required,
        failed_required_steps=failed_required,
        warning_steps=warning_steps,
        skipped_optional_steps=skipped_optional,
        next_actions=build_next_actions(results),
        no_live_capture_started=True,
    )


def write_summary(summary: OperatorFinalSummary, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / SUMMARY_JSON
    md_path = output_dir / SUMMARY_MD
    json_path.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    return json_path, md_path


def render_markdown(summary: OperatorFinalSummary) -> str:
    lines = [
        "# MSN Source Adapter Operator Final Summary",
        "",
        f"Overall status: `{summary.overall_status.value}`",
        "",
        f"Root: `{summary.root}`",
        f"Source URL: `{summary.source_url or 'not supplied'}`",
        f"Output directory: `{summary.output_dir}`",
        f"No live capture started: `{summary.no_live_capture_started}`",
        "",
        "## Step results",
        "",
        "| Step | Status | Return code | Report dir |",
        "| --- | --- | ---: | --- |",
    ]
    for step in summary.steps:
        returncode = "" if step.returncode is None else str(step.returncode)
        lines.append(f"| {step.name} | {step.status.value} | {returncode} | `{step.report_dir}` |")
    lines.extend(["", "## Next actions", ""])
    for action in summary.next_actions:
        lines.append(f"- {action}")
    lines.extend(["", "## Source-role reminder", ""])
    lines.append(
        "MSN can be a captured platform or republisher. A visible publisher such as The Independent, a visible media credit such as Google Street View, and a missing original uploader/raw media source must remain separately recorded."
    )
    lines.append("")
    return "\n".join(lines)


def run_operator_final(
    *,
    root: Path,
    output_dir: Path | None = None,
    source_url: str = "",
    python_exe: str | None = None,
    repo_dir: Path | None = None,
) -> OperatorFinalSummary:
    output = output_dir or root / "msn_source_adapter_operator_final"
    steps = build_steps(root=root, output_dir=output, source_url=source_url, python_exe=python_exe, repo_dir=repo_dir)
    results = tuple(run_step(step) for step in steps)
    summary = build_summary(root=root, output_dir=output, source_url=source_url, steps=steps, results=results)
    write_summary(summary, output)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run final local MSN adapter operator reports against an existing output folder.")
    parser.add_argument("root", help="Existing MSN output/capture/export folder to assess.")
    parser.add_argument("--source-url", default="", help="Original MSN article URL, if known.")
    parser.add_argument("--output-dir", default="", help="Output directory. Defaults to <root>/msn_source_adapter_operator_final.")
    parser.add_argument("--json", action="store_true", help="Print summary JSON to stdout.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    output = Path(args.output_dir) if args.output_dir else None
    summary = run_operator_final(root=root, output_dir=output, source_url=args.source_url)
    json_path, md_path = write_summary(summary, Path(summary.output_dir))
    if args.json:
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"MSN operator final status: {summary.overall_status.value}")
        print(f"JSON: {json_path}")
        print(f"Markdown: {md_path}")
    return 0 if summary.overall_status != OverallStatus.BLOCKED else 2


if __name__ == "__main__":
    raise SystemExit(main())
