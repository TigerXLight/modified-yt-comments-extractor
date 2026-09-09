from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

main_text = (ROOT / "main.py").read_text(encoding="utf-8")
backend_text = (ROOT / "profile_media_file_converter_r42eh.py").read_text(encoding="utf-8")

def segment(start_name: str, end_name: str) -> str:
    start = main_text.find("    def " + start_name)
    end = main_text.find("    def " + end_name, start + 1)
    if start == -1 or end == -1:
        return ""
    return main_text[start:end]

convert_ui = segment("_open_file_converter_convert_settings_window", "_open_file_converter_compression_settings_window")
compression_ui = segment("_open_file_converter_compression_settings_window", "_file_converter_toggle_compression_for_selected")
apply_simple = segment("_file_converter_apply_simple_compression_profiles", "_file_converter_settings_window_shell")
normalised_compression = segment("_file_converter_normalised_compression_settings", "_file_converter_resolve_auto_target_for_path")

checks = {
    "main_py_compile_context_present": "def _open_file_converter_convert_settings_window" in main_text,
    "convert_settings_scrollable_body": "CTkScrollableFrame" in convert_ui,
    "compression_settings_scrollable_body": "CTkScrollableFrame" in compression_ui,
    "convert_advanced_tabs_image_video_audio": 'values=["Image", "Video", "Audio"]' in convert_ui and "advanced_tab_var" in convert_ui,
    "compression_advanced_tabs_image_video_audio": 'values=["Image", "Video", "Audio"]' in compression_ui and "advanced_tab_var" in compression_ui,
    "compression_simple_image_resolution": '"Image resolution"' in compression_ui and '"image_target_resolution"' in compression_ui,
    "compression_simple_video_resolution": '"Video resolution"' in compression_ui and '"video_target_resolution"' in compression_ui,
    "convert_simple_no_resolution_controls": '"Image resolution"' not in convert_ui and '"Video resolution"' not in convert_ui,
    "resolution_defaults_present": '"image_target_resolution": "auto"' in main_text and '"video_target_resolution": "auto"' in main_text,
    "resolution_allowed_helpers_present": "_file_converter_allowed_image_target_resolutions" in main_text and "_file_converter_allowed_video_target_resolutions" in main_text,
    "resolution_normalised": 'merged["image_target_resolution"]' in normalised_compression and 'merged["video_target_resolution"]' in normalised_compression,
    "simple_resolution_maps_to_max_side": "_file_converter_target_resolution_to_max_side" in apply_simple and 'next_settings["image_max_dimension"]' in apply_simple and 'next_settings["video_max_dimension"]' in apply_simple,
    "only_optimised_speed_presets_kept": '["Optimised", "Speed"]' in convert_ui and '["Optimised", "Speed"]' in compression_ui and "Lower Size" not in main_text,
    "r42et_matcher_retained": "bits_per_pixel_frame" in backend_text and "_system_capability_probe" in backend_text and "remux_copy" in backend_text,
    "prior_pack_grid_crash_marker_absent": "file_size_label.grid" not in main_text,
}

print(json.dumps({
    "schema": "ytce.r42eu.scrollable_advanced_tabs_resolution_settings.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_STATIC_UI_CONTRACT_CHECK",
    "checks": checks,
    "verdict": all(checks.values()),
}, indent=2))

if not all(checks.values()):
    raise SystemExit(1)
