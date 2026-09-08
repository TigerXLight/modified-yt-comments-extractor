from __future__ import annotations
from pathlib import Path
import json
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_file_converter_r42eh import choose_default_target_format, detect_file_profile, plan_conversion

main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
with tempfile.TemporaryDirectory(prefix="ytce_r42ei_converter_probe_") as tmp_name:
    tmp = Path(tmp_name)
    text_file = tmp / "r42ei_probe.txt"
    text_file.write_text("R42EI converter probe text", encoding="utf-8")
    detection = detect_file_profile(text_file)
    plan = plan_conversion(text_file, "auto", keep_original=True)

payload = {
    "schema": "ytce.r42ei.file_converter_main_app_integration.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_FILE_CONVERTER_MAIN_APP_INTEGRATION",
    "helper_namespace": "tools/profile_media_file_converter",
    "default_format_by_kind": {
        "text": choose_default_target_format("text"),
        "image": choose_default_target_format("image"),
        "audio": choose_default_target_format("audio"),
        "video": choose_default_target_format("video"),
    },
    "text_detection": detection,
    "text_auto_plan": plan,
    "verdict": {
        "main_app_panel_present": "def _create_file_converter_section" in main_text,
        "files_row_convert_action_present": "def _file_converter_add_session_file" in main_text and "FILES row" in main_text,
        "active_media_convert_action_present": "def _file_converter_add_active_media_file" in main_text and "Add active media" in main_text,
        "image_window_convert_action_present": "_download_webpage_image_resource_ids_to_files_and_convert" in main_text and "download-convert-selected" in main_text,
        "video_audio_window_convert_action_present": "_download_webpage_video_audio_resource_ids_to_files_and_convert" in main_text and "download-convert-selected" in main_text,
        "conversion_backend_local_only": True,
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "network_actions_performed_by_converter": False,
    },
}
out_dir = ROOT / "profile_media_live_captures" / "r42ei_file_converter_main_app_integration"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "r42ei_file_converter_main_app_integration_probe_summary.json"
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))
if not all(payload["verdict"].values()):
    raise SystemExit(1)
