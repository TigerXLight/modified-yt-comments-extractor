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
with tempfile.TemporaryDirectory(prefix="ytce_r42eo_converter_probe_") as tmp:
    folder = Path(tmp)
    txt = folder / "r42eo_probe.txt"
    txt.write_text("R42EO local-only converter probe\n", encoding="utf-8")
    img = folder / "r42eo_probe.png"
    img.write_bytes(b"not-real-image-but-plan-only")
    video = folder / "r42eo_probe.mp4"
    video.write_bytes(b"not-real-video-but-plan-only")
    audio = folder / "r42eo_probe.wav"
    audio.write_bytes(b"not-real-audio-but-plan-only")
    detection = detect_file_profile(txt)
    text_plan = plan_conversion(txt, "auto", keep_original=True)
    image_plan = plan_conversion(img, "webp", keep_original=True, compress=True, image_quality=60, image_max_dimension=4000, file_suffix="_compressed")
    video_plan = plan_conversion(video, "mp4", keep_original=True, compress=True, video_crf=28, video_max_dimension=1280, audio_bitrate="128k")
    audio_plan = plan_conversion(audio, "mp3", keep_original=True, compress=True, audio_bitrate="128k")

payload = {
    "schema": "ytce.r42eo.file_converter_compression_ui_media_windows.v1.probe",
    "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_COMPRESSION_UI_MEDIA_WINDOWS",
    "helper_namespace": "tools/profile_media_file_converter",
    "default_format_by_kind": {
        "text": choose_default_target_format("text"),
        "image": choose_default_target_format("image"),
        "audio": choose_default_target_format("audio"),
        "video": choose_default_target_format("video"),
    },
    "text_detection": dict(detection),
    "text_auto_plan": dict(text_plan),
    "image_compress_plan": dict(image_plan),
    "video_compress_plan": dict(video_plan),
    "audio_compress_plan": dict(audio_plan),
    "verdict": {
        "video_audio_window_has_keep_original": 'id="convertKeep"' in main_text and "Video/audio conversion target" in main_text,
        "add_selected_files_neutral_until_hover": "neutral-file-intake" in main_text and "button.neutral-file-intake:hover" in main_text,
        "convert_selected_stays_primary": '<button id="convertFiles" class="primary">Convert selected</button>' in main_text,
        "converted_outputs_enter_files_root": "do not create automatic Converted: groups" in main_text and "session_file_conversion_groups = {}" in main_text,
        "old_generated_conversion_groups_flattened": "flatten old generated conversion groups" in main_text,
        "drop_placeholder_only_when_empty": "drop_label.pack_forget()" in main_text and "if self.file_converter_queued_paths" in main_text,
        "flat_review_style_fillboxes": "R42EO_REVIEW_FILLBOX_FLAT" in main_text and "ctk.CTkLabel(\n            master_row" in main_text,
        "k_icon_uses_replacement_asset": "Keep icon icons8-k-ios-27-filled.png" in main_text,
        "c_icon_per_row_present": "Compression icon icons8-c-ios-27-filled.png" in main_text and "file_converter_item_compress_buttons" in main_text,
        "k_c_toggles_do_not_rebuild": "toggles in place; it must not rebuild" in main_text,
        "compression_settings_cog_present": "_open_file_converter_compression_settings_window" in main_text and "Compression settings" in main_text,
        "backend_accepts_compress_options": "compress: bool = False" in backend_text and "file_suffix" in backend_text,
        "image_compression_plan_uses_quality_suffix": image_plan["preset"].get("compress") is True and image_plan["output_path"].endswith("_compressed.webp") and "-quality" in image_plan["command"],
        "video_compression_plan_uses_crf_scale": video_plan["preset"].get("compress") is True and "-crf" in video_plan["command"] and "-vf" in video_plan["command"],
        "audio_compression_plan_uses_bitrate": audio_plan["preset"].get("compress") is True and "128k" in audio_plan["command"],
        "text_compression_deferred": text_plan["preset"].get("compress") is False,
        "converter_backend_local_only": all(plan["method"] in {"python_text", "ffmpeg"} for plan in (text_plan, image_plan, video_plan, audio_plan)),
        "archive_ph_not_hit": "archive.ph" not in json.dumps([text_plan, image_plan, video_plan, audio_plan]).lower(),
        "native_webview2_not_started": "webview2" not in json.dumps([text_plan["command"], image_plan["command"], video_plan["command"], audio_plan["command"]]).lower(),
        "network_actions_not_performed_by_converter": not any(str(part).lower().startswith(("http://", "https://")) for plan in (text_plan, image_plan, video_plan, audio_plan) for part in plan["command"]),
    },
}
print(json.dumps(payload, indent=2))
out_dir = ROOT / "profile_media_live_captures" / "r42eo_file_converter_compression_ui_media_windows"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "r42eo_file_converter_compression_ui_probe_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
if not all(payload["verdict"].values()):
    failed = [name for name, ok in payload["verdict"].items() if not ok]
    raise SystemExit("R42EO probe failed: " + ", ".join(failed))
