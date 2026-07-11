from pathlib import Path
from tempfile import TemporaryDirectory
import json

from total_export_package_zip import create_total_export_package_zip
from total_export_prepare import prepare_total_export_with_summary
from total_export_zip_sidecar import (
    build_total_export_zip_sidecar_text,
    build_zip_sha256_sidecar_text,
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
    write_total_export_zip_sidecars,
    zip_sidecar_result_to_dict,
)


VALID_ID = "aB3_dE-9xYz"


def _prepare_zip(temp_dir: str) -> str:
    prepared = prepare_total_export_with_summary(
        base_folder=temp_dir,
        source_url=f"https://www.youtube.com/watch?v={VALID_ID}&t=30s",
        selected_capture_options=["comments"],
        package_id="zip sidecar package",
        create_asset_folders=False,
        write_readme=True,
        write_plan_report=True,
        write_inventory_report=True,
    )
    package_folder = prepared.workflow_result.package_result.package_result.package_folder
    zip_result = create_total_export_package_zip(package_folder)
    assert zip_result.zip_created
    return zip_result.zip_path

def _assert_sidecar_write_state(result, *, sha256_written: bool, json_written: bool) -> None:
    assert result.sha256_written is sha256_written
    assert result.json_written is json_written



def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        zip_path = _prepare_zip(temp_dir)
        result = write_total_export_zip_sidecars(zip_path)
        _assert_sidecar_write_state(result, sha256_written=True, json_written=True)
        assert result.sha256_path == default_zip_sha256_sidecar_path(zip_path)
        assert result.json_path == default_zip_json_sidecar_path(zip_path)
        assert Path(result.sha256_path).is_file()
        assert Path(result.json_path).is_file()
        assert Path(result.sha256_path).read_text(encoding="utf-8") == (
            f"{result.zip_sha256}  {Path(zip_path).name}\n"
        )
        assert build_zip_sha256_sidecar_text(zip_path, result.zip_sha256).endswith("\n")

        sidecar_json = json.loads(Path(result.json_path).read_text(encoding="utf-8"))
        inspection = sidecar_json["zip_inspection"]
        assert sidecar_json["sidecar_metadata"]["zip_basename"] == Path(zip_path).name
        assert inspection["zip_sha256"] == result.zip_sha256
        assert inspection["status"] == "ok"
        assert any(
            entry["relative_path"] == "metadata/SOURCE_CAPTURE_PLAN.txt"
            for entry in inspection["standard_entries"]
        )

        existing = write_total_export_zip_sidecars(zip_path)
        _assert_sidecar_write_state(existing, sha256_written=False, json_written=False)
        assert any("already exists" in error for error in existing.errors)

        overwritten = write_total_export_zip_sidecars(zip_path, overwrite=True)
        _assert_sidecar_write_state(overwritten, sha256_written=True, json_written=True)

        custom_sha_path = str(Path(temp_dir) / "custom" / "custom.sha256")
        custom_json_path = str(Path(temp_dir) / "custom" / "custom.inspection.json")
        custom = write_total_export_zip_sidecars(
            zip_path,
            sha256_path=custom_sha_path,
            json_path=custom_json_path,
        )
        _assert_sidecar_write_state(custom, sha256_written=True, json_written=True)
        assert custom.sha256_path == custom_sha_path
        assert custom.json_path == custom_json_path
        assert Path(custom_sha_path).is_file()
        assert Path(custom_json_path).is_file()

        same_as_zip = write_total_export_zip_sidecars(
            zip_path,
            sha256_path=zip_path,
            json_path=str(Path(temp_dir) / "same_as_zip.json"),
        )
        _assert_sidecar_write_state(same_as_zip, sha256_written=False, json_written=False)
        assert any("must not equal the ZIP path" in error for error in same_as_zip.errors)

        missing_zip_path = str(Path(temp_dir) / "missing.zip")
        missing = write_total_export_zip_sidecars(missing_zip_path)
        _assert_sidecar_write_state(missing, sha256_written=False, json_written=False)
        assert missing.zip_status == "missing_zip"
        assert any("inspection status" in error for error in missing.errors)

        missing_diagnostic_json_path = str(Path(temp_dir) / "missing.inspection.json")
        missing_diagnostic = write_total_export_zip_sidecars(
            missing_zip_path,
            json_path=missing_diagnostic_json_path,
            require_zip_status_ok=False,
        )
        _assert_sidecar_write_state(missing_diagnostic, sha256_written=False, json_written=True)
        assert Path(missing_diagnostic_json_path).is_file()
        missing_json = json.loads(Path(missing_diagnostic_json_path).read_text(encoding="utf-8"))
        assert missing_json["zip_inspection"]["status"] == "missing_zip"

        invalid_zip_path = Path(temp_dir) / "invalid.zip"
        invalid_zip_path.write_text("not a zip", encoding="utf-8")
        invalid = write_total_export_zip_sidecars(str(invalid_zip_path))
        _assert_sidecar_write_state(invalid, sha256_written=False, json_written=False)
        assert invalid.zip_status == "invalid_zip"

        invalid_diagnostic = write_total_export_zip_sidecars(
            str(invalid_zip_path),
            sha256_path=str(Path(temp_dir) / "invalid.sha256"),
            json_path=str(Path(temp_dir) / "invalid.inspection.json"),
            require_zip_status_ok=False,
        )
        _assert_sidecar_write_state(invalid_diagnostic, sha256_written=True, json_written=True)

        entries_result = write_total_export_zip_sidecars(
            zip_path,
            sha256_path=str(Path(temp_dir) / "entries.sha256"),
            json_path=str(Path(temp_dir) / "entries.inspection.json"),
            include_entries=True,
            hash_entries=True,
        )
        entries_json = json.loads(Path(entries_result.json_path).read_text(encoding="utf-8"))
        assert entries_json["zip_inspection"]["entries"]
        assert any(
            entry["sha256"]
            for entry in entries_json["zip_inspection"]["entries"]
            if not entry["is_dir"]
        )

        as_dict = zip_sidecar_result_to_dict(result)
        assert set(as_dict) == {
            "errors",
            "json_path",
            "json_written",
            "sha256_path",
            "sha256_written",
            "warnings",
            "zip_entry_count",
            "zip_file_entry_count",
            "zip_path",
            "zip_sha256",
            "zip_size_bytes",
            "zip_status",
        }
        assert as_dict["zip_status"] == "ok"

        text = build_total_export_zip_sidecar_text(result)
        assert "Total Export ZIP sidecars" in text
        assert "SHA256 written: yes" in text
        assert "JSON written: yes" in text
        assert "ZIP status: ok" in text


if __name__ == "__main__":
    run_self_test()
    print("Total Export ZIP sidecar self-test passed.")
