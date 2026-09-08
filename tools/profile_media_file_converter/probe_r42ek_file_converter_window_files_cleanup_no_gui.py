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
with tempfile.TemporaryDirectory(prefix="ytce_r42ek_converter_probe_") as tmp:
    sample = Path(tmp) / "r42ek_probe.txt"
    sample.write_text("R42EK local-only converter probe\n", encoding="utf-8")
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
    "schema": "ytce.r42ek.file_converter_window_files_cleanup.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_FILE_CONVERTER_WINDOW_FILES_CLEANUP",
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
        "files_rows_no_converter_checkbox": "converter_checkbox = ctk.CTkCheckBox" not in main_text,
        "files_rows_no_k_button": "keep_button = ctk.CTkButton(row_frame" not in main_text,
        "files_header_open_folder_icon": "self.files_output_folder_button" in main_text,
        "drop_box_holds_list_inside_drop_area": "self.file_converter_queue_textbox = ctk.CTkTextbox(\n            self.file_converter_drop_frame" in main_text,
        "take_all_by_file_type": "def _file_converter_take_all_from_files" in main_text,
        "drag_files_rows_to_converter": "def _session_file_drop_target_is_converter" in main_text,
        "clear_button_short_label": "text=\"Clear\"" in main_text and "text=\"Clear converter\"" not in main_text,
        "media_windows_have_target_dropdown": "id=\"convertTarget\"" in main_text,
        "media_windows_have_keep_original_toggle": "id=\"convertKeep\"" in main_text,
        "image_window_outputs_enter_files_after_conversion": "source_label=\"image-window conversion\"" in main_text,
        "video_audio_window_outputs_enter_files_after_conversion": "source_label=\"video-audio-window conversion\"" in main_text,
        "converter_backend_local_only": _attr(plan, "method", "") in {"python_text", "ffmpeg"},
        "archive_ph_not_hit": "archive.ph" not in json.dumps(_attr(plan, "command", [])).lower(),
        "native_webview2_not_started": "webview2" not in json.dumps(_attr(plan, "command", [])).lower(),
        "network_actions_not_performed_by_converter": not any(str(part).lower().startswith(("http://", "https://")) for part in _attr(plan, "command", [])),
    },
}
print(json.dumps(payload, indent=2))
out_dir = ROOT / "profile_media_live_captures" / "r42ek_file_converter_window_files_cleanup"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "r42ek_file_converter_window_files_cleanup_probe_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
if not all(payload["verdict"].values()):
    failed = [name for name, ok in payload["verdict"].items() if not ok]
    raise SystemExit("R42EK probe failed: " + ", ".join(failed))
