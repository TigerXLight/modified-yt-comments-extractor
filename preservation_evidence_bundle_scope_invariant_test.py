import json
import subprocess
import sys
import tempfile
from pathlib import Path

from preservation_evidence_bundle import (
    build_preservation_evidence_bundle_from_dict,
    preservation_evidence_bundle_to_dict,
)


BUNDLE_INPUT = {
    "source_url": "https://www.telegraph.co.uk/news/example/",
    "bundle_label": "Scope invariant evidence",
    "status": "manual_supplied",
    "items": [
        {
            "artifact_id": "screenshot",
            "artifact_format": "png",
            "capture_method_id": "scrollable_container_screenshot",
            "path_hint": r"captures\\comments.png",
            "notes": "Path hint only; do not inspect.",
        }
    ],
}


def _run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _assert_local_only_bundle(bundle: dict) -> None:
    scope = bundle["scope"].lower()
    assert "no file open" in scope, scope
    assert "scan" in scope, scope
    assert "hash" in scope, scope
    assert "upload" in scope, scope
    assert "capture" in scope, scope
    assert "network" in scope, scope
    assert "archive" in scope, scope
    assert "download" in scope, scope

    item = bundle["items"][0]
    assert item["path_hint"] == r"captures\\comments.png"
    assert item["limitations"]


def _assert_local_only_text(output: str) -> None:
    lower_output = output.lower()
    normalized_output = output.replace("\\\\", "\\").lower()
    assert (
        "path_hint=captures\\comments.png" in normalized_output
        or "path hint: captures\\comments.png" in normalized_output
    ), output
    assert "scan" in lower_output, output
    assert "hash" in lower_output, output
    assert "upload" in lower_output, output
    assert "capture" in lower_output, output
    assert "network" in lower_output, output
    assert "archive" in lower_output, output
    assert "download" in lower_output, output
    assert (
        "not opened or checked" in lower_output
        or "no file open" in lower_output
        or "not opened" in lower_output
    ), output


def run_self_test() -> None:
    bundle = build_preservation_evidence_bundle_from_dict(BUNDLE_INPUT)
    model_data = preservation_evidence_bundle_to_dict(bundle)
    _assert_local_only_bundle(model_data)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "evidence_bundle.json"
        input_path.write_text(json.dumps(BUNDLE_INPUT), encoding="utf-8")

        standalone_result = _run_command(
            "preservation_evidence_bundle_cli.py",
            "--input",
            str(input_path),
            "--format",
            "json",
        )
        assert standalone_result.returncode == 0, standalone_result.stderr
        assert standalone_result.stderr == "", standalone_result.stderr
        standalone_bundle = json.loads(standalone_result.stdout)
        _assert_local_only_bundle(standalone_bundle)

        standalone_text_result = _run_command(
            "preservation_evidence_bundle_cli.py",
            "--input",
            str(input_path),
            "--format",
            "text",
        )
        assert standalone_text_result.returncode == 0, standalone_text_result.stderr
        assert standalone_text_result.stderr == "", standalone_text_result.stderr
        _assert_local_only_text(standalone_text_result.stdout)

        standalone_markdown_result = _run_command(
            "preservation_evidence_bundle_cli.py",
            "--input",
            str(input_path),
            "--format",
            "markdown",
        )
        assert standalone_markdown_result.returncode == 0, standalone_markdown_result.stderr
        assert standalone_markdown_result.stderr == "", standalone_markdown_result.stderr
        _assert_local_only_text(standalone_markdown_result.stdout)

        backend_input_path = Path(temp_dir) / "backend_plan.json"
        backend_input_path.write_text(
            json.dumps(
                {
                    "source_url": BUNDLE_INPUT["source_url"],
                    "selected_backend_ids": ["manual_local_files"],
                    "selected_format_ids": ["html"],
                    "evidence_bundle": BUNDLE_INPUT,
                }
            ),
            encoding="utf-8",
        )
        backend_plan_result = _run_command(
            "preservation_backend_plan_cli.py",
            "--input",
            str(backend_input_path),
            "--format",
            "json",
        )
        assert backend_plan_result.returncode == 0, backend_plan_result.stderr
        assert backend_plan_result.stderr == "", backend_plan_result.stderr
        backend_plan = json.loads(backend_plan_result.stdout)
        backend_bundle = backend_plan.get("evidence_bundle")
        assert isinstance(backend_bundle, dict), backend_plan
        _assert_local_only_bundle(backend_bundle)

        backend_plan_text_result = _run_command(
            "preservation_backend_plan_cli.py",
            "--input",
            str(backend_input_path),
            "--format",
            "text",
        )
        assert backend_plan_text_result.returncode == 0, backend_plan_text_result.stderr
        assert backend_plan_text_result.stderr == "", backend_plan_text_result.stderr
        _assert_local_only_text(backend_plan_text_result.stdout)

        backend_plan_markdown_result = _run_command(
            "preservation_backend_plan_cli.py",
            "--input",
            str(backend_input_path),
            "--format",
            "markdown",
        )
        assert backend_plan_markdown_result.returncode == 0, backend_plan_markdown_result.stderr
        assert backend_plan_markdown_result.stderr == "", backend_plan_markdown_result.stderr
        _assert_local_only_text(backend_plan_markdown_result.stdout)

        total_export_result = _run_command(
            "total_export_prepare_cli.py",
            "--explain-preservation-plan",
            "--source-url",
            "https://www.telegraph.co.uk/news/example/",
            "--preservation-backend",
            "manual_local_files",
            "--preservation-format",
            "html",
            "--evidence-bundle-input",
            str(input_path),
            "--json",
        )
        assert total_export_result.returncode == 0, total_export_result.stderr
        assert total_export_result.stderr == "", total_export_result.stderr
        total_export_plan = json.loads(total_export_result.stdout)
        _assert_local_only_bundle(total_export_plan["evidence_bundle"])

        total_export_text_result = _run_command(
            "total_export_prepare_cli.py",
            "--explain-preservation-plan",
            "--source-url",
            "https://www.telegraph.co.uk/news/example/",
            "--preservation-backend",
            "manual_local_files",
            "--preservation-format",
            "html",
            "--evidence-bundle-input",
            str(input_path),
        )
        assert total_export_text_result.returncode == 0, total_export_text_result.stderr
        assert total_export_text_result.stderr == "", total_export_text_result.stderr
        _assert_local_only_text(total_export_text_result.stdout)

        temp_file_names = sorted(path.name for path in Path(temp_dir).iterdir())
        assert temp_file_names == ["backend_plan.json", "evidence_bundle.json"], temp_file_names
        assert not (Path(temp_dir) / "captures").exists()


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle scope invariant self-test passed.")
