from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_database_saved_views import (
    ProfileMediaSavedView,
    ProfileMediaSavedViewLibrary,
    load_saved_view_library,
    remove_saved_view,
    render_saved_view_library_text,
    save_saved_view_library,
    saved_view_from_mapping,
    upsert_saved_view,
)
from profile_media_database_session import ProfileMediaDatabaseSessionConfig


def test_saved_view_library_round_trip_and_upsert() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "saved_views.json"
        view = ProfileMediaSavedView(
            name="Source gaps",
            description="Review source-chain gaps",
            config=ProfileMediaDatabaseSessionConfig(
                database_root="Database",
                batch_json_files=("case_batch.json",),
                source_chain_gap=True,
            ),
        ).normalized()
        library = upsert_saved_view(ProfileMediaSavedViewLibrary(), view)
        assert len(library.views) == 1
        assert library.views[0].name == "Source gaps"
        save_saved_view_library(path, library)
        loaded = load_saved_view_library(path)
        assert len(loaded.views) == 1
        assert loaded.views[0].config.source_chain_gap is True
        assert loaded.folder_scan_performed is False
        assert loaded.folder_move_performed is False
        assert loaded.folder_rename_performed is False
        text = render_saved_view_library_text(loaded)
        assert "Source gaps" in text
        assert "Folder scan performed: false" in text


def test_saved_view_from_mapping_and_remove() -> None:
    view = saved_view_from_mapping(
        {
            "name": "Disputes",
            "description": "Disputed framing only",
            "config": {
                "database_root": "Database",
                "batch_json_files": ["case_batch.json"],
                "disputed_framing": "true",
                "source_bucket": "Social Media/Online",
            },
        }
    )
    assert view.name == "Disputes"
    assert view.config.disputed_framing is True
    assert view.config.source_bucket == "Social Media/Online"
    library = ProfileMediaSavedViewLibrary(views=(view,))
    removed = remove_saved_view(library, "Disputes")
    assert not removed.views


def main() -> int:
    test_saved_view_library_round_trip_and_upsert()
    test_saved_view_from_mapping_and_remove()
    print("profile_media_database_saved_views v75z OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
