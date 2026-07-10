import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from total_export_bundle_index import (
    BUNDLE_INDEX_STATUS_COMPLETE,
    BUNDLE_INDEX_STATUS_INSPECTION_UNREADABLE,
    BUNDLE_INDEX_STATUS_MISSING_INSPECTION_SIDECAR,
    BUNDLE_INDEX_STATUS_MISSING_SHA256_SIDECAR,
    BUNDLE_INDEX_STATUS_NEEDS_REVIEW,
    BUNDLE_INDEX_STATUS_SHA256_MISMATCH,
    build_bundle_index,
    build_bundle_index_item,
    build_bundle_index_markdown,
    build_bundle_index_text,
    bundle_index_item_to_dict,
    bundle_index_to_dict,
    find_bundle_zip_files,
    read_sha256_sidecar,
    sha256_file,
)
from total_export_zip_sidecar import (
    build_zip_sha256_sidecar_text,
    default_zip_json_sidecar_path,
    default_zip_sha256_sidecar_path,
)


def _write_fake_zip(path: Path, data: bytes = b"fake zip bytes\n") -> str:
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _write_sha_sidecar(zip_path: Path, sha256_value: str) -> Path:
    sidecar = Path(default_zip_sha256_sidecar_path(str(zip_path)))
    sidecar.write_text(build_zip_sha256_sidecar_text(str(zip_path), sha256_value), encoding="utf-8")
    return sidecar


def _write_inspection_sidecar(zip_path: Path, sha256_value: str, size_bytes: int) -> Path:
    sidecar = Path(default_zip_json_sidecar_path(str(zip_path)))
    sidecar.write_text(
        json.dumps(
            {
                "sidecar_metadata": {
                    "format": "total_export_zip_inspection",
                    "version": 1,
                    "zip_basename": zip_path.name,
                    "zip_path": str(zip_path),
                },
                "zip_inspection": {
                    "entry_count": 3,
                    "file_entry_count": 3,
                    "status": "ok",
                    "zip_sha256": sha256_value,
                    "zip_size_bytes": size_bytes,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return sidecar


def _write_complete_bundle(root: Path, name: str = "bundle.zip") -> Path:
    zip_path = root / name
    sha = _write_fake_zip(zip_path)
    _write_sha_sidecar(zip_path, sha)
    _write_inspection_sidecar(zip_path, sha, zip_path.stat().st_size)
    return zip_path


def run_self_test() -> None:
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        complete_zip = _write_complete_bundle(root, "complete.zip")
        complete_item = build_bundle_index_item(str(complete_zip))
        assert complete_item.status == BUNDLE_INDEX_STATUS_COMPLETE
        assert complete_item.zip_filename == "complete.zip"
        assert complete_item.zip_size_bytes == complete_zip.stat().st_size
        assert complete_item.zip_sha256 == sha256_file(str(complete_zip))
        assert complete_item.sha256_sidecar_present is True
        assert complete_item.sha256_sidecar_matches is True
        assert complete_item.inspection_sidecar_present is True
        assert complete_item.inspection_sidecar_readable is True
        assert complete_item.inspection_summary["status"] == "ok"
        assert complete_item.recommended_actions == ()

        unchecked_hash = build_bundle_index_item(str(complete_zip), compute_hash=False)
        assert unchecked_hash.status == BUNDLE_INDEX_STATUS_NEEDS_REVIEW
        assert unchecked_hash.zip_sha256 == ""
        assert any("not compared" in warning for warning in unchecked_hash.warnings)

        sha_path = Path(default_zip_sha256_sidecar_path(str(complete_zip)))
        assert read_sha256_sidecar(str(sha_path)) == complete_item.zip_sha256
        hash_only_path = root / "hash_only.sha256"
        hash_only_path.write_text(complete_item.zip_sha256 + "\n", encoding="utf-8")
        assert read_sha256_sidecar(str(hash_only_path)) == complete_item.zip_sha256

        missing_sha_zip = _write_complete_bundle(root, "missing_sha.zip")
        Path(default_zip_sha256_sidecar_path(str(missing_sha_zip))).unlink()
        missing_sha = build_bundle_index_item(str(missing_sha_zip))
        assert missing_sha.status == BUNDLE_INDEX_STATUS_MISSING_SHA256_SIDECAR
        assert missing_sha.sha256_sidecar_present is False
        assert any("SHA256 sidecar missing" in warning for warning in missing_sha.warnings)

        mismatch_zip = _write_complete_bundle(root, "mismatch.zip")
        _write_sha_sidecar(mismatch_zip, "0" * 64)
        mismatch = build_bundle_index_item(str(mismatch_zip))
        assert mismatch.status == BUNDLE_INDEX_STATUS_SHA256_MISMATCH
        assert mismatch.sha256_sidecar_matches is False
        assert any("does not match" in warning for warning in mismatch.warnings)

        missing_json_zip = _write_complete_bundle(root, "missing_json.zip")
        Path(default_zip_json_sidecar_path(str(missing_json_zip))).unlink()
        missing_json = build_bundle_index_item(str(missing_json_zip))
        assert missing_json.status == BUNDLE_INDEX_STATUS_MISSING_INSPECTION_SIDECAR
        assert missing_json.inspection_sidecar_present is False

        invalid_json_zip = _write_complete_bundle(root, "invalid_json.zip")
        Path(default_zip_json_sidecar_path(str(invalid_json_zip))).write_text("{not json\n", encoding="utf-8")
        invalid_json = build_bundle_index_item(str(invalid_json_zip))
        assert invalid_json.status == BUNDLE_INDEX_STATUS_INSPECTION_UNREADABLE
        assert invalid_json.inspection_sidecar_present is True
        assert invalid_json.inspection_sidecar_readable is False

        nested = root / "nested"
        nested.mkdir()
        nested_zip = _write_complete_bundle(nested, "nested.zip")
        assert tuple(path.name for path in find_bundle_zip_files(str(root), recursive=False)) == (
            "complete.zip",
            "invalid_json.zip",
            "mismatch.zip",
            "missing_json.zip",
            "missing_sha.zip",
        )
        recursive_names = tuple(
            path.relative_to(root).as_posix()
            for path in find_bundle_zip_files(str(root), recursive=True)
        )
        assert "nested/nested.zip" in recursive_names

        non_recursive = build_bundle_index(str(root), recursive=False)
        assert non_recursive.zip_count == 5
        assert non_recursive.status_counts[BUNDLE_INDEX_STATUS_COMPLETE] == 1
        assert non_recursive.status_counts[BUNDLE_INDEX_STATUS_MISSING_SHA256_SIDECAR] == 1
        assert non_recursive.status_counts[BUNDLE_INDEX_STATUS_SHA256_MISMATCH] == 1
        assert non_recursive.status_counts[BUNDLE_INDEX_STATUS_MISSING_INSPECTION_SIDECAR] == 1
        assert non_recursive.status_counts[BUNDLE_INDEX_STATUS_INSPECTION_UNREADABLE] == 1

        recursive = build_bundle_index(str(root), recursive=True)
        assert recursive.zip_count == 6
        assert any(item.zip_path == str(nested_zip) for item in recursive.items)

        item_dict = bundle_index_item_to_dict(complete_item)
        assert list(item_dict) == [
            "zip_path",
            "zip_filename",
            "zip_size_bytes",
            "zip_sha256",
            "sha256_sidecar_path",
            "sha256_sidecar_present",
            "sha256_sidecar_matches",
            "inspection_sidecar_path",
            "inspection_sidecar_present",
            "inspection_sidecar_readable",
            "inspection_summary",
            "review_folder_path",
            "review_folder_present",
            "status",
            "warnings",
            "recommended_actions",
        ]

        result_dict = bundle_index_to_dict(non_recursive)
        assert list(result_dict) == [
            "errors",
            "items",
            "recursive",
            "root_path",
            "status_counts",
            "warnings",
            "zip_count",
        ]
        assert result_dict["status_counts"][BUNDLE_INDEX_STATUS_COMPLETE] == 1

        text = build_bundle_index_text(non_recursive)
        assert "Total Export bundle index" in text
        assert "ZIP count: 5" in text
        assert "missing_sha256_sidecar" in text
        assert "no ZIP extraction, network, archive checks, downloads" in text

        markdown = build_bundle_index_markdown(non_recursive)
        assert "# Total Export Bundle Index" in markdown
        assert "| ZIP path | Status | Size bytes | SHA-256 sidecar | SHA-256 matches | Inspection sidecar | Inspection readable | Recommended actions |" in markdown
        assert "No ZIP extraction is performed" in markdown

        missing_root = build_bundle_index(str(root / "missing"))
        assert missing_root.zip_count == 0
        assert missing_root.errors
        assert "does not exist" in missing_root.errors[0]


if __name__ == "__main__":
    run_self_test()
    print("Total Export bundle index self-test passed.")
