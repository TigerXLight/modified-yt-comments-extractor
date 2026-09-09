from pathlib import Path
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
stamp = time.strftime("%Y%m%d_%H%M%S")
out_dir = ROOT / "profile_media_live_captures" / "r42et_dynamic_optimised_video_matcher"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"ytce_r42et_dynamic_optimised_video_matcher_debug_{stamp}.zip"
files = [
    "main.py",
    "profile_media_file_converter_r42eh.py",
    "profile_media_file_converter_r42eh_test.py",
    "R42ET_DYNAMIC_OPTIMISED_VIDEO_MATCHER_REMX_COPY_NOTES_20260909.md",
    "tools/profile_media_file_converter/smoke_r42et_dynamic_optimised_video_matcher.cmd",
    "tools/profile_media_file_converter/probe_r42et_dynamic_optimised_video_matcher_no_gui.py",
    "tools/profile_media_file_converter/probe_r42et_dynamic_optimised_video_matcher_no_gui.cmd",
]
probe = subprocess.run(["py", "-3.11", "tools/profile_media_file_converter/probe_r42et_dynamic_optimised_video_matcher_no_gui.py"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
probe_txt = out_dir / f"r42et_probe_{stamp}.txt"
probe_txt.write_text((probe.stdout or "") + "\nSTDERR:\n" + (probe.stderr or ""), encoding="utf-8")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for rel in files:
        p = ROOT / rel
        if p.exists() and p.is_file():
            zf.write(p, rel)
    zf.write(probe_txt, probe_txt.name)
print(out)
