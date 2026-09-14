from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

from source_resource_state import RESOURCE_KIND_IMAGE, RESOURCE_KIND_VIDEO_AUDIO, SourceResourceItem, SourceResourceRowState

from profile_media_unified_media_window_app_bridge_r42gx import (
    BACKGROUND_WEBVIEW2_MODE_ID,
    R42GX_MARKER,
    R42GX_PASS_STATUS,
    VISIBLE_ESCALATION_MODE_ID,
    build_background_webview2_media_observer_policy_r42gx,
    build_report,
    build_unified_media_window_bridge_state_r42gx,
)


def _row() -> SourceResourceRowState:
    row_id = "twitter_x:example:1234567890"
    source_url = "https://x.com/example/status/1234567890"
    return SourceResourceRowState(
        row_id=row_id,
        raw_url=source_url,
        canonical_url=source_url,
        adapter_id="twitter_x",
        adapter_display_name="X/Twitter",
        source_id="1234567890",
        title="Example X post",
        domain="x.com",
        display_label="Example X post - x.com",
        image_resources=(
            SourceResourceItem(
                resource_id="img",
                source_row_id=row_id,
                resource_kind=RESOURCE_KIND_IMAGE,
                reference_url="https://pbs.twimg.com/media/r42gx.jpg?format=jpg&name=large",
                canonical_url="https://pbs.twimg.com/media/r42gx.jpg?format=jpg&name=large",
                display_name="image",
                media_type="image",
                mime_type="image/jpeg",
                extension="jpg",
                status="remote_candidate_review_required",
                provenance="R42GV visible browser observation",
            ),
        ),
        video_audio_resources=(
            SourceResourceItem(
                resource_id="manifest",
                source_row_id=row_id,
                resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
                reference_url="https://video.twimg.com/ext_tw_video/123/pu/pl/manifest.m3u8?tag=16",
                canonical_url="https://video.twimg.com/ext_tw_video/123/pu/pl/manifest.m3u8?tag=16",
                display_name="manifest",
                media_type="manifest",
                mime_type="application/x-mpegURL",
                extension="m3u8",
                status="remote_candidate_review_required",
                selectable=True,
                provenance="R42GV visible browser observation",
            ),
            SourceResourceItem(
                resource_id="seg1",
                source_row_id=row_id,
                resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
                reference_url="https://video.twimg.com/ext_tw_video/123/pu/seg/00001.ts",
                canonical_url="https://video.twimg.com/ext_tw_video/123/pu/seg/00001.ts",
                display_name="00001.ts",
                media_type="segment",
                mime_type="video/mp2t",
                extension="ts",
                status="remote_candidate_review_required",
                selectable=True,
                provenance="R42GV visible browser observation",
            ),
        ),
        provenance="test",
    )


def test_background_webview2_policy() -> None:
    policy = build_background_webview2_media_observer_policy_r42gx(_row())
    assert policy["marker"] == R42GX_MARKER
    assert policy["mode_id"] == BACKGROUND_WEBVIEW2_MODE_ID
    assert policy["visible_escalation_mode_id"] == VISIBLE_ESCALATION_MODE_ID
    assert policy["enabled_for_media_window_fast_path"] is True
    assert policy["per_link_basis"] is True
    assert policy["review_window_separate"] is True
    assert "no token or cookie extraction" in policy["hard_boundaries"]


def test_bridge_state_tabs_and_segments() -> None:
    state = build_unified_media_window_bridge_state_r42gx(_row(), active_tab="all")
    media_state = state["unified_media_window_state"]
    assert state["marker"] == R42GX_MARKER
    assert media_state["tabs"] == ["all", "images", "videos"]
    assert media_state["review_window_separate"] is True
    assert any(row["row_role"] == "package" for row in state["all_tree_rows"])
    assert any(row.get("media_class") == "segment" and row.get("selectable") is False for row in state["all_tree_rows"])
    assert state["background_webview2_policy"]["mode_id"] == BACKGROUND_WEBVIEW2_MODE_ID


def test_main_ui_wiring_source_strings() -> None:
    import main
    from main import App

    refresh_source = inspect.getsource(App._refresh_source_resource_rows)
    open_source = inspect.getsource(App._open_source_resource_window)
    unified_source = inspect.getsource(App._open_unified_media_window_for_source_row)

    assert "twitter_unified_media_window_button_expected_by_ui_test" in refresh_source
    assert 'text="Media"' in refresh_source
    assert "_open_unified_media_window_for_source_row(row_id, active_tab=\"all\")" in refresh_source
    assert "Media window: All / Images / Videos" in refresh_source

    assert 'if row.adapter_id == "twitter_x":' in open_source
    assert 'active_tab = "images" if resource_kind == RESOURCE_KIND_IMAGE else "videos"' in open_source
    assert "self._open_unified_media_window_for_source_row(row_id, active_tab=active_tab)" in open_source

    assert "All" in unified_source and "Images" in unified_source and "Videos" in unified_source
    assert "Background WebView2 fast observer" in unified_source
    assert "Review window stays separate" in unified_source
    assert "filter_unified_media_window_state" in unified_source
    assert "flatten_media_window_tree" in unified_source
    assert "build_background_webview2_media_observer_policy_r42gx" in unified_source
    assert "R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING" in unified_source


def test_report_green(tmp_path: Path | None = None) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build_report(Path(tmp))
        assert report.status == R42GX_PASS_STATUS
        assert report.passed
        payload = json.loads((Path(tmp) / "R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING_REPORT.json").read_text(encoding="utf-8"))
        assert payload["marker"] == R42GX_MARKER
        assert payload["status"] == R42GX_PASS_STATUS
        assert payload["background_webview2_policy"]["review_window_separate"] is True


def run_self_test() -> None:
    test_background_webview2_policy()
    test_bridge_state_tabs_and_segments()
    test_main_ui_wiring_source_strings()
    test_report_green()
    print("profile_media_unified_media_window_app_bridge_r42gx_test: PASS")


if __name__ == "__main__":
    run_self_test()
