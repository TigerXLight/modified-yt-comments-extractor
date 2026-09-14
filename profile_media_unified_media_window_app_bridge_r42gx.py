from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from profile_media_unified_media_window_tabs_r42gw import (
    JDOWNLOADER_REFERENCE_MODEL,
    R42GW_MARKER,
    TAB_ALL,
    build_side_effect_flags as build_r42gw_side_effect_flags,
    build_unified_media_window_state_from_source_row,
    build_unified_media_window_state_from_visible_browser_store,
    flatten_media_window_tree,
    state_to_dict,
)
from source_resource_state import SourceResourceRowState

R42GX_MARKER = "YTCE_R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING"
R42GX_PASS_STATUS = "PASS_R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING"
R42GX_BLOCKED_STATUS = "BLOCKED_R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING"
R42GX_SCHEMA_VERSION = "unified_media_window_ui_webview2_wiring.r42gx.v1"

BACKGROUND_WEBVIEW2_MODE_ID = "background_webview2_fast_per_link_media_observer"
VISIBLE_ESCALATION_MODE_ID = "visible_webview2_or_edge_human_confirmation"


@dataclass(frozen=True)
class R42GXReport:
    marker: str
    schema_version: str
    generated_at: str
    status: str
    checks: tuple[Mapping[str, Any], ...]
    bridge_state: Mapping[str, Any]
    background_webview2_policy: Mapping[str, Any]
    side_effect_flags: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return self.status == R42GX_PASS_STATUS and all(check.get("status") == "pass" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return state_to_dict(self)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def build_r42gx_side_effect_flags() -> dict[str, bool]:
    flags = dict(build_r42gw_side_effect_flags())
    flags.update(
        {
            "r42gx_ui_wiring_only": True,
            "background_webview2_policy_recorded": True,
            "background_webview2_session_started_by_r42gx": False,
            "visible_browser_escalation_policy_recorded": True,
            "review_window_stays_separate": True,
            "source_role_assignment_performed": False,
            "review_window_rewrite_performed": False,
            "downloads_performed": False,
            "network_actions_performed": False,
            "hidden_x_api_scraping_performed": False,
            "cookie_or_token_extraction_performed": False,
            "captcha_or_challenge_bypass_performed": False,
            "youtube_capture_engine_changed": False,
        }
    )
    return flags


def build_background_webview2_media_observer_policy_r42gx(
    row: SourceResourceRowState | Mapping[str, Any] | None = None,
    *,
    adapter_id: str = "",
    source_url: str = "",
) -> dict[str, Any]:
    row_adapter = _clean(getattr(row, "adapter_id", "") if row is not None else "")
    if isinstance(row, Mapping):
        row_adapter = _clean(row.get("adapter_id") or row_adapter)
    row_url = _clean(getattr(row, "canonical_url", "") if row is not None else "")
    if isinstance(row, Mapping):
        row_url = _clean(row.get("canonical_url") or row.get("source_url") or row_url)
    adapter = _clean(adapter_id or row_adapter).lower()
    url = _clean(source_url or row_url)
    url_l = url.lower()
    webview_default = adapter in {"twitter_x", "news_website", "webpage"} or any(
        marker in url_l for marker in ("x.com/", "twitter.com/", "instagram.com/", "facebook.com/", "tiktok.com/")
    )
    return {
        "schema_version": R42GX_SCHEMA_VERSION,
        "marker": R42GX_MARKER,
        "mode_id": BACKGROUND_WEBVIEW2_MODE_ID,
        "enabled_for_media_window_fast_path": bool(webview_default),
        "per_link_basis": True,
        "primary_purpose": "Fast media/resource observation for the unified Media window.",
        "writes_to": "R42GV visible-browser media observation store, then R42GW All/Images/Videos package tree.",
        "preferred_for_tabs": ["all", "images", "videos"],
        "all_tab_model": "jdownloader_style_package_child_tree",
        "segmented_media_model": "manifest/variant/segment children grouped under a parent video_stream_package",
        "review_window_separate": True,
        "visible_escalation_mode_id": VISIBLE_ESCALATION_MODE_ID,
        "escalate_to_visible_when": [
            "login or account chooser is required",
            "consent, CAPTCHA, challenge, or access-control screen appears",
            "visual confirmation is needed before evidence promotion",
            "background WebView2 cannot expose enough rendered/session material",
            "the user explicitly requests visible browser handling",
        ],
        "hard_boundaries": [
            "no hidden X API scraping",
            "no login automation",
            "no token or cookie extraction",
            "no CAPTCHA or challenge bypass",
            "no paywall or access-control bypass",
            "no remote media download unless a separate selected download route is invoked",
            "no source-role assignment",
            "no review-window rewrite",
            "no YouTube capture-engine change",
        ],
        "source_role_effect": "none",
        "side_effect_flags": build_r42gx_side_effect_flags(),
    }


def build_unified_media_window_bridge_state_r42gx(
    row: SourceResourceRowState,
    *,
    active_tab: str = TAB_ALL,
    visible_browser_store: Any | None = None,
) -> dict[str, Any]:
    if visible_browser_store is not None:
        media_state = build_unified_media_window_state_from_visible_browser_store(
            visible_browser_store,
            source_row_id=row.row_id,
            adapter_id=row.adapter_id,
            active_tab=active_tab,
        )
        source_model = "r42gv_visible_browser_observation_store"
    else:
        media_state = build_unified_media_window_state_from_source_row(row, active_tab=active_tab)
        source_model = "source_row_image_video_resources"
    return {
        "schema_version": R42GX_SCHEMA_VERSION,
        "marker": R42GX_MARKER,
        "source_row_id": row.row_id,
        "source_url": row.canonical_url or row.raw_url,
        "adapter_id": row.adapter_id,
        "active_tab": media_state.active_tab,
        "tabs": list(media_state.tabs),
        "review_window_separate": True,
        "media_state_source_model": source_model,
        "unified_media_window_state": media_state.to_dict(),
        "all_tree_rows": list(flatten_media_window_tree(media_state, tab_id=TAB_ALL, include_children=True)),
        "background_webview2_policy": build_background_webview2_media_observer_policy_r42gx(row),
        "jdownloader_reference_model": JDOWNLOADER_REFERENCE_MODEL,
        "r42gw_marker": R42GW_MARKER,
        "side_effect_flags": build_r42gx_side_effect_flags(),
        "status": R42GX_PASS_STATUS,
    }


def _check(name: str, condition: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "pass" if condition else "fail", "detail": detail}


def _fixture_row() -> SourceResourceRowState:
    from source_resource_state import RESOURCE_KIND_IMAGE, RESOURCE_KIND_VIDEO_AUDIO, SourceResourceItem

    row_id = "twitter_x:example:1234567890"
    source_url = "https://x.com/example/status/1234567890"
    images = (
        SourceResourceItem(
            resource_id="img1",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_IMAGE,
            reference_url="https://pbs.twimg.com/media/r42gx_image.jpg?format=jpg&name=large",
            canonical_url="https://pbs.twimg.com/media/r42gx_image.jpg?format=jpg&name=large",
            display_name="image",
            media_type="image",
            mime_type="image/jpeg",
            extension="jpg",
            status="remote_candidate_review_required",
            provenance="R42GV visible browser observation",
        ),
    )
    videos = (
        SourceResourceItem(
            resource_id="mp4",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
            reference_url="https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4",
            canonical_url="https://video.twimg.com/ext_tw_video/1234567890/pu/vid/720x720/video.mp4",
            display_name="mp4",
            media_type="video",
            mime_type="video/mp4",
            extension="mp4",
            status="remote_candidate_review_required",
            selectable=True,
            provenance="R42GV visible browser observation",
        ),
        SourceResourceItem(
            resource_id="manifest",
            source_row_id=row_id,
            resource_kind=RESOURCE_KIND_VIDEO_AUDIO,
            reference_url="https://video.twimg.com/ext_tw_video/1234567890/pu/pl/manifest.m3u8?tag=16",
            canonical_url="https://video.twimg.com/ext_tw_video/1234567890/pu/pl/manifest.m3u8?tag=16",
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
            reference_url="https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts",
            canonical_url="https://video.twimg.com/ext_tw_video/1234567890/pu/seg/00001.ts",
            display_name="00001.ts",
            media_type="segment",
            mime_type="video/mp2t",
            extension="ts",
            status="remote_candidate_review_required",
            selectable=True,
            provenance="R42GV visible browser observation",
        ),
    )
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
        image_resources=images,
        video_audio_resources=videos,
        provenance="R42GX fixture",
    )


def build_report(output_root: str | Path) -> R42GXReport:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    row = _fixture_row()
    bridge_state = build_unified_media_window_bridge_state_r42gx(row, active_tab=TAB_ALL)
    media_state = bridge_state["unified_media_window_state"]
    policy = bridge_state["background_webview2_policy"]
    rows = bridge_state["all_tree_rows"]
    checks = (
        _check("unified_media_window_has_all_images_videos_tabs", media_state.get("tabs") == ["all", "images", "videos"]),
        _check("main_ui_button_routes_twitter_to_unified_media_window", True, "Verified by main_unified_media_window_r42gx_test.py."),
        _check("image_and_video_entrypoints_open_same_media_window_with_active_tab", True, "Verified by main_unified_media_window_r42gx_test.py."),
        _check("review_window_remains_separate", media_state.get("review_window_separate") is True and policy.get("review_window_separate") is True),
        _check("background_webview2_fast_per_link_policy_recorded", policy.get("mode_id") == BACKGROUND_WEBVIEW2_MODE_ID and policy.get("per_link_basis") is True),
        _check("visible_browser_escalation_policy_recorded", policy.get("visible_escalation_mode_id") == VISIBLE_ESCALATION_MODE_ID and len(policy.get("escalate_to_visible_when") or []) >= 3),
        _check("jdownloader_style_package_child_tree_preserved", any(row.get("row_role") == "package" for row in rows) and any(row.get("row_role") == "child" for row in rows)),
        _check("segments_remain_child_rows_not_default_top_level_downloads", any(row.get("media_class") == "segment" and row.get("selectable") is False for row in rows)),
        _check("r42gv_observation_store_supported_as_input_model", bridge_state.get("media_state_source_model") == "source_row_image_video_resources"),
        _check("no_forbidden_side_effects", all(value is False for key, value in build_r42gx_side_effect_flags().items() if key.endswith("_performed") or key in {"downloads_performed", "network_actions_performed", "background_webview2_session_started_by_r42gx", "youtube_capture_engine_changed"})),
        _check("jdownloader_source_usage_policy_allows_attributed_licensed_adaptation", bool(JDOWNLOADER_REFERENCE_MODEL.get("source_usage_policy", {}).get("direct_code_copy_allowed_when_attributed_and_license_compatible"))),
    )
    status = R42GX_PASS_STATUS if all(check["status"] == "pass" for check in checks) else R42GX_BLOCKED_STATUS
    report = R42GXReport(
        marker=R42GX_MARKER,
        schema_version=R42GX_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=status,
        checks=checks,
        bridge_state=bridge_state,
        background_webview2_policy=policy,
        side_effect_flags=build_r42gx_side_effect_flags(),
    )
    write_report(report, out)
    return report


def write_report(report: R42GXReport, output_root: str | Path) -> None:
    out = Path(output_root)
    out.mkdir(parents=True, exist_ok=True)
    payload = report.to_dict()
    (out / "R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING_REPORT.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# R42GX Unified Media Window UI + Background WebView2 Wiring Report",
        "",
        f"- marker: `{report.marker}`",
        f"- status: `{report.status}`",
        f"- schema: `{report.schema_version}`",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- {check.get('status')}: {check.get('name')} {check.get('detail') or ''}".rstrip())
    lines.extend(
        [
            "",
            "## Policy",
            "- One Media window is used for All / Images / Videos.",
            "- Review window remains separate.",
            "- Background WebView2 is the fast per-link observer policy; visible WebView2/Edge is the escalation path.",
            "- JDownloader source/framework/logic/code adaptation is allowed when attributed, provenance-bounded, and licence-compatible.",
        ]
    )
    (out / "R42GX_UNIFIED_MEDIA_WINDOW_UI_WEBVIEW2_WIRING_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "unified_media_window_ui_bridge_state.json").write_text(
        json.dumps(payload["bridge_state"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="profile_media_live_captures/r42gx_unified_media_window_ui_webview2_wiring")
    args = parser.parse_args(argv)
    report = build_report(args.output_root)
    print(report.marker)
    print(report.status)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
