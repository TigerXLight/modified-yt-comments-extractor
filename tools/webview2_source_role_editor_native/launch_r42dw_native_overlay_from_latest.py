from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_archive_role_payload_r42dw import build_latest_archive_role_payload

SOURCE = "https://archive.ph/6mr3C"


def main() -> int:
    result = build_latest_archive_role_payload(
        project_root=ROOT,
        source_url=SOURCE,
        output_root=ROOT / "profile_media_live_captures" / "r42dw_archive_role_payload",
        text_paint_style=os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", "").strip(),
    )
    if not result.get("ok"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    from profile_media_link_source_real_webview_overlay_v83d import launch_role_overlay_native_webview2_async

    overlay = {
        "selected_url": result["source_url"],
        "launch_start_url": result["source_url"],
        "overlay_json_path": result["payload_path"],
        "overlay_changes_jsonl_path": result["changes_path"],
        "launch_log_path": str(ROOT / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"),
        "initial_mode": "semantic",
        "native_command_action": "role_overlay_refresh",
    }
    launch = launch_role_overlay_native_webview2_async(overlay)
    summary = {
        "schema": "ytce.r42dw.launch_native_role_overlay_from_latest.v1",
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "source_url": SOURCE,
        "payload": result,
        "native_launch_result": launch,
        "note": "This command opens/refreshes native WebView2. Use R42DY probe for no-GUI testing.",
    }
    outdir = ROOT / "profile_media_live_captures" / "r42dw_archive_role_payload"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / ("launch_native_role_overlay_from_latest_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if launch.get("launched") else 4


if __name__ == "__main__":
    raise SystemExit(main())
