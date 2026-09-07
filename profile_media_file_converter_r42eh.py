"""R42EH multipurpose local file converter backend.

Reference-backed desktop implementation for the YTCE File Converter.  The
architecture follows the ConvertIt-style split between detection, planning, and
execution, but uses local FFmpeg/FFprobe plus the Python standard library.

Policy boundary: local files only.  No network, browser, WebView2, archive.ph,
account, channel, or device-adapter actions are performed here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import csv
import html
import json
import mimetypes
import os
import shutil
import subprocess

R42EH_SCHEMA = "ytce.r42eh.file_converter.v1"
R42EG_SCHEMA = R42EH_SCHEMA  # compatibility for any old caller that reads this constant

AUDIO_INPUT_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma", ".aif", ".aiff", ".amr", ".mka", ".spx"}
VIDEO_INPUT_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".wmv", ".flv", ".m4v", ".mpeg", ".mpg", ".ts"}
IMAGE_INPUT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".ico"}
TEXT_INPUT_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".json", ".csv", ".xml", ".srt", ".vtt", ".log"}

AUDIO_OUTPUT_FORMATS = {"mp3", "m4a", "aac", "wav", "flac", "opus", "ogg"}
VIDEO_OUTPUT_FORMATS = {"mp4", "mkv", "webm", "mov"}
IMAGE_OUTPUT_FORMATS = {"webp", "jpg", "jpeg", "png", "bmp", "tiff"}
TEXT_OUTPUT_FORMATS = {"txt", "md", "html", "json", "csv"}
ALL_OUTPUT_FORMATS = AUDIO_OUTPUT_FORMATS | VIDEO_OUTPUT_FORMATS | IMAGE_OUTPUT_FORMATS | TEXT_OUTPUT_FORMATS | {"auto"}

DEFAULT_FORMAT_BY_KIND = {
    "text": "html",
    "image": "webp",
    "audio": "mp3",
    "video": "mp4",
}

@dataclass(frozen=True)
class DetectionResult:
    schema: str
    input_path: str
    detected_kind: str
    method: str
    extension: str
    mime_type: str
    ffprobe_kind: str
    text_encoding: str
    text_score: float
    binary_ratio: float
    warning: str = ""

@dataclass(frozen=True)
class ConversionPlan:
    schema: str
    input_path: str
    output_path: str
    input_kind: str
    output_kind: str
    target_format: str
    requested_format: str
    keep_original: bool
    command: list[str]
    method: str
    destructive_after_success: bool
    detection: dict[str, Any]
    preset: dict[str, Any]


def normalize_format(fmt: str) -> str:
    value = str(fmt or "").strip().lower().lstrip(".")
    if value == "jpeg":
        return "jpg"
    if value not in ALL_OUTPUT_FORMATS:
        raise ValueError(f"Unsupported converter output format: {fmt!r}")
    return value


def _extension_kind(ext: str) -> str:
    ext = str(ext or "").lower()
    if ext in TEXT_INPUT_EXTENSIONS:
        return "text"
    if ext in IMAGE_INPUT_EXTENSIONS:
        return "image"
    if ext in AUDIO_INPUT_EXTENSIONS:
        return "audio"
    if ext in VIDEO_INPUT_EXTENSIONS:
        return "video"
    return "unknown"


def _mimetype_kind(path: Path) -> tuple[str, str]:
    mime_type, _encoding = mimetypes.guess_type(str(path))
    mime_type = mime_type or ""
    if mime_type.startswith("text/") or mime_type in {"application/json", "application/xml", "application/x-subrip"}:
        return "text", mime_type
    if mime_type.startswith("image/"):
        return "image", mime_type
    if mime_type.startswith("audio/"):
        return "audio", mime_type
    if mime_type.startswith("video/"):
        return "video", mime_type
    return "unknown", mime_type


def _run_ffprobe_kind(path: Path, *, timeout: int = 8) -> str:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.is_file():
        return ""
    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if proc.returncode != 0 or not proc.stdout.strip():
        return ""
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return ""
    streams = payload.get("streams") if isinstance(payload, dict) else None
    if not isinstance(streams, list):
        return ""
    has_video = any(isinstance(s, dict) and s.get("codec_type") == "video" for s in streams)
    has_audio = any(isinstance(s, dict) and s.get("codec_type") == "audio" for s in streams)
    # Prefer video when both streams exist; this is a container-level converter.
    if has_video:
        return "video"
    if has_audio:
        return "audio"
    return ""


def _text_sniff(path: Path, *, max_bytes: int = 16384) -> tuple[bool, str, float, float]:
    try:
        data = path.read_bytes()[:max_bytes]
    except Exception:
        return False, "", 0.0, 1.0
    if not data:
        return True, "empty", 1.0, 0.0
    nul_ratio = data.count(b"\x00") / max(1, len(data))
    binary_controls = sum(1 for b in data if b < 9 or (13 < b < 32))
    binary_ratio = max(nul_ratio, binary_controls / max(1, len(data)))
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = data.decode(enc)
        except Exception:
            continue
        printable = sum(1 for ch in text if ch in "\r\n\t" or ch.isprintable())
        score = printable / max(1, len(text))
        if score >= 0.86 and binary_ratio < 0.30:
            return True, enc, round(score, 4), round(binary_ratio, 4)
    try:
        text = data.decode("utf-8")
        printable = sum(1 for ch in text if ch in "\r\n\t" or ch.isprintable())
        score = printable / max(1, len(text))
        if score >= 0.86 and binary_ratio < 0.30:
            return True, "utf-8", round(score, 4), round(binary_ratio, 4)
    except Exception:
        pass
    return False, "", 0.0, round(binary_ratio, 4)


def detect_file_profile(path: str | os.PathLike[str]) -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    ext = p.suffix.lower()
    ext_kind = _extension_kind(ext)
    mime_kind, mime_type = _mimetype_kind(p)
    ffprobe_kind = ""
    text_ok = False
    text_encoding = ""
    text_score = 0.0
    binary_ratio = 1.0

    if ext_kind != "unknown":
        kind = ext_kind
        method = "extension"
    elif mime_kind != "unknown":
        kind = mime_kind
        method = "mimetype"
    else:
        ffprobe_kind = _run_ffprobe_kind(p)
        if ffprobe_kind:
            kind = ffprobe_kind
            method = "ffprobe"
        else:
            text_ok, text_encoding, text_score, binary_ratio = _text_sniff(p)
            if text_ok:
                kind = "text"
                method = "text_sniff"
            else:
                kind = "unknown"
                method = "unknown"

    # Run ffprobe as a media confirmation/fallback when extension says media but
    # the file has no trustworthy mimetype.  Do not override known text/image by
    # probing accidentally invalid files.
    if not ffprobe_kind and kind in {"audio", "video"}:
        ffprobe_kind = _run_ffprobe_kind(p)
    if method != "text_sniff" and kind == "unknown":
        text_ok, text_encoding, text_score, binary_ratio = _text_sniff(p)

    warning = "" if kind != "unknown" else "File type could not be auto-detected. Choose a supported text, image, audio, or video file."
    return asdict(DetectionResult(
        schema=R42EH_SCHEMA + ".detection",
        input_path=str(p),
        detected_kind=kind,
        method=method,
        extension=ext,
        mime_type=mime_type,
        ffprobe_kind=ffprobe_kind,
        text_encoding=text_encoding,
        text_score=float(text_score),
        binary_ratio=float(binary_ratio),
        warning=warning,
    ))


def detect_file_kind(path: str | os.PathLike[str]) -> str:
    return str(detect_file_profile(path).get("detected_kind") or "unknown")


def output_kind_for_format(fmt: str) -> str:
    fmt = normalize_format(fmt)
    if fmt == "auto":
        return "auto"
    if fmt in AUDIO_OUTPUT_FORMATS:
        return "audio"
    if fmt in VIDEO_OUTPUT_FORMATS:
        return "video"
    if fmt in IMAGE_OUTPUT_FORMATS:
        return "image"
    if fmt in TEXT_OUTPUT_FORMATS:
        return "text"
    return "unknown"


def choose_default_target_format(input_kind: str) -> str:
    return DEFAULT_FORMAT_BY_KIND.get(str(input_kind or "").lower(), "")


def _make_output_path(input_path: Path, target_format: str, output_dir: str | os.PathLike[str] | None, overwrite: bool) -> Path:
    folder = Path(output_dir).expanduser() if output_dir else input_path.parent
    folder.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem or "converted"
    suffix = ".jpg" if target_format == "jpeg" else f".{target_format}"
    candidate = folder / f"{stem}{suffix}"
    if candidate.resolve() == input_path.resolve():
        candidate = folder / f"{stem}_converted{suffix}"
    if overwrite or not candidate.exists():
        return candidate
    for index in range(2, 1000):
        candidate = folder / f"{stem}_converted_{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not allocate a unique converter output path")


def _available_ffmpeg_encoders() -> set[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return set()
    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
    except Exception:
        return set()
    if proc.returncode != 0:
        return set()
    encoders: set[str] = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] and parts[0][0] in {"V", "A", "S"}:
            encoders.add(parts[1])
    return encoders


def _audio_codec(fmt: str) -> tuple[list[str], dict[str, Any]]:
    mapping = {
        "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
        "m4a": ["-c:a", "aac", "-b:a", "192k"],
        "aac": ["-c:a", "aac", "-b:a", "192k"],
        "wav": ["-c:a", "pcm_s16le"],
        "flac": ["-c:a", "flac"],
        "opus": ["-c:a", "libopus", "-b:a", "128k"],
        "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
    }
    args = list(mapping[fmt])
    return args, {"family": "audio", "codec_args": args}


def _video_codecs(fmt: str) -> tuple[list[str], dict[str, Any]]:
    encoders = _available_ffmpeg_encoders()
    if fmt == "webm":
        if "libvpx-vp9" in encoders:
            args = ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-c:a", "libopus"]
        elif "libvpx" in encoders:
            args = ["-c:v", "libvpx", "-b:v", "1M", "-c:a", "libopus"]
        elif "libaom-av1" in encoders:
            args = ["-c:v", "libaom-av1", "-crf", "34", "-b:v", "0", "-c:a", "libopus"]
        else:
            args = ["-c:v", "libvpx-vp9", "-crf", "32", "-b:v", "0", "-c:a", "libopus"]
    elif fmt in {"mp4", "mov"}:
        args = ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    else:  # mkv
        args = ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "192k"]
    return args, {"family": "video", "codec_args": args, "ffmpeg_encoder_count": len(encoders)}


def _image_codec(fmt: str, image_quality: int) -> tuple[list[str], dict[str, Any]]:
    q = max(1, min(100, int(image_quality)))
    if fmt == "jpg":
        qscale = max(2, min(31, int(round((100 - q) / 3.25)) or 2))
        args = ["-frames:v", "1", "-q:v", str(qscale)]
    elif fmt == "webp":
        args = ["-lossless", "0", "-quality", str(q)]
    elif fmt in {"png", "bmp", "tiff"}:
        args = ["-frames:v", "1"]
    else:
        args = []
    return args, {"family": "image", "quality": q, "codec_args": args}


def _validate_route(input_kind: str, output_kind: str, target_format: str) -> None:
    if input_kind == "unknown":
        raise ValueError("Cannot convert because the input file type is UNKNOWN")
    if input_kind == output_kind:
        return
    # Allow extracting audio from video, a normal FFmpeg route.
    if input_kind == "video" and output_kind == "audio":
        return
    raise ValueError(f"Unsupported converter route: {input_kind} -> {target_format} ({output_kind})")


def plan_conversion(input_path: str | os.PathLike[str], target_format: str = "auto", *, output_dir: str | os.PathLike[str] | None = None, keep_original: bool = False, overwrite: bool = False, image_quality: int = 92) -> dict[str, Any]:
    input_file = Path(input_path).expanduser().resolve()
    if not input_file.is_file():
        raise FileNotFoundError(str(input_file))
    detection = detect_file_profile(input_file)
    input_kind = str(detection.get("detected_kind") or "unknown")
    requested_format = normalize_format(target_format or "auto")
    fmt = choose_default_target_format(input_kind) if requested_format == "auto" else requested_format
    if not fmt:
        raise ValueError(f"No automatic converter preset for input kind: {input_kind}")
    fmt = normalize_format(fmt)
    output_kind = output_kind_for_format(fmt)
    _validate_route(input_kind, output_kind, fmt)

    output_file = _make_output_path(input_file, fmt, output_dir, overwrite)
    preset: dict[str, Any] = {}
    if output_kind == "text":
        method = "python_text"
        command = ["python_text_convert", str(input_file), str(output_file)]
        preset = {"family": "text", "preserve_original_text": True}
    else:
        method = "ffmpeg"
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        command = [ffmpeg, "-hide_banner", "-y", "-i", str(input_file), "-map_metadata", "0"]
        if output_kind == "audio":
            command += ["-vn"]
            args, preset = _audio_codec(fmt)
            command += args
        elif output_kind == "video":
            args, preset = _video_codecs(fmt)
            command += args
        elif output_kind == "image":
            args, preset = _image_codec(fmt, image_quality)
            command += args
        else:
            raise ValueError(f"Unsupported converter route: {input_kind} -> {fmt}")
        command += [str(output_file)]

    return asdict(ConversionPlan(
        schema=R42EH_SCHEMA + ".plan",
        input_path=str(input_file),
        output_path=str(output_file),
        input_kind=input_kind,
        output_kind=output_kind,
        target_format=fmt,
        requested_format=requested_format,
        keep_original=bool(keep_original),
        command=command,
        method=method,
        destructive_after_success=not bool(keep_original),
        detection=detection,
        preset=preset,
    ))


def _write_text_conversion(input_path: Path, output_path: Path, fmt: str) -> None:
    text = input_path.read_text(encoding="utf-8", errors="replace")
    if fmt == "html":
        output_path.write_text("<!doctype html>\n<meta charset=\"utf-8\">\n<pre>" + html.escape(text) + "</pre>\n", encoding="utf-8")
    elif fmt == "json":
        try:
            data = json.loads(text)
        except Exception:
            data = {"schema": R42EH_SCHEMA + ".text_wrap", "source_name": input_path.name, "text": text}
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif fmt == "csv":
        with output_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["line_number", "text"])
            for idx, line in enumerate(text.splitlines(), start=1):
                writer.writerow([idx, line])
    elif fmt in {"txt", "md"}:
        output_path.write_text(text, encoding="utf-8")
    else:
        raise ValueError(f"Text output format is not implemented: {fmt}")


def _delete_original_safely(input_path: Path, output_path: Path) -> tuple[bool, str]:
    try:
        if not input_path.is_file():
            return False, "original_missing"
        if input_path.resolve() == output_path.resolve():
            return False, "same_input_output"
        if input_path.is_symlink():
            return False, "input_is_symlink"
        if not output_path.is_file() or output_path.stat().st_size < 1:
            return False, "converted_output_missing_or_empty"
        input_path.unlink()
        return True, "deleted"
    except Exception as exc:
        return False, f"delete_failed: {exc}"


def run_conversion(plan: dict[str, Any], *, timeout: int = 1800) -> dict[str, Any]:
    input_path = Path(str(plan["input_path"]))
    output_path = Path(str(plan["output_path"]))
    fmt = str(plan["target_format"])
    method = str(plan.get("method") or "")
    command = [str(part) for part in (plan.get("command") or [])]
    result: dict[str, Any] = {
        "schema": R42EH_SCHEMA + ".result",
        "success": False,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "input_kind": plan.get("input_kind", "unknown"),
        "output_kind": plan.get("output_kind", "unknown"),
        "target_format": fmt,
        "requested_format": plan.get("requested_format", fmt),
        "method": method,
        "detection": plan.get("detection", {}),
        "preset": plan.get("preset", {}),
        "original_deleted": False,
        "delete_reason": "not_attempted",
        "returncode": None,
        "stderr_tail": "",
        "side_effects": {"network_actions_performed": False, "archive_ph_hit": False, "native_webview2_started": False, "app_started": False},
    }
    try:
        if method == "python_text":
            _write_text_conversion(input_path, output_path, fmt)
            rc = 0
            stderr = ""
        else:
            if not command:
                raise ValueError("Converter plan has no command")
            executable = Path(command[0])
            if not shutil.which(executable.name) and not executable.is_file():
                raise FileNotFoundError("ffmpeg executable not found on PATH")
            proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            rc = int(proc.returncode)
            stderr = proc.stderr or ""
        result["returncode"] = rc
        result["stderr_tail"] = stderr[-4000:]
        result["success"] = bool(rc == 0 and output_path.exists() and output_path.stat().st_size > 0)
        if result["success"] and bool(plan.get("destructive_after_success")):
            deleted, reason = _delete_original_safely(input_path, output_path)
            result["original_deleted"] = deleted
            result["delete_reason"] = reason
    except Exception as exc:
        result["error"] = str(exc)
    return result


def probe_environment() -> dict[str, Any]:
    return {
        "schema": R42EH_SCHEMA + ".environment",
        "ffmpeg_path": shutil.which("ffmpeg") or "",
        "ffprobe_path": shutil.which("ffprobe") or "",
        "supported_inputs": {
            "audio": sorted(AUDIO_INPUT_EXTENSIONS),
            "video": sorted(VIDEO_INPUT_EXTENSIONS),
            "image": sorted(IMAGE_INPUT_EXTENSIONS),
            "text": sorted(TEXT_INPUT_EXTENSIONS),
        },
        "supported_outputs": {
            "audio": sorted(AUDIO_OUTPUT_FORMATS),
            "video": sorted(VIDEO_OUTPUT_FORMATS),
            "image": sorted(IMAGE_OUTPUT_FORMATS),
            "text": sorted(TEXT_OUTPUT_FORMATS),
            "auto": ["auto"],
        },
        "default_format_by_kind": dict(DEFAULT_FORMAT_BY_KIND),
        "side_effects": {"network_actions_performed": False, "archive_ph_hit": False, "native_webview2_started": False, "app_started": False},
    }
