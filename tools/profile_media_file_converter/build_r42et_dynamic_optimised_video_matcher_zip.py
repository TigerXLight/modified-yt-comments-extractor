from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ytce_r42et_dynamic_optimised_video_matcher_patch_20260909.zip"
FILES = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42ET_DYNAMIC_OPTIMISED_VIDEO_MATCHER_REMX_COPY_NOTES_20260909.md",
    "assets/Keep icon icons8-k-ios-27-filled.png",
    "assets/Compression icon icons8-c-ios-27-filled.png",
    "tools/profile_media_file_converter/smoke_r42et_dynamic_optimised_video_matcher.cmd",
    "tools/profile_media_file_converter/probe_r42et_dynamic_optimised_video_matcher_no_gui.py",
    "tools/profile_media_file_converter/probe_r42et_dynamic_optimised_video_matcher_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42et_dynamic_optimised_video_matcher_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42et_dynamic_optimised_video_matcher_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42et_dynamic_optimised_video_matcher_zip.py",
    "tools/profile_media_file_converter/build_r42et_dynamic_optimised_video_matcher_zip.cmd",
]
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in FILES:
        path = ROOT / rel
        if not path.exists():
            raise FileNotFoundError(rel)
        zf.write(path, "project/" + rel)
print(OUT)
