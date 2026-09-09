from pathlib import Path
import zipfile, datetime, subprocess
ROOT = Path(__file__).resolve().parents[2]
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42eu_scrollable_advanced_tabs_resolution_settings"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"ytce_r42eu_scrollable_advanced_tabs_resolution_settings_debug_{stamp}.zip"
items = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "R42EU_SCROLLABLE_ADVANCED_TABS_RESOLUTION_SETTINGS_NOTES_20260909.md",
    "tools/profile_media_file_converter/probe_r42eu_scrollable_advanced_tabs_resolution_settings_no_gui.py",
    "tools/profile_media_file_converter/probe_r42eu_scrollable_advanced_tabs_resolution_settings_no_gui.cmd",
    "tools/profile_media_file_converter/smoke_r42eu_scrollable_advanced_tabs_resolution_settings.cmd",
]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in items:
        p = ROOT / rel
        if p.exists():
            z.write(p, rel)
    for name, cmd in {
        "git_status_short.txt": ["git", "status", "--short"],
        "git_log_8.txt": ["git", "--no-pager", "log", "-8", "--oneline", "--decorate"],
        "git_diff_stat.txt": ["git", "--no-pager", "diff", "--stat", "--", "main.py", "R42EU_SCROLLABLE_ADVANCED_TABS_RESOLUTION_SETTINGS_NOTES_20260909.md", "tools/profile_media_file_converter"],
    }.items():
        try:
            data = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=20)
            z.writestr(name, (data.stdout or "") + (data.stderr or ""))
        except Exception as exc:
            z.writestr(name, repr(exc))
print(out)
