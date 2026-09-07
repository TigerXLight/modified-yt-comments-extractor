from pathlib import Path
import json
import zipfile
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ytce_r42eh_file_converter_auto_detect_patch_20260907.zip"
FILES = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eg.py",
    "profile_media_file_converter_r42eh_test.py",
    "R42EH_FILE_CONVERTER_AUTO_DETECT_NOTES_20260907.md",
    "assets/Keep icon icons8-kappa-100.png",
    "tools/webview2_source_role_editor_native/_r42eh_python.cmd",
    "tools/webview2_source_role_editor_native/smoke_r42eh_file_converter_auto_detect.cmd",
    "tools/webview2_source_role_editor_native/probe_r42eh_file_converter_auto_detect_no_gui.py",
    "tools/webview2_source_role_editor_native/probe_r42eh_file_converter_auto_detect_no_gui.cmd",
    "tools/webview2_source_role_editor_native/make_r42eh_file_converter_auto_detect_debug_upload_zip.py",
    "tools/webview2_source_role_editor_native/make_r42eh_file_converter_auto_detect_debug_upload_zip.cmd",
    "tools/webview2_source_role_editor_native/build_r42eh_file_converter_auto_detect_zip.py",
    "tools/webview2_source_role_editor_native/build_r42eh_file_converter_auto_detect_zip.cmd",
]
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for rel in FILES:
        p = ROOT / rel
        if p.exists():
            zf.write(p, "project/" + rel)
print(json.dumps({"created": str(OUT), "files": len(FILES)}, indent=2))
