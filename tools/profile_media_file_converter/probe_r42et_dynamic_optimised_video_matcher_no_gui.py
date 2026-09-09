from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import profile_media_file_converter_r42eh as backend

main_text = (ROOT / "main.py").read_text(encoding="utf-8")
backend_text = (ROOT / "profile_media_file_converter_r42eh.py").read_text(encoding="utf-8")

checks = {
    "simple_convert_only_optimised_speed": '_menu_row(simple_frame, "Preset", "convert_preset", ["Optimised", "Speed"]' in main_text,
    "simple_compression_only_optimised_speed": '_menu_row(simple_frame, "Preset", "compression_preset", ["Optimised", "Speed"]' in main_text,
    "old_quality_lower_size_removed_from_converter_ui": all(token not in main_text for token in ["Lower Size", "Quality keeps", "Image preset", "Video preset", "file_size_profile", "file_size_var"]),
    "target_size_mb_present": "target_file_size_mb" in main_text and "target_file_size_mb" in backend_text,
    "advanced_image_settings_present": all(token in main_text for token in ["Image quality", "Image max side", "WebP method", "PNG compression", "JPG subsampling"]),
    "advanced_video_encoder_auto_present": 'return ["auto", "h264", "h265", "vp9", "av1"]' in main_text,
    "manual_crf_is_advanced_override": "Manual CRF/RF" in main_text and "0 lets Optimised choose" in main_text,
    "compression_c_kept": "Compression button toggles C" in main_text,
    "backend_has_metadata_matcher": "_ffprobe_media_metadata" in backend_text and "bits_per_pixel_frame" in backend_text,
    "backend_has_capability_probe": "_system_capability_probe" in backend_text and "hardware_encoders" in backend_text,
    "backend_has_remux_copy_mode": "optimisation_mode\": \"remux_copy" in backend_text or "remux_copy" in backend_text,
}

tmp = Path(__file__).parent / "r42et_probe_input.mp4"
tmp.write_bytes(b"fake mp4 data for extension-only plan tests")

normal_plan = backend.plan_conversion(tmp, "mp4", output_dir=Path(__file__).parent, keep_original=True, compress=False)
checks["normal_video_convert_prefers_remux_copy"] = normal_plan["preset"].get("optimisation_mode") == "remux_copy" and "-c" in normal_plan["command"] and "copy" in normal_plan["command"]

# Deterministic matcher probes: fake metadata/encoders without running ffmpeg.
orig_meta = backend._ffprobe_media_metadata
orig_encoders = backend._available_ffmpeg_encoders
try:
    backend._available_ffmpeg_encoders = lambda: {"libx264", "libx265", "libvpx-vp9", "libsvtav1", "h264_amf", "hevc_amf"}
    backend._ffprobe_media_metadata = lambda path: {
        "schema": backend.R42EH_SCHEMA + ".video_metadata",
        "ffprobe_available": True,
        "duration_seconds": 300.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "container": "mov,mp4,m4a,3gp,3g2,mj2",
        "video_bitrate_kbps": 14000,
        "audio_bitrate_kbps": 160,
        "format_bitrate_kbps": 14160,
        "bits_per_pixel_frame": 0.225,
    }
    high_plan = backend.plan_conversion(tmp, "mp4", output_dir=Path(__file__).parent, keep_original=True, compress=True, optimisation_preset="Optimised")
    checks["high_bitrate_optimised_prefers_hevc"] = high_plan["preset"].get("selected_encoder_family") == "h265"
    target_plan = backend.plan_conversion(tmp, "mp4", output_dir=Path(__file__).parent, keep_original=True, compress=True, optimisation_preset="Optimised", target_file_size_mb="20")
    checks["target_size_activates_bitrate_mode"] = target_plan["preset"].get("optimisation_mode") == "target_size_bitrate" and int(target_plan["preset"].get("target_video_bitrate_kbps") or 0) > 0
    backend._ffprobe_media_metadata = lambda path: {
        "schema": backend.R42EH_SCHEMA + ".video_metadata",
        "ffprobe_available": True,
        "duration_seconds": 45.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "video_codec": "h264",
        "audio_codec": "aac",
        "container": "mov,mp4,m4a,3gp,3g2,mj2",
        "video_bitrate_kbps": 12000,
        "audio_bitrate_kbps": 160,
        "format_bitrate_kbps": 12160,
        "bits_per_pixel_frame": 0.193,
    }
    short_plan = backend.plan_conversion(tmp, "mp4", output_dir=Path(__file__).parent, keep_original=True, compress=True, optimisation_preset="Optimised")
    checks["short_video_can_auto_pick_av1"] = short_plan["preset"].get("selected_encoder_family") == "av1"
    speed_plan = backend.plan_conversion(tmp, "mp4", output_dir=Path(__file__).parent, keep_original=True, compress=True, optimisation_preset="Speed")
    checks["speed_preset_uses_speed_policy"] = speed_plan["preset"].get("optimisation_preset") == "Speed" and speed_plan["preset"].get("selected_encoder_family") == "h264"
finally:
    backend._ffprobe_media_metadata = orig_meta
    backend._available_ffmpeg_encoders = orig_encoders

env = backend.probe_environment()
checks["env_reports_auto_encoder"] = "auto" in env.get("video_encoder_options", [])

print(json.dumps({
    "schema": "ytce.r42et.dynamic_optimised_video_matcher.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_DYNAMIC_MATCHER",
    "checks": checks,
    "normal_video_convert_plan": normal_plan,
    "verdict": all(checks.values()),
}, indent=2))

if not all(checks.values()):
    raise SystemExit(1)
