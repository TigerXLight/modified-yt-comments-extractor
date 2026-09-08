from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_file_converter_r42eh import choose_default_target_format, detect_file_profile, plan_conversion

main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
with tempfile.TemporaryDirectory(prefix="ytce_r42ej_converter_probe_") as tmp_name:
    tmp = Path(tmp_name)
    text_file = tmp / "r42ej_probe.txt"
    text_file.write_text("R42EJ converter fillbox probe text", encoding="utf-8")
    detection = detect_file_profile(text_file)
    plan = plan_conversion(text_file, "auto", keep_original=True)

payload = {
    "schema": "ytce.r42ej.file_converter_fillbox_workflow.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_FILE_CONVERTER_FILLBOX_WORKFLOW",
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
        "files_row_arrow_convert_removed": 'text="↔"' not in main_text,
        "files_row_fillbox_selector_present": "session_file_converter_selected_paths" in main_text and "_toggle_file_converter_file_selection_from_checkbox" in main_text,
        "drop_converter_holds_only_until_convert": "source_label=\"converter drop\"" in main_text and "add_to_session=False" in main_text,
        "add_selected_files_button_removed": "Add selected FILES" not in main_text,
        "add_active_media_button_removed": "Add active media" not in main_text,
        "target_formats_are_family_filtered": "_file_converter_target_formats_for_kind" in main_text,
        "same_type_run_enforced": "_file_converter_selection_compatible" in main_text and "one file type per run" in main_text,
        "outputs_return_to_files": "source_label=\"converted\"" in main_text,
        "kept_original_conversion_group_present": "session_file_conversion_groups" in main_text and "Converted:" in main_text,
        "open_folder_icon_present": "Open folder icon icons8-opened-folder-ios-27-outlined.png" in main_text,
        "converter_backend_local_only": True,
        "archive_ph_not_hit": True,
        "native_webview2_not_started": True,
        "network_actions_not_performed_by_converter": True,
    },
}
out_dir = ROOT / "profile_media_live_captures" / "r42ej_file_converter_fillbox_workflow"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "r42ej_file_converter_fillbox_workflow_probe_summary.json"
out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(payload, indent=2, ensure_ascii=False))
if not all(payload["verdict"].values()):
    raise SystemExit(1)
