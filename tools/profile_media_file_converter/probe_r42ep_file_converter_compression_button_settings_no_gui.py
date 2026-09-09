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
backend_text = (ROOT / "profile_media_file_converter_r42eh.py").read_text(encoding="utf-8", errors="replace")
note_text = (ROOT / "R42EP_FILE_CONVERTER_COMPRESSION_BUTTON_AND_SETTINGS_POLISH_NOTES_20260909.md").read_text(encoding="utf-8", errors="replace")

with tempfile.TemporaryDirectory(prefix="ytce_r42ep_converter_probe_") as tmp:
    folder = Path(tmp)
    txt = folder / "r42ep_probe.txt"
    txt.write_text("R42EP local-only converter probe\n", encoding="utf-8")
    img = folder / "r42ep_probe.png"
    img.write_bytes(b"not-real-image-but-plan-only")
    video = folder / "r42ep_probe.mp4"
    video.write_bytes(b"not-real-video-but-plan-only")
    audio = folder / "r42ep_probe.wav"
    audio.write_bytes(b"not-real-audio-but-plan-only")
    detection = detect_file_profile(txt)
    text_plan = plan_conversion(txt, "auto", keep_original=True)
    image_plan = plan_conversion(img, "webp", keep_original=True, compress=True, image_quality=60, image_max_dimension=4000, file_suffix="_compressed")
    video_plan = plan_conversion(video, "mp4", keep_original=True, compress=True, video_crf=28, video_max_dimension=1280, audio_bitrate="128k")
    audio_plan = plan_conversion(audio, "mp3", keep_original=True, compress=True, audio_bitrate="128k")

plans = (text_plan, image_plan, video_plan, audio_plan)
commands_text = json.dumps([plan.get("command", []) for plan in plans]).lower()

payload = {
    "schema": "ytce.r42ep.file_converter_compression_button_settings_polish.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_COMPRESSION_BUTTON_SETTINGS_POLISH",
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
    "audio_compress_plan": dict(audio_plan),
    "verdict": {
        "uses_shared_asr_cog_control_for_compression": "text=\"Compression\"" in main_text and "_create_asr_action_control(" in main_text and "file_converter_compression_settings_button" in main_text,
        "compression_main_button_toggles_selected_rows": "def _file_converter_toggle_compression_for_selected" in main_text and "selected_paths = self._file_converter_selected_held_paths()" in main_text,
        "simple_settings_default_present": '"settings_mode": "Simple"' in main_text and "CTkSegmentedButton" in main_text and 'values=["Simple", "Advanced"]' in main_text,
        "simple_settings_use_sliders": "def _simple_slider_row" in main_text and "CTkSlider" in main_text and "number_of_steps" in main_text,
        "simple_image_video_audio_profiles": all(x in main_text for x in ['["Low", "Medium", "High"]', '["Light", "Medium", "Strong"]', '["Small", "Medium", "High"]']),
        "advanced_uses_raw_max_pixels_wording": "Image max pixels" in main_text and "Video max pixels" in main_text and "Video CRF number" in main_text,
        "keep_original_label_polished": "Keep all original files" in main_text and "Keep all originals for this run" not in main_text,
        "transcript_editor_label_polished": "Transcript Editor" in main_text and "show_transcript_panel_button" in main_text,
        "drag_ghost_has_no_checkbox_glyph": "drag ghost shows only" in main_text and 'return f"{len(paths)} FILES"' in main_text and 'return f"⬜' not in main_text and 'return "⬜' not in main_text,
        "drop_placeholder_hidden_when_held": "label.pack_forget()" in main_text and "has_held and not active and not message" in main_text,
        "held_list_uses_larger_review_fillboxes": "size=20" in main_text and "file_converter_selected_count_label" in main_text,
        "held_master_count_only": "text=str(len(selected_set))" in main_text and "All held files (" not in main_text,
        "row_metadata_default_line_removed": "default -> ." not in main_text and "video/extension" not in main_text,
        "row_dropdown_compacted": "width=68" in main_text,
        "converted_groups_and_folders_flattened": "Converted:" in main_text and "generated_folders" in main_text and "session_file_folders = {" in main_text,
        "media_window_keep_original_file_label": "Keep original file" in main_text,
        "media_add_files_neutral_until_hover": "neutral-file-intake" in main_text and "button.neutral-file-intake:hover" in main_text,
        "reference_intake_honest_boundary": "does not vendor or embed" in note_text and "compressorjs" in note_text and "UPNG.js" in note_text,
        "backend_accepts_compress_options": "compress: bool = False" in backend_text and "file_suffix" in backend_text,
        "image_compression_plan_still_works": image_plan["preset"].get("compress") is True and image_plan["output_path"].endswith("_compressed.webp") and "-quality" in image_plan["command"],
        "video_compression_plan_still_works": video_plan["preset"].get("compress") is True and "-crf" in video_plan["command"] and "-vf" in video_plan["command"],
        "audio_compression_plan_still_works": audio_plan["preset"].get("compress") is True and "128k" in audio_plan["command"],
        "text_compression_deferred": text_plan["preset"].get("compress") is False,
        "converter_backend_local_only": all(plan["method"] in {"python_text", "ffmpeg"} for plan in plans),
        "archive_ph_not_hit": "archive.ph" not in json.dumps(plans).lower(),
        "native_webview2_not_started": "webview2" not in commands_text,
        "network_actions_not_performed_by_converter": not any(str(part).lower().startswith(("http://", "https://")) for plan in plans for part in plan["command"]),
    },
}
print(json.dumps(payload, indent=2))
out_dir = ROOT / "profile_media_live_captures" / "r42ep_file_converter_compression_button_settings_polish"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "r42ep_file_converter_compression_button_settings_probe_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
if not all(payload["verdict"].values()):
    failed = [name for name, ok in payload["verdict"].items() if not ok]
    raise SystemExit("R42EP probe failed: " + ", ".join(failed))
