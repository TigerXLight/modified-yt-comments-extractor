from pathlib import Path
import tempfile

from profile_media_unified_media_window_tabs_r42gw import (
    BYTE_STATUS_LOCAL,
    BYTE_STATUS_REMOTE,
    MEDIA_CLASS_IMAGE,
    MEDIA_CLASS_MANIFEST,
    MEDIA_CLASS_SEGMENT,
    R42GW_MARKER,
    R42GW_PASS_STATUS,
    TAB_ALL,
    TAB_IMAGES,
    TAB_VIDEOS,
    MediaWindowFilterState,
    build_report,
    build_unified_media_window_state_from_visible_browser_store,
    filter_unified_media_window_state,
    flatten_media_window_tree,
    machine_url_fields_are_plain,
)


def _sample_store(tmp: Path):
    local = tmp / "session_local.jpg"
    local.write_bytes(b"local fixture")
    source_url = "https://x.com/example/status/1234567890"
    manifest = "https://video.twimg.com/ext_tw_video/1234567890/pu/pl/manifest.m3u8?tag=16"
    return {
        "source_url": source_url,
        "canonical_source_url": source_url,
        "observations": [
            {
                "observation_id": "img1",
                "media_kind": "image",
                "media_url": "https://pbs.twimg.com/media/photo1.jpg?format=jpg&name=large",
                "canonical_media_url": "https://pbs.twimg.com/media/photo1.jpg?format=jpg&name=large",
                "content_type": "image/jpeg",
                "source_kind": "visible_browser_network_response",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "img2",
                "media_kind": "image",
                "media_url": "https://pbs.twimg.com/media/photo2.jpg?format=jpg&name=large",
                "canonical_media_url": "https://pbs.twimg.com/media/photo2.jpg?format=jpg&name=large",
                "content_type": "image/jpeg",
                "source_kind": "visible_browser_network_response",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "manifest",
                "media_kind": "manifest",
                "media_url": manifest,
                "canonical_media_url": manifest,
                "content_type": "application/x-mpegURL",
                "source_kind": "visible_browser_network_response",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "mp4",
                "media_kind": "video",
                "media_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4",
                "canonical_media_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4",
                "content_type": "video/mp4",
                "source_kind": "visible_browser_network_response",
                "byte_status": BYTE_STATUS_REMOTE,
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
            {
                "observation_id": "session-local-image",
                "media_kind": "image",
                "media_url": "https://pbs.twimg.com/media/session_local.jpg?format=jpg&name=large",
                "canonical_media_url": "https://pbs.twimg.com/media/session_local.jpg?format=jpg&name=large",
                "content_type": "image/jpeg",
                "source_kind": "session_local_file",
                "byte_status": BYTE_STATUS_LOCAL,
                "local_session_path": str(local),
                "sha256": "fixture-sha256",
                "canonical_post_url": source_url,
                "status_id": "1234567890",
            },
        ],
        "segment_rows": [
            {
                "segment_id": "seg1",
                "segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts",
                "canonical_segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts",
                "playlist_manifest_url": manifest,
                "content_type": "video/mp2t",
                "segment_index": 1,
                "byte_status": BYTE_STATUS_REMOTE,
            },
            {
                "segment_id": "seg2",
                "segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00002.ts",
                "canonical_segment_url": "https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00002.ts",
                "playlist_manifest_url": manifest,
                "content_type": "video/mp2t",
                "segment_index": 2,
                "byte_status": BYTE_STATUS_REMOTE,
            },
        ],
    }


def test_unified_window_tabs_are_fixed_and_review_is_separate() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = build_unified_media_window_state_from_visible_browser_store(
            _sample_store(Path(td)),
            source_row_id="twitter_x:example:1234567890",
        )
    assert state.marker == R42GW_MARKER
    assert state.tabs == (TAB_ALL, TAB_IMAGES, TAB_VIDEOS)
    assert state.review_window_separate is True
    assert state.package_count >= 2
    assert state.child_count >= 6


def test_all_tab_is_jdownloader_style_package_child_tree() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = build_unified_media_window_state_from_visible_browser_store(
            _sample_store(Path(td)),
            source_row_id="twitter_x:example:1234567890",
        )
    rows = flatten_media_window_tree(state, tab_id=TAB_ALL)
    assert rows[0]["row_role"] == "package"
    assert any(row["row_role"] == "child" for row in rows)
    assert any(row.get("segment_child_count", 0) >= 2 for row in rows if row["row_role"] == "package")
    assert machine_url_fields_are_plain(rows)


def test_image_and_video_tabs_are_filtered_views_of_same_model() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = build_unified_media_window_state_from_visible_browser_store(
            _sample_store(Path(td)),
            source_row_id="twitter_x:example:1234567890",
        )
    image_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_IMAGES))
    video_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_VIDEOS))

    assert image_state.child_count >= 3
    assert all(child.media_class == MEDIA_CLASS_IMAGE for package in image_state.packages for child in package.children)
    assert video_state.child_count >= 3
    assert all(child.media_class != MEDIA_CLASS_IMAGE for package in video_state.packages for child in package.children)
    assert any(child.media_class == MEDIA_CLASS_MANIFEST for package in video_state.packages for child in package.children)


def test_segment_children_are_listed_but_not_top_level_or_selected_by_default() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = build_unified_media_window_state_from_visible_browser_store(
            _sample_store(Path(td)),
            source_row_id="twitter_x:example:1234567890",
        )
    video_packages = state.tab_packages(TAB_VIDEOS)
    segment_children = [child for package in video_packages for child in package.children if child.media_class == MEDIA_CLASS_SEGMENT]

    assert len(segment_children) >= 2
    assert any(package.segment_child_count >= 2 for package in video_packages)
    assert any(
        package.segment_child_count >= 2 and any(child.media_class == MEDIA_CLASS_MANIFEST for child in package.children)
        for package in video_packages
    )
    assert not any(child.selectable for child in segment_children)
    assert not any(package.package_kind == MEDIA_CLASS_SEGMENT for package in video_packages)


def test_jdownloader_like_filters_cover_extension_host_class_and_selectable() -> None:
    with tempfile.TemporaryDirectory() as td:
        state = build_unified_media_window_state_from_visible_browser_store(
            _sample_store(Path(td)),
            source_row_id="twitter_x:example:1234567890",
        )

    ts_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_VIDEOS, extension_filter="ts"))
    assert ts_state.segment_child_count >= 2
    assert all(child.extension == ".ts" for package in ts_state.packages for child in package.children)

    host_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_IMAGES, host_filter="pbs.twimg.com"))
    assert host_state.child_count >= 3
    assert all("pbs.twimg.com" in child.host for package in host_state.packages for child in package.children)

    selectable_video_state = filter_unified_media_window_state(state, MediaWindowFilterState(tab_id=TAB_VIDEOS, only_selectable=True))
    assert selectable_video_state.child_count >= 1
    assert all(child.selectable for package in selectable_video_state.packages for child in package.children)
    assert all(child.media_class != MEDIA_CLASS_SEGMENT for package in selectable_video_state.packages for child in package.children)


def test_report_is_green_and_side_effect_free() -> None:
    with tempfile.TemporaryDirectory() as td:
        report = build_report(Path(td))
    assert report.status == R42GW_PASS_STATUS
    assert all(check["status"] == "pass" for check in report.checks)
    flags = report.side_effect_flags
    assert flags["local_projection_only"] is True
    assert flags["network_actions_performed"] is False
    assert flags["downloads_performed"] is False
    assert flags["jdownloader_direct_source_included_in_r42gw"] is False
    assert flags["jdownloader_source_usage_policy_recorded"] is True
    assert flags["jdownloader_direct_code_copy_allowed_when_attributed_and_license_compatible"] is True


def run_self_test() -> None:
    test_unified_window_tabs_are_fixed_and_review_is_separate()
    test_all_tab_is_jdownloader_style_package_child_tree()
    test_image_and_video_tabs_are_filtered_views_of_same_model()
    test_segment_children_are_listed_but_not_top_level_or_selected_by_default()
    test_jdownloader_like_filters_cover_extension_host_class_and_selectable()
    test_report_is_green_and_side_effect_free()
    print("profile_media_unified_media_window_tabs_r42gw_test: PASS")


if __name__ == "__main__":
    run_self_test()
