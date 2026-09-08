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
with tempfile.TemporaryDirectory(prefix="ytce_r42el_converter_probe_") as tmp:
    sample = Path(tmp) / "r42el_probe.txt"
    sample.write_text("R42EL local-only converter probe\n", encoding="utf-8")
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
    "schema": "ytce.r42el.file_converter_review_style_held_rows.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_FILE_CONVERTER_REVIEW_STYLE_HELD_ROWS",
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
        "files_tickbox_restored_for_multiselect_drag": "session_file_selected_paths" in main_text and "def _toggle_session_file_selected" in main_text,
        "files_tickbox_not_converter_queue": "not a converter queue switch" in main_text,
        "k_not_on_normal_files_rows": "keep_button = ctk.CTkButton(row_frame" not in main_text and "queue arrow, or K button on FILES rows" not in main_text,
        "k_inside_converter_held_rows": "def _toggle_session_file_keep_original_from_converter" in main_text and "text=\"K\"" in main_text,
        "held_files_scrollable_review_style_rows": "self.file_converter_drop_list_frame = ctk.CTkScrollableFrame" in main_text and "self.file_converter_item_widgets" in main_text,
        "each_held_item_has_fillbox_and_target_dropdown": "self.file_converter_item_select_vars" in main_text and "def _file_converter_set_item_target" in main_text and "values=allowed" in main_text,
        "global_convert_to_applies_selected_only": "def _file_converter_apply_global_format_to_selected" in main_text and "selected held rows" in main_text,
        "convert_runs_selected_held_only": "selected_paths = [path for path in queued if path in selected_set]" in main_text,
        "take_all_compact_button": "text=\"Take all\"" in main_text and "text=\"Take all:\"" not in main_text,
        "drag_hover_converter_animation": "session_file_drag_over_converter" in main_text and "Release to hold" in main_text,
        "multi_drag_selected_files": "def _selected_session_file_paths_for_drag" in main_text and "self.session_file_drag_source_paths" in main_text,
        "converter_backend_local_only": _attr(plan, "method", "") in {"python_text", "ffmpeg"},
        "archive_ph_not_hit": "archive.ph" not in json.dumps(_attr(plan, "command", [])).lower(),
        "native_webview2_not_started": "webview2" not in json.dumps(_attr(plan, "command", [])).lower(),
        "network_actions_not_performed_by_converter": not any(str(part).lower().startswith(("http://", "https://")) for part in _attr(plan, "command", [])),
    },
}
print(json.dumps(payload, indent=2))
out_dir = ROOT / "profile_media_live_captures" / "r42el_file_converter_review_style_held_rows"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "r42el_file_converter_review_style_held_rows_probe_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
if not all(payload["verdict"].values()):
    failed = [name for name, ok in payload["verdict"].items() if not ok]
    raise SystemExit("R42EL probe failed: " + ", ".join(failed))
