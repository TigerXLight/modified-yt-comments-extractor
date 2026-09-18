from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_twitter_x_account_media_ledger_r43a import TwitterXAccountRecordR43A
from profile_media_twitter_x_fast_media_to_post_ledger_binding_r43t import (
    R43T_PASS_STATUS,
    bind_fast_media_observations_to_post_records_r43t,
    build_report,
    write_unbound_media_index_r43t,
)


def test_r43t_binds_fast_media_observations_to_posts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner = root / "runner"
        _write_binding_fixture(runner)
        records = (
            TwitterXAccountRecordR43A(record_id="1111111111111111111", record_type="post", source_url="https://x.com/examaddaorg/status/1111111111111111111", visible_text="text only", observed_order=1),
            TwitterXAccountRecordR43A(record_id="2222222222222222222", record_type="post", source_url="https://x.com/examaddaorg/status/2222222222222222222", visible_text="media post", observed_order=2),
            TwitterXAccountRecordR43A(record_id="3333333333333333333", record_type="post", source_url="https://x.com/examaddaorg/status/3333333333333333333", visible_text="remote image", observed_order=3),
        )
        articles = (
            {
                "status_id": "2222222222222222222",
                "canonical_status_url": "https://x.com/examaddaorg/status/2222222222222222222",
                "article_media_candidates": [{"media_url": "https://pbs.twimg.com/media/dom_match.jpg?format=jpg&name=large"}],
            },
        )
        result = bind_fast_media_observations_to_post_records_r43t(records, articles=articles, runner_root=runner)
        assert result.status == R43T_PASS_STATUS
        summary = result.summary
        assert summary["bound_media_count"] >= 7
        assert summary["unbound_media_count"] == 1
        assert summary["bound_image_count"] >= 3
        assert summary["bound_video_count"] >= 2
        assert summary["bound_manifest_count"] == 1
        assert summary["bound_segment_count"] == 2
        assert summary["session_local_media_count"] == 2
        assert summary["metadata_only_media_count"] >= 5
        assert summary["raw_bound_media_candidate_count"] == summary["bound_media_count"]
        assert summary["ledger_media_item_count"] == sum(len(row.media_items or ()) for row in result.records)
        assert summary["deduped_bound_media_candidate_count"] <= summary["raw_bound_media_candidate_count"]
        assert summary["duplicate_bound_media_candidate_count"] >= 0
        assert "raw bound observation candidate count" in summary["count_semantics"]

        media_222 = next(row for row in result.records if row.record_id == "2222222222222222222").media_items
        reasons = {item.binding_reason for item in media_222}
        assert "status_id_match" in reasons
        assert "canonical_post_url_match" in reasons
        assert "article_dom_media_url_match" in reasons
        assert any(item.local_path and Path(item.local_path).is_file() and item.media_class == "image" for item in media_222)
        assert any(item.local_path and Path(item.local_path).is_file() and item.media_class == "video" for item in media_222)
        assert not any("abs.twimg.com" in item.media_url for item in media_222)
        assert not any("profile_images" in item.media_url for item in media_222)

        paths = write_unbound_media_index_r43t(root / "capture", result.unbound_media)
        assert Path(paths["unbound_media_index_path"]).is_file()


def test_r43t_live_scope_passes_when_observed_media_is_unbound_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        runner = root / "live_runner_output"
        store = runner / "visible_browser_media_observation_store"
        store.mkdir(parents=True, exist_ok=True)
        visible_rows = [
            {"canonical_media_url": "https://pbs.twimg.com/media/account_level_1.jpg?format=jpg&name=large", "media_class": "image"},
            {"canonical_media_url": "https://pbs.twimg.com/media/account_level_2.jpg?format=jpg&name=large", "media_class": "image"},
        ]
        _write_json(store / "visible_browser_media_observations.json", {"observations": visible_rows})
        (store / "visible_browser_media_observations.ndjson").write_text("\n".join(json.dumps(row) for row in visible_rows) + "\n", encoding="utf-8")
        package = runner / "r42gt_visible_browser_media_package" / "source_exports" / "twitter_x" / "examaddaorg" / "capture_20260918T000000Z"
        package.mkdir(parents=True, exist_ok=True)
        _write_json(package / "manifest.json", {"marker": "R42GT_LIVE_LIKE"})
        media_rows = [
            {"canonical_media_url": "https://pbs.twimg.com/media/account_level_3.jpg?format=jpg&name=large", "media_kind": "image"},
            {"canonical_media_url": "https://pbs.twimg.com/media/account_level_4.jpg?format=jpg&name=large", "media_kind": "image"},
        ]
        _write_json(package / "media_index.json", {"media": media_rows})
        (package / "media_index.ndjson").write_text("\n".join(json.dumps(row) for row in media_rows) + "\n", encoding="utf-8")
        records = (
            TwitterXAccountRecordR43A(record_id="1111111111111111111", record_type="post", source_url="https://x.com/examaddaorg/status/1111111111111111111", visible_text="text only", observed_order=1),
            TwitterXAccountRecordR43A(record_id="2222222222222222222", record_type="post", source_url="https://x.com/examaddaorg/status/2222222222222222222", visible_text="text only two", observed_order=2),
        )
        result = bind_fast_media_observations_to_post_records_r43t(records, runner_root=runner)
        assert result.status == R43T_PASS_STATUS
        assert result.summary["count_scope"] == "live_runner_observation_binding_scope"
        assert result.summary["bound_media_count"] == 0
        assert result.summary["raw_bound_media_candidate_count"] == 0
        assert result.summary["ledger_media_item_count"] == 0
        assert result.summary["unbound_media_count"] == 4
        assert all(len(row.media_items or ()) == 0 for row in result.records)



def test_r43t_report_fixture_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = build_report(Path(tmp) / "report")
        assert result.status == R43T_PASS_STATUS


def _write_binding_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    local_image = root / "local_image.jpg"
    local_video = root / "local_video.mp4"
    local_image.write_bytes(b"IMAGE")
    local_video.write_bytes(b"VIDEO")
    store = root / "visible_browser_media_observation_store"
    store.mkdir(parents=True, exist_ok=True)
    visible_rows = [
        {"canonical_media_url": "https://pbs.twimg.com/media/status_image.jpg?format=jpg&name=large", "status_id": "2222222222222222222", "media_class": "image", "local_session_path": str(local_image)},
        {"canonical_media_url": "https://video.twimg.com/ext_tw_video/222/pu/vid/720x720/local_video.mp4", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "media_class": "video", "local_session_path": str(local_video)},
        {"canonical_media_url": "https://pbs.twimg.com/media/dom_match.jpg?format=jpg&name=large", "media_class": "image"},
        {"canonical_media_url": "https://abs.twimg.com/icons/ui.png", "status_id": "2222222222222222222", "media_class": "image"},
        {"canonical_media_url": "https://pbs.twimg.com/profile_images/avatar.jpg", "status_id": "2222222222222222222", "media_class": "image"},
        {"canonical_media_url": "https://pbs.twimg.com/media/loose.jpg?format=jpg&name=large", "media_class": "image"},
    ]
    _write_json(store / "visible_browser_media_observations.json", {"observations": visible_rows})
    (store / "visible_browser_media_observations.ndjson").write_text("\n".join(json.dumps(row) for row in visible_rows) + "\n", encoding="utf-8")
    segments = [
        {"canonical_segment_url": "https://video.twimg.com/ext_tw_video/222/pu/seg/00001.ts", "playlist_manifest_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "status_id": "2222222222222222222"},
        {"canonical_segment_url": "https://video.twimg.com/ext_tw_video/222/pu/seg/00002.ts", "playlist_manifest_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "status_id": "2222222222222222222"},
    ]
    (store / "visible_browser_media_segments.ndjson").write_text("\n".join(json.dumps(row) for row in segments) + "\n", encoding="utf-8")
    package = root / "r42gt_visible_browser_media_package" / "source_exports" / "twitter_x" / "examaddaorg" / "capture_20260918T000000Z"
    package.mkdir(parents=True, exist_ok=True)
    _write_json(package / "manifest.json", {"marker": "R42GT"})
    media_rows = [
        {"canonical_media_url": "https://video.twimg.com/ext_tw_video/222/pu/pl/manifest.m3u8", "canonical_post_url": "https://x.com/examaddaorg/status/2222222222222222222", "post_id": "2222222222222222222", "media_kind": "manifest"},
        {"canonical_media_url": "https://pbs.twimg.com/media/remote_333.jpg?format=jpg&name=large", "canonical_post_url": "https://x.com/examaddaorg/status/3333333333333333333", "post_id": "3333333333333333333", "media_kind": "image"},
    ]
    _write_json(package / "media_index.json", {"media": media_rows})
    (package / "media_index.ndjson").write_text("\n".join(json.dumps(row) for row in media_rows) + "\n", encoding="utf-8")
    _write_json(root / "media_inventory.json", [{"media_url": "https://video.twimg.com/ext_tw_video/222/pu/vid/720x720/remote.mp4", "status_id": "2222222222222222222", "media_class": "video"}])


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    test_r43t_binds_fast_media_observations_to_posts()
    test_r43t_live_scope_passes_when_observed_media_is_unbound_only()
    test_r43t_report_fixture_passes()
    print("R43T tests passed")
