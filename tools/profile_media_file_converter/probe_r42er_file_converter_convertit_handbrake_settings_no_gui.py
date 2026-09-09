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
note_text = (ROOT / "R42ER_FILE_CONVERTER_CONVERTIT_HANDBRAKE_SETTINGS_POLISH_NOTES_20260909.md").read_text(encoding="utf-8", errors="replace")

with tempfile.TemporaryDirectory(prefix="ytce_r42er_converter_probe_") as tmp:
    folder = Path(tmp)
    txt = folder / "r42er_probe.txt"
    txt.write_text("R42ER local-only converter probe\n", encoding="utf-8")
    img = folder / "r42er_probe.png"
    img.write_bytes(b"not-real-image-but-plan-only")
    video = folder / "r42er_probe.mp4"
    video.write_bytes(b"not-real-video-but-plan-only")
    audio = folder / "r42er_probe.wav"
    audio.write_bytes(b"not-real-audio-but-plan-only")

    detection = detect_file_profile(txt)
    text_plan = plan_conversion(txt, "auto", keep_original=True)
    image_plan = plan_conversion(img, "webp", keep_original=True, compress=False, image_quality=72, image_max_dimension=4000, image_webp_method=4)
    image_compress_plan = plan_conversion(img, "webp", keep_original=True, compress=True, image_quality=58, image_max_dimension=1920, image_webp_method=6, file_suffix="_compressed")
    video_plan = plan_conversion(video, "mp4", keep_original=True, compress=False, video_crf=31, video_max_dimension=720, video_preset="fast", video_fps="30", audio_bitrate="96k", audio_sample_rate="44100", audio_channels="mono", playback_speed="1.25")
    video_compress_plan = plan_conversion(video, "mp4", keep_original=True, compress=True, video_crf=26, video_max_dimension=1280, video_encoder="h264", video_preset="medium", video_fps="source", audio_bitrate="160k", audio_sample_rate="48000", audio_channels="stereo")
    audio_plan = plan_conversion(audio, "opus", keep_original=True, compress=False, audio_bitrate="320k", audio_sample_rate="48000", audio_channels="stereo", playback_speed="1.5", cue_split_mode="auto")
    amr_plan = plan_conversion(audio, "amr", keep_original=True, compress=True, audio_bitrate="24k", audio_sample_rate="16000", audio_channels="mono")

env = probe_environment()
commands_text = json.dumps([
    text_plan.get("command", []),
    image_plan.get("command", []),
    image_compress_plan.get("command", []),
    video_plan.get("command", []),
    video_compress_plan.get("command", []),
    audio_plan.get("command", []),
    amr_plan.get("command", []),
]).lower()

payload = {
    "schema": "ytce.r42er.file_converter_convertit_handbrake_settings_polish.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_CONVERTIT_HANDBRAKE_SETTINGS_POLISH",
    "helper_namespace": "tools/profile_media_file_converter",
    "default_format_by_kind": {
        "text": choose_default_target_format("text"),
        "image": choose_default_target_format("image"),
        "audio": choose_default_target_format("audio"),
        "video": choose_default_target_format("video"),
    },
    "text_detection": dict(detection),
    "image_convert_plan": dict(image_plan),
    "image_compress_plan": dict(image_compress_plan),
    "video_convert_plan": dict(video_plan),
    "video_compress_plan": dict(video_compress_plan),
    "audio_convert_plan": dict(audio_plan),
    "amr_compress_plan": dict(amr_plan),
    "supported_outputs": env.get("supported_outputs", {}),
    "verdict": {
        "compression_optimised_is_dropdown_not_slider_stop": '"compression_preset": "Optimised"' in main_text and '"Preset", "compression_preset"' in main_text and "video_size_reduction_percent" not in main_text,
        "compression_simple_file_size_small_medium_max": 'ctk.CTkSlider(size_row, from_=0, to=2' in main_text and "Small  •  Medium  •  Max" in main_text and "Video size reduction" not in main_text,
        "compression_advanced_pane_is_real": "WebP method" in main_text and "PNG compression" in main_text and "Video CRF number" in main_text and "mode_switch.configure(command=_show_mode)" in main_text,
        "convert_simple_has_profiles": all(value in main_text for value in ["Image conversion", "Video conversion", "Audio conversion", '"Quality", "Optimised", "Lower Size"']),
        "convert_advanced_is_handling_not_output": "Advanced only controls how converted media is handled" in main_text and "Channel control" in main_text and "Playback speed" in main_text and "CUE track splitting" in main_text,
        "sample_rates_display_khz": "44.1 kHz" in main_text and "Audio sample rate" in main_text,
        "convertit_audio_model_ported": all(value in backend_text for value in ["AUDIO_CHANNEL_OPTIONS", "AUDIO_PLAYBACK_SPEED_OPTIONS", "CUE_SPLIT_OPTIONS", "libopus", "libspeex", "amr_wb", "atempo=", "cue_split_mode"]),
        "convertit_audio_formats_include_aiff": "aiff" in env.get("supported_outputs", {}).get("audio", []) and "pcm_s16be" in backend_text,
        "handbrake_video_model_ported": all(value in main_text + backend_text for value in ["VIDEO_ENCODER_OPTIONS", "VIDEO_PRESET_OPTIONS", "VIDEO_FPS_OPTIONS", "HandBrake-style", "video_crf", "video_max_dimension"]),
        "video_settings_similar_to_audio_bitrate": all(value in main_text for value in ["Video encoder", "Video preset", "Video frame rate", "Video CRF number"]),
        "video_convert_profile_affects_command": "-crf" in video_plan.get("command", []) and "31" in video_plan.get("command", []) and "-r" in video_plan.get("command", []) and "30" in video_plan.get("command", []),
        "audio_handling_affects_command": "-ac" in commands_text and "atempo=1.5" in commands_text and "-ar" in commands_text,
        "amr_guard_is_16khz_mono": "amr_wb" in commands_text and "16000" in commands_text and "-ac" in commands_text,
        "parent_child_fillbox_indentation": 'master_row.pack(fill="x", padx=(2, 4)' in main_text and 'row.pack(fill="x", padx=(54, 4)' in main_text,
        "files_blank_area_lasso_selection": all(value in main_text for value in ["_bind_files_rectangle_selection_handlers", "_files_rectangle_select_start", "_files_rectangle_select_motion", "_files_rectangle_select_end", "Drag to select FILES rows"]),
        "kc_icons_included_and_no_rebuild_style": "Keep icon icons8-k-ios-27-filled.png" in main_text and "Compression icon icons8-c-ios-27-filled.png" in main_text and "keep_button = ctk.CTkLabel(" in main_text and "compress_button = ctk.CTkLabel(" in main_text,
        "media_direct_conversion_uses_convert_settings": "**self._file_converter_conversion_options_for_path(input_path, False)" in main_text,
        "reference_boundary_honest": "does not wholesale vendor HandBrake" in note_text and "ports the relevant settings model" in note_text,
        "converter_backend_local_only": "network_actions_performed" in backend_text and "archive_ph_hit" in backend_text and "native_webview2_started" in backend_text,
    },
}

if not all(payload["verdict"].values()):
    print(json.dumps(payload, indent=2))
    failed = [key for key, value in payload["verdict"].items() if not value]
    raise SystemExit("R42ER probe failed: " + ", ".join(failed))

print(json.dumps(payload, indent=2))
