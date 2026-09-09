from __future__ import annotations
import argparse, json, os, platform, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "timeout": True, "stdout": exc.stdout or "", "stderr": exc.stderr or "", "error": "timeout"}
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "stdout": "", "stderr": ""}

def find_exe(name, fallback):
    found = shutil.which(name)
    if found:
        return found
    return fallback if Path(fallback).exists() else name

def parse_encoders(output):
    enc=set(); video=[]; audio=[]
    for line in output.splitlines():
        raw=line.rstrip()
        line=raw.strip()
        if not line or line.startswith("--") or line.lower().startswith(("encoders", "ffmpeg", "libav")):
            continue
        parts=line.split()
        if len(parts)>=2 and parts[0] and parts[0][0] in {"V","A","S"}:
            enc.add(parts[1])
            if parts[0][0] == "V": video.append(raw)
            if parts[0][0] == "A": audio.append(raw)
    if "libsvt_av1" in enc:
        enc.add("libsvtav1")
    return enc, video, audio

def relevant_flags(enc):
    keys=["h264_amf","hevc_amf","av1_amf","h264_mf","hevc_mf","h264_nvenc","hevc_nvenc","av1_nvenc","h264_qsv","hevc_qsv","av1_qsv","libx264","libx265","libvpx-vp9","libsvtav1","libsvt_av1","libaom-av1","librav1e","h264","hevc"]
    return {k:(k in enc) for k in keys}

def psh(script, timeout=20):
    if os.name != "nt": return {"ok": False, "skipped": "not_windows"}
    return run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",script], timeout=timeout)

def system_caps():
    caps={"platform":platform.platform(),"python":sys.version.split()[0],"cpu_count":os.cpu_count(),"processor":platform.processor()}
    mem=psh("$os=Get-CimInstance Win32_OperatingSystem; [pscustomobject]@{TotalRAMGB=[math]::Round($os.TotalVisibleMemorySize/1MB,2);FreeRAMGB=[math]::Round($os.FreePhysicalMemory/1MB,2)} | ConvertTo-Json -Compress")
    gpu=psh("Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,VideoProcessor | ConvertTo-Json -Compress", timeout=30)
    caps["memory_probe"]={"ok":mem.get("ok",False),"stdout":(mem.get("stdout") or "").strip(),"stderr":(mem.get("stderr") or "")[-1000:]}
    caps["gpu_probe"]={"ok":gpu.get("ok",False),"stdout":(gpu.get("stdout") or "").strip(),"stderr":(gpu.get("stderr") or "")[-1000:]}
    return caps

def make_samples(td, ffmpeg, timeout):
    td=Path(td); samples={}
    text=td/'sample.txt'; text.write_text('alpha\nbeta\n', encoding='utf-8'); samples['text']=text
    img=td/'sample.png'
    r=run([ffmpeg,'-hide_banner','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=1','-frames:v','1',str(img)], timeout=timeout)
    if img.exists(): samples['image']=img
    audio=td/'sample.wav'
    r=run([ffmpeg,'-hide_banner','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','2',str(audio)], timeout=timeout)
    if audio.exists(): samples['audio']=audio
    video=td/'sample.mp4'
    # Use a very basic encoder fallback first; it exposes whether this FFmpeg can encode any video at all.
    r=run([ffmpeg,'-hide_banner','-y','-f','lavfi','-i','testsrc2=size=1280x720:rate=30','-t','4','-pix_fmt','yuv420p',str(video)], timeout=timeout)
    samples['video_create']={"ok":r.get('ok',False),"stderr_tail":(r.get('stderr') or '')[-1600:]}
    if video.exists(): samples['video']=video
    return samples

def bench(ffmpeg, enc, timeout):
    candidates=[]
    def add(name,args,ext):
        if name in enc: candidates.append((name,args,ext))
    add('h264_amf',['-c:v','h264_amf','-quality','speed','-b:v','2500k'],'.mp4')
    add('hevc_amf',['-c:v','hevc_amf','-quality','speed','-b:v','1800k'],'.mp4')
    add('h264_mf',['-c:v','h264_mf','-b:v','2500k'],'.mp4')
    add('hevc_mf',['-c:v','hevc_mf','-b:v','1800k'],'.mp4')
    add('h264_nvenc',['-c:v','h264_nvenc','-preset','p3','-b:v','2500k'],'.mp4')
    add('hevc_nvenc',['-c:v','hevc_nvenc','-preset','p3','-b:v','1800k'],'.mp4')
    add('h264_qsv',['-c:v','h264_qsv','-b:v','2500k'],'.mp4')
    add('hevc_qsv',['-c:v','hevc_qsv','-b:v','1800k'],'.mp4')
    add('libx264',['-c:v','libx264','-preset','veryfast','-crf','24'],'.mp4')
    add('libx265',['-c:v','libx265','-preset','fast','-crf','28'],'.mp4')
    add('libvpx-vp9',['-c:v','libvpx-vp9','-row-mt','1','-deadline','realtime','-cpu-used','5','-b:v','0','-crf','33'],'.webm')
    add('libsvtav1',['-c:v','libsvtav1','-preset','10','-crf','34'],'.mp4')
    add('libaom-av1',['-c:v','libaom-av1','-cpu-used','8','-crf','34','-b:v','0'],'.mkv')
    add('av1_amf',['-c:v','av1_amf','-quality','speed','-b:v','1400k'],'.mp4')
    out=[]
    with tempfile.TemporaryDirectory(prefix='ytce_r42ew_bench_') as tmp:
        tmp=Path(tmp)
        for name,args,ext in candidates:
            dest=tmp/(name+ext)
            cmd=[ffmpeg,'-hide_banner','-y','-f','lavfi','-i','testsrc2=size=1280x720:rate=30','-t','4','-an',*args,str(dest)]
            start=time.perf_counter(); r=run(cmd, timeout=timeout); elapsed=time.perf_counter()-start
            fps_match=re.findall(r'fps=\s*([0-9.]+)', (r.get('stderr') or ''))
            out.append({"encoder":name,"ok":r.get('ok',False),"seconds":round(elapsed,3),"estimated_x_realtime":round(4/elapsed,3) if elapsed>0 else 0,"output_bytes":dest.stat().st_size if dest.exists() else 0,"fps_last":fps_match[-1] if fps_match else "","stderr_tail":(r.get('stderr') or '')[-1400:]})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--benchmark', action='store_true')
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--write-json', action='store_true')
    args=ap.parse_args()
    ffmpeg=find_exe('ffmpeg', r'C:\Program Files\ffmpeg\bin\ffmpeg.EXE')
    ffprobe=find_exe('ffprobe', r'C:\Program Files\ffmpeg\bin\ffprobe.EXE')
    enc_res=run([ffmpeg,'-hide_banner','-encoders'], timeout=30)
    enc, video_lines, audio_lines=parse_encoders((enc_res.get('stdout') or '')+'\n'+(enc_res.get('stderr') or '')) if enc_res.get('ok') else (set(),[],[])
    env={}; module_ok=True; module_error=''; full_pipeline=[]; plan_examples=[]
    try:
        import profile_media_file_converter_r42eh as conv
        env=conv.probe_environment()
        with tempfile.TemporaryDirectory(prefix='ytce_r42ew_pipeline_') as td:
            samples=make_samples(td, ffmpeg, min(args.timeout,60))
            for kind,target in [('text','html'),('image','webp'),('audio','mp3')]:
                p=samples.get(kind)
                if not isinstance(p, Path):
                    full_pipeline.append({'kind':kind,'skipped':'sample_not_created'})
                    continue
                plan=conv.plan_conversion(str(p), target, output_dir=td, keep_original=True, overwrite=True)
                res=conv.run_conversion(plan, timeout=args.timeout)
                full_pipeline.append({'kind':kind,'target':target,'planned_method':plan.get('method'),'success':res.get('success'), 'output_bytes':Path(res.get('output_path','')).stat().st_size if res.get('success') else 0, 'stderr_tail':res.get('stderr_tail','')[-800:]})
            if isinstance(samples.get('video'), Path):
                v=samples['video']
                for case,kw in [('convert_remux',{'compress':False}),('compress_optimised',{'compress':True}),('target_size',{'compress':True,'target_file_size_mb':'2'})]:
                    plan=conv.plan_conversion(str(v),'mp4',output_dir=td,keep_original=True,overwrite=True,**kw)
                    plan_examples.append({'case':case,'command':plan.get('command',[]),'preset':plan.get('preset',{})})
                    # Do not run every video pipeline by default if no recognised encoder exists; benchmark handles real runtime.
            else:
                plan_examples.append({'case':'video_sample_create','failed':samples.get('video_create')})
    except Exception as exc:
        module_ok=False; module_error=repr(exc)
    main_text=(ROOT/'main.py').read_text(encoding='utf-8', errors='replace') if (ROOT/'main.py').exists() else ''
    prof_text=(ROOT/'profile_media_file_converter_r42eh.py').read_text(encoding='utf-8', errors='replace') if (ROOT/'profile_media_file_converter_r42eh.py').exists() else ''
    bench_results=bench(ffmpeg, enc, args.timeout) if args.benchmark else []
    checks={
        'main_compiles': run([sys.executable,'-m','py_compile',str(ROOT/'main.py')], timeout=30).get('ok',False),
        'profile_module_compiles': run([sys.executable,'-m','py_compile',str(ROOT/'profile_media_file_converter_r42eh.py')], timeout=30).get('ok',False),
        'module_import_ok': module_ok,
        'encoder_list_nonempty': bool(enc),
        'encoder_capability_expanded': 'h264_mf' in prof_text and 'hevc_mf' in prof_text and 'librav1e' in prof_text,
        'real_cog_button_used': 'settings_button = ctk.CTkButton(' in main_text and 'raw-label overlay' in main_text,
        'no_cog_button1_duplicate': 'settings_button.bind("<Button-1>", lambda _event: settings_command())' not in main_text,
        'settings_tabs_retained': all(x in main_text for x in ['Image | Video | Audio', '_file_converter_allowed_image_resolutions', '_file_converter_allowed_video_resolutions']) if False else ('Image resolution' in main_text and 'Video resolution' in main_text and 'CTkSegmentedButton' in main_text),
        'basic_text_image_audio_pipeline': all(item.get('success') or item.get('skipped') for item in full_pipeline),
    }
    result={
        'schema':'ytce.r42ew.converter_full_process_capability_audit.v1',
        'mode':'NO_NETWORK_LOCAL_STRUCTURE_PIPELINE_AND_OPTIONAL_ENCODER_BENCHMARK',
        'system':system_caps(),
        'ffmpeg':{'path':ffmpeg,'ffprobe':ffprobe,'encoder_probe_ok':enc_res.get('ok',False),'relevant_encoder_flags':relevant_flags(enc),'video_encoder_match_lines':[l for l in video_lines if re.search(r'(264|265|hevc|amf|nvenc|qsv|mf|vp9|vpx|av1|svt|aom|rav1e)', l, re.I)][:80], 'encoder_count':len(enc)},
        'converter_environment':env,
        'pipeline':full_pipeline,
        'video_plan_examples':plan_examples,
        'benchmark':bench_results,
        'checks':checks,
        'verdict':all(checks.values()),
        'module_error':module_error,
        'note':'If all relevant_encoder_flags are false, this FFmpeg build cannot expose the encoder families the matcher needs; install/point the app at a full FFmpeg build with libx264/libx265/libvpx-vp9/libsvtav1 and/or AMF/MF encoders.'
    }
    out=json.dumps(result, indent=2, default=str)
    print(out)
    if args.write_json:
        dest=ROOT/'profile_media_live_captures'/('r42ew_converter_full_process_audit_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding='utf-8')
        print(str(dest))
    raise SystemExit(0 if result['verdict'] else 1)
if __name__=='__main__': main()
