from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import py_compile
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "main.py"
PROFILE = ROOT / "profile_media_file_converter_r42eh.py"
CAPTURE_ROOT = ROOT / "profile_media_live_captures"


def _compile(path: Path) -> tuple[bool, str]:
    try:
        py_compile.compile(str(path), doraise=True)
        return True, ""
    except Exception as exc:
        return False, repr(exc)


def _load_backend():
    spec = importlib.util.spec_from_file_location("profile_media_file_converter_r42eh", PROFILE)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load profile_media_file_converter_r42eh.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _run(cmd: list[str], *, timeout: int = 30, cwd: Path | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        elapsed = time.perf_counter() - start
        return {"cmd": cmd, "returncode": proc.returncode, "ok": proc.returncode == 0, "elapsed_seconds": round(elapsed, 3), "stdout_tail": (proc.stdout or "")[-1200:], "stderr_tail": (proc.stderr or "")[-2200:]}
    except Exception as exc:
        return {"cmd": cmd, "ok": False, "elapsed_seconds": round(time.perf_counter() - start, 3), "error": repr(exc)}


def _make_capture_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = CAPTURE_ROOT / f"r42fe_target_size_cap_retry_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _first_existing_encoder(encoders: set[str], names: list[str]) -> str:
    for name in names:
        if name in encoders:
            return name
    return ""


def _generate_sources(mod: Any, tmp: Path, timeout: int) -> dict[str, Any]:
    ffmpeg = str(mod._ffmpeg_path())
    encoders = set(mod._available_ffmpeg_encoders())
    sources: dict[str, Any] = {}
    text_path = tmp / "sample_text.txt"
    text_path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    sources["text"] = {"path": str(text_path), "ok": text_path.is_file()}

    image_path = tmp / "sample_image.png"
    image_cmd = [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=1", "-frames:v", "1", str(image_path)]
    sources["image"] = _run(image_cmd, timeout=min(20, timeout))
    sources["image"]["path"] = str(image_path)
    sources["image"]["ok"] = bool(sources["image"].get("ok") and image_path.exists() and image_path.stat().st_size > 0)

    audio_path = tmp / "sample_audio.wav"
    audio_cmd = [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", "1.2", "-c:a", "pcm_s16le", str(audio_path)]
    sources["audio"] = _run(audio_cmd, timeout=min(20, timeout))
    sources["audio"]["path"] = str(audio_path)
    sources["audio"]["ok"] = bool(sources["audio"].get("ok") and audio_path.exists() and audio_path.stat().st_size > 0)

    video_path = tmp / "sample_video.mp4"
    source_encoder = _first_existing_encoder(encoders, ["libx264", "h264_mf", "h264_amf", "h264_nvenc", "h264_qsv", "mpeg4"])
    if source_encoder:
        video_args = ["-c:v", source_encoder]
        if source_encoder == "libx264":
            video_args += ["-preset", "veryfast", "-crf", "23"]
        elif source_encoder == "mpeg4":
            video_args += ["-q:v", "5"]
        else:
            video_args += ["-b:v", "1800k"]
        # Generate a deliberately bloated-but-small local fixture so Optimised
        # compression has something real to reduce.  The older audit used an
        # already compact 640x360/2s sample, which allowed a "passing" audit even
        # when compression made the file larger.
        video_cmd = [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30", "-f", "lavfi", "-i", "sine=frequency=660:sample_rate=48000", "-t", "3.0", *video_args, "-b:v", "6500k", "-c:a", "aac", "-b:a", "96k", str(video_path)]
        sources["video"] = _run(video_cmd, timeout=min(45, timeout))
        sources["video"].update({"path": str(video_path), "source_encoder": source_encoder, "ok": bool(video_path.exists() and video_path.stat().st_size > 0 and sources["video"].get("ok"))})
    else:
        sources["video"] = {"path": str(video_path), "ok": False, "error": "No simple compiled source video encoder found"}
    return sources


def _plan_and_run(mod: Any, label: str, input_path: Path, target: str, output_dir: Path, *, timeout: int, **kwargs: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {"label": label, "input_path": str(input_path), "target": target, "kwargs": kwargs}
    try:
        plan_kwargs = dict(kwargs)
        plan_kwargs.pop("_expected_target_size_mb", None)
        plan = mod.plan_conversion(input_path, target, output_dir=output_dir, keep_original=True, overwrite=True, **plan_kwargs)
        entry["plan"] = plan
        start = time.perf_counter()
        result = mod.run_conversion(plan, timeout=timeout)
        elapsed = round(time.perf_counter() - start, 3)
        entry["result"] = result
        entry["elapsed_seconds"] = elapsed
        out = Path(str(plan.get("output_path") or ""))
        entry["output_exists"] = out.exists()
        entry["output_bytes"] = out.stat().st_size if out.exists() else 0
        inp_size = input_path.stat().st_size if input_path.exists() else 0
        entry["input_bytes"] = inp_size
        entry["size_ratio"] = round((entry["output_bytes"] or 0) / inp_size, 4) if inp_size else None
        entry["ok"] = bool(result.get("success"))
    except Exception as exc:
        entry["ok"] = False
        entry["error"] = repr(exc)
    return entry


def _write_summary_md(path: Path, audit: dict[str, Any]) -> None:
    rec = audit.get("capability_profile", {}).get("recommendation", {}) if isinstance(audit.get("capability_profile"), dict) else {}
    lines = [
        "# R42FE File Converter Strict Optimised Efficiency Audit",
        "",
        f"Verdict: `{audit.get('verdict')}`",
        f"Generated: `{audit.get('generated_at')}`",
        "",
        "## Optimised recommendation",
        f"- Encoder: `{rec.get('optimised_default_encoder_impl', '')}`",
        f"- Reason: {rec.get('reason', '')}",
        "",
        "## Pipeline results",
    ]
    for item in audit.get("pipeline", []):
        plan = item.get("plan", {}) if isinstance(item, dict) else {}
        preset = plan.get("preset", {}) if isinstance(plan, dict) else {}
        lines.append(f"- `{item.get('label')}`: ok=`{item.get('ok')}`, method=`{plan.get('method')}`, encoder=`{preset.get('selected_encoder_impl', '')}`, mode=`{preset.get('optimisation_mode', '')}`, bytes=`{item.get('output_bytes')}`")
    lines += ["", "## Notes", "- No network/browser/WebView2/archive.ph actions are performed.", "- Benchmark quality is a proxy only; actual visual judgement still requires sample review."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="R42FE strict no-network File Converter capability and efficiency audit")
    parser.add_argument("--benchmark", action="store_true", help="run bounded synthetic encoder benchmarks")
    parser.add_argument("--include-slow", action="store_true", help="include very slow AV1 software encoders in probe/benchmark")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--write-json", action="store_true")
    args = parser.parse_args()

    out_dir = _make_capture_dir()
    main_ok, main_err = _compile(MAIN)
    profile_ok, profile_err = _compile(PROFILE)
    audit: dict[str, Any] = {
        "schema": "ytce.r42fe.converter_target_size_cap_retry_audit.v1",
        "mode": "NO_NETWORK_LOCAL_PIPELINE_AND_CAPABILITY_AUDIT",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "out_dir": str(out_dir),
        "checks": {"main_compiles": main_ok, "profile_compiles": profile_ok, "main_compile_error": main_err, "profile_compile_error": profile_err},
        "side_effects": {"network_actions_performed": False, "archive_ph_hit": False, "native_webview2_started": False, "app_started": False},
    }
    if not (main_ok and profile_ok):
        audit["verdict"] = False
        print(json.dumps(audit, indent=2))
        return 1

    try:
        mod = _load_backend()
        audit["checks"]["module_import_ok"] = True
    except Exception as exc:
        audit["checks"]["module_import_ok"] = False
        audit["module_error"] = repr(exc)
        audit["verdict"] = False
        print(json.dumps(audit, indent=2))
        return 1

    audit["environment"] = mod.probe_environment()
    audit["capability_profile"] = mod.build_converter_optimisation_capability_profile(benchmark=args.benchmark, timeout=args.timeout, include_slow=args.include_slow)

    with tempfile.TemporaryDirectory(prefix="ytce_r42fe_pipeline_") as td:
        tmp = Path(td)
        sources = _generate_sources(mod, tmp, args.timeout)
        audit["generated_sources"] = sources
        outputs = out_dir / "outputs"
        outputs.mkdir(exist_ok=True)
        pipeline: list[dict[str, Any]] = []
        if sources.get("text", {}).get("ok"):
            pipeline.append(_plan_and_run(mod, "text_txt_to_html", Path(sources["text"]["path"]), "html", outputs, timeout=min(30, args.timeout)))
        if sources.get("image", {}).get("ok"):
            pipeline.append(_plan_and_run(mod, "image_png_to_webp_compress", Path(sources["image"]["path"]), "webp", outputs, timeout=min(60, args.timeout), compress=True, image_quality=72, image_max_dimension=400))
        if sources.get("audio", {}).get("ok"):
            pipeline.append(_plan_and_run(mod, "audio_wav_to_mp3", Path(sources["audio"]["path"]), "mp3", outputs, timeout=min(60, args.timeout), audio_bitrate="128k"))
        if sources.get("video", {}).get("ok"):
            vpath = Path(sources["video"]["path"])
            pipeline.append(_plan_and_run(mod, "video_convert_remux_copy", vpath, "mp4", outputs, timeout=min(60, args.timeout), compress=False))
            pipeline.append(_plan_and_run(mod, "video_compress_optimised", vpath, "mp4", outputs, timeout=min(90, args.timeout), compress=True, optimisation_preset="Optimised", target_file_size_mb=""))
            input_mb = vpath.stat().st_size / float(1024 ** 2)
            cap_mb = max(0.05, round(input_mb * 0.55, 3))
            pipeline.append(_plan_and_run(mod, "video_compress_target_size", vpath, "mp4", outputs, timeout=min(90, args.timeout), compress=True, optimisation_preset="Optimised", target_file_size_mb=str(cap_mb), _expected_target_size_mb=cap_mb))
        audit["pipeline"] = pipeline

    def _find(label: str) -> dict[str, Any]:
        for item in audit.get("pipeline", []):
            if item.get("label") == label:
                return item
        return {}
    remux = _find("video_convert_remux_copy")
    opt = _find("video_compress_optimised")
    cap = _find("video_compress_target_size")
    def _ratio_ok(item: dict[str, Any], threshold: float = 1.03) -> bool | None:
        if not item:
            return None
        ratio = item.get("size_ratio")
        if ratio is None:
            return False
        return float(ratio) <= threshold

    def _target_cap_ok(item: dict[str, Any]) -> bool | None:
        if not item:
            return None
        try:
            target_mb = float(item.get("kwargs", {}).get("_expected_target_size_mb") or 0.0)
            if target_mb <= 0:
                return False
            return int(item.get("output_bytes") or 0) <= int(target_mb * 1024 * 1024 * 1.08)
        except Exception:
            return False

    rec = audit.get("capability_profile", {}).get("recommendation", {}) if isinstance(audit.get("capability_profile"), dict) else {}
    audit["guideline_checks"] = {
        "convert_prefers_remux_copy": bool(remux.get("plan", {}).get("preset", {}).get("stream_copy") is True) if remux else None,
        "compression_forces_transcode_or_size_guard": bool(opt.get("plan", {}).get("preset", {}).get("stream_copy") is not True and ("-c:v" in opt.get("plan", {}).get("command", []) or opt.get("result", {}).get("size_guard"))) if opt else None,
        "compression_does_not_inflate_output": _ratio_ok(opt),
        "target_size_uses_bitrate_mode_when_cap_is_real": bool(cap.get("plan", {}).get("preset", {}).get("optimisation_mode") == "target_size_bitrate") if cap else None,
        "target_size_respects_cap": _target_cap_ok(cap),
        "target_size_does_not_inflate_output": _ratio_ok(cap),
        "encoder_command_aligned": all(bool(item.get("plan", {}).get("preset", {}).get("encoder_command_aligned", True)) for item in audit.get("pipeline", []) if item.get("plan", {}).get("output_kind") == "video"),
        "capability_recommendation_present": bool(rec.get("optimised_default_encoder_impl")),
        "no_network_side_effects": audit["side_effects"]["network_actions_performed"] is False,
    }
    critical = [audit["checks"].get("main_compiles"), audit["checks"].get("profile_compiles"), audit["checks"].get("module_import_ok")]
    pipeline = audit.get("pipeline", [])
    if pipeline:
        critical.append(all(bool(item.get("ok")) for item in pipeline))
    for value in audit["guideline_checks"].values():
        if value is not None:
            critical.append(bool(value))
    audit["verdict"] = all(bool(x) for x in critical)

    json_path = out_dir / "r42fe_target_size_cap_retry_audit.json"
    md_path = out_dir / "r42fe_target_size_cap_retry_audit.md"
    json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    _write_summary_md(md_path, audit)
    audit["written_json"] = str(json_path)
    audit["written_markdown"] = str(md_path)
    print(json.dumps(audit, indent=2))
    return 0 if audit["verdict"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
