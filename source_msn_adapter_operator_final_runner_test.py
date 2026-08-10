from __future__ import annotations

import tempfile
from pathlib import Path

from source_msn_adapter_operator_final_runner import (
    OperatorStep,
    OperatorStepResult,
    OverallStatus,
    StepStatus,
    build_steps,
    build_summary,
    derive_overall_status,
    run_operator_final,
    write_summary,
)


def test_build_steps_uses_existing_local_tools_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        root = Path(tmp) / "root"
        output = Path(tmp) / "out"
        repo.mkdir()
        root.mkdir()
        for name in (
            "source_msn_adapter_completion_cli.py",
            "source_msn_adapter_final_validator.py",
            "source_msn_adapter_done_gate.py",
            "source_msn_adapter_acceptance_suite.py",
            "source_msn_adapter_live_acceptance_pack.py",
            "source_msn_adapter_operator_smoke_pack.py",
        ):
            (repo / name).write_text("print('ok')\n", encoding="utf-8")

        steps = build_steps(
            root=root,
            output_dir=output,
            source_url="https://www.msn.com/example",
            python_exe="python",
            repo_dir=repo,
        )
        names = [step.name for step in steps]
        assert names == [
            "completion_cli",
            "final_validation",
            "done_gate",
            "acceptance_suite",
            "live_acceptance_pack",
            "operator_smoke_pack",
        ]
        all_commands = "\n".join(" ".join(step.command) for step in steps)
        assert "--media-dry-run" in all_commands
        assert "--target-url" in all_commands
        assert "--article-url" in all_commands
        assert "playwright" not in all_commands.lower()
        assert "selenium" not in all_commands.lower()


def test_overall_status_derivation() -> None:
    required = ("a", "b")
    passing = (
        OperatorStepResult("a", "A", StepStatus.PASS, 0, ("cmd",), "a"),
        OperatorStepResult("b", "B", StepStatus.PASS, 0, ("cmd",), "b"),
        OperatorStepResult("optional", "O", StepStatus.WARN, 1, ("cmd",), "o"),
    )
    assert derive_overall_status(passing[:2], required) == OverallStatus.CONFIDENT_WITH_MANUAL_REVIEW
    assert derive_overall_status(passing, required) == OverallStatus.PARTIAL_REVIEW_NEEDED
    failed = (
        OperatorStepResult("a", "A", StepStatus.PASS, 0, ("cmd",), "a"),
        OperatorStepResult("b", "B", StepStatus.FAIL, 1, ("cmd",), "b"),
    )
    assert derive_overall_status(failed, required) == OverallStatus.BLOCKED


def test_write_summary_outputs_json_and_markdown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "root"
        output = Path(tmp) / "out"
        root.mkdir()
        step = OperatorStep("done_gate", "Done gate", ("python", "x.py"), str(output / "done"), True)
        result = OperatorStepResult("done_gate", "Done gate", StepStatus.PASS, 0, ("python", "x.py"), str(output / "done"))
        summary = build_summary(
            root=root,
            output_dir=output,
            source_url="https://www.msn.com/example",
            steps=(step,),
            results=(result,),
        )
        json_path, md_path = write_summary(summary, output)
        assert json_path.exists()
        assert md_path.exists()
        assert "CONFIDENT_WITH_MANUAL_REVIEW" in json_path.read_text(encoding="utf-8")
        md = md_path.read_text(encoding="utf-8")
        assert "MSN Source Adapter Operator Final Summary" in md
        assert "The Independent" in md
        assert "No live capture started" in md


def test_runner_can_execute_fake_local_tools_without_live_capture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        root = Path(tmp) / "root"
        output = Path(tmp) / "out"
        repo.mkdir()
        root.mkdir()
        for name in (
            "source_msn_adapter_completion_cli.py",
            "source_msn_adapter_final_validator.py",
            "source_msn_adapter_done_gate.py",
            "source_msn_adapter_acceptance_suite.py",
        ):
            (repo / name).write_text("print('fake required pass')\n", encoding="utf-8")
        (repo / "source_msn_adapter_live_acceptance_pack.py").write_text("print('fake optional pass')\n", encoding="utf-8")
        summary = run_operator_final(root=root, output_dir=output, source_url="https://www.msn.com/example", repo_dir=repo)
        assert summary.overall_status == OverallStatus.CONFIDENT_WITH_MANUAL_REVIEW
        assert summary.no_live_capture_started is True
        assert (output / "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json").exists()
        assert (output / "MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.md").exists()


def run_all_tests() -> None:
    test_build_steps_uses_existing_local_tools_only()
    test_overall_status_derivation()
    test_write_summary_outputs_json_and_markdown()
    test_runner_can_execute_fake_local_tools_without_live_capture()
    print("MSN operator final runner self-test passed.")


if __name__ == "__main__":
    run_all_tests()
