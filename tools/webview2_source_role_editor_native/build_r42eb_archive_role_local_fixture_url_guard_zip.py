from __future__ import annotations
from pathlib import Path
from datetime import datetime
import zipfile, os, json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "profile_media_live_captures" / "r42eb_archive_role_local_fixture"
OUT.mkdir(parents=True, exist_ok=True)
FILES = [
"profile_media_archive_role_local_fixture_r42eb.py",
"profile_media_archive_role_local_fixture_r42eb_test.py",
"profile_media_link_source_real_webview_overlay_v83d.py",
"R42EB_ARCHIVE_ROLE_LOCAL_FIXTURE_URL_GUARD_NOTES_20260907.md",
"tools/webview2_source_role_editor_native/Program.cs",
"tools/webview2_source_role_editor_native/_r42eb_python.cmd",
"tools/webview2_source_role_editor_native/reset_r42eb_stuck_app_native_helper.cmd",
"tools/webview2_source_role_editor_native/smoke_r42eb_archive_role_local_fixture_url_guard.cmd",
"tools/webview2_source_role_editor_native/probe_r42eb_archive_role_local_fixture_no_gui.cmd",
"tools/webview2_source_role_editor_native/probe_r42eb_archive_role_local_fixture_no_gui_recolor.cmd",
"tools/webview2_source_role_editor_native/launch_r42eb_cached_archive_role_fixture_native.cmd",
"tools/webview2_source_role_editor_native/launch_r42eb_cached_archive_role_fixture_native_recolor.cmd",
"tools/webview2_source_role_editor_native/probe_r42eb_native_log_after_local_fixture.cmd",
"tools/webview2_source_role_editor_native/build_r42eb_archive_role_local_fixture_url_guard_zip.py",
"tools/webview2_source_role_editor_native/build_r42eb_archive_role_local_fixture_url_guard_zip.cmd",
"tools/webview2_source_role_editor_native/make_r42eb_archive_role_local_fixture_debug_upload_zip.py",
"tools/webview2_source_role_editor_native/make_r42eb_archive_role_local_fixture_debug_upload_zip.cmd",
]
def main():
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    zp=OUT/f"r42eb_archive_role_local_fixture_url_guard_{stamp}.zip"
    added=set()
    with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
        for rel in FILES:
            p=ROOT/rel
            if p.exists() and rel not in added:
                z.write(p, rel); added.add(rel)
    dl=Path(os.environ.get("USERPROFILE",str(Path.home())))/"Downloads"/zp.name
    try: dl.write_bytes(zp.read_bytes()); print("[DONE] Copied ZIP to Downloads:", dl)
    except Exception as exc: print("[WARN] Could not copy to Downloads:", repr(exc))
    print("[DONE] Created ZIP:", zp)
    print("[DONE] Files included:", len(added))
if __name__=="__main__": main()
