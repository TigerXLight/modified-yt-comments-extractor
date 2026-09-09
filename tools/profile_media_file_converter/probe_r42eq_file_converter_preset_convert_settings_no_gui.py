from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_file_converter_r42eh import choose_default_target_format, detect_file_profile, plan_conversion, probe_environment

main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
backend_text = (ROOT / "profile_media_file_converter_r42eh.py").read_text(encoding="utf-8", errors="replace")
note_text = (ROOT / "R42EQ_FILE_CONVERTER_PRESET_AND_CONVERT_SETTINGS_POLISH_NOTES_20260909.md").read_text(encoding="utf-8", errors="replace")

with tempfile.TemporaryDirectory(prefix="ytce_r42eq_converter_probe_") as tmp:
    folder = Path(tmp)
    txt = folder / "r42eq_probe.txt"
    txt.write_text("R42EQ local-only converter probe\n", encoding="utf-8")
    img = folder / "r42eq_probe.png"
    img.write_bytes(b"not-real-image-but-plan-only")
    video = folder / "r42eq_probe.mp4"
    video.write_bytes(b"not-real-video-but-plan-only")
    audio = folder / "r42eq_probe.wav"
    audio.write_bytes(b"not-real-audio-but-plan-only")

    detection = detect_file_profile(txt)
    text_plan = plan_conversion(txt, "auto", keep_original=True)
    image_plan = plan_conversion(img, "webp", keep_original=True, compress=True, image_quality=72, image_max_dimension=4000, file_suffix="_compressed")
    video_plan = plan_conversion(video, "mp4", keep_original=True, compress=True, video_crf=26, video_max_dimension=1280, audio_bitrate="160k", audio_sample_rate="48000")
    audio_plan = plan_conversion(audio, "opus", keep_original=True, compress=False, audio_bitrate="320k", audio_sample_rate="48000")
    amr_plan = plan_conversion(audio, "amr", keep_original=True, compress=True, audio_bitrate="24k", audio_sample_rate="16000")

env = probe_environment()
commands_text = json.dumps([text_plan.get("command", []), image_plan.get("command", []), video_plan.get("command", []), audio_plan.get("command", []), amr_plan.get("command", [])]).lower()

payload = {
    "schema": "ytce.r42eq.file_converter_preset_convert_settings_polish.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_PRESET_CONVERT_SETTINGS_POLISH",
    "helper_namespace": "tools/profile_media_file_converter",
    "default_format_by_kind": {
        "text": choose_default_target_format("text"),
        "image": choose_default_target_format("image"),
        "audio": choose_default_target_format("audio"),
        "video": choose_default_target_format("video"),
    },
    "text_detection": dict(detection),
    "image_compress_plan": dict(image_plan),
    "video_compress_plan": dict(video_plan),
    "audio_convert_plan": dict(audio_plan),
    "amr_compress_plan": dict(amr_plan),
    "supported_outputs": env.get("supported_outputs", {}),
    "verdict": {
        "convert_button_uses_asr_style_cog": "file_converter_convert_settings_button" in main_text and "def _open_file_converter_convert_settings_window" in main_text,
        "compression_window_title_exact": '"file_converter_compression_settings_window", "Compression settings"' in main_text and "File Converter compression settings" not in main_text,
        "simple_advanced_in_header_helper": "def _file_converter_pack_settings_header" in main_text and 'values=["Simple", "Advanced"]' in main_text,
        "image_video_audio_quality_labels": all(value in main_text for value in ["Image quality", "Video quality", "Audio quality"]),
        "video_size_reduction_percent_slider": "Video size reduction" in main_text and "video_size_reduction_percent" in main_text and "CTkSlider" in main_text,
        "optimised_preset_for_all_media": main_text.count("Optimised") >= 8 and '"image_quality_profile": "Optimised"' in main_text and '"video_quality_profile": "Optimised"' in main_text and '"audio_quality_profile": "Optimised"' in main_text,
        "audio_bitrates_go_beyond_192k": all(value in main_text for value in ["256k", "320k", "512k", "768k", "1024k"]) and "AUDIO_BITRATE_OPTIONS" in backend_text and "1024k" in backend_text,
        "convertit_style_audio_outputs": all(value in env.get("supported_outputs", {}).get("audio", []) for value in ["amr", "mka", "opus", "spx", "wma"]),
        "convert_settings_resolve_auto": "def _file_converter_resolve_auto_target_for_path" in main_text and "target_format = self._file_converter_resolve_auto_target_for_path" in main_text,
        "parent_child_fillbox_indentation": 'master_row.pack(fill="x", padx=(2, 4)' in main_text and 'row.pack(fill="x", padx=(34, 4)' in main_text,
        "larger_fillboxes": 'size=24, weight="bold"' in main_text,
        "kc_toggles_are_labels_not_buttons": "keep_button = ctk.CTkLabel(" in main_text and "compress_button = ctk.CTkLabel(" in main_text,
        "kc_toggles_do_not_rebuild": "self._file_converter_sync_keep_button(path)" in main_text and "self._file_converter_sync_compress_button(path)" in main_text and "_file_converter_refresh_queue_label()" not in main_text[main_text.find("def _toggle_session_file_keep_original_from_converter"):main_text.find("def _session_file_selected_enabled")],
        "row_metadata_default_line_removed": "video/extension default" not in main_text,
        "transcript_editor_label_preserved": "Transcript Editor" in main_text,
        "backend_accepts_audio_sample_rate": "audio_sample_rate" in backend_text and "-ar" in backend_text,
        "backend_preserve_metadata_option": "preserve_metadata" in backend_text,
        "converter_backend_local_only": "network_actions_performed" in backend_text and "archive_ph_hit" in backend_text and "native_webview2_started" in backend_text,
        "reference_intake_honest_boundary": "does not vendor or paste Convertit" in note_text and "JavaScript compression repos are still external references" in note_text,
    },
}

if not all(payload["verdict"].values()):
    print(json.dumps(payload, indent=2))
    failed = [key for key, value in payload["verdict"].items() if not value]
    raise SystemExit("R42EQ probe failed: " + ", ".join(failed))

print(json.dumps(payload, indent=2))
