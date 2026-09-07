from __future__ import annotations

"""R42EA no-GUI/no-network archive role-refresh live spooler.

R42DX/R42DY/R42DZ proved that the archive.ph material and role-ready payload are
valid from local files.  R42EA closes the remaining app-side gap without opening
the app, without starting WebView2, and without touching archive.ph during tests.

The production helper in main.py uses this module after R42DS spans are built:
it writes a `role_overlay_refresh` command only to an already-running native
WebView2 warm server.  It never starts a helper itself.  Program.cs/R42DZ then
refreshes in-place if the matching archive page is already loaded; otherwise it
logs `r42dz_role_overlay_refresh_deferred_no_navigation` and returns.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
import json
import os
import re
import subprocess
import sys
import time
import uuid

SOURCE = "https://archive.ph/6mr3C"
SCHEMA = "ytce.r42ea.archive_role_refresh_live_spool.v1"
VERSION = "20260907_r42ea_existing_native_server_role_refresh_spool"


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _canonical_url(value: object) -> str:
    text = str(value or "").strip().strip('"\'')
    if not text:
        return ""
    text = text.replace("\\(", "(").replace("\\)", ")").replace("\\]", "]").replace("\\[", "[")
    urls = re.findall(r"https?://[^\s\]\)]+", text, flags=re.IGNORECASE)
    if urls:
        text = urls[0]
    return text.strip().strip("<>").rstrip(".,;:)]}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"_read_error": repr(exc), "_path": str(path)}
    return {}


def _json_int(obj: Mapping[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(obj.get(key) or default)
    except Exception:
        return default


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            completed = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            return str(pid) in (completed.stdout or "")
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _command_dir(project_root: Path) -> Path:
    return project_root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "r42cr_native_editor_server"


def _ready_path(project_root: Path) -> Path:
    return _command_dir(project_root) / "r42cr_server_ready.json"


def _role_db_path(project_root: Path) -> Path:
    return project_root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_roleplan.sqlite"


def _role_db_summary_path(project_root: Path) -> Path:
    return project_root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_roleplan_summary.json"


def native_server_status(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    ready = _ready_path(root)
    data = _read_json(ready)
    pid = _json_int(data, "pid", 0)
    alive = _pid_alive(pid)
    return {
        "ready_path": str(ready),
        "ready_file_present": ready.is_file(),
        "pid": pid,
        "pid_alive": alive,
        "command_dir": str(_command_dir(root)),
        "server_ready": ready.is_file() and alive,
    }


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("pending_" + path.name + "_" + uuid.uuid4().hex + ".tmp")
    with open(temp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except Exception:
            pass
    os.replace(str(temp), str(path))


def _payload_counts(payload_path: Path) -> dict[str, Any]:
    payload = _read_json(payload_path)
    rows_by_mode = payload.get("rows_by_mode") if isinstance(payload, dict) else {}
    def rows(mode: str) -> list[Mapping[str, Any]]:
        value = rows_by_mode.get(mode) if isinstance(rows_by_mode, dict) else []
        return value if isinstance(value, list) else []
    def count(mode: str) -> dict[str, int]:
        out = {"PRIMARY": 0, "SECONDARY": 0, "TERTIARY": 0, "UNKNOWN": 0, "BLANK": 0}
        key = "media_source_role" if mode == "media" else "semantic_role"
        for row in rows(mode):
            role = _clean(row.get(key) or row.get("active_role") or row.get("role") or "UNKNOWN").upper()
            if role not in out:
                role = "UNKNOWN"
            out[role] += 1
        return out
    return {
        "payload_readable": bool(payload) and not payload.get("_read_error"),
        "selected_url": _canonical_url(payload.get("selected_url") or payload.get("launch_start_url") or ""),
        "semantic_rows": len(rows("semantic")),
        "media_rows": len(rows("media")),
        "semantic_counts": count("semantic"),
        "media_counts": count("media"),
        "plain_text_chars": len(str(payload.get("plain_text") or "")),
    }


def spool_live_role_overlay_refresh_if_server_ready(
    *,
    project_root: str | Path | None = None,
    payload_path: str | Path,
    changes_path: str | Path,
    selected_url: object = SOURCE,
    mode: str = "semantic",
    output_root: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Queue role_overlay_refresh only when an existing native server is alive.

    The function never starts the app or native helper.  In dry_run mode it writes
    a command to a private dry-run folder, never to the live server folder.
    """

    root = Path(project_root or Path.cwd()).resolve()
    payload = Path(payload_path)
    changes = Path(changes_path)
    if not payload.is_absolute():
        payload = (root / payload).resolve()
    if not changes.is_absolute():
        changes = (root / changes).resolve()

    selected = _canonical_url(selected_url) or _canonical_url(_payload_counts(payload).get("selected_url")) or SOURCE
    initial_mode = "media" if str(mode or "").lower() == "media" else "semantic"
    counts = _payload_counts(payload)
    status = native_server_status(root)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_base = Path(output_root or (root / "profile_media_live_captures" / "r42ea_archive_role_refresh_live_spool"))
    out_base.mkdir(parents=True, exist_ok=True)

    live_allowed = (not dry_run) and bool(status.get("server_ready"))
    destination_dir = _command_dir(root) if live_allowed else (out_base / ("dry_run_" + stamp) / "dry_run_native_command_dir")
    command_path = destination_dir / f"command_{stamp}_{os.getpid()}_r42ea_role_overlay_refresh.json"

    command: dict[str, Any] = {
        "marker": "YTCE_R42CR_NATIVE_WEBVIEW2_SERVER_COMMAND",
        "created_at": time.time(),
        "action": "role_overlay_refresh",
        "root": str(root),
        "payload": str(payload),
        "changes": str(changes),
        "role_db": str(_role_db_path(root)),
        "role_db_summary": str(_role_db_summary_path(root)),
        "url": selected,
        "mode": initial_mode,
        "r42ea_existing_server_only": True,
        "r42ea_no_gui_no_network_spool": True,
        "r42ea_expect_program_r42dz_no_navigation_guard": True,
    }
    if dry_run or not live_allowed:
        command["do_not_place_in_live_command_dir"] = True
        command["r42ea_dry_run"] = True

    _atomic_write_json(command_path, command)

    queued = bool(live_allowed)
    reason = "server_command_queued_existing_native_server_no_start" if queued else (
        "dry_run_only" if dry_run else "native_server_not_ready_no_gui_no_start"
    )
    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "LIVE_EXISTING_SERVER_SPOOL" if queued else "NO_GUI_NO_NETWORK_DRY_RUN_OR_SERVER_ABSENT",
        "source_url": selected,
        "payload_path": str(payload),
        "changes_path": str(changes),
        "command_path": str(command_path),
        "queued": queued,
        "launched": queued,  # compatibility with the older app log wording: queued means dispatched to existing helper.
        "reason": reason,
        "server_status": status,
        "payload_counts": counts,
        "side_effects": {
            "app_started": False,
            "native_webview2_started_by_this_tool": False,
            "archive_ph_hit": False,
            "network_actions_performed": False,
            "tor_camoufox_started": False,
            "openclaw_tool_call_performed": False,
            "account_polling_performed": False,
            "message_read_performed": False,
            "outbound_channel_send_performed": False,
            "credentials_read": False,
        },
        "expected_native_runtime_marker_if_live_server_receives_it": "r42dw_role_overlay_refresh_applied OR r42dz_role_overlay_refresh_deferred_no_navigation",
        "expected_counter_values": {
            "semantic": counts.get("semantic_counts", {}),
            "media": counts.get("media_counts", {}),
        },
    }

    summary_path = out_base / ("r42ea_role_refresh_spool_summary_" + stamp + ".json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def build_no_gui_probe(
    *,
    project_root: str | Path | None = None,
    source_url: object = SOURCE,
    recolor: bool = False,
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from profile_media_archive_role_payload_r42dw import build_latest_archive_role_payload  # type: ignore

    out_root = root / "profile_media_live_captures" / "r42ea_archive_role_refresh_live_spool"
    payload_result = build_latest_archive_role_payload(
        project_root=root,
        source_url=source_url,
        output_root=out_root,
        text_paint_style="recolor" if recolor else "",
    )
    payload_path = payload_result.get("payload_path") or ""
    changes_path = payload_result.get("changes_path") or str(out_root / "archive_role_overlay_changes_r42ea.jsonl")

    spool = spool_live_role_overlay_refresh_if_server_ready(
        project_root=root,
        payload_path=payload_path,
        changes_path=changes_path,
        selected_url=payload_result.get("source_url") or source_url,
        mode="semantic",
        output_root=out_root,
        dry_run=True,
    )

    main_text = (root / "main.py").read_text(encoding="utf-8", errors="replace") if (root / "main.py").is_file() else ""
    overlay_text = (root / "profile_media_link_source_real_webview_overlay_v83d.py").read_text(encoding="utf-8", errors="replace") if (root / "profile_media_link_source_real_webview_overlay_v83d.py").is_file() else ""
    program_text = (root / "tools" / "webview2_source_role_editor_native" / "Program.cs").read_text(encoding="utf-8", errors="replace") if (root / "tools" / "webview2_source_role_editor_native" / "Program.cs").is_file() else ""

    summary: dict[str, Any] = {
        "schema": SCHEMA + ".probe",
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_APP_SIDE_SPOOL_AUDIT",
        "source_url": _canonical_url(source_url),
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "app_started": False,
        "payload_result": payload_result,
        "spool_dry_run": spool,
        "static_wiring": {
            "main_uses_r42ea_spooler": "spool_live_role_overlay_refresh_if_server_ready" in main_text,
            "main_no_longer_uses_launch_role_overlay_for_post_capture_refresh": "native_command_action\\\": \\\"role_overlay_refresh" not in main_text and "native_command_action\": \"role_overlay_refresh" not in main_text,
            "overlay_can_queue_native_command_actions": "native_command_action" in overlay_text and "_r42cr_send_native_server_command" in overlay_text,
            "program_has_role_overlay_refresh_branch": "role_overlay_refresh" in program_text,
            "program_has_r42dz_no_navigation_guard": "r42dz_role_overlay_refresh_deferred_no_navigation" in program_text and "YTCE_R42DZ_ALLOW_ROLE_REFRESH_NAVIGATION" in program_text,
            "program_updates_native_toolbar_from_payload": "LoadNativeToolbarFromPayload(_payloadJson" in program_text and "counts_semantic=" in program_text,
        },
        "verdict": {
            "payload_ok": bool(payload_result.get("ok")) and int(payload_result.get("semantic_rows") or 0) > 0 and int(payload_result.get("media_rows") or 0) > 0,
            "dry_run_command_ok": bool(spool.get("command_path")) and Path(str(spool.get("command_path") or "")).is_file(),
            "app_side_uses_existing_server_only_spool": "spool_live_role_overlay_refresh_if_server_ready" in main_text,
            "no_gui_no_network_safe": True,
            "ready_for_one_final_visual_check_later": bool(payload_result.get("ok")) and "spool_live_role_overlay_refresh_if_server_ready" in main_text,
        },
        "next_step": "Do not reopen archive.ph for repeated tests. Use this probe to confirm app-side refresh is queued existing-server-only; then do one final visual check only after the no-GUI chain is green.",
    }

    probe_dir = out_root / ("probe_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    probe_dir.mkdir(parents=True, exist_ok=True)
    summary_path = probe_dir / "r42ea_archive_role_refresh_live_spool_probe_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def run_self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        payload_dir = root / "payloads"
        payload_dir.mkdir()
        payload = payload_dir / "payload.json"
        changes = payload_dir / "changes.jsonl"
        payload.write_text(json.dumps({
            "selected_url": SOURCE,
            "rows_by_mode": {
                "semantic": [
                    {"text": "People shout seagull eater", "semantic_role": "SECONDARY"},
                    {"text": "Unknown row", "semantic_role": "UNKNOWN"},
                    {"text": "Blank row", "semantic_role": "BLANK"},
                ],
                "media": [
                    {"text": "People shout seagull eater", "media_source_role": "SECONDARY"},
                    {"text": "Unknown row", "media_source_role": "UNKNOWN"},
                ],
            },
            "plain_text": "People shout seagull eater",
        }), encoding="utf-8")
        result = spool_live_role_overlay_refresh_if_server_ready(
            project_root=root,
            payload_path=payload,
            changes_path=changes,
            selected_url=SOURCE,
            dry_run=True,
        )
        assert result["queued"] is False
        assert result["reason"] == "dry_run_only"
        assert Path(result["command_path"]).is_file()
        assert result["payload_counts"]["semantic_rows"] == 3
        assert result["payload_counts"]["semantic_counts"]["SECONDARY"] == 1
        assert result["payload_counts"]["media_counts"]["UNKNOWN"] == 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="R42EA no-GUI/no-network existing-native-server role refresh spooler.")
    parser.add_argument("source_url", nargs="?", default=SOURCE)
    parser.add_argument("--root", default=".")
    parser.add_argument("--recolor", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--live-if-server-ready", action="store_true", help="Queue to live command dir only if existing native server is already alive; never starts it.")
    parser.add_argument("--payload", default="")
    parser.add_argument("--changes", default="")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("R42EA self-test passed.")
        raise SystemExit(0)
    if args.live_if_server_ready:
        result = spool_live_role_overlay_refresh_if_server_ready(
            project_root=args.root,
            payload_path=args.payload,
            changes_path=args.changes,
            selected_url=args.source_url,
            dry_run=False,
        )
    else:
        result = build_no_gui_probe(project_root=args.root, source_url=args.source_url, recolor=args.recolor)
    print(json.dumps(result, ensure_ascii=False, indent=2))
