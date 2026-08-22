"""Tests for V80R persistent FILES/media identity store."""

from __future__ import annotations

import tempfile
from pathlib import Path

from file_intake_dedupe import ExistingFileRecord, build_file_intake_dedupe_plan, FileIntakeCandidate
from file_intake_identity_store import (
    FILE_INTAKE_IDENTITY_STORE_SCHEMA_VERSION,
    load_file_intake_identity_store,
    make_file_intake_identity_record,
    merge_file_intake_identity_records,
    save_file_intake_identity_store,
)


def test_identity_store_persists_and_reuses_existing_local_file() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        local_file = root / "image.jpg"
        local_file.write_bytes(b"image")
        store_path = root / "identity" / "store.json"
        record = make_file_intake_identity_record(
            record_id="browser-grid:row-1:image-1",
            display_name="image.jpg",
            source_url="https://example.com/image.jpg?utm_source=x&a=1",
            local_path=str(local_file),
            media_type="image",
        )
        saved = save_file_intake_identity_store(store_path, (record,))
        assert saved.saved_count == 1
        assert store_path.is_file()
        loaded = load_file_intake_identity_store(store_path)
        assert loaded.schema_version == FILE_INTAKE_IDENTITY_STORE_SCHEMA_VERSION
        assert loaded.record_count == 1
        plan = build_file_intake_dedupe_plan(
            candidates=(
                FileIntakeCandidate(
                    candidate_id="image-1-again",
                    source_url="https://example.com/image.jpg?a=1&utm_campaign=ignored",
                    media_type="image",
                ),
            ),
            existing_records=loaded.records,
        )
        assert plan.reused_count == 1
        assert plan.decisions[0].existing_record_id == "browser-grid:row-1:image-1"


def test_identity_store_filters_stale_temp_paths_when_requested() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        missing_file = root / "deleted.jpg"
        store_path = root / "store.json"
        record = make_file_intake_identity_record(
            record_id="stale",
            source_url="https://example.com/deleted.jpg",
            local_path=str(missing_file),
            media_type="image",
        )
        save_file_intake_identity_store(store_path, (record,))
        strict = load_file_intake_identity_store(store_path, require_existing_local_path=True)
        assert strict.record_count == 0
        assert strict.stale_count == 1
        loose = load_file_intake_identity_store(store_path, require_existing_local_path=False)
        assert loose.record_count == 1


def test_identity_store_merge_newest_record_wins_and_bounds() -> None:
    old = ExistingFileRecord(
        record_id="old",
        source_url="https://example.com/same.png",
        local_path="C:/old/same.png",
        media_type="image",
    )
    new = ExistingFileRecord(
        record_id="new",
        source_url="https://example.com/same.png",
        local_path="C:/new/same.png",
        media_type="image",
    )
    other = ExistingFileRecord(record_id="other", source_url="https://example.com/other.png")
    merged = merge_file_intake_identity_records((old,), (new, other), max_records=2)
    assert [record.record_id for record in merged] == ["new", "other"]
    bounded = merge_file_intake_identity_records((), (old, new, other), max_records=1)
    assert [record.record_id for record in bounded] == ["other"]


if __name__ == "__main__":
    test_identity_store_persists_and_reuses_existing_local_file()
    test_identity_store_filters_stale_temp_paths_when_requested()
    test_identity_store_merge_newest_record_wins_and_bounds()
    print("file_intake_identity_store_test.py: OK")
