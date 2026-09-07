from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "profile_media_live_captures" / "r42du_archive_visible_material_source_roles" / ("probe_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
OUT.mkdir(parents=True, exist_ok=True)

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def contains(path: Path, needle: str) -> bool:
    return needle in read_text(path)

program = ROOT / "tools" / "webview2_source_role_editor_native" / "Program.cs"
overlay = ROOT / "profile_media_link_source_real_webview_overlay_v83d.py"
surface = ROOT / "profile_media_archive_source_role_surface_r42ds.py"
summary = {
    "mode": "probe",
    "schema": "ytce.r42du.archive_visible_material_source_roles_probe.v1",
    "outdir": str(OUT),
    "program_cs_present": program.is_file(),
    "program_material_over_challenge_fix": contains(program, "r42du_material_over_challenge_promoted") and contains(program, "rawChallengeLike") and contains(program, "challengeLike = rawChallengeLike && !materialLike"),
    "program_writes_article_when_material_like": contains(program, "if (materialLike)") and contains(program, "article_text.txt"),
    "native_counts_use_paintable_rows": contains(program, "for (const row of rows()) { const r = roleOf(row);"),
    "metro_parity_js_present": contains(program, "r42du_metro_archive_parity"),
    "r42ds_metro_review_parity_present": contains(surface, "_METRO_SEAGULL_SEMANTIC_ROWS") and contains(surface, "r42du_metro_archive_review_parity"),
    "optional_recolor_style_present": contains(program, "ytce-r42du-text-recolor"),
    "bridge_alias_still_present": contains(overlay, "def r42ct_capture_material_with_native_webview2"),
    "single_source_for_app_test": "https://archive.ph/6mr3C",
    "side_effects": {
        "network_actions_performed": False,
        "native_webview2_started": False,
        "tor_camoufox_started": False,
        "account_polling_performed": False,
        "message_read_performed": False,
        "outbound_channel_send_performed": False,
        "credentials_read": False,
        "openclaw_tool_call_performed": False,
    },
}
(OUT / "r42du_archive_visible_material_source_roles_probe_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
