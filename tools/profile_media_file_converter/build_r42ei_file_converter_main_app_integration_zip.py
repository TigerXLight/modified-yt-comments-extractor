from pathlib import Path
import zipfile, json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ytce_r42ei_file_converter_main_app_integration_patch_20260908.zip"
FILES = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eg.py",
    "profile_media_file_converter_r42eh_test.py",
    "R42EI_FILE_CONVERTER_MAIN_APP_INTEGRATION_NOTES_20260908.md",
    "assets/Keep icon icons8-kappa-100.png",
    "tools/profile_media_file_converter/_r42ei_python.cmd",
    "tools/profile_media_file_converter/smoke_r42ei_file_converter_main_app_integration.cmd",
    "tools/profile_media_file_converter/probe_r42ei_file_converter_main_app_integration_no_gui.py",
    "tools/profile_media_file_converter/probe_r42ei_file_converter_main_app_integration_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42ei_file_converter_main_app_integration_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42ei_file_converter_main_app_integration_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42ei_file_converter_main_app_integration_zip.py",
    "tools/profile_media_file_converter/build_r42ei_file_converter_main_app_integration_zip.cmd",
]
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for rel in FILES:
        p = ROOT / rel
        if p.exists():
            zf.write(p, "project/" + rel)
print(json.dumps({"created": str(OUT), "files": len(FILES)}, indent=2))
