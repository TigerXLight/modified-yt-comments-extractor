from __future__ import annotations
import argparse, json, os, platform, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def run(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, encoding="utf-8", errors="replace")
        return {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "cmd": list(map(str, cmd))}
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "timeout": True, "stdout": exc.stdout or "", "stderr": exc.stderr or "", "error": "timeout", "cmd": list(map(str, cmd))}
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "stdout": "", "stderr": "", "cmd": list(map(str, cmd))}

def find_exe(name, fallback):
    found = shutil.which(name)
    if found:
        return found
    return fallback if Path(fallback).exists() else name

def parse_encoders(output):
    enc=set(); video=[]; audio=[]
    for raw in output.splitlines():
        line=raw.strip()
        if not line or line.startswith("--") or line.lower().startswith(("encoders", "ffmpeg", "libav")):
            continue
        parts=line.split()
        if len(parts)>=2 and parts[0] and parts[0][0] in {"V","A","S"}:
            enc.add(parts[1])
            if parts[0][0] == "V": video.append(raw.rstrip())
            if parts[0][0] == "A": audio.append(raw.rstrip())
    if "libsvt_av1" in enc:
        enc.add("libsvtav1")
    return enc, video, audio

def relevant_flags(enc):
    keys=["h264_amf","hevc_amf","av1_amf","h264_mf","hevc_mf","av1_mf","h264_vulkan","hevc_vulkan","av1_vulkan","h264_nvenc","hevc_nvenc","av1_nvenc","h264_qsv","hevc_qsv","av1_qsv","libx264","libx265","libvpx-vp9","libsvtav1","libsvt_av1","libaom-av1","librav1e","h264","hevc"]
    return {k:(k in enc) for k in keys}

def psh(script, timeout=20):
    if os.name != "nt": return {"ok": False, "skipped": "not_windows"}
    return run(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",script], timeout=timeout)

def system_caps():
    caps={"platform":platform.platform(),"python":sys.version.split()[0],"cpu_count":os.cpu_count(),"processor":platform.processor()}
    mem=psh("$os=Get-CimInstance Win32_OperatingSystem; $total=[math]::Round(($os.TotalVisibleMemorySize*1KB)/1GB,2); $free=[math]::Round(($os.FreePhysicalMemory*1KB)/1GB,2); [pscustomobject]@{TotalRAMGB=$total;FreeRAMGB=$free} | ConvertTo-Json -Compress")
    gpu=psh("Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion,VideoProcessor | ConvertTo-Json -Compress", timeout=30)
    caps["memory_probe"]={"ok":mem.get("ok",False),"stdout":(mem.get("stdout") or "").strip(),"stderr":(mem.get("stderr") or "")[-1000:]}
    caps["gpu_probe"]={"ok":gpu.get("ok",False),"stdout":(gpu.get("stdout") or "").strip(),"stderr":(gpu.get("stderr") or "")[-1000:]}
    return caps

def command_video_encoder(cmd):
    cmd=[str(x) for x in (cmd or [])]
    if "-c:v" in cmd:
        i=cmd.index("-c:v")
        if i+1 < len(cmd): return cmd[i+1]
    if "-c" in cmd:
        i=cmd.index("-c")
        if i+1 < len(cmd): return cmd[i+1]
    return ""

def make_samples(td, ffmpeg, timeout):
    td=Path(td); samples={}
    text=td/'sample.txt'; text.write_text('alpha\nbeta\n', encoding='utf-8'); samples['text']=text
    img=td/'sample.png'
    r=run([ffmpeg,'-hide_banner','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=1','-frames:v','1',str(img)], timeout=timeout)
    samples['image_create']={"ok":r.get('ok',False),"stderr_tail":(r.get('stderr') or '')[-1200:]}
    if img.exists(): samples['image']=img
    audio=td/'sample.wav'
    r=run([ffmpeg,'-hide_banner','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','2',str(audio)], timeout=timeout)
    samples['audio_create']={"ok":r.get('ok',False),"stderr_tail":(r.get('stderr') or '')[-1200:]}
    if audio.exists(): samples['audio']=audio
    video=td/'sample.mp4'
    r=run([ffmpeg,'-hide_banner','-y','-f','lavfi','-i','testsrc2=size=1280x720:rate=30','-t','4','-pix_fmt','yuv420p',str(video)], timeout=timeout)
    samples['video_create']={"ok":r.get('ok',False),"stderr_tail":(r.get('stderr') or '')[-1600:]}
    if video.exists(): samples['video']=video
    return samples

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
    env={}; module_ok=True; module_error=''; pipeline=[]; plan_examples=[]; runnable_probe={}; runnable=set()
    try:
        import profile_media_file_converter_r42eh as conv
        env=conv.probe_environment()
        if hasattr(conv, '_probe_runnable_video_encoders'):
            runnable_probe=conv._probe_runnable_video_encoders(enc, timeout=max(3, min(args.timeout, 5)), include_slow=bool(args.benchmark))
            runnable=set(runnable_probe.get('runnable_encoders') or [])
        with tempfile.TemporaryDirectory(prefix='ytce_r42ex_pipeline_') as td:
            samples=make_samples(td, ffmpeg, min(args.timeout,60))
            for kind,target in [('text','html'),('image','webp'),('audio','mp3')]:
                p=samples.get(kind)
                if not isinstance(p, Path):
                    pipeline.append({'kind':kind,'skipped':'sample_not_created', 'create': samples.get(kind+'_create')})
                    continue
                plan=conv.plan_conversion(str(p), target, output_dir=td, keep_original=True, overwrite=True)
                start=time.perf_counter(); res=conv.run_conversion(plan, timeout=args.timeout); elapsed=time.perf_counter()-start
                pipeline.append({'kind':kind,'target':target,'planned_method':plan.get('method'),'success':res.get('success'), 'seconds':round(elapsed,3), 'output_bytes':Path(res.get('output_path','')).stat().st_size if res.get('success') else 0, 'stderr_tail':res.get('stderr_tail','')[-800:]})
            if isinstance(samples.get('video'), Path):
                v=samples['video']
                cases=[('convert_remux',{'compress':False}),('compress_optimised',{'compress':True}),('target_size',{'compress':True,'target_file_size_mb':'2'})]
                for case,kw in cases:
                    plan=conv.plan_conversion(str(v),'mp4',output_dir=td,keep_original=True,overwrite=True,**kw)
                    preset=plan.get('preset',{})
                    cmd=plan.get('command',[])
                    cmd_enc=command_video_encoder(cmd)
                    selected=str(preset.get('selected_encoder_impl') or '')
                    aligned=(not selected) or selected == cmd_enc or (selected == 'libsvt_av1' and cmd_enc == 'libsvtav1')
                    run_result={}
                    should_run = case in {'convert_remux','compress_optimised'} and (case == 'convert_remux' or cmd_enc in runnable or not runnable)
                    if should_run:
                        start=time.perf_counter(); res=conv.run_conversion(plan, timeout=args.timeout); elapsed=time.perf_counter()-start
                        run_result={'ran':True,'success':res.get('success'), 'seconds':round(elapsed,3), 'output_bytes':Path(res.get('output_path','')).stat().st_size if res.get('success') else 0, 'stderr_tail':res.get('stderr_tail','')[-1000:]}
                    else:
                        run_result={'ran':False,'reason':'selected command encoder was not in runnable probe'}
                    plan_examples.append({'case':case,'command_encoder':cmd_enc,'selected_encoder_impl':selected,'encoder_command_aligned':aligned,'runnable_selected':bool((not selected) or selected in runnable or cmd_enc in runnable), 'command':cmd,'preset':preset,'run':run_result})
            else:
                plan_examples.append({'case':'video_sample_create','failed':samples.get('video_create')})
    except Exception as exc:
        module_ok=False; module_error=repr(exc)
    main_text=(ROOT/'main.py').read_text(encoding='utf-8', errors='replace') if (ROOT/'main.py').exists() else ''
    prof_text=(ROOT/'profile_media_file_converter_r42eh.py').read_text(encoding='utf-8', errors='replace') if (ROOT/'profile_media_file_converter_r42eh.py').exists() else ''
    video_plans_ok=bool(plan_examples) and all(p.get('encoder_command_aligned', True) for p in plan_examples if p.get('case') != 'convert_remux')
    runnable_nonempty=bool(runnable)
    checks={
        'main_compiles': run([sys.executable,'-m','py_compile',str(ROOT/'main.py')], timeout=30).get('ok',False),
        'profile_module_compiles': run([sys.executable,'-m','py_compile',str(ROOT/'profile_media_file_converter_r42eh.py')], timeout=30).get('ok',False),
        'module_import_ok': module_ok,
        'encoder_list_nonempty': bool(enc),
        'runnable_encoder_probe_present': '_probe_runnable_video_encoders' in prof_text,
        'runnable_encoder_probe_nonempty': runnable_nonempty,
        'compiled_not_used_as_hw_proof': 'compiled encoder list is not treated as GPU usability proof' in prof_text,
        'encoder_command_alignment_checked': 'encoder_command_aligned' in prof_text,
        'video_plan_encoder_command_aligned': video_plans_ok,
        'real_cog_button_used': 'settings_button = ctk.CTkButton(' in main_text,
        'cog_first_paint_darker_visible': 'R42EX: use the darker cog colour' in main_text,
        'basic_text_image_audio_pipeline': all(item.get('success') or item.get('skipped') for item in pipeline),
        'video_process_exercised': any(p.get('run',{}).get('ran') and p.get('run',{}).get('success') for p in plan_examples),
    }
    result={
        'schema':'ytce.r42ex.converter_real_capability_process_audit.v1',
        'mode':'NO_NETWORK_LOCAL_STRUCTURE_PIPELINE_RUNNABLE_ENCODER_PROBE',
        'system':system_caps(),
        'ffmpeg':{'path':ffmpeg,'ffprobe':ffprobe,'encoder_probe_ok':enc_res.get('ok',False),'relevant_encoder_flags':relevant_flags(enc),'video_encoder_match_lines':[l for l in video_lines if re.search(r'(264|265|hevc|amf|nvenc|qsv|mf|vulkan|vp9|vpx|av1|svt|aom|rav1e)', l, re.I)][:100], 'encoder_count':len(enc)},
        'runnable_encoder_probe':runnable_probe,
        'converter_environment':env,
        'pipeline':pipeline,
        'video_plan_examples':plan_examples,
        'checks':checks,
        'verdict':all(checks.values()),
        'module_error':module_error,
        'note':'R42EX treats an encoder as hardware-usable only after a tiny synthetic encode succeeds. Compiled FFmpeg support is discovery, not proof of GPU capability.'
    }
    out=json.dumps(result, indent=2, default=str)
    print(out)
    if args.write_json:
        dest=ROOT/'profile_media_live_captures'/('r42ex_converter_real_capability_process_audit_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding='utf-8')
        print(str(dest))
    raise SystemExit(0 if result['verdict'] else 1)
if __name__=='__main__': main()
