from __future__ import annotations

"""R42EC archive role closeout probe.

This is a no-GUI / no-network / no-archive-hit verification layer after R42EB.
It checks that:
- cached archive material and role payload still produce non-zero counts;
- the local fixture contains deterministic media targets, not just text captions;
- the native Program.cs can log page-side toolbar state after receiving it;
- the probe accepts the real native log count format: counts_semantic=P0/S35/T0/U15.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
import json
import re
import sys

SOURCE = "https://archive.ph/6mr3C"
SCHEMA = "ytce.r42ec.archive_role_closeout_no_gui.v1"
VERSION = "20260907_r42ec_archive_role_closeout_no_gui"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(_read(path))
    except Exception:
        return {}


def _latest_file(base: Path, pattern: str) -> Path | None:
    items = [p for p in base.rglob(pattern) if p.is_file()]
    if not items:
        return None
    return max(items, key=lambda p: p.stat().st_mtime)


def build_closeout_probe(*, project_root: str | Path | None = None, recolor: bool = False) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from profile_media_archive_role_local_fixture_r42eb import (
        build_cached_archive_role_fixture,
        clean_source_url,
        _log_has_count_format,
    )

    fixture_result = build_cached_archive_role_fixture(
        project_root=root,
        source_url=SOURCE,
        recolor=recolor,
        output_root=root / "profile_media_live_captures" / "r42ec_archive_role_closeout_no_gui",
    )

    fixture_path = Path(str(fixture_result.get("fixture_path") or ""))
    fixture_html = _read(fixture_path)
    payload_summary = fixture_result.get("payload_summary") if isinstance(fixture_result.get("payload_summary"), Mapping) else {}
    sem_counts = payload_summary.get("semantic_counts") if isinstance(payload_summary.get("semantic_counts"), Mapping) else {}
    med_counts = payload_summary.get("media_counts") if isinstance(payload_summary.get("media_counts"), Mapping) else {}

    program = root / "tools" / "webview2_source_role_editor_native" / "Program.cs"
    program_text = _read(program)

    log_path = root / "profile_media_live_captures" / "link_source_role_webview_overlay" / "selected_link_source_role_native_webview2_launch.log"
    log_text = _read(log_path)
    tail = "\n".join(log_text.splitlines()[-700:])

    expected_sem = {k: int(sem_counts.get(k, 0) or 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")}
    expected_med = {k: int(med_counts.get(k, 0) or 0) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")}

    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_CLOSEOUT",
        "source_url": clean_source_url(SOURCE),
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "app_started": False,
        "fixture_result": fixture_result,
        "payload_counts": {
            "semantic": expected_sem,
            "media": expected_med,
        },
        "fixture_static_checks": {
            "fixture_file_present": fixture_path.is_file(),
            "fixture_url_is_file_url": str(fixture_result.get("fixture_file_url") or "").startswith("file:///"),
            "fixture_has_main_video_target": "data-ytce-main-video='1'" in fixture_html or 'data-ytce-main-video="1"' in fixture_html,
            "fixture_has_local_media_class": "r42ec-local-media-target" in fixture_html,
            "fixture_has_no_http_resource_refs": not bool(re.search(r"""(?:src|href)\s*=\s*['\"]https?://""", fixture_html, flags=re.IGNORECASE)),
            "fixture_has_captioned_figures": fixture_html.lower().count("<figure") >= 2 and "figcaption" in fixture_html.lower(),
        },
        "program_static_checks": {
            "program_has_native_toolbar_state_success_log": 'r42ec_state_applied=true' in program_text and '_log.Log("native_toolbar_state"' in program_text,
            "program_has_page_side_native_toolbar_state_post": "post('native_toolbar_state'" in program_text,
            "program_has_role_paint_ready_marker": "r42dv_role_paint_js_ready" in program_text,
            "program_uses_p_s_t_u_count_log_format": "counts_semantic={semanticCountsText}; counts_media={mediaCountsText}" in program_text,
        },
        "latest_native_log_observation": {
            "log_present": log_path.is_file(),
            "tail_has_file_fixture": "file:///" in tail and "r42eb_cached_archive_role_fixture.html" in tail,
            "tail_has_semantic_counts_current_format": _log_has_count_format(tail, "counts_semantic", expected_sem),
            "tail_has_media_counts_current_format": _log_has_count_format(tail, "counts_media", expected_med),
            "tail_has_role_paint_ready": "r42dv_role_paint_js_ready" in tail,
            "tail_has_first_role_paint": "first_role_paint" in tail,
            "tail_has_native_toolbar_state": "native_toolbar_state:" in tail or "type=native_toolbar_state" in tail,
        },
        "side_effects": {
            "archive_ph_hit": False,
            "native_webview2_started": False,
            "app_started": False,
            "network_actions_performed": False,
            "tor_camoufox_started": False,
            "openclaw_tool_call_performed": False,
            "account_polling_performed": False,
            "message_read_performed": False,
            "outbound_channel_send_performed": False,
            "credentials_read": False,
        },
    }
    payload_counts_nonzero = expected_sem.get("SECONDARY", 0) > 0 and expected_med.get("SECONDARY", 0) > 0
    text_roles_ok = int((payload_summary or {}).get("semantic_rows") or 0) >= 50
    media_targets_ok = all(result["fixture_static_checks"][k] for k in ("fixture_has_main_video_target", "fixture_has_local_media_class", "fixture_has_captioned_figures"))
    count_probe_fixed = result["latest_native_log_observation"]["tail_has_semantic_counts_current_format"] and result["latest_native_log_observation"]["tail_has_media_counts_current_format"]
    state_log_patch_present = result["program_static_checks"]["program_has_native_toolbar_state_success_log"]
    result["verdict"] = {
        "payload_counts_nonzero": payload_counts_nonzero,
        "local_fixture_exercises_text_roles": text_roles_ok,
        "local_fixture_exercises_media_targets": media_targets_ok,
        "log_probe_count_false_negative_fixed": count_probe_fixed,
        "native_toolbar_state_logging_patch_present": state_log_patch_present,
        "no_gui_no_network_safe": True,
        "ready_to_close_archive_role_display_issue": bool(payload_counts_nonzero and text_roles_ok and media_targets_ok and state_log_patch_present),
        "next_workstream": "semantic_media_logic_comprehension_matrix_and_text_colouring_cleanup",
    }

    out = root / "profile_media_live_captures" / "r42ec_archive_role_closeout_no_gui" / ("probe_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "r42ec_archive_role_closeout_no_gui_summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["summary_path"] = str(summary_path)
    return result


def run_self_test() -> None:
    here = Path(__file__).resolve().parent
    program = here / "tools" / "webview2_source_role_editor_native" / "Program.cs"
    if program.is_file():
        text = _read(program)
        assert "r42ec_state_applied=true" in text
    from profile_media_archive_role_local_fixture_r42eb import _log_has_count_format
    expected = {"PRIMARY": 0, "SECONDARY": 35, "TERTIARY": 0, "UNKNOWN": 15, "BLANK": 11}
    assert _log_has_count_format("counts_semantic=P0/S35/T0/U15", "counts_semantic", expected)
    assert _log_has_count_format("counts_semantic=0,35,0,15", "counts_semantic", expected)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="R42EC no-GUI archive role closeout probe.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--recolor", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        print("R42EC self-test passed.")
    else:
        print(json.dumps(build_closeout_probe(project_root=args.root, recolor=args.recolor), ensure_ascii=False, indent=2))
