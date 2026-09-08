from pathlib import Path
import zipfile, json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ytce_r42ej_file_converter_fillbox_workflow_patch_20260908.zip"
FILES = [
    "main.py",
    "R42EJ_FILE_CONVERTER_FILLBOX_WORKFLOW_NOTES_20260908.md",
    "assets/Open folder icon icons8-opened-folder-ios-27-outlined.png",
    "tools/profile_media_file_converter/smoke_r42ej_file_converter_fillbox_workflow.cmd",
    "tools/profile_media_file_converter/probe_r42ej_file_converter_fillbox_workflow_no_gui.py",
    "tools/profile_media_file_converter/probe_r42ej_file_converter_fillbox_workflow_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42ej_file_converter_fillbox_workflow_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42ej_file_converter_fillbox_workflow_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42ej_file_converter_fillbox_workflow_zip.py",
    "tools/profile_media_file_converter/build_r42ej_file_converter_fillbox_workflow_zip.cmd",
]
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for rel in FILES:
        p = ROOT / rel
        if p.exists():
            zf.write(p, "project/" + rel)
print(json.dumps({"created": str(OUT), "files": len(FILES)}, indent=2))
