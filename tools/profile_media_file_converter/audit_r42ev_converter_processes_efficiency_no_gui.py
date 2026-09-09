from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout[-6000:], "stderr": p.stderr[-6000:]}
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "stdout": "", "stderr": ""}

def find_exe(name, fallback):
    found = shutil.which(name)
    if found: return found
    return fallback if Path(fallback).exists() else name

def parse_encoders(output):
    found=set()
    for line in output.splitlines():
        parts=line.split()
        if len(parts)>=2 and not parts[0].startswith('--'):
            found.add(parts[1])
    return found

def flags(enc):
    return {
        "h264_amf": "h264_amf" in enc,
        "hevc_amf": "hevc_amf" in enc,
        "av1_amf": "av1_amf" in enc,
        "libx264": "libx264" in enc,
        "libx265": "libx265" in enc,
        "libvpx-vp9": "libvpx-vp9" in enc,
        "libsvtav1": "libsvtav1" in enc or "libsvt_av1" in enc,
    }

def bench(ffmpeg, enc, timeout):
    candidates=[]
    if "h264_amf" in enc: candidates.append(("h264_amf", ["-c:v","h264_amf","-quality","speed","-b:v","2500k"], ".mp4"))
    if "hevc_amf" in enc: candidates.append(("hevc_amf", ["-c:v","hevc_amf","-quality","speed","-b:v","1800k"], ".mp4"))
    if "libx264" in enc: candidates.append(("libx264", ["-c:v","libx264","-preset","veryfast","-crf","24"], ".mp4"))
    if "libx265" in enc: candidates.append(("libx265", ["-c:v","libx265","-preset","fast","-crf","28"], ".mp4"))
    if "libvpx-vp9" in enc: candidates.append(("libvpx-vp9", ["-c:v","libvpx-vp9","-deadline","realtime","-cpu-used","5","-b:v","0","-crf","33"], ".webm"))
    if "libsvtav1" in enc: candidates.append(("libsvtav1", ["-c:v","libsvtav1","-preset","10","-crf","34"], ".mp4"))
    if "av1_amf" in enc: candidates.append(("av1_amf", ["-c:v","av1_amf","-quality","speed","-b:v","1400k"], ".mp4"))
    out=[]
    with tempfile.TemporaryDirectory(prefix="ytce_r42ev_bench_") as td:
        td=Path(td)
        for name,args,ext in candidates:
            dest=td/(name+ext)
            cmd=[ffmpeg,"-hide_banner","-y","-f","lavfi","-i","testsrc2=size=1280x720:rate=30","-t","4","-an",*args,str(dest)]
            start=time.perf_counter(); r=run(cmd, timeout=timeout); elapsed=time.perf_counter()-start
            out.append({"encoder":name,"ok":r.get("ok",False),"seconds":round(elapsed,3),"output_bytes":dest.stat().st_size if dest.exists() else 0,"stderr_tail":(r.get("stderr") or "")[-1000:]})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--no-benchmark", action="store_true")
    ap.add_argument("--timeout", type=int, default=30)
    args=ap.parse_args()
    ffmpeg=find_exe("ffmpeg", r"C:\Program Files\ffmpeg\bin\ffmpeg.EXE")
    ffprobe=find_exe("ffprobe", r"C:\Program Files\ffmpeg\bin\ffprobe.EXE")
    enc_res=run([ffmpeg,"-hide_banner","-encoders"], timeout=20)
    enc=parse_encoders(enc_res.get("stdout", "") + "\n" + enc_res.get("stderr", "")) if enc_res.get("ok") else set()
    module_ok=True; module_error=""; env={}
    try:
        import profile_media_file_converter_r42eh as conv
        env=conv.probe_environment()
    except Exception as exc:
        module_ok=False; module_error=repr(exc)
    main_text=(ROOT/"main.py").read_text(encoding="utf-8", errors="replace")
    prof_text=(ROOT/"profile_media_file_converter_r42eh.py").read_text(encoding="utf-8", errors="replace") if (ROOT/"profile_media_file_converter_r42eh.py").exists() else ""
    checks={
        "main_compiles": run([sys.executable,"-m","py_compile",str(ROOT/"main.py")], timeout=30).get("ok", False),
        "profile_module_compiles": run([sys.executable,"-m","py_compile",str(ROOT/"profile_media_file_converter_r42eh.py")], timeout=30).get("ok", False),
        "module_import_ok": module_ok,
        "ffmpeg_encoder_list_available": bool(enc),
        "dynamic_matcher_present": "_select_optimised_video_strategy" in prof_text,
        "remux_copy_present": "stream_copy" in prof_text and "-c" in prof_text and "copy" in prof_text,
        "playback_default_fixed": '"playback_speed": "1.0x"' in main_text,
        "cog_lift_present": "def _keep_cog_visible()" in main_text and "settings_button.lift()" in main_text,
    }
    result={
        "schema":"ytce.r42ev.converter_process_efficiency_audit.v1",
        "mode":"NO_NETWORK_OPTIONAL_LOCAL_SYNTHETIC_BENCHMARK",
        "system":{"platform":platform.platform(),"python":sys.version.split()[0],"cpu_count":os.cpu_count(),"processor":platform.processor()},
        "ffmpeg":{"path":ffmpeg,"ffprobe":ffprobe,"encoder_probe_ok":enc_res.get("ok", False),"available_relevant_encoders":flags(enc)},
        "converter_environment": env,
        "checks": checks,
        "benchmark": [] if args.no_benchmark or not args.benchmark else bench(ffmpeg, enc, args.timeout),
        "verdict": all(checks.values()),
        "module_error": module_error,
    }
    print(json.dumps(result, indent=2, default=str))
    raise SystemExit(0 if result["verdict"] else 1)
if __name__ == "__main__": main()
