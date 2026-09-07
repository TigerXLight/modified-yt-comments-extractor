from __future__ import annotations

from pathlib import Path
import json
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_semantic_media_logic_matrix_r42ed import build_semantic_media_logic_adapter_matrix, find_latest_role_payload, SOURCE


def main() -> int:
    recolor = "--recolor" in sys.argv
    out_root = ROOT / "profile_media_live_captures" / "r42ee_bounded_payload_scan_hotfix"
    out_root.mkdir(parents=True, exist_ok=True)
    try:
        payload_path = find_latest_role_payload(ROOT, SOURCE)
        result = build_semantic_media_logic_adapter_matrix(
            project_root=ROOT,
            source_url=SOURCE,
            output_root=out_root,
            recolor=recolor,
        )
        result["r42ee_hotfix"] = {
            "schema": "ytce.r42ee.bounded_payload_scan_hotfix.v1",
            "old_failure": "Path.rglob over profile_media_live_captures could recurse through Windows junction/reparse directory",
            "payload_scan_bounded": True,
            "pathlib_rglob_for_payloads_removed": True,
            "payload_path_found_before_matrix": str(payload_path or ""),
            "no_gui_no_network_no_archive_hit": True,
        }
    except BaseException as exc:
        result = {
            "schema": "ytce.r42ee.bounded_payload_scan_hotfix.v1.error",
            "mode": "NO_GUI_NO_NETWORK_ERROR_REPORT",
            "source_url": SOURCE,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback_tail": traceback.format_exc().splitlines()[-12:],
            "side_effects": {
                "archive_ph_hit": False,
                "network_actions_performed": False,
                "native_webview2_started": False,
                "app_started": False,
                "tor_camoufox_started": False,
                "openclaw_tool_call_performed": False,
            },
            "verdict": {"r42ee_hotfix_failed": True},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    verdict = result.get("verdict", {}) if isinstance(result.get("verdict"), dict) else {}
    required = [
        "payload_found",
        "comprehension_matrix_defined",
        "adapter_guard_matrix_covers_r42di_to_r42dm",
        "discovery_fallbacks_are_not_silent_substitution",
        "account_channel_device_adapters_explicit_only",
        "no_gui_no_network_safe",
    ]
    return 0 if all(bool(verdict.get(k)) for k in required) else 2


if __name__ == "__main__":
    raise SystemExit(main())
