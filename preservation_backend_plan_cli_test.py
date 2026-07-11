import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from preservation_backend_plan_cli import main


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def _assert_cli_failure(argv: list[str], expected_error: str) -> None:
    code, stdout, stderr = _run_cli(argv)
    assert code == 1
    assert stdout == ""
    assert expected_error in stderr


def _run_cli_error(argv: list[str]) -> tuple[int, str]:
    stderr = io.StringIO()
    try:
        with redirect_stderr(stderr):
            main(argv)
    except SystemExit as exc:
        return int(exc.code), stderr.getvalue()
    raise AssertionError("Expected argparse SystemExit.")


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def run_self_test() -> None:
    code, markdown, stderr = _run_cli([])
    assert code == 0
    assert stderr == ""
    assert "# Preservation Backend Plan" in markdown
    assert "Status: needs_selection" in markdown
    assert "Manual local files" in markdown
    assert "ArchiveBox-style self-hosted store" in markdown
    assert "does not fetch URLs" in markdown
    assert "Media preservation choice: none" in markdown
    assert "No capture method is selected or specified" in markdown

    code, text, stderr = _run_cli(["--format", "text"])
    assert code == 0
    assert stderr == ""
    assert "Preservation backend plan" in text
    assert "manual_local_files" in text
    assert "archivebox_self_hosted" in text
    assert "no fetch/capture/network" in text
    assert "media_preservation_choice: none" in text

    code, json_output, stderr = _run_cli(["--format", "json"])
    assert code == 0
    assert stderr == ""
    parsed = json.loads(json_output)
    assert parsed["status"] == "needs_selection"
    assert parsed["selected_backend_ids"] == []
    assert parsed["selected_format_ids"] == []
    assert parsed["media_preservation_choice"] == "none"
    assert any(
        item["backend_id"] == "archivebox_self_hosted"
        for item in parsed["available_backends"]
    )
    assert any(item["format_id"] == "warc" for item in parsed["available_formats"])

    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        input_path = root / "preservation_plan.json"
        _write_json(
            input_path,
            {
                "source_url": "https://www.telegraph.co.uk/news/example/?utm=x",
                "selected_backend_ids": [
                    "manual_local_files",
                    "archivebox_self_hosted",
                    "manual_local_files",
                    "unknown_backend",
                ],
                "selected_format_ids": ["html", "pdf", "warc", "html"],
                "media_preservation_choice": "select",
                "selected_capture_method_ids": [
                    "visible_screenshot",
                    "scrollable_container_screenshot",
                ],
                "notes": "User wants backup metadata only.",
            },
        )

        code, plan_json, stderr = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed_plan = json.loads(plan_json)
        assert parsed_plan["status"] == "ready"
        assert parsed_plan["selected_backend_ids"] == [
            "manual_local_files",
            "archivebox_self_hosted",
        ]
        assert parsed_plan["selected_format_ids"] == ["html", "pdf", "warc"]
        assert parsed_plan["unknown_backend_ids"] == ["unknown_backend"]
        assert parsed_plan["duplicate_backend_ids"] == ["manual_local_files"]
        assert parsed_plan["duplicate_format_ids"] == ["html"]
        assert parsed_plan["media_preservation_choice"] == "select"
        assert parsed_plan["selected_capture_method_ids"] == [
            "visible_screenshot",
            "scrollable_container_screenshot",
        ]
        assert parsed_plan["capture_methods"][1]["display_name"] == "Scrollable-container screenshot"

        code, direct_capture_json, stderr = _run_cli(
            [
                "--capture-method",
                "raw_saved_html",
                "--capture-method",
                "manual_evidence_bundle",
                "--format",
                "json",
            ]
        )
        assert code == 0
        assert stderr == ""
        parsed_direct = json.loads(direct_capture_json)
        assert parsed_direct["selected_capture_method_ids"] == [
            "raw_saved_html",
            "manual_evidence_bundle",
        ]

        error_code, error_output = _run_cli_error(
            ["--capture-method", "unknown_capture"]
        )
        assert error_code == 2
        assert "invalid choice" in error_output

        output_path = root / "PRESERVATION_BACKEND_PLAN.md"
        output_args = ["--input", str(input_path), "--output", str(output_path)]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Preservation Backend Plan"
        )

        _assert_cli_failure(output_args, "output path already exists")

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "Selected backends: manual_local_files, archivebox_self_hosted" in (
            output_path.read_text(encoding="utf-8")
        )

        missing_input = root / "missing.json"
        _assert_cli_failure(
            ["--input", str(missing_input)],
            "input file not found",
        )

        invalid_input = root / "invalid.json"
        invalid_input.write_text("{not json\n", encoding="utf-8")
        _assert_cli_failure(
            ["--input", str(invalid_input)],
            "invalid JSON",
        )

        list_input = root / "list.json"
        _write_json(list_input, [])
        _assert_cli_failure(
            ["--input", str(list_input)],
            "input JSON must be an object",
        )

        bad_backends = root / "bad_backends.json"
        _write_json(bad_backends, {"selected_backend_ids": "manual_local_files"})
        _assert_cli_failure(
            ["--input", str(bad_backends)],
            "selected_backend_ids must be a list of strings",
        )

        bad_formats = root / "bad_formats.json"
        _write_json(bad_formats, {"selected_format_ids": "html"})
        _assert_cli_failure(
            ["--input", str(bad_formats)],
            "selected_format_ids must be a list of strings",
        )

        bad_media_choice = root / "bad_media_choice.json"
        _write_json(bad_media_choice, {"media_preservation_choice": "everything"})
        _assert_cli_failure(
            ["--input", str(bad_media_choice)],
            "expected one of none, select, all",
        )

    # input evidence bundle JSON should be rendered without opening or checking path hints
    with TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "plan_with_evidence_bundle.json"
        _write_json(
            input_path,
            {
                "source_url": "https://www.telegraph.co.uk/news/example/",
                "selected_backend_ids": ["manual_local_files"],
                "selected_format_ids": ["html"],
                "selected_capture_method_ids": ["scrollable_container_screenshot"],
                "media_preservation_choice": "select",
                "evidence_bundle": {
                    "source_url": "https://www.telegraph.co.uk/news/example/",
                    "bundle_label": "Input evidence",
                    "status": "manual_supplied",
                    "uploaded": True,
                    "items": [
                        {
                            "artifact_id": "screenshot",
                            "artifact_format": "png",
                            "capture_method_id": "scrollable_container_screenshot",
                            "artifact_role": "primary",
                            "origin": "manual",
                            "path_hint": r"captures\comments.png",
                            "notes": "Input JSON path hint only.",
                            "sha256": "not-computed",
                        }
                    ],
                },
            },
        )
        code, stdout, stderr = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(stdout)
        assert parsed["source_url"] == "https://www.telegraph.co.uk/news/example/"
        assert parsed["evidence_bundle"]["status"] == "manual_supplied"
        assert parsed["evidence_bundle"]["bundle_label"] == "Input evidence"
        assert "uploaded" not in parsed["evidence_bundle"]
        assert parsed["evidence_bundle"]["items"][0]["artifact_id"] == "screenshot"
        assert parsed["evidence_bundle"]["items"][0]["artifact_format"] == "png"
        assert parsed["evidence_bundle"]["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
        assert parsed["evidence_bundle"]["items"][0]["artifact_role"] == "primary"
        assert parsed["evidence_bundle"]["items"][0]["origin"] == "manual"
        assert parsed["evidence_bundle"]["items"][0]["path_hint"] == r"captures\comments.png"
        assert parsed["evidence_bundle"]["items"][0]["notes"] == "Input JSON path hint only."
        assert "sha256" not in parsed["evidence_bundle"]["items"][0]
        assert "no file open" in parsed["evidence_bundle"]["scope"]

        bad_input_path = Path(temp_dir) / "bad_plan_with_evidence_bundle.json"
        _write_json(
            bad_input_path,
            {
                "evidence_bundle": [],
            },
        )
        _assert_cli_failure(
            ["--input", str(bad_input_path)],
            "evidence_bundle must be an object",
        )

        bad_items_path = Path(temp_dir) / "bad_plan_with_evidence_bundle_items_string.json"
        _write_json(
            bad_items_path,
            {
                "evidence_bundle": {
                    "items": "screenshot",
                },
            },
        )
        _assert_cli_failure(
            ["--input", str(bad_items_path)],
            "evidence_bundle.items must be a list",
        )

        bad_item_object_path = Path(temp_dir) / "bad_plan_with_evidence_bundle_item_object.json"
        _write_json(
            bad_item_object_path,
            {
                "evidence_bundle": {
                    "items": ["screenshot"],
                },
            },
        )
        _assert_cli_failure(
            ["--input", str(bad_item_object_path)],
            "evidence bundle item must be an object",
        )

        bad_capture_method_path = Path(temp_dir) / "bad_plan_with_evidence_bundle_capture_method.json"
        _write_json(
            bad_capture_method_path,
            {
                "evidence_bundle": {
                    "items": [
                        {
                            "artifact_id": "screenshot",
                            "artifact_format": "png",
                            "capture_method_id": "unknown_capture",
                        }
                    ],
                },
            },
        )
        _assert_cli_failure(
            ["--input", str(bad_capture_method_path)],
            "invalid capture method ID",
        )

        duplicate_item_path = Path(temp_dir) / "bad_plan_with_evidence_bundle_duplicate_item.json"
        _write_json(
            duplicate_item_path,
            {
                "evidence_bundle": {
                    "items": [
                        {"artifact_id": "screenshot", "artifact_format": "png"},
                        {"artifact_id": "screenshot", "artifact_format": "html"},
                    ],
                },
            },
        )
        _assert_cli_failure(
            ["--input", str(duplicate_item_path)],
            "duplicate artifact IDs: screenshot",
        )

    # backend detail specs should reject malformed values before rendering
    _assert_cli_failure(
        [
            "--evidence-bundle-status",
            "manual_supplied",
            "--evidence-item",
            "screenshot:png",
            "--evidence-item-role",
            "screenshot-primary",
        ],
        "item role must use artifact_id=value",
    )

    _assert_cli_failure(
        [
            "--evidence-bundle-status",
            "manual_supplied",
            "--evidence-item",
            "screenshot:png",
            "--evidence-item-role",
            "missing=primary",
        ],
        "unknown artifact IDs",
    )

    _assert_cli_failure(
        [
            "--evidence-bundle-status",
            "manual_supplied",
            "--evidence-item",
            "screenshot:png",
            "--evidence-item-role",
            "screenshot=primary",
            "--evidence-item-role",
            "screenshot=supporting",
        ],
        "duplicate item role metadata",
    )



if __name__ == "__main__":
    run_self_test()
    print("Preservation backend plan CLI self-test passed.")
