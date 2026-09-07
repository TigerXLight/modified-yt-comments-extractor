from __future__ import annotations

"""R42DZ command-line-only post-capture role-refresh dispatch probe.

This is deliberately a dry-run layer:
- does not open the app
- does not open native WebView2
- does not navigate archive.ph
- does not start Tor/Camoufox
- does not call OpenClaw
- does not poll account/channel adapters

It proves that the already-captured archive material can produce the exact
role_overlay_refresh command payload the app should send after R42DS spans are
available, while keeping archive.ph access out of the test loop.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
import json
import os
import re
import sys
import time

SOURCE = "https://archive.ph/6mr3C"
SCHEMA = "ytce.r42dz.archive_role_refresh_dispatch_no_gui.v1"
VERSION = "20260907_r42dz_cmdline_archive_role_refresh_dispatch_no_gui"


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _role_counts(rows: list[Mapping[str, Any]], *, mode: str) -> dict[str, int]:
    out = {"PRIMARY": 0, "SECONDARY": 0, "TERTIARY": 0, "UNKNOWN": 0, "BLANK": 0}
    for row in rows:
        role = _clean(row.get("media_source_role" if mode == "media" else "semantic_role") or row.get("active_role") or row.get("role") or "UNKNOWN").upper()
        if role not in out:
            role = "UNKNOWN"
        out[role] += 1
    return out


def _latest_json(base: Path, name: str) -> Path | None:
    if not base.exists():
        return None
    items = [p for p in base.rglob(name) if p.is_file()]
    items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return items[0] if items else None


def _program_static_checks(program_path: Path) -> dict[str, object]:
    txt = program_path.read_text(encoding="utf-8", errors="replace") if program_path.is_file() else ""
    return {
        "program_cs_present": bool(txt),
        "role_overlay_refresh_branch": "role_overlay_refresh" in txt,
        "deferred_no_navigation_marker": "r42dz_role_overlay_refresh_deferred_no_navigation" in txt,
        "explicit_navigation_env_gate": "YTCE_R42DZ_ALLOW_ROLE_REFRESH_NAVIGATION" in txt,
        "old_unconditional_refresh_fallback_navigation_absent": "r42dw_role_overlay_refresh_fallback_navigation\", $" in txt and "explicit_env_allowed=true" in txt,
        "document_start_script_present": "DocumentStartRoleEditorScript" in txt,
        "r42dv_ready_marker_present": "r42dv_role_paint_js_ready" in txt,
        "native_toolbar_state_bridge_present": "native_toolbar_state" in txt,
    }


def build_no_gui_dispatch_probe(
    *,
    project_root: str | Path | None = None,
    source_url: object = SOURCE,
    output_root: str | Path | None = None,
    recolor: bool = False,
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Import only after root is on sys.path.
    from profile_media_archive_role_payload_r42dw import build_latest_archive_role_payload  # type: ignore

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = Path(output_root or (root / "profile_media_live_captures" / "r42dz_archive_role_refresh_dispatch_no_gui"))
    outdir = out_root / ("probe_" + stamp)
    dry_cmd_dir = outdir / "dry_run_native_command_dir"
    outdir.mkdir(parents=True, exist_ok=True)
    dry_cmd_dir.mkdir(parents=True, exist_ok=True)

    payload_result = build_latest_archive_role_payload(
        project_root=root,
        source_url=source_url,
        output_root=out_root,
        text_paint_style="recolor" if recolor else "",
    )

    payload_path = Path(str(payload_result.get("payload_path") or ""))
    payload_data: dict[str, Any] = {}
    if payload_path.is_file():
        payload_data = json.loads(payload_path.read_text(encoding="utf-8", errors="replace"))

    rows_by_mode = payload_data.get("rows_by_mode") if isinstance(payload_data, dict) else {}
    semantic_rows = rows_by_mode.get("semantic") if isinstance(rows_by_mode, dict) else []
    media_rows = rows_by_mode.get("media") if isinstance(rows_by_mode, dict) else []
    if not isinstance(semantic_rows, list):
        semantic_rows = []
    if not isinstance(media_rows, list):
        media_rows = []

    changes_path = payload_result.get("changes_path") or str(outdir / "archive_role_overlay_changes_r42dz.jsonl")
    selected_url = _clean(payload_result.get("source_url") or payload_data.get("selected_url") or SOURCE)

    command = {
        "marker": "YTCE_R42CR_NATIVE_WEBVIEW2_SERVER_COMMAND",
        "created_at": time.time(),
        "action": "role_overlay_refresh",
        "root": str(root),
        "payload": str(payload_path),
        "changes": str(changes_path),
        "role_db": str(root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_roleplan.sqlite"),
        "url": selected_url,
        "mode": "semantic",
        "r42dz_dry_run": True,
        "no_gui": True,
        "no_network": True,
        "do_not_place_in_live_command_dir": True,
    }
    dry_command_path = dry_cmd_dir / ("command_" + stamp + "_r42dz_role_overlay_refresh_DRY_RUN.json")
    dry_command_path.write_text(json.dumps(command, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    latest_material_capture = _latest_json(root / "profile_media_live_captures" / "r42ct_archive_source_material", "native_webview2_material_capture.json")
    latest_surface = _latest_json(root / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2", "archive_source_role_surface_r42ds.json")

    static = _program_static_checks(root / "tools" / "webview2_source_role_editor_native" / "Program.cs")

    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_DRY_RUN_DISPATCH",
        "source_url": selected_url,
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "app_started": False,
        "tor_camoufox_started": False,
        "openclaw_tool_call_performed": False,
        "account_polling_performed": False,
        "outbound_channel_send_performed": False,
        "credentials_read": False,
        "latest_material_capture_path": str(latest_material_capture) if latest_material_capture else "",
        "latest_r42ds_surface_path": str(latest_surface) if latest_surface else "",
        "payload_result": payload_result,
        "payload_rows": {
            "semantic": len(semantic_rows),
            "media": len(media_rows),
        },
        "payload_counts": {
            "semantic": _role_counts(semantic_rows, mode="semantic"),
            "media": _role_counts(media_rows, mode="media"),
        },
        "dry_run_command_path": str(dry_command_path),
        "dry_run_command": {
            "action": command["action"],
            "url": command["url"],
            "payload": command["payload"],
            "mode": command["mode"],
            "do_not_place_in_live_command_dir": True,
        },
        "program_static_checks": static,
        "verdict": {
            "payload_ok": bool(payload_result.get("ok")) and len(semantic_rows) > 0 and len(media_rows) > 0,
            "command_action_ok": command["action"] == "role_overlay_refresh",
            "command_points_to_role_ready_payload": payload_path.is_file() and len(semantic_rows) > 0 and len(media_rows) > 0,
            "no_gui_no_network_archive_safe": True,
            "runtime_no_navigation_guard_present": bool(static.get("deferred_no_navigation_marker") and static.get("explicit_navigation_env_gate")),
            "ready_for_next_step": bool(payload_result.get("ok")) and len(semantic_rows) > 0 and len(media_rows) > 0 and bool(static.get("deferred_no_navigation_marker")),
        },
        "next_step": "Only after this passes, inspect/patch app-side dispatch logging or use a local-file WebView2 render test; do not navigate archive.ph.",
    }

    summary_path = outdir / "r42dz_archive_role_refresh_dispatch_no_gui_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def run_self_test() -> None:
    sample_rows = [
        {"semantic_role": "SECONDARY", "media_source_role": "UNKNOWN"},
        {"semantic_role": "BLANK", "media_source_role": "SECONDARY"},
        {"semantic_role": "other", "media_source_role": ""},
    ]
    assert _role_counts(sample_rows, mode="semantic") == {"PRIMARY": 0, "SECONDARY": 1, "TERTIARY": 0, "UNKNOWN": 1, "BLANK": 1}
    assert _role_counts(sample_rows, mode="media") == {"PRIMARY": 0, "SECONDARY": 1, "TERTIARY": 0, "UNKNOWN": 2, "BLANK": 0}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="R42DZ no-GUI/no-network role-overlay refresh dispatch dry run.")
    parser.add_argument("source_url", nargs="?", default=SOURCE)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-root", default="")
    parser.add_argument("--recolor", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("R42DZ self-test passed.")
        raise SystemExit(0)
    result = build_no_gui_dispatch_probe(
        project_root=args.root,
        source_url=args.source_url,
        output_root=args.output_root or None,
        recolor=args.recolor,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("verdict", {}).get("ready_for_next_step") else 5)
