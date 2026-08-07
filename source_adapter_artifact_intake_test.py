from __future__ import annotations

import hashlib
from pathlib import Path

from source_adapter_artifact_intake import ARTIFACT_INTAKE_STATUS, build_source_adapter_artifact_intake, output_documents


def _write(path: Path, data: bytes) -> dict:
    path.write_bytes(data)
    return {"byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _sample_session(tmp_path: Path) -> tuple[dict, list[dict]]:
    article_path = tmp_path / "article.html"
    metadata_path = tmp_path / "metadata.json"
    article = _write(article_path, b"<html><title>Example</title></html>")
    metadata = _write(metadata_path, b'{"title":"Example"}')
    session = {
        "source_adapter_capture_session_id": "source_adapter_capture_session.example",
        "artifact_receipts": [
            {
                "receipt_id": "r.article",
                "adapter_id": "article",
                "artifact_role": "article_html_or_text",
                "artifact_basename": "article.html",
                "source_url": "https://article.example/story",
                **article,
            },
            {
                "receipt_id": "r.metadata",
                "adapter_id": "article",
                "artifact_role": "metadata_json",
                "artifact_basename": "metadata.json",
                "source_url": "https://article.example/story",
                **metadata,
            },
        ],
    }
    bindings = [
        {"receipt_id": "r.article", "path": str(article_path)},
        {"receipt_id": "r.metadata", "path": str(metadata_path)},
    ]
    return session, bindings


def test_builds_artifact_intake(tmp_path: Path) -> None:
    session, bindings = _sample_session(tmp_path)
    package = build_source_adapter_artifact_intake(session, bindings)
    assert package["artifact_intake_status"] == ARTIFACT_INTAKE_STATUS
    assert package["source_adapter_artifact_intake_id"].startswith("source_adapter_artifact_intake.")
    assert package["receipt_count"] == 2
    assert package["artifact_file_count"] == 2
    assert package["collection_count"] == 1
    assert package["source_artifact_collections"][0]["collection_status"] == "READY_FOR_EXTRACTION"
    assert package["safety_contract"]["artifact_bytes_read_for_hash_validation"] is True
    assert package["safety_contract"]["full_local_paths_serialized"] is False


def test_rejects_hash_mismatch(tmp_path: Path) -> None:
    session, bindings = _sample_session(tmp_path)
    session["artifact_receipts"][0]["sha256"] = "0" * 64
    try:
        build_source_adapter_artifact_intake(session, bindings)
    except ValueError as exc:
        assert "sha256 mismatch" in str(exc)
    else:
        raise AssertionError("hash mismatch was accepted")


def test_rejects_basename_mismatch(tmp_path: Path) -> None:
    session, bindings = _sample_session(tmp_path)
    other = tmp_path / "other.html"
    other.write_bytes((tmp_path / "article.html").read_bytes())
    bindings[0] = {"receipt_id": "r.article", "path": str(other)}
    try:
        build_source_adapter_artifact_intake(session, bindings)
    except ValueError as exc:
        assert "basename mismatch" in str(exc)
    else:
        raise AssertionError("basename mismatch was accepted")


def test_output_documents_have_expected_roles(tmp_path: Path) -> None:
    session, bindings = _sample_session(tmp_path)
    docs = output_documents(build_source_adapter_artifact_intake(session, bindings))
    assert sorted(docs) == [
        "source_adapter_artifact_collection_handoff",
        "source_adapter_artifact_collection_index",
        "source_adapter_artifact_intake_operator_summary",
        "source_adapter_artifact_intake_package",
        "source_adapter_artifact_intake_validation_report",
    ]


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_builds_artifact_intake(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_rejects_hash_mismatch(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_rejects_basename_mismatch(Path(tmp))
    with tempfile.TemporaryDirectory() as tmp:
        test_output_documents_have_expected_roles(Path(tmp))
    print("Source Adapter Artifact Intake self-test passed.")
