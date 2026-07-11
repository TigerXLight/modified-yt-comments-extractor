import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from preservation_evidence_bundle_cli import main


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def run_self_test() -> None:
    code, output, error = _run_cli([])
    assert code == 0
    assert error == ""
    assert "status: planned" in output
    assert "no file existence or capture execution is implied" in output

    args = [
        "--source-url",
        "https://www.telegraph.co.uk/news/example/",
        "--bundle-label",
        "Manual evidence",
        "--status",
        "manual_supplied",
        "--item",
        "screenshot:png:scrollable_container_screenshot",
        "--item-role",
        "screenshot=primary",
        "--item-origin",
        "screenshot=manual",
        "--item-path-hint",
        r"screenshot=captures\comments.png",
        "--item-notes",
        "screenshot=CLI supplied screenshot; path hint only.",
    ]
    code, text, error = _run_cli([*args, "--format", "text"])
    assert code == 0
    assert error == ""
    assert "status: manual_supplied" in text
    assert "screenshot: format=png" in text
    assert "role=primary" in text
    assert "origin=manual" in text
    assert r"path_hint=captures\comments.png" in text
    assert "notes=CLI supplied screenshot; path hint only." in text
    assert "focused or selected" in text
    assert "execution=metadata only" in text

    code, json_output, error = _run_cli([*args, "--format", "json"])
    assert code == 0
    assert error == ""
    parsed = json.loads(json_output)
    assert parsed["source_url"] == "https://www.telegraph.co.uk/news/example/"
    assert parsed["status"] == "manual_supplied"
    assert parsed["items"][0]["artifact_id"] == "screenshot"
    assert parsed["items"][0]["artifact_format"] == "png"
    assert parsed["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert parsed["items"][0]["artifact_role"] == "primary"
    assert parsed["items"][0]["origin"] == "manual"
    assert parsed["items"][0]["path_hint"] == r"captures\comments.png"
    assert parsed["items"][0]["notes"] == "CLI supplied screenshot; path hint only."
    assert "no file open" in parsed["scope"]

    with TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "evidence_bundle.json"
        input_path.write_text(
            json.dumps(
                {
                    "source_url": "https://www.telegraph.co.uk/news/example/",
                    "bundle_label": "Input evidence",
                    "status": "manual_supplied",
                    "items": [
                        {
                            "artifact_id": "screenshot",
                            "artifact_format": "png",
                            "capture_method_id": "scrollable_container_screenshot",
                            "artifact_role": "primary",
                            "origin": "manual",
                            "path_hint": r"captures\comments.png",
                            "notes": "Input JSON path hint only.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        code, json_output, error = _run_cli(
            ["--input", str(input_path), "--format", "json"]
        )
        assert code == 0
        assert error == ""
        parsed = json.loads(json_output)
        assert parsed["bundle_label"] == "Input evidence"
        assert parsed["status"] == "manual_supplied"
        assert parsed["items"][0]["artifact_id"] == "screenshot"
        assert parsed["items"][0]["artifact_role"] == "primary"
        assert parsed["items"][0]["origin"] == "manual"
        assert parsed["items"][0]["path_hint"] == r"captures\comments.png"
        assert parsed["items"][0]["notes"] == "Input JSON path hint only."
        assert "no file open" in parsed["scope"]

        code, output, error = _run_cli(
            ["--input", str(input_path), "--item", "screenshot:png"]
        )
        assert code == 1
        assert output == ""
        assert "--input cannot be combined" in error

        bad_input_path = Path(temp_dir) / "bad_bundle.json"
        bad_input_path.write_text("[]", encoding="utf-8")
        code, output, error = _run_cli(["--input", str(bad_input_path)])
        assert code == 1
        assert output == ""
        assert "input JSON must be an object" in error

        bad_input_items_path = Path(temp_dir) / "bad_input_items.json"
        bad_input_items_path.write_text(
            json.dumps({"items": "screenshot"}),
            encoding="utf-8",
        )
        code, output, error = _run_cli(["--input", str(bad_input_items_path)])
        assert code == 1
        assert output == ""
        assert "evidence_bundle.items must be a list" in error

        bad_input_item_path = Path(temp_dir) / "bad_input_item.json"
        bad_input_item_path.write_text(
            json.dumps({"items": ["screenshot"]}),
            encoding="utf-8",
        )
        code, output, error = _run_cli(["--input", str(bad_input_item_path)])
        assert code == 1
        assert output == ""
        assert "evidence bundle item must be an object" in error

        bad_input_capture_method_path = Path(temp_dir) / "bad_input_capture_method.json"
        bad_input_capture_method_path.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "artifact_id": "screenshot",
                            "artifact_format": "png",
                            "capture_method_id": "unknown_capture",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        code, output, error = _run_cli(["--input", str(bad_input_capture_method_path)])
        assert code == 1
        assert output == ""
        assert "invalid capture method ID" in error

        duplicate_input_item_path = Path(temp_dir) / "duplicate_input_item.json"
        duplicate_input_item_path.write_text(
            json.dumps(
                {
                    "items": [
                        {"artifact_id": "screenshot", "artifact_format": "png"},
                        {"artifact_id": "screenshot", "artifact_format": "html"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        code, output, error = _run_cli(["--input", str(duplicate_input_item_path)])
        assert code == 1
        assert output == ""
        assert "duplicate artifact IDs: screenshot" in error

        missing_input_path = Path(temp_dir) / "missing_bundle.json"
        code, output, error = _run_cli(["--input", str(missing_input_path)])
        assert code == 1
        assert output == ""
        assert "input file not found" in error

        invalid_json_path = Path(temp_dir) / "invalid_bundle.json"
        invalid_json_path.write_text("{", encoding="utf-8")
        code, output, error = _run_cli(["--input", str(invalid_json_path)])
        assert code == 1
        assert output == ""
        assert "invalid JSON in" in error

    code, output, error = _run_cli(["--item", "bad:exe"])
    assert code == 1
    assert output == ""
    assert "invalid artifact format" in error

    code, output, error = _run_cli(["--item", "bad:png:unknown"])
    assert code == 1
    assert output == ""
    assert "invalid capture method ID" in error

    code, output, error = _run_cli(
        ["--item", "screenshot:png", "--item-role", "missing=primary"]
    )
    assert code == 1
    assert output == ""
    assert "unknown artifact IDs" in error

    code, output, error = _run_cli(
        ["--item", "screenshot:png", "--item-role", "screenshot-primary"]
    )
    assert code == 1
    assert output == ""
    assert "item role must use artifact_id=value" in error

    code, output, error = _run_cli(
        [
            "--item",
            "screenshot:png",
            "--item-role",
            "screenshot=primary",
            "--item-role",
            "screenshot=supporting",
        ]
    )
    assert code == 1
    assert output == ""
    assert "duplicate item role metadata" in error

    code, output, error = _run_cli(
        ["--item", "same:png", "--item", "same:html"]
    )
    assert code == 1
    assert output == ""
    assert "duplicate artifact IDs: same" in error

    code, output, error = _run_cli(["--item", "missing_format"])
    assert code == 1
    assert output == ""
    assert "artifact_id:artifact_format" in error


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle CLI self-test passed.")
