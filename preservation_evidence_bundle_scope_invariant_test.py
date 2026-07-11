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


FORBIDDEN_FILE_STATE_KEYS = {
    "captured",
    "checksum",
    "created",
    "exists",
    "file_size",
    "hash",
    "mtime",
    "opened",
    "sha256",
    "size_bytes",
    "uploaded",
    "validated",
}


RENDERED_FILE_STATE_FIELD_MARKERS = (
    "checksum",
    "file_size",
    "mtime",
    "sha256",
    "size_bytes",
)


def _assert_no_file_state_keys(value: object) -> None:
    if isinstance(value, dict):
        forbidden = FORBIDDEN_FILE_STATE_KEYS.intersection(value)
        assert not forbidden, forbidden
        for child in value.values():
            _assert_no_file_state_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_file_state_keys(child)


def _assert_rejects_file_state_key(key: str) -> None:
    try:
        _assert_no_file_state_keys({"items": [{key: "example"}]})
    except AssertionError:
        return
    raise AssertionError(f"Expected file-state key to be rejected: {key!r}")


def _assert_descriptive_path_hint(path_hint: str) -> None:
    assert path_hint == r"captures\\comments.png", path_hint
    assert "://" not in path_hint, path_hint
    assert ":" not in path_hint, path_hint
    assert not path_hint.startswith(("/", "\\")), path_hint
    assert not Path(path_hint).is_absolute(), path_hint
    normalized_parts = path_hint.replace("\\", "/").split("/")
    assert ".." not in normalized_parts, path_hint


def _assert_rejects_path_hint(path_hint: str) -> None:
    try:
        _assert_descriptive_path_hint(path_hint)
    except AssertionError:
        return
    raise AssertionError(f"Expected path hint to be rejected: {path_hint!r}")


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
    _assert_no_file_state_keys(bundle)

    item = bundle["items"][0]
    _assert_descriptive_path_hint(item["path_hint"])
    assert item["limitations"]
    execution = item.get("execution")
    if execution is not None:
        assert str(execution).lower() == "metadata only", item


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
    for marker in RENDERED_FILE_STATE_FIELD_MARKERS:
        assert marker not in lower_output, output
    assert "metadata only" in lower_output, output
    assert (
        "not opened or checked" in lower_output
        or "no file open" in lower_output
        or "not opened" in lower_output
    ), output


def _assert_no_temp_path_leak(output: str, temp_dir: str) -> None:
    temp_path = Path(temp_dir)
    temp_strings = {
        str(temp_path),
        temp_path.as_posix(),
        temp_path.name,
    }
    input_file_names = {
        "backend_plan.json",
        "evidence_bundle.json",
    }
    for temp_string in temp_strings.union(input_file_names):
        assert temp_string not in output, output


def _assert_clean_local_command(
    result: subprocess.CompletedProcess[str],
    temp_dir: str,
) -> None:
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", result.stderr
    _assert_no_temp_path_leak(result.stdout, temp_dir)


def _assert_rejects_temp_path_leak(output: str, temp_dir: str) -> None:
    try:
        _assert_no_temp_path_leak(output, temp_dir)
    except AssertionError:
        return
    raise AssertionError(f"Expected temp path leak to be rejected: {output!r}")


def run_self_test() -> None:
    bundle = build_preservation_evidence_bundle_from_dict(BUNDLE_INPUT)
    model_data = preservation_evidence_bundle_to_dict(bundle)
    _assert_local_only_bundle(model_data)

    _assert_rejects_path_hint("https://example.invalid/captures/comments.png")
    _assert_rejects_path_hint(r"C:\captures\comments.png")
    _assert_rejects_path_hint(r"\captures\comments.png")
    _assert_rejects_path_hint("/tmp/captures/comments.png")
    _assert_rejects_path_hint(r"..\captures\comments.png")
    _assert_rejects_path_hint("../captures/comments.png")
    _assert_rejects_path_hint(r"captures\..\comments.png")
    _assert_rejects_path_hint("captures/../comments.png")

    for forbidden_key in sorted(FORBIDDEN_FILE_STATE_KEYS):
        _assert_rejects_file_state_key(forbidden_key)

    with tempfile.TemporaryDirectory() as temp_dir:
        _assert_rejects_temp_path_leak(f"leaked temp dir: {temp_dir}", temp_dir)
        _assert_rejects_temp_path_leak(
            f"leaked temp input: {Path(temp_dir) / 'evidence_bundle.json'}",
            temp_dir,
        )
        _assert_rejects_temp_path_leak("leaked backend_plan.json", temp_dir)
        _assert_rejects_temp_path_leak("leaked evidence_bundle.json", temp_dir)

        input_path = Path(temp_dir) / "evidence_bundle.json"
        input_path.write_text(json.dumps(BUNDLE_INPUT), encoding="utf-8")

        standalone_result = _run_command(
            "preservation_evidence_bundle_cli.py",
            "--input",
            str(input_path),
            "--format",
            "json",
        )
        _assert_clean_local_command(standalone_result, temp_dir)
        standalone_bundle = json.loads(standalone_result.stdout)
        _assert_local_only_bundle(standalone_bundle)

        standalone_text_result = _run_command(
            "preservation_evidence_bundle_cli.py",
            "--input",
            str(input_path),
            "--format",
            "text",
        )
        _assert_clean_local_command(standalone_text_result, temp_dir)
        _assert_local_only_text(standalone_text_result.stdout)

        standalone_markdown_result = _run_command(
            "preservation_evidence_bundle_cli.py",
            "--input",
            str(input_path),
            "--format",
            "markdown",
        )
        _assert_clean_local_command(standalone_markdown_result, temp_dir)
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
        _assert_clean_local_command(backend_plan_result, temp_dir)
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
        _assert_clean_local_command(backend_plan_text_result, temp_dir)
        _assert_local_only_text(backend_plan_text_result.stdout)

        backend_plan_markdown_result = _run_command(
            "preservation_backend_plan_cli.py",
            "--input",
            str(backend_input_path),
            "--format",
            "markdown",
        )
        _assert_clean_local_command(backend_plan_markdown_result, temp_dir)
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
        _assert_clean_local_command(total_export_result, temp_dir)
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
        _assert_clean_local_command(total_export_text_result, temp_dir)
        _assert_local_only_text(total_export_text_result.stdout)

        temp_file_names = sorted(path.name for path in Path(temp_dir).iterdir())
        assert temp_file_names == ["backend_plan.json", "evidence_bundle.json"], temp_file_names
        assert not (Path(temp_dir) / "captures").exists()


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle scope invariant self-test passed.")
