from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT_ROOT = ROOT / "profile_media_live_captures" / "r42dt_archive_native_webview2_bridge"
OUT_DIR = OUT_ROOT / ("probe_" + time.strftime("%Y%m%d_%H%M%S"))

def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import importlib

    overlay = importlib.import_module("profile_media_link_source_real_webview_overlay_v83d")
    chain = importlib.import_module("profile_media_archive_material_chain_r42ct")

    r42cr_ok = callable(getattr(overlay, "r42cr_capture_material_with_native_webview2", None))
    r42ct_ok = callable(getattr(overlay, "r42ct_capture_material_with_native_webview2", None))
    resolver = getattr(chain, "_resolve_native_webview2_material_capture_callable", None)
    resolved_name = ""
    resolved_ok = False
    if callable(resolver):
        fn, resolved_name = resolver()
        resolved_ok = callable(fn)

    overlay_text = _load_text(ROOT / "profile_media_link_source_real_webview_overlay_v83d.py")
    chain_text = _load_text(ROOT / "profile_media_archive_material_chain_r42ct.py")

    summary = {
        "mode": "probe",
        "schema": "ytce.r42dt.archive_native_webview2_bridge_probe.v1",
        "outdir": str(OUT_DIR),
        "single_source_for_app_test": "https://archive.ph/6mr3C",
        "overlay_exports_r42cr": r42cr_ok,
        "overlay_exports_r42ct_alias": r42ct_ok,
        "archive_chain_has_bridge_resolver": callable(resolver),
        "archive_chain_resolved_native_bridge": resolved_ok,
        "archive_chain_resolved_bridge_name": str(resolved_name),
        "archive_chain_uses_generic_playwright_fallback": "generic Playwright fallback" in chain_text and "not used" not in chain_text,
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
        "notes": [
            "Probe only: imports and resolves the bridge without starting browser/network.",
            "The app test should use exactly one URL: https://archive.ph/6mr3C",
        ],
    }

    path = OUT_DIR / "r42dt_archive_native_webview2_bridge_probe_summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not (r42cr_ok and r42ct_ok and callable(resolver) and resolved_ok):
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
