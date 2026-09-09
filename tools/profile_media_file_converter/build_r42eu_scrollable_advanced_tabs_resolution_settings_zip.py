from pathlib import Path
import zipfile
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ytce_r42eu_scrollable_advanced_tabs_resolution_settings_patch_20260909.zip"
files = [
    "main.py",
    "R42EU_SCROLLABLE_ADVANCED_TABS_RESOLUTION_SETTINGS_NOTES_20260909.md",
    "tools/profile_media_file_converter/smoke_r42eu_scrollable_advanced_tabs_resolution_settings.cmd",
    "tools/profile_media_file_converter/probe_r42eu_scrollable_advanced_tabs_resolution_settings_no_gui.py",
    "tools/profile_media_file_converter/probe_r42eu_scrollable_advanced_tabs_resolution_settings_no_gui.cmd",
    "tools/profile_media_file_converter/make_r42eu_scrollable_advanced_tabs_resolution_settings_debug_upload_zip.py",
    "tools/profile_media_file_converter/make_r42eu_scrollable_advanced_tabs_resolution_settings_debug_upload_zip.cmd",
    "tools/profile_media_file_converter/build_r42eu_scrollable_advanced_tabs_resolution_settings_zip.py",
    "tools/profile_media_file_converter/build_r42eu_scrollable_advanced_tabs_resolution_settings_zip.cmd",
]
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        p = ROOT / rel
        if p.exists():
            z.write(p, "project/" + rel)
print(OUT)
