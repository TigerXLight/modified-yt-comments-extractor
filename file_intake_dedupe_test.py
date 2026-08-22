import hashlib
import tempfile
from pathlib import Path

from file_intake_dedupe import (
    ExistingFileRecord,
    FILE_INTAKE_STATUS_ADDED,
    FILE_INTAKE_STATUS_DUPLICATE,
    FILE_INTAKE_STATUS_FAILED,
    FILE_INTAKE_STATUS_REUSED,
    FileIntakeCandidate,
    build_file_intake_dedupe_plan,
    build_intake_identity_key,
    canonicalize_intake_source_url,
    candidate_with_file_hash,
    existing_file_record_from_mapping,
    file_intake_candidate_from_mapping,
    hash_local_file,
    intake_identity_keys_for,
    normalize_intake_local_path,
    normalize_sha256,
    render_file_intake_dedupe_summary,
)


def run_self_test() -> None:
    canonical = canonicalize_intake_source_url(
        "HTTPS://Example.COM:443/path/File.jpg?utm_source=x&b=2&a=1#frag"
    )
    assert canonical == "https://example.com/path/File.jpg?a=1&b=2", canonical
    assert canonicalize_intake_source_url("not-a-url") == ""
    assert normalize_intake_local_path(r"T:\Evidence\\Clip.MP4") == "t:/evidence/clip.mp4"
    assert normalize_sha256("F" * 64) == "f" * 64
    assert normalize_sha256("not-a-hash") == ""

    strong_key = build_intake_identity_key(sha256="a" * 64, size_bytes=12, source_url="https://example.test/a")
    assert strong_key == f"sha256-size:{'a' * 64}:12"
    assert intake_identity_keys_for(sha256="b" * 64, size_bytes=3) == (
        f"sha256-size:{'b' * 64}:3",
        f"sha256:{'b' * 64}",
    )

    existing = ExistingFileRecord(
        record_id="existing-1",
        source_url="https://example.test/image.png?utm_campaign=old&id=7",
    )
    candidates = [
        FileIntakeCandidate(
            candidate_id="candidate-reuse-url",
            source_url="https://EXAMPLE.test/image.png?id=7&utm_source=new",
        ),
        FileIntakeCandidate(
            candidate_id="candidate-add",
            source_url="https://example.test/other.png",
        ),
        FileIntakeCandidate(
            candidate_id="candidate-duplicate",
            source_url="https://example.test/other.png#section",
        ),
        FileIntakeCandidate(candidate_id="candidate-failed"),
    ]
    plan = build_file_intake_dedupe_plan(candidates=candidates, existing_records=[existing])
    statuses = [decision.status for decision in plan.decisions]
    assert statuses == [
        FILE_INTAKE_STATUS_REUSED,
        FILE_INTAKE_STATUS_ADDED,
        FILE_INTAKE_STATUS_DUPLICATE,
        FILE_INTAKE_STATUS_FAILED,
    ], statuses
    assert plan.reused_count == 1
    assert plan.added_count == 1
    assert plan.duplicate_count == 1
    assert plan.failed_count == 1
    assert plan.decisions[0].existing_record_id == "existing-1"
    assert plan.decisions[2].duplicate_of_candidate_id == "candidate-add"
    assert plan.decisions[3].warnings == ("candidate_requires_source_url_local_path_or_sha256",)
    assert render_file_intake_dedupe_summary(plan) == (
        "FILES/media intake review: 1 added, 1 reused, 1 duplicate, 1 failed"
    )
    data = plan.to_dict()
    assert data["file_copy_performed"] is False
    assert data["media_download_performed"] is False
    assert data["browser_action_performed"] is False
    assert data["status_counts"][FILE_INTAKE_STATUS_ADDED] == 1

    sha = "c" * 64
    existing_hash = ExistingFileRecord(record_id="existing-hash", sha256=sha, size_bytes=5)
    hash_plan = build_file_intake_dedupe_plan(
        candidates=[{"candidate_id": "hash-candidate", "sha256": sha, "size_bytes": 5}],
        existing_records=[existing_hash],
    )
    assert hash_plan.decisions[0].status == FILE_INTAKE_STATUS_REUSED
    assert hash_plan.decisions[0].existing_record_id == "existing-hash"

    mapped_candidate = file_intake_candidate_from_mapping(
        {"resource_id": "res-1", "url": "https://example.test/raw", "output_path": "T:/a/b.png"}
    )
    assert mapped_candidate.candidate_id == "res-1"
    assert mapped_candidate.source_url == "https://example.test/raw"
    mapped_existing = existing_file_record_from_mapping(
        {"item_id": "item-1", "reference_url": "https://example.test/ref"}
    )
    assert mapped_existing.record_id == "item-1"

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "payload.bin"
        payload = b"ytce-file-intake-dedupe"
        path.write_bytes(payload)
        hash_result = hash_local_file(path)
        assert hash_result.status == FILE_INTAKE_STATUS_ADDED
        assert hash_result.sha256 == hashlib.sha256(payload).hexdigest()
        assert hash_result.size_bytes == len(payload)
        enriched = candidate_with_file_hash(
            FileIntakeCandidate(candidate_id="local", local_path=str(path))
        )
        assert enriched.sha256 == hash_result.sha256
        assert enriched.size_bytes == len(payload)
        local_plan = build_file_intake_dedupe_plan(
            candidates=[FileIntakeCandidate(candidate_id="local2", local_path=str(path))],
            existing_records=[ExistingFileRecord(record_id="existing-local", local_path=str(path))],
            enrich_hashes=True,
        )
        assert local_plan.decisions[0].status == FILE_INTAKE_STATUS_REUSED

    missing = hash_local_file("")
    assert missing.status == FILE_INTAKE_STATUS_FAILED
    assert missing.warnings == ("path_required",)


if __name__ == "__main__":
    run_self_test()
    print("file_intake_dedupe_test.py: OK")
