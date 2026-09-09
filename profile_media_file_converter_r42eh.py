"""R42EH/R42ER multipurpose local file converter backend.

Reference-backed desktop implementation for the YTCE File Converter.  The
architecture follows the ConvertIt-style split between detection, planning,
execution, bitrate/sample-rate/playback-speed/channel controls, and optional
CUE-style splitting metadata, but uses local FFmpeg/FFprobe plus the Python
standard library.

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
import re
import shutil
import subprocess

R42EH_SCHEMA = "ytce.r42eh.file_converter.v1"
R42EG_SCHEMA = R42EH_SCHEMA  # compatibility for any old caller that reads this constant

AUDIO_INPUT_EXTENSIONS = {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma", ".aif", ".aiff", ".amr", ".mka", ".spx"}
VIDEO_INPUT_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".wmv", ".flv", ".m4v", ".mpeg", ".mpg", ".ts"}
IMAGE_INPUT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".ico"}
TEXT_INPUT_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".json", ".csv", ".xml", ".srt", ".vtt", ".log"}

AUDIO_BITRATE_OPTIONS = ("9k", "16k", "24k", "32k", "48k", "64k", "96k", "128k", "160k", "192k", "256k", "320k", "512k", "768k", "1024k")
AUDIO_SAMPLE_RATE_OPTIONS = ("8000", "12000", "16000", "22050", "24000", "32000", "44100", "48000", "88200", "96000", "192000")
AUDIO_CHANNEL_OPTIONS = ("source", "mono", "stereo")
AUDIO_PLAYBACK_SPEED_OPTIONS = ("0.5", "0.75", "1.0", "1.25", "1.5", "2.0")
CUE_SPLIT_OPTIONS = ("off", "auto", "manual")
VIDEO_ENCODER_OPTIONS = ("h264", "h265", "vp9", "av1")
VIDEO_PRESET_OPTIONS = ("veryfast", "fast", "medium", "slow")
VIDEO_FPS_OPTIONS = ("source", "24", "25", "30", "50", "60")

# R42EQ: expanded to match the Convertit-style audio option range where local FFmpeg supports it.
AUDIO_OUTPUT_FORMATS = {"mp3", "m4a", "aac", "wav", "flac", "opus", "ogg", "wma", "mka", "spx", "amr", "aiff"}
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


def _safe_output_suffix(file_suffix: str) -> str:
    suffix = str(file_suffix or "").strip()
    if not suffix:
        return ""
    suffix = re.sub(r"[^A-Za-z0-9_.-]+", "_", suffix)[:64]
    if not suffix:
        return ""
    return suffix if suffix.startswith("_") else "_" + suffix


def _make_output_path(input_path: Path, target_format: str, output_dir: str | os.PathLike[str] | None, overwrite: bool, file_suffix: str = "") -> Path:
    folder = Path(output_dir).expanduser() if output_dir else input_path.parent
    folder.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem or "converted"
    suffix = ".jpg" if target_format == "jpeg" else f".{target_format}"
    name_suffix = _safe_output_suffix(file_suffix)
    candidate = folder / f"{stem}{name_suffix}{suffix}"
    if candidate.resolve() == input_path.resolve():
        candidate = folder / f"{stem}_converted{suffix}"
    if overwrite or not candidate.exists():
        return candidate
    base = f"{stem}{name_suffix}" if name_suffix else f"{stem}_converted"
    for index in range(2, 1000):
        candidate = folder / f"{base}_{index}{suffix}"
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


def _normalise_bitrate(value: str, default: str = "128k") -> str:
    bitrate = str(value or "").strip().lower()
    if re.fullmatch(r"\d{2,4}k", bitrate):
        return bitrate
    return default


def _normalise_sample_rate(value: str, default: str = "") -> str:
    sample_rate = str(value or "").strip().lower()
    sample_rate = sample_rate.replace("khz", "").replace("hz", "").strip()
    if sample_rate.endswith("k"):
        try:
            sample_rate = str(int(float(sample_rate[:-1]) * 1000))
        except Exception:
            sample_rate = ""
    if sample_rate in {"", "source"}:
        return ""
    return sample_rate if sample_rate in AUDIO_SAMPLE_RATE_OPTIONS else default


def _normalise_audio_channels(value: str) -> str:
    mode = str(value or "source").strip().lower()
    if mode in {"1", "mono"}:
        return "mono"
    if mode in {"2", "stereo"}:
        return "stereo"
    return "source"


def _normalise_playback_speed(value: str) -> str:
    raw = str(value or "1.0").strip().lower().rstrip("x")
    try:
        speed = max(0.5, min(2.0, float(raw)))
    except Exception:
        speed = 1.0
    return f"{speed:.2f}".rstrip("0").rstrip(".") or "1"


def _normalise_video_encoder(value: str, fmt: str) -> str:
    encoder = str(value or "h264").strip().lower().replace(".", "")
    aliases = {"x264": "h264", "avc": "h264", "x265": "h265", "hevc": "h265", "vp9": "vp9", "libvpx-vp9": "vp9", "aom-av1": "av1", "svt-av1": "av1"}
    encoder = aliases.get(encoder, encoder)
    if fmt == "webm" and encoder not in {"vp9", "av1"}:
        return "vp9"
    if encoder not in VIDEO_ENCODER_OPTIONS:
        return "h264"
    return encoder


def _normalise_video_preset(value: str) -> str:
    preset = str(value or "medium").strip().lower().replace(" ", "")
    return preset if preset in VIDEO_PRESET_OPTIONS else "medium"


def _normalise_video_fps(value: str) -> str:
    fps = str(value or "source").strip().lower()
    return fps if fps in VIDEO_FPS_OPTIONS else "source"


def _append_audio_handling_args(args: list[str], *, fmt: str, bitrate: str, sample_rate: str, audio_channels: str, playback_speed: str) -> None:
    channel_mode = _normalise_audio_channels(audio_channels)
    speed = _normalise_playback_speed(playback_speed)
    # Convertit reference behaviour: AMR-WB is speech-focused, 16 kHz mono.
    if fmt == "amr":
        args += ["-ar", "16000", "-ac", "1"]
    else:
        sample = _normalise_sample_rate(sample_rate)
        if sample:
            args += ["-ar", sample]
        if channel_mode == "mono":
            args += ["-ac", "1"]
        elif channel_mode == "stereo":
            args += ["-ac", "2"]
    if fmt == "opus" and bitrate.replace("k", "").isdigit() and int(bitrate.replace("k", "")) <= 48:
        args += ["-application", "voip"]
    if speed not in {"1", "1.0"}:
        args += ["-filter:a", f"atempo={speed}"]


def _audio_codec(fmt: str, *, compress: bool = False, audio_bitrate: str = "", audio_sample_rate: str = "", audio_channels: str = "source", playback_speed: str = "1.0", cue_split_mode: str = "off") -> tuple[list[str], dict[str, Any]]:
    bitrate = _normalise_bitrate(audio_bitrate, "160k" if compress else "256k")
    mapping = {
        "mp3": ["-c:a", "libmp3lame", "-b:a", bitrate],
        "m4a": ["-c:a", "aac", "-b:a", bitrate],
        "aac": ["-c:a", "aac", "-b:a", bitrate],
        "wav": ["-c:a", "pcm_s16le"],
        "aiff": ["-c:a", "pcm_s16be"],
        "flac": ["-c:a", "flac"],
        "opus": ["-c:a", "libopus", "-b:a", _normalise_bitrate(audio_bitrate, "96k") if compress else bitrate],
        "ogg": ["-c:a", "libvorbis", "-q:a", "3" if compress else "5"],
        "wma": ["-c:a", "wmav2", "-b:a", bitrate],
        "mka": ["-c:a", "libvorbis", "-q:a", "3" if compress else "5"],
        "spx": ["-c:a", "libspeex"],
        "amr": ["-c:a", "amr_wb", "-b:a", _normalise_bitrate(audio_bitrate, "24k")],
    }
    args = list(mapping[fmt])
    effective_bitrate = _normalise_bitrate(audio_bitrate, "24k") if fmt == "amr" else bitrate
    _append_audio_handling_args(args, fmt=fmt, bitrate=effective_bitrate, sample_rate=audio_sample_rate, audio_channels=audio_channels, playback_speed=playback_speed)
    return args, {
        "family": "audio",
        "codec_args": args,
        "compress": bool(compress),
        "audio_bitrate": effective_bitrate,
        "audio_sample_rate": _normalise_sample_rate(audio_sample_rate) or ("16000" if fmt == "amr" else "source"),
        "audio_channels": _normalise_audio_channels(audio_channels),
        "playback_speed": _normalise_playback_speed(playback_speed),
        "cue_split_mode": str(cue_split_mode or "off").strip().lower(),
    }


def _video_codecs(fmt: str, *, compress: bool = False, video_crf: int = 23, video_max_dimension: int = 0, audio_bitrate: str = "", audio_sample_rate: str = "", audio_channels: str = "source", playback_speed: str = "1.0", video_encoder: str = "h264", video_preset: str = "medium", video_fps: str = "source", web_optimise: bool = True) -> tuple[list[str], dict[str, Any]]:
    encoders = _available_ffmpeg_encoders()
    # R42ER: Convert settings can also apply quality/size profiles;
    # C/compress still controls suffix/destructive flow, not whether CRF is usable.
    crf = max(16, min(38, int(video_crf or 23)))
    audio_br = _normalise_bitrate(audio_bitrate, "128k") if compress else _normalise_bitrate(audio_bitrate, "192k")
    encoder = _normalise_video_encoder(video_encoder, fmt)
    preset = _normalise_video_preset(video_preset)
    fps = _normalise_video_fps(video_fps)
    if fmt == "webm":
        if encoder == "av1" and "libaom-av1" in encoders:
            args = ["-c:v", "libaom-av1", "-crf", str(max(28, crf + 6)), "-b:v", "0", "-c:a", "libopus", "-b:a", _normalise_bitrate(audio_bitrate, "96k") if compress else "128k"]
        elif "libvpx-vp9" in encoders or encoder == "vp9":
            args = ["-c:v", "libvpx-vp9", "-crf", str(max(24, crf + 4)), "-b:v", "0", "-c:a", "libopus", "-b:a", _normalise_bitrate(audio_bitrate, "96k") if compress else "128k"]
        else:
            args = ["-c:v", "libvpx", "-b:v", "900k" if compress else "1M", "-c:a", "libopus"]
    else:
        if encoder == "h265":
            video_args = ["-c:v", "libx265", "-preset", preset, "-crf", str(max(20, crf + 2))]
        elif encoder == "av1" and "libaom-av1" in encoders:
            video_args = ["-c:v", "libaom-av1", "-crf", str(max(28, crf + 6)), "-b:v", "0"]
        else:
            video_args = ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
        args = video_args + ["-c:a", "aac", "-b:a", audio_br]
        if fmt in {"mp4", "mov"} and bool(web_optimise):
            args += ["-movflags", "+faststart"]
    max_side = 0
    try:
        max_side = max(0, int(video_max_dimension or 0))
    except Exception:
        max_side = 0
    if max_side:
        scale = f"scale='if(gt(iw,ih),min({max_side},iw),-2)':'if(gt(ih,iw),min({max_side},ih),-2)'"
        args = ["-vf", scale] + args
    if fps != "source":
        args += ["-r", fps]
    _append_audio_handling_args(args, fmt="aac" if fmt != "webm" else "opus", bitrate=audio_br, sample_rate=audio_sample_rate, audio_channels=audio_channels, playback_speed=playback_speed)
    return args, {"family": "video", "codec_args": args, "ffmpeg_encoder_count": len(encoders), "compress": bool(compress), "crf": crf, "max_dimension": max_side, "audio_bitrate": audio_br, "audio_sample_rate": _normalise_sample_rate(audio_sample_rate) or "source", "audio_channels": _normalise_audio_channels(audio_channels), "playback_speed": _normalise_playback_speed(playback_speed), "video_encoder": encoder, "video_preset": preset, "video_fps": fps, "web_optimise": bool(web_optimise)}


def _image_codec(fmt: str, image_quality: int, *, compress: bool = False, image_max_dimension: int = 0, webp_method: int = 4, png_compression_level: int = 9, jpeg_chroma_subsampling: str = "auto") -> tuple[list[str], dict[str, Any]]:
    q = max(1, min(100, int(image_quality)))
    args: list[str] = []
    max_side = 0
    try:
        max_side = max(0, int(image_max_dimension or 0))
    except Exception:
        max_side = 0
    if max_side:
        args += ["-vf", f"scale='if(gt(iw,ih),min({max_side},iw),-2)':'if(gt(ih,iw),min({max_side},ih),-2)'"]
    if fmt == "jpg":
        qscale = max(2, min(31, int(round((100 - q) / 3.25)) or 2))
        args += ["-frames:v", "1", "-q:v", str(qscale)]
        chroma = str(jpeg_chroma_subsampling or "auto").strip().lower()
        if chroma in {"4:4:4", "444"}:
            args += ["-pix_fmt", "yuvj444p"]
        elif chroma in {"4:2:0", "420"}:
            args += ["-pix_fmt", "yuvj420p"]
    elif fmt == "webp":
        method = max(0, min(6, int(webp_method)))
        args += ["-lossless", "0", "-quality", str(q), "-method", str(method)]
    elif fmt == "png":
        level = max(0, min(9, int(png_compression_level)))
        args += ["-frames:v", "1", "-compression_level", str(level)]
    elif fmt in {"bmp", "tiff"}:
        args += ["-frames:v", "1"]
    return args, {"family": "image", "quality": q, "codec_args": args, "compress": bool(compress), "max_dimension": max_side, "webp_method": int(webp_method), "png_compression_level": int(png_compression_level), "jpeg_chroma_subsampling": str(jpeg_chroma_subsampling or "auto")}


def _validate_route(input_kind: str, output_kind: str, target_format: str) -> None:
    if input_kind == "unknown":
        raise ValueError("Cannot convert because the input file type is UNKNOWN")
    if input_kind == output_kind:
        return
    # Allow extracting audio from video, a normal FFmpeg route.
    if input_kind == "video" and output_kind == "audio":
        return
    raise ValueError(f"Unsupported converter route: {input_kind} -> {target_format} ({output_kind})")


def plan_conversion(input_path: str | os.PathLike[str], target_format: str = "auto", *, output_dir: str | os.PathLike[str] | None = None, keep_original: bool = False, overwrite: bool = False, image_quality: int = 92, compress: bool = False, image_max_dimension: int = 0, image_webp_method: int = 4, image_png_compression_level: int = 9, image_jpeg_chroma_subsampling: str = "auto", video_crf: int = 23, video_max_dimension: int = 0, video_encoder: str = "h264", video_preset: str = "medium", video_fps: str = "source", web_optimise: bool = True, audio_bitrate: str = "", audio_sample_rate: str = "", audio_channels: str = "source", playback_speed: str = "1.0", cue_split_mode: str = "off", preserve_metadata: bool = True, file_suffix: str = "") -> dict[str, Any]:
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

    output_file = _make_output_path(input_file, fmt, output_dir, overwrite, file_suffix if compress else "")
    preset: dict[str, Any] = {}
    if output_kind == "text":
        method = "python_text"
        command = ["python_text_convert", str(input_file), str(output_file)]
        preset = {"family": "text", "preserve_original_text": True, "compress": False}
    else:
        method = "ffmpeg"
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
        command = [ffmpeg, "-hide_banner", "-y", "-i", str(input_file)]
        if preserve_metadata:
            command += ["-map_metadata", "0"]
        if output_kind == "audio":
            command += ["-vn"]
            args, preset = _audio_codec(fmt, compress=bool(compress), audio_bitrate=audio_bitrate, audio_sample_rate=audio_sample_rate, audio_channels=audio_channels, playback_speed=playback_speed, cue_split_mode=cue_split_mode)
            command += args
        elif output_kind == "video":
            args, preset = _video_codecs(fmt, compress=bool(compress), video_crf=video_crf, video_max_dimension=video_max_dimension, audio_bitrate=audio_bitrate, audio_sample_rate=audio_sample_rate, audio_channels=audio_channels, playback_speed=playback_speed, video_encoder=video_encoder, video_preset=video_preset, video_fps=video_fps, web_optimise=web_optimise)
            command += args
        elif output_kind == "image":
            args, preset = _image_codec(fmt, image_quality, compress=bool(compress), image_max_dimension=image_max_dimension, webp_method=image_webp_method, png_compression_level=image_png_compression_level, jpeg_chroma_subsampling=image_jpeg_chroma_subsampling)
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
        "audio_bitrate_options": list(AUDIO_BITRATE_OPTIONS),
        "audio_sample_rate_options": ["source", *AUDIO_SAMPLE_RATE_OPTIONS],
        "audio_channel_options": list(AUDIO_CHANNEL_OPTIONS),
        "audio_playback_speed_options": list(AUDIO_PLAYBACK_SPEED_OPTIONS),
        "cue_split_options": list(CUE_SPLIT_OPTIONS),
        "video_encoder_options": list(VIDEO_ENCODER_OPTIONS),
        "video_preset_options": list(VIDEO_PRESET_OPTIONS),
        "video_fps_options": list(VIDEO_FPS_OPTIONS),
        "side_effects": {"network_actions_performed": False, "archive_ph_hit": False, "native_webview2_started": False, "app_started": False},
    }
