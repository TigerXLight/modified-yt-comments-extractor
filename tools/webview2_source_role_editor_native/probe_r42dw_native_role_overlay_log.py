from __future__ import annotations
from pathlib import Path
import json
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"
OUTROOT = ROOT / "profile_media_live_captures" / "r42dw_archive_role_payload"
OUTROOT.mkdir(parents=True, exist_ok=True)

def main() -> int:
    text = LOG.read_text(encoding="utf-8", errors="replace") if LOG.is_file() else ""
    tail = "\n".join(text.splitlines()[-260:])
    summary = {
        "schema": "ytce.r42dw.native_role_overlay_log_probe.v1",
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "log_path": str(LOG),
        "log_present": LOG.is_file(),
        "found_role_overlay_refresh_command": "action=role_overlay_refresh" in tail,
        "found_r42dw_refresh_applied": "r42dw_role_overlay_refresh_applied" in tail,
        "found_r42dv_js_ready": "r42dv_role_paint_js_ready" in tail,
        "found_first_role_paint": "first_role_paint" in tail,
        "found_native_toolbar_state": "native_toolbar_state" in tail,
        "latest_native_toolbar_ready_lines": [line for line in text.splitlines() if "native_toolbar_ready:" in line][-5:],
        "latest_r42dw_lines": [line for line in text.splitlines() if "r42dw_" in line or "role_overlay_refresh" in line][-20:],
    }
    out = OUTROOT / ("native_role_overlay_log_probe_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["found_role_overlay_refresh_command"]:
        return 2
    if not (summary["found_r42dw_refresh_applied"] or summary["found_first_role_paint"] or summary["found_native_toolbar_state"]):
        return 3
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
