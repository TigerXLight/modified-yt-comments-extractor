from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_file_converter_r42eh import detect_file_profile, plan_conversion, probe_environment, run_conversion


def main() -> int:
    root = ROOT
    out_root = root / "profile_media_live_captures" / "r42eh_file_converter_auto_detect"
    out_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ytce_r42eh_converter_probe_") as td:
        td_path = Path(td)
        extless = td_path / "extensionless_note"
        extless.write_text("extensionless text\nline two\n", encoding="utf-8")
        extless_profile = detect_file_profile(extless)

        keep_src = td_path / "converter_probe.txt"
        keep_src.write_text("line one\nline two\n", encoding="utf-8")
        plan_keep = plan_conversion(keep_src, "auto", keep_original=True)
        result_keep = run_conversion(plan_keep)

        destructive_src = td_path / "converter_probe_delete.txt"
        destructive_src.write_text("delete after success\n", encoding="utf-8")
        plan_delete = plan_conversion(destructive_src, "json", keep_original=False)
        result_delete = run_conversion(plan_delete)

        dry_audio = td_path / "sample_audio.wav"; dry_audio.write_bytes(b"dry")
        dry_video = td_path / "sample_video.mp4"; dry_video.write_bytes(b"dry")
        dry_image = td_path / "sample_image.png"; dry_image.write_bytes(b"dry")
        audio_plan = plan_conversion(dry_audio, "auto", keep_original=True)
        video_plan = plan_conversion(dry_video, "auto", keep_original=True)
        image_plan = plan_conversion(dry_image, "auto", keep_original=True)

    summary = {
        "schema": "ytce.r42eh.file_converter_auto_detect.v1.probe",
        "version": "20260907_r42eh_file_converter_auto_detect",
        "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_FILE_CONVERTER_AUTO_DETECT",
        "environment": probe_environment(),
        "extensionless_text_profile": extless_profile,
        "text_auto_plan": plan_keep,
        "text_keep_result": result_keep,
        "text_delete_result": result_delete,
        "dry_auto_plans": {"audio": audio_plan, "video": video_plan, "image": image_plan},
        "verdict": {
            "text_sniff_detects_extensionless_text": extless_profile.get("detected_kind") == "text",
            "auto_text_defaults_to_html": plan_keep.get("target_format") == "html",
            "keep_original_true_keeps_source": bool(result_keep.get("success") and not result_keep.get("original_deleted")),
            "keep_original_false_deletes_after_success": bool(result_delete.get("success") and result_delete.get("original_deleted")),
            "audio_auto_plan_defined": audio_plan.get("input_kind") == "audio" and audio_plan.get("target_format") == "mp3",
            "video_auto_plan_defined": video_plan.get("input_kind") == "video" and video_plan.get("target_format") == "mp4",
            "image_auto_plan_defined": image_plan.get("input_kind") == "image" and image_plan.get("target_format") == "webp",
            "no_gui_no_network_safe": True,
            "pytest_not_required": True,
        },
    }
    summary_path = out_root / "r42eh_file_converter_auto_detect_probe_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
