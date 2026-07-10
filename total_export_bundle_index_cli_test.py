import hashlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_bundle_index_cli import main
from total_export_zip_sidecar import (
    build_zip_sha256_sidecar_text,
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
)


def _write_fake_zip(path: Path, data: bytes = b"fake bundle index cli zip\n") -> str:
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _write_complete_bundle(root: Path, name: str = "bundle.zip") -> Path:
    zip_path = root / name
    sha256_value = _write_fake_zip(zip_path)
    Path(default_zip_sha256_sidecar_path(str(zip_path))).write_text(
        build_zip_sha256_sidecar_text(str(zip_path), sha256_value),
        encoding="utf-8",
    )
    Path(default_zip_json_sidecar_path(str(zip_path))).write_text(
        json.dumps(
            {
                "sidecar_metadata": {
                    "format": "total_export_zip_inspection",
                    "version": 1,
                    "zip_basename": zip_path.name,
                    "zip_path": str(zip_path),
                },
                "zip_inspection": {
                    "entry_count": 2,
                    "file_entry_count": 2,
                    "status": "ok",
                    "zip_sha256": sha256_value,
                    "zip_size_bytes": zip_path.stat().st_size,
                },
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
        bundle = _write_complete_bundle(root, "complete.zip")
        nested = root / "nested"
        nested.mkdir()
        nested_bundle = _write_complete_bundle(nested, "nested.zip")

        code, stdout, stderr = _run_cli(["--root", str(root)])
        assert code == 0
        assert stderr == ""
        assert "Total Export bundle index" in stdout
        assert f"Root path: {root}" in stdout
        assert "ZIP count: 1" in stdout
        assert "complete" in stdout
        assert str(bundle) in stdout
        assert str(nested_bundle) not in stdout
        assert "no ZIP extraction, network, archive checks, downloads" in stdout

        code, markdown, stderr = _run_cli(["--root", str(root), "--format", "markdown"])
        assert code == 0
        assert stderr == ""
        assert "# Total Export Bundle Index" in markdown
        assert "| ZIP path | Status | Size bytes | SHA-256 sidecar | SHA-256 matches | Inspection sidecar | Inspection readable | Recommended actions |" in markdown
        assert "## Safety Notes" in markdown

        code, json_output, stderr = _run_cli(["--root", str(root), "--format", "json"])
        assert code == 0
        assert stderr == ""
        parsed = json.loads(json_output)
        assert parsed["root_path"] == str(root)
        assert parsed["recursive"] is False
        assert parsed["zip_count"] == 1
        assert parsed["status_counts"]["complete"] == 1
        assert parsed["items"][0]["zip_path"] == str(bundle)

        code, recursive_json, stderr = _run_cli(
            ["--root", str(root), "--recursive", "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        recursive = json.loads(recursive_json)
        assert recursive["recursive"] is True
        assert recursive["zip_count"] == 2
        assert any(item["zip_path"] == str(nested_bundle) for item in recursive["items"])

        code, no_hash_json, stderr = _run_cli(
            ["--root", str(root), "--no-compute-hash", "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        no_hash = json.loads(no_hash_json)
        assert no_hash["items"][0]["status"] == "needs_review"
        assert no_hash["items"][0]["zip_sha256"] == ""
        assert any("not compared" in warning for warning in no_hash["items"][0]["warnings"])

        output_path = root / "TOTAL_EXPORT_BUNDLE_INDEX_REPORT.md"
        code, stdout, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--format",
                "markdown",
                "--output",
                str(output_path),
            ]
        )
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert output_path.read_text(encoding="utf-8").startswith("# Total Export Bundle Index")

        code, stdout, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--format",
                "markdown",
                "--output",
                str(output_path),
            ]
        )
        assert code == 1
        assert stdout == ""
        assert "Output file already exists" in stderr

        output_path.write_text("old\n", encoding="utf-8")
        code, stdout, stderr = _run_cli(
            [
                "--root",
                str(root),
                "--format",
                "markdown",
                "--output",
                str(output_path),
                "--overwrite",
            ]
        )
        assert code == 0
        assert stdout == ""
        assert stderr == ""
        assert "# Total Export Bundle Index" in output_path.read_text(encoding="utf-8")

        code, missing_stdout, stderr = _run_cli(
            ["--root", str(root / "missing"), "--format", "json"]
        )
        assert code == 0
        assert stderr == ""
        missing = json.loads(missing_stdout)
        assert missing["zip_count"] == 0
        assert missing["errors"]
        assert "does not exist" in missing["errors"][0]


if __name__ == "__main__":
    run_self_test()
    print("Total Export bundle index CLI self-test passed.")
