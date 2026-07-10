import hashlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_bundle_index_reconcile_cli import main
from total_export_zip_sidecar import (
    build_zip_sha256_sidecar_text,
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
)


def _write_complete_bundle(root: Path, name: str) -> Path:
    zip_path = root / name
    data = f"fake reconciliation CLI bundle: {name}\n".encode("utf-8")
    zip_path.write_bytes(data)
    sha256_value = hashlib.sha256(data).hexdigest()
    Path(default_zip_sha256_sidecar_path(str(zip_path))).write_text(
        build_zip_sha256_sidecar_text(str(zip_path), sha256_value),
        encoding="utf-8",
    )
    Path(default_zip_json_sidecar_path(str(zip_path))).write_text(
        json.dumps(
            {
                "zip_inspection": {
                    "entry_count": 1,
                    "file_entry_count": 1,
                    "status": "ok",
                    "zip_sha256": sha256_value,
                    "zip_size_bytes": zip_path.stat().st_size,
                }
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return zip_path


def _run_cli(argv: list[str]):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        complete_zip = _write_complete_bundle(root, "complete.zip")
        missing_zip = root / "missing.zip"
        nested = root / "nested"
        nested.mkdir()
        nested_zip = _write_complete_bundle(nested, "nested.zip")

        object_input = root / "expected.json"
        object_input.write_text(
            json.dumps(
                {
                    "expected_bundles": [
                        {
                            "expected_zip_path": str(complete_zip),
                            "package_id": "complete-package",
                            "source_url": "https://example.invalid/complete",
                            "notes": "Manual expected bundle.",
                        },
                        str(missing_zip),
                    ]
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        code, text, stderr = _run_cli(
            ["--root", str(root), "--expected", str(object_input)]
        )
        assert code == 0
        assert stderr == ""
        assert "Total Export bundle index reconciliation" in text
        assert "Expected count: 2" in text
        assert "Present expected count: 1" in text
        assert "Missing expected count: 1" in text
        assert "Unexpected ZIP count: 0" in text
        assert "no ZIP extraction, network, archive checks, downloads" in text

        code, markdown, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--expected",
                str(object_input),
                "--format",
                "markdown",
            ]
        )
        assert code == 0
        assert stderr == ""
        assert "# Total Export Bundle Index Reconciliation" in markdown
        assert "| ZIP path | Status | Index status | Sidecars OK | Follow-up | Warnings | Recommended actions |" in markdown
        assert "## Safety Notes" in markdown
        assert "No ZIP extraction is performed" in markdown

        code, json_output, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--expected",
                str(object_input),
                "--format",
                "json",
            ]
        )
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert parsed["expected_count"] == 2
        assert parsed["present_expected_count"] == 1
        assert parsed["missing_expected_count"] == 1
        assert parsed["unexpected_zip_count"] == 0
        assert parsed["items"][0]["status"] == "present"
        assert parsed["items"][0]["package_id"] == "complete-package"
        assert parsed["items"][1]["status"] == "missing_expected_zip"

        bare_input = root / "expected_bare.json"
        bare_input.write_text(json.dumps([str(complete_zip)]), encoding="utf-8")
        code, bare_json, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--expected",
                str(bare_input),
                "--format",
                "json",
            ]
        )
        assert code == 0
        assert stderr == ""
        assert json.loads(bare_json)["present_expected_count"] == 1

        text_input = root / "expected.txt"
        text_input.write_text(
            f"# Local expected bundles\n\n{complete_zip}\n{missing_zip}\n",
            encoding="utf-8",
        )
        code, text_json, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--expected",
                str(text_input),
                "--format",
                "json",
            ]
        )
        assert code == 0
        assert stderr == ""
        assert json.loads(text_json)["expected_count"] == 2

        nested_input = root / "expected_nested.json"
        nested_input.write_text(
            json.dumps([str(complete_zip), str(nested_zip)]),
            encoding="utf-8",
        )
        code, non_recursive_json, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--expected",
                str(nested_input),
                "--format",
                "json",
            ]
        )
        assert code == 0
        assert stderr == ""
        non_recursive = json.loads(non_recursive_json)
        assert non_recursive["present_expected_count"] == 1
        assert non_recursive["missing_expected_count"] == 1

        code, recursive_json, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--expected",
                str(nested_input),
                "--recursive",
                "--format",
                "json",
            ]
        )
        assert code == 0
        assert stderr == ""
        recursive = json.loads(recursive_json)
        assert recursive["present_expected_count"] == 2
        assert recursive["missing_expected_count"] == 0

        code, no_hash_json, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--expected",
                str(bare_input),
                "--no-compute-hash",
                "--format",
                "json",
            ]
        )
        assert code == 0
        assert stderr == ""
        no_hash = json.loads(no_hash_json)
        assert no_hash["items"][0]["status"] == "present_needs_review"
        assert no_hash["items"][0]["index_status"] == "needs_review"
        assert any("not compared" in warning for warning in no_hash["items"][0]["warnings"])

        output_path = root / "TOTAL_EXPORT_BUNDLE_INDEX_RECONCILE_REPORT.md"
        output_args = [
            "--root",
            str(root),
            "--expected",
            str(bare_input),
            "--format",
            "markdown",
            "--output",
            str(output_path),
        ]
        code, stdout, stderr = _run_cli(output_args)
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith(
            "# Total Export Bundle Index Reconciliation"
        )

        code, stdout, stderr = _run_cli(output_args)
        assert code == 1
        assert stdout == ""
        assert "Output file already exists" in stderr

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli([*output_args, "--overwrite"])
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "# Total Export Bundle Index Reconciliation" in output_path.read_text(
            encoding="utf-8"
        )

        code, stdout, stderr = _run_cli(
            ["--root", str(root), "--expected", str(root / "missing.json")]
        )
        assert code == 1
        assert stdout == ""
        assert "does not exist" in stderr

        invalid_json = root / "invalid.json"
        invalid_json.write_text("{not json\n", encoding="utf-8")
        code, stdout, stderr = _run_cli(
            ["--root", str(root), "--expected", str(invalid_json)]
        )
        assert code == 1
        assert stdout == ""
        assert "Invalid expected bundle JSON" in stderr


if __name__ == "__main__":
    run_self_test()
    print("Total Export bundle index reconciliation CLI self-test passed.")
