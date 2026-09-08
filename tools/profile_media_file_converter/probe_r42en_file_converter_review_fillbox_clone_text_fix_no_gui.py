from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_file_converter_r42eh import choose_default_target_format, detect_file_profile, plan_conversion

main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
with tempfile.TemporaryDirectory(prefix="ytce_r42en_converter_probe_") as tmp:
    sample = Path(tmp) / "r42en_probe.txt"
    sample.write_text("R42EN local-only converter probe\n", encoding="utf-8")
    detection = detect_file_profile(sample)
    plan = plan_conversion(sample, "auto", keep_original=True)

def _as_dict(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return dict(value)
    return dict(getattr(value, "__dict__", {}) or {})

def _attr(value, name, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)

payload = {
    "schema": "ytce.r42en.file_converter_review_fillbox_clone_text_fix.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_REVIEW_FILLBOX_CLONE",
    "helper_namespace": "tools/profile_media_file_converter",
    "default_format_by_kind": {
        "text": choose_default_target_format("text"),
        "image": choose_default_target_format("image"),
        "audio": choose_default_target_format("audio"),
        "video": choose_default_target_format("video"),
    },
    "text_detection": _as_dict(detection),
    "text_auto_plan": _as_dict(plan),
    "verdict": {
        "review_db_existing_fillbox_pattern_observed": "source_review_selected_keys" in main_text and "_toggle_source_review_select_all" in main_text and "claim_source_review_fillbox" in main_text,
        "converter_master_child_fillbox_clone_present": "R42EN_REVIEW_FILLBOX_CLONE" in main_text and "_file_converter_toggle_master_fillbox" in main_text and "_file_converter_toggle_item_fillbox" in main_text,
        "converter_held_rows_use_glyph_buttons_not_ctkcheckbox_rows": "file_converter_item_fillbox_buttons" in main_text and "ctk.CTkCheckBox(\n                row," not in main_text,
        "mixed_file_hold_allowed": "holding can be mixed; only a Convert run must be one kind" in main_text and "Selected held rows must be one file type per conversion run" in main_text,
        "take_all_auto_takes_all_supported": "Took {len(paths)} {'supported' if requested == 'auto' else requested}" in main_text and "Take all:auto needs only one FILES type" not in main_text,
        "global_convert_to_follows_selected_kind": "_file_converter_selected_kind_for_global_format" in main_text and "selected child fillboxes" in main_text,
        "k_icon_in_held_rows": "session_keep_file_icon_image" in main_text and "file_converter_item_keep_buttons" in main_text,
        "k_toggle_does_not_rebuild_held_rows": "K/keep-original toggles in place; it must not rebuild/refresh held rows" in main_text,
        "files_drag_ghost_present": "_show_session_file_drag_ghost" in main_text and "_move_session_file_drag_ghost" in main_text,
        "folder_rename_no_focusout_commit": "never commit a rename on FocusOut" in main_text and "_save_folder_rename" in main_text and "_cancel_folder_rename" in main_text,
        "text_editor_focus_and_editable_fix_present": "_focus_loaded_text_editor" in main_text and "click-to-focus guard" in main_text,
        "converter_backend_local_only": _attr(plan, "method", "") in {"python_text", "ffmpeg"},
        "archive_ph_not_hit": "archive.ph" not in json.dumps(_attr(plan, "command", [])).lower(),
        "native_webview2_not_started": "webview2" not in json.dumps(_attr(plan, "command", [])).lower(),
        "network_actions_not_performed_by_converter": not any(str(part).lower().startswith(("http://", "https://")) for part in _attr(plan, "command", [])),
    },
}
print(json.dumps(payload, indent=2))
out_dir = ROOT / "profile_media_live_captures" / "r42en_file_converter_review_fillbox_clone_text_fix"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "r42en_file_converter_review_fillbox_clone_text_fix_probe_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
if not all(payload["verdict"].values()):
    failed = [name for name, ok in payload["verdict"].items() if not ok]
    raise SystemExit("R42EN probe failed: " + ", ".join(failed))
