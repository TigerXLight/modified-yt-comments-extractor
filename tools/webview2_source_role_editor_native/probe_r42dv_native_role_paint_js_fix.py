from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "profile_media_live_captures" / "r42dv_native_role_paint_js_fix" / ("probe_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
OUT.mkdir(parents=True, exist_ok=True)
program = ROOT / "tools" / "webview2_source_role_editor_native" / "Program.cs"
text = program.read_text(encoding="utf-8", errors="replace") if program.is_file() else ""

def extract_count(var: str) -> dict[str, int]:
    m = re.search(r"const\s+" + re.escape(var) + r"\s*=\s*(\[[\s\S]*?\]);", text)
    out = {"PRIMARY": 0, "SECONDARY": 0, "TERTIARY": 0, "UNKNOWN": 0, "BLANK": 0, "TOTAL": 0}
    if not m:
        return out
    try:
        rows = json.loads(m.group(1))
        out["TOTAL"] = len(rows)
        for item in rows:
            role = str(item.get("role") or "").strip().upper()
            if role in out:
                out[role] += 1
    except Exception:
        pass
    return out

summary = {
    "mode": "probe",
    "schema": "ytce.r42dv.native_role_paint_js_fix_probe.v1",
    "outdir": str(OUT),
    "program_cs_present": program.is_file(),
    "bad_duplicate_textForRow_present": "function textForRow  function textForRow" in text,
    "valid_textForRow_declared": "function textForRow(row) { return clean(row.text || row.url || row.media_url || ''); }" in text,
    "page_side_ready_marker_present": "r42dv_role_paint_js_ready" in text,
    "native_toolbar_state_bridge_present": "post('native_toolbar_state', state)" in text,
    "native_counts_use_paintable_rows": "for (const row of rows()) { const r = roleOf(row); if (out[r] !== undefined) out[r] += 1; }" in text,
    "optional_recolor_css_present": "html.ytce-r42du-text-recolor .ytce-role-hit" in text,
    "semantic_parity_counts": extract_count("semanticParity"),
    "media_parity_counts": extract_count("mediaParity"),
    "expected_runtime_markers_after_app_go": [
        "r42du_material_over_challenge_promoted",
        "r42cr_material_capture_success",
        "R42DS archive source-role surface ready for WebView2: spans=61",
        "page_message: type=r42dv_role_paint_js_ready",
        "page_message: type=first_role_paint",
        "page_message: type=native_toolbar_state"
    ],
    "single_source_for_app_test": "https://archive.ph/6mr3C",
    "side_effects": {
        "network_actions_performed": False,
        "native_webview2_started": False,
        "tor_camoufox_started": False,
        "account_polling_performed": False,
        "message_read_performed": False,
        "outbound_channel_send_performed": False,
        "credentials_read": False,
        "openclaw_tool_call_performed": False
    }
}
(OUT / "r42dv_native_role_paint_js_fix_probe_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
raise SystemExit(1 if summary["bad_duplicate_textForRow_present"] or not summary["valid_textForRow_declared"] else 0)
