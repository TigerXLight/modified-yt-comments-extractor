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
VIDEO_ENCODER_OPTIONS = ("auto", "h264", "h265", "vp9", "av1")
VIDEO_PRESET_OPTIONS = ("auto", "veryfast", "fast", "medium", "slow")
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
    ffprobe = _ffprobe_path()
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


def _ffmpeg_path() -> str:
    bundled = Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.EXE")
    found = shutil.which("ffmpeg")
    if found:
        return found
    if os.name == "nt" and bundled.exists():
        return str(bundled)
    return "ffmpeg"


def _ffprobe_path() -> str:
    bundled = Path(r"C:\Program Files\ffmpeg\bin\ffprobe.EXE")
    found = shutil.which("ffprobe")
    if found:
        return found
    if os.name == "nt" and bundled.exists():
        return str(bundled)
    return "ffprobe"


def _available_ffmpeg_encoders() -> set[str]:
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        return set()
    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
    except Exception:
        return set()
    if proc.returncode != 0:
        return set()
    encoders: set[str] = set()
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        line = line.strip()
        if not line or line.startswith("--") or line.lower().startswith("encoders"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] and parts[0][0] in {"V", "A", "S"}:
            encoders.add(parts[1])
    # Normalise common spelling aliases exposed by some Windows builds.
    if "libsvt_av1" in encoders:
        encoders.add("libsvtav1")
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




def _parse_float(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value or "").strip())
    except Exception:
        return default


def _parse_fraction(value: object) -> float:
    raw = str(value or "").strip()
    if not raw or raw in {"0/0", "N/A"}:
        return 0.0
    if "/" in raw:
        try:
            left, right = raw.split("/", 1)
            denom = float(right or 0)
            return float(left) / denom if denom else 0.0
        except Exception:
            return 0.0
    return _parse_float(raw, 0.0)


def _bitrate_to_kbps(value: object) -> int:
    raw = str(value or "").strip().lower()
    if not raw or raw == "n/a":
        return 0
    try:
        if raw.endswith("k"):
            return int(float(raw[:-1]))
        if raw.endswith("m"):
            return int(float(raw[:-1]) * 1000)
        return int(float(raw) / 1000.0) if float(raw) > 10000 else int(float(raw))
    except Exception:
        return 0


def _target_size_mb_to_float(value: object) -> float:
    raw = str(value or "").strip().lower().replace("mb", "").replace("mib", "").strip()
    if raw in {"", "auto", "none", "off"}:
        return 0.0
    try:
        return max(0.0, float(raw))
    except Exception:
        return 0.0


def _ffprobe_media_metadata(path: Path, *, timeout: int = 8) -> dict[str, Any]:
    """Fast local metadata read for the Optimised matcher.

    R42ET: this is deliberately a cheap/instant pass, not a sample encode.  It
    gives the dynamic matcher duration, resolution, fps, bitrate and bpppf so
    Optimised can choose copy/remux, H.264, HEVC, VP9 or AV1 without hardcoding
    a single encoder for every file.
    """
    metadata: dict[str, Any] = {
        "schema": R42EH_SCHEMA + ".video_metadata",
        "ffprobe_available": False,
        "duration_seconds": 0.0,
        "width": 0,
        "height": 0,
        "fps": 0.0,
        "video_codec": "",
        "audio_codec": "",
        "container": "",
        "video_bitrate_kbps": 0,
        "audio_bitrate_kbps": 0,
        "format_bitrate_kbps": 0,
        "bits_per_pixel_frame": 0.0,
    }
    ffprobe = _ffprobe_path()
    if not ffprobe or not path.is_file():
        return metadata
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
    except Exception as exc:
        metadata["warning"] = f"ffprobe_failed: {exc}"
        return metadata
    if proc.returncode != 0 or not proc.stdout.strip():
        metadata["warning"] = (proc.stderr or "ffprobe returned no metadata")[-500:]
        return metadata
    try:
        payload = json.loads(proc.stdout)
    except Exception as exc:
        metadata["warning"] = f"ffprobe_json_failed: {exc}"
        return metadata
    fmt = payload.get("format") if isinstance(payload, dict) else {}
    streams = payload.get("streams") if isinstance(payload, dict) else []
    if not isinstance(fmt, dict):
        fmt = {}
    if not isinstance(streams, list):
        streams = []
    metadata["ffprobe_available"] = True
    metadata["container"] = str(fmt.get("format_name") or "")
    metadata["duration_seconds"] = _parse_float(fmt.get("duration"), 0.0)
    metadata["format_bitrate_kbps"] = _bitrate_to_kbps(fmt.get("bit_rate"))
    video_stream = next((s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"), {})
    if isinstance(video_stream, dict):
        metadata["video_codec"] = str(video_stream.get("codec_name") or "")
        try:
            metadata["width"] = int(video_stream.get("width") or 0)
            metadata["height"] = int(video_stream.get("height") or 0)
        except Exception:
            pass
        metadata["fps"] = _parse_fraction(video_stream.get("avg_frame_rate")) or _parse_fraction(video_stream.get("r_frame_rate"))
        metadata["video_bitrate_kbps"] = _bitrate_to_kbps(video_stream.get("bit_rate"))
    if isinstance(audio_stream, dict):
        metadata["audio_codec"] = str(audio_stream.get("codec_name") or "")
        metadata["audio_bitrate_kbps"] = _bitrate_to_kbps(audio_stream.get("bit_rate"))
    if not metadata["video_bitrate_kbps"] and metadata["format_bitrate_kbps"]:
        metadata["video_bitrate_kbps"] = max(0, int(metadata["format_bitrate_kbps"]) - int(metadata["audio_bitrate_kbps"] or 0))
    width = int(metadata["width"] or 0)
    height = int(metadata["height"] or 0)
    fps = float(metadata["fps"] or 0.0)
    video_kbps = int(metadata["video_bitrate_kbps"] or 0)
    if width > 0 and height > 0 and fps > 0 and video_kbps > 0:
        metadata["bits_per_pixel_frame"] = round((video_kbps * 1000.0) / (width * height * fps), 6)
    return metadata


def _system_capability_probe(encoders: set[str], runnable_encoders: set[str] | None = None) -> dict[str, Any]:
    """Return compiled and actually-runnable encoder capability.

    R42EX: FFmpeg may list encoders that the current GPU cannot actually run
    (for example av1_amf on a GPU without AV1 encode hardware).  Keep compiled
    availability separate from runnable availability so Optimised does not make a
    false hardware choice.
    """
    cpu_count = os.cpu_count() or 0
    hardware_suffixes = ("_amf", "_nvenc", "_qsv", "_mf", "_vulkan")
    software_known = {"libx264", "libx265", "libvpx-vp9", "libsvtav1", "libsvt_av1", "libaom-av1", "librav1e"}
    runnable = set(runnable_encoders or ())
    selection = runnable if runnable else set(encoders)
    return {
        "schema": R42EH_SCHEMA + ".capability_probe",
        "cpu_count": cpu_count,
        "compiled_hardware_encoders": sorted(name for name in encoders if name.endswith(hardware_suffixes)),
        "compiled_software_encoders": sorted(name for name in encoders if name in software_known),
        "runnable_encoders": sorted(runnable),
        "hardware_encoders": sorted(name for name in selection if name.endswith(hardware_suffixes)),
        "software_encoders": sorted(name for name in selection if name in software_known),
        "has_h264_hw": any(name in selection for name in {"h264_amf", "h264_nvenc", "h264_qsv", "h264_mf", "h264_vulkan"}),
        "has_hevc_hw": any(name in selection for name in {"hevc_amf", "hevc_nvenc", "hevc_qsv", "hevc_mf", "hevc_vulkan"}),
        "has_av1_hw": any(name in selection for name in {"av1_amf", "av1_nvenc", "av1_qsv", "av1_mf", "av1_vulkan"}),
        "has_h264_sw": any(name in selection for name in {"libx264", "h264"}),
        "has_hevc_sw": any(name in selection for name in {"libx265", "hevc"}),
        "has_vp9_sw": "libvpx-vp9" in selection,
        "has_av1_sw": any(name in selection for name in {"libsvtav1", "libsvt_av1", "libaom-av1", "librav1e"}),
        "compiled_only_warning": "compiled encoder list is not treated as GPU usability proof" if runnable else "runnable probe not yet run; compiled list used only as fallback",
    }


def _choose_existing_encoder(encoders: set[str], names: tuple[str, ...], fallback: str) -> str:
    for name in names:
        if name in encoders:
            return name
    return fallback

_RUNNABLE_ENCODER_CACHE: dict[str, Any] = {"encoders": set(), "results": [], "source_encoder_count": -1}

def _quick_encoder_test_args(name: str) -> tuple[list[str], str]:
    if name == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "speed", "-b:v", "1800k"], ".mp4"
    if name == "hevc_amf":
        return ["-c:v", "hevc_amf", "-quality", "speed", "-b:v", "1200k"], ".mp4"
    if name == "av1_amf":
        return ["-c:v", "av1_amf", "-quality", "speed", "-b:v", "1000k"], ".mp4"
    if name == "h264_mf":
        return ["-c:v", "h264_mf", "-b:v", "1800k"], ".mp4"
    if name == "hevc_mf":
        return ["-c:v", "hevc_mf", "-b:v", "1200k"], ".mp4"
    if name == "av1_mf":
        return ["-c:v", "av1_mf", "-b:v", "1000k"], ".mp4"
    if name == "h264_vulkan":
        return ["-c:v", "h264_vulkan", "-b:v", "1800k"], ".mp4"
    if name == "hevc_vulkan":
        return ["-c:v", "hevc_vulkan", "-b:v", "1200k"], ".mp4"
    if name == "av1_vulkan":
        return ["-c:v", "av1_vulkan", "-b:v", "1000k"], ".mp4"
    if name == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "1800k"], ".mp4"
    if name == "hevc_nvenc":
        return ["-c:v", "hevc_nvenc", "-preset", "p4", "-b:v", "1200k"], ".mp4"
    if name == "av1_nvenc":
        return ["-c:v", "av1_nvenc", "-preset", "p4", "-b:v", "1000k"], ".mp4"
    if name == "h264_qsv":
        return ["-c:v", "h264_qsv", "-b:v", "1800k"], ".mp4"
    if name == "hevc_qsv":
        return ["-c:v", "hevc_qsv", "-b:v", "1200k"], ".mp4"
    if name == "av1_qsv":
        return ["-c:v", "av1_qsv", "-b:v", "1000k"], ".mp4"
    if name == "libx264":
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"], ".mp4"
    if name == "libx265":
        return ["-c:v", "libx265", "-preset", "ultrafast", "-crf", "30"], ".mp4"
    if name == "libvpx-vp9":
        return ["-c:v", "libvpx-vp9", "-row-mt", "1", "-deadline", "realtime", "-cpu-used", "8", "-b:v", "0", "-crf", "36"], ".webm"
    if name in {"libsvtav1", "libsvt_av1"}:
        return ["-c:v", "libsvtav1", "-preset", "12", "-crf", "38"], ".mp4"
    if name == "libaom-av1":
        return ["-c:v", "libaom-av1", "-cpu-used", "8", "-crf", "38", "-b:v", "0"], ".mkv"
    if name == "librav1e":
        return ["-c:v", "librav1e", "-speed", "10", "-qp", "120"], ".mkv"
    return ["-c:v", name, "-b:v", "1200k"], ".mp4"

def _probe_runnable_video_encoders(encoders: set[str] | None = None, *, timeout: int = 5, include_slow: bool = False) -> dict[str, Any]:
    """Test which compiled encoders actually run on this machine.

    This is deliberately tiny and synthetic.  It prevents Optimised from
    choosing e.g. av1_amf merely because the FFmpeg binary was compiled with
    that encoder when the installed GPU cannot execute it.
    """
    ffmpeg = _ffmpeg_path()
    compiled = set(encoders or _available_ffmpeg_encoders())
    candidates = [
        "h264_amf", "hevc_amf", "av1_amf", "h264_mf", "hevc_mf", "av1_mf",
        "h264_vulkan", "hevc_vulkan", "av1_vulkan",
        "h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_qsv", "hevc_qsv", "av1_qsv",
        "libx264", "libx265", "libvpx-vp9", "libsvtav1",
    ]
    if include_slow:
        candidates += ["libaom-av1", "librav1e"]
    runnable: set[str] = set()
    results: list[dict[str, Any]] = []
    import tempfile, time
    with tempfile.TemporaryDirectory(prefix="ytce_encoder_probe_") as tmp:
        tmp_path = Path(tmp)
        for name in candidates:
            if name not in compiled:
                continue
            args, ext = _quick_encoder_test_args(name)
            out_path = tmp_path / f"probe_{name}{ext}"
            cmd = [ffmpeg, "-hide_banner", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=15", "-t", "0.6", "-an", *args, str(out_path)]
            started = time.perf_counter()
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=max(2, int(timeout)), encoding="utf-8", errors="replace")
                elapsed = round(time.perf_counter() - started, 3)
                ok = proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0
                if ok:
                    runnable.add("libsvt_av1" if name == "libsvtav1" and "libsvt_av1" in compiled else name)
                    runnable.add("libsvtav1" if name == "libsvt_av1" else name)
                results.append({"encoder": name, "ok": bool(ok), "seconds": elapsed, "output_bytes": out_path.stat().st_size if out_path.exists() else 0, "stderr_tail": (proc.stderr or "")[-700:]})
            except Exception as exc:
                results.append({"encoder": name, "ok": False, "error": repr(exc)})
    return {"schema": R42EH_SCHEMA + ".runnable_encoder_probe", "runnable_encoders": sorted(runnable), "results": results}

def _runnable_video_encoders_cached(encoders: set[str] | None = None, *, timeout: int = 4) -> set[str]:
    compiled = set(encoders or _available_ffmpeg_encoders())
    cached_count = int(_RUNNABLE_ENCODER_CACHE.get("source_encoder_count") or -1)
    if cached_count == len(compiled) and _RUNNABLE_ENCODER_CACHE.get("encoders"):
        return set(_RUNNABLE_ENCODER_CACHE.get("encoders") or set())
    probe = _probe_runnable_video_encoders(compiled, timeout=timeout, include_slow=False)
    runnable = set(probe.get("runnable_encoders") or [])
    # If the runtime probe fails completely, fall back to the compiled list rather
    # than breaking conversion.  The capability report still says the runnable
    # probe was not proof.
    if not runnable:
        runnable = set(compiled)
    _RUNNABLE_ENCODER_CACHE["encoders"] = set(runnable)
    _RUNNABLE_ENCODER_CACHE["results"] = list(probe.get("results") or [])
    _RUNNABLE_ENCODER_CACHE["source_encoder_count"] = len(compiled)
    return set(runnable)


def _classify_source_bitrate(metadata: dict[str, Any]) -> str:
    bpppf = float(metadata.get("bits_per_pixel_frame") or 0.0)
    video_kbps = int(metadata.get("video_bitrate_kbps") or 0)
    if bpppf:
        if bpppf < 0.055:
            return "low"
        if bpppf < 0.145:
            return "medium"
        return "high"
    if video_kbps:
        if video_kbps < 1600:
            return "low"
        if video_kbps < 6500:
            return "medium"
        return "high"
    return "unknown"


def _target_video_kbps_from_size(metadata: dict[str, Any], target_file_size_mb: object, audio_bitrate: str) -> int:
    target_mb = _target_size_mb_to_float(target_file_size_mb)
    duration = float(metadata.get("duration_seconds") or 0.0)
    if target_mb <= 0 or duration <= 0:
        return 0
    # MB -> total kbit/sec.  Use 8192 kb per MiB for a conservative cap and
    # reserve enough for audio/container overhead.
    total_kbps = int((target_mb * 8192.0) / max(duration, 1.0))
    audio_kbps = _bitrate_to_kbps(audio_bitrate) or int(metadata.get("audio_bitrate_kbps") or 128) or 128
    return max(120, total_kbps - audio_kbps - 64)


def _optimised_max_side(metadata: dict[str, Any], *, target_video_kbps: int, source_class: str, preset: str) -> int:
    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    source_max = max(width, height)
    if preset == "speed":
        return 1280 if source_max > 1280 else 0
    if target_video_kbps:
        if target_video_kbps < 900:
            return 720 if source_max > 720 else 0
        if target_video_kbps < 2400:
            return 1280 if source_max > 1280 else 0
        return 1920 if source_max > 1920 else 0
    if source_class == "low":
        return 0 if source_max <= 1920 else 1920
    if source_max > 1920:
        return 1920
    if source_max > 1280 and source_class == "high":
        return 1280
    return 0


def _build_video_encoder_args(encoder_impl: str, *, fmt: str, crf: int, bitrate_kbps: int, speed: str, audio_br: str, web_optimise: bool) -> list[str]:
    bitrate = f"{bitrate_kbps}k" if bitrate_kbps else ""
    maxrate = f"{max(bitrate_kbps, int(bitrate_kbps * 1.35))}k" if bitrate_kbps else ""
    bufsize = f"{max(bitrate_kbps * 2, 500)}k" if bitrate_kbps else ""
    if encoder_impl in {"h264_amf", "h264_nvenc", "h264_qsv", "h264_vulkan"}:
        args = ["-c:v", encoder_impl]
        if bitrate_kbps:
            args += ["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize]
        else:
            args += ["-quality", "balanced", "-rc", "cqp", "-qp_i", str(max(18, crf - 2)), "-qp_p", str(crf)]
    elif encoder_impl in {"hevc_amf", "hevc_nvenc", "hevc_qsv", "hevc_vulkan"}:
        args = ["-c:v", encoder_impl]
        if bitrate_kbps:
            args += ["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize]
        else:
            args += ["-quality", "balanced", "-rc", "cqp", "-qp_i", str(max(20, crf - 2)), "-qp_p", str(crf)]
    elif encoder_impl in {"av1_amf", "av1_nvenc", "av1_qsv", "av1_mf", "av1_vulkan"}:
        # Hardware AV1 encoders are only used after a runnable probe.  Prefer
        # bitrate-style settings because support for CRF-like controls differs
        # across AMF/NVENC/QSV/MF/Vulkan implementations.
        args = ["-c:v", encoder_impl, "-b:v", bitrate or "1400k"]
        if bitrate_kbps:
            args += ["-maxrate", maxrate, "-bufsize", bufsize]
    elif encoder_impl in {"h264_mf", "hevc_mf"}:
        # Windows Media Foundation encoders are generally bitrate-driven.
        args = ["-c:v", encoder_impl, "-b:v", bitrate or ("2500k" if encoder_impl == "h264_mf" else "1800k")]
    elif encoder_impl == "libx265":
        args = ["-c:v", "libx265", "-preset", speed if speed in {"veryfast", "fast", "medium", "slow"} else "fast"]
        args += (["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize] if bitrate_kbps else ["-crf", str(crf)])
    elif encoder_impl == "libvpx-vp9":
        args = ["-c:v", "libvpx-vp9", "-row-mt", "1"]
        args += (["-b:v", bitrate] if bitrate_kbps else ["-crf", str(crf), "-b:v", "0"])
    elif encoder_impl == "libsvtav1":
        args = ["-c:v", "libsvtav1", "-preset", "8"]
        args += (["-b:v", bitrate] if bitrate_kbps else ["-crf", str(crf)])
    elif encoder_impl == "libaom-av1":
        args = ["-c:v", "libaom-av1", "-cpu-used", "6"]
        args += (["-b:v", bitrate] if bitrate_kbps else ["-crf", str(crf), "-b:v", "0"])
    elif encoder_impl == "librav1e":
        args = ["-c:v", "librav1e", "-speed", "8"]
        args += (["-b:v", bitrate] if bitrate_kbps else ["-qp", str(max(80, crf * 4))])
    elif encoder_impl in {"h264", "hevc"}:
        args = ["-c:v", encoder_impl]
        args += (["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize] if bitrate_kbps else ["-q:v", "5"])
    else:
        args = ["-c:v", "libx264", "-preset", speed if speed in {"veryfast", "fast", "medium", "slow"} else "fast"]
        args += (["-b:v", bitrate, "-maxrate", maxrate, "-bufsize", bufsize] if bitrate_kbps else ["-crf", str(crf)])
    if fmt == "webm":
        audio_codec = ["-c:a", "libopus", "-b:a", _normalise_bitrate(audio_br, "128k")]
    else:
        audio_codec = ["-c:a", "aac", "-b:a", _normalise_bitrate(audio_br, "160k")]
    args += audio_codec
    if fmt in {"mp4", "mov"} and bool(web_optimise):
        args += ["-movflags", "+faststart"]
    return args


def _select_optimised_video_strategy(path: Path, fmt: str, *, compress: bool, target_file_size_mb: object, optimisation_preset: str, audio_bitrate: str, video_encoder: str, video_preset: str, video_crf: int, video_max_dimension: int, web_optimise: bool) -> tuple[list[str], dict[str, Any]]:
    encoders = _available_ffmpeg_encoders()
    runnable_encoders = _runnable_video_encoders_cached(encoders)
    # Selection must use actually-runnable encoders.  The compiled FFmpeg list is
    # only a discovery list and can include encoders for hardware not present.
    selection_encoders = runnable_encoders or encoders
    metadata = _ffprobe_media_metadata(path)
    capability = _system_capability_probe(encoders, runnable_encoders)
    preset_name = str(optimisation_preset or "Optimised").strip().replace("_", " ").title()
    preset_key = "speed" if preset_name == "Speed" else "optimised"
    source_class = _classify_source_bitrate(metadata)
    target_kbps = _target_video_kbps_from_size(metadata, target_file_size_mb, audio_bitrate)
    duration = float(metadata.get("duration_seconds") or 0.0)
    short_video = bool(duration and duration <= 120)
    requested_encoder = _normalise_video_encoder(video_encoder, fmt)
    speed = _normalise_video_preset(video_preset)
    if speed == "auto":
        speed = "veryfast" if preset_key == "speed" else "fast"

    if target_kbps:
        mode = "target_size_bitrate"
    else:
        mode = "quality_crf"

    reason: list[str] = []
    encoder_impl = ""
    chosen_family = "h264"

    if requested_encoder != "auto":
        chosen_family = requested_encoder
        reason.append(f"manual encoder override: {requested_encoder}")
    elif preset_key == "speed":
        chosen_family = "h264"
        reason.append("Speed preset prefers a fast, compatible encoder")
    elif short_video and any(name in selection_encoders for name in {"av1_amf", "av1_nvenc", "av1_qsv", "av1_mf", "av1_vulkan", "libsvtav1", "libsvt_av1", "libaom-av1", "librav1e"}):
        chosen_family = "av1"
        reason.append("short video allows AV1 efficiency without an excessive default wait")
    elif fmt == "webm":
        chosen_family = "vp9"
        reason.append("WebM/open output favours VP9 when AV1 is not selected")
    elif target_kbps and target_kbps < 2600:
        chosen_family = "h265"
        reason.append("target size implies lower target bitrate; HEVC/H.265 is preferred for smaller MP4")
    elif source_class == "high":
        chosen_family = "h265"
        reason.append("source bitrate looks high/bloated; HEVC/H.265 should reduce size while preserving clarity")
    else:
        chosen_family = "h264"
        reason.append("normal/unknown bitrate keeps H.264 for compatibility and practical runtime")

    if chosen_family == "av1":
        encoder_impl = _choose_existing_encoder(selection_encoders, ("av1_amf", "av1_nvenc", "av1_qsv", "av1_mf", "av1_vulkan", "libsvtav1", "libsvt_av1", "libaom-av1", "librav1e"), "libsvtav1")
        crf = 32 if source_class != "low" else 28
    elif chosen_family == "h265":
        encoder_impl = _choose_existing_encoder(selection_encoders, ("hevc_amf", "hevc_mf", "hevc_vulkan", "hevc_nvenc", "hevc_qsv", "libx265", "hevc"), "libx265")
        crf = 27 if source_class != "low" else 24
    elif chosen_family == "vp9":
        encoder_impl = _choose_existing_encoder(selection_encoders, ("libvpx-vp9",), "libvpx-vp9")
        crf = 34 if source_class != "low" else 30
    else:
        encoder_impl = _choose_existing_encoder(selection_encoders, ("h264_amf", "h264_mf", "h264_vulkan", "h264_nvenc", "h264_qsv", "libx264", "h264"), "libx264")
        crf = 24 if source_class != "low" else 21

    if preset_key == "speed":
        # Speed is allowed to be larger, but should stay clear/readable.
        if chosen_family == "h264":
            crf = max(crf, 26)
        speed = "veryfast" if encoder_impl == "libx264" else "fast"
    if video_crf:
        try:
            manual_crf = int(video_crf)
            if requested_encoder != "auto":
                crf = max(16, min(45, manual_crf))
        except Exception:
            pass

    max_side = 0
    try:
        max_side = max(0, int(video_max_dimension or 0))
    except Exception:
        max_side = 0
    if not max_side:
        max_side = _optimised_max_side(metadata, target_video_kbps=target_kbps, source_class=source_class, preset=preset_key)

    args = _build_video_encoder_args(encoder_impl, fmt=fmt, crf=crf, bitrate_kbps=target_kbps, speed=speed, audio_br=audio_bitrate, web_optimise=web_optimise)
    if max_side:
        scale = f"scale='if(gt(iw,ih),min({max_side},iw),-2)':'if(gt(ih,iw),min({max_side},ih),-2)'"
        args = ["-vf", scale] + args

    return args, {
        "family": "video",
        "codec_args": args,
        "ffmpeg_encoder_count": len(encoders),
        "compress": bool(compress),
        "optimisation_preset": "Speed" if preset_key == "speed" else "Optimised",
        "optimisation_mode": mode,
        "target_file_size_mb": _target_size_mb_to_float(target_file_size_mb),
        "target_video_bitrate_kbps": target_kbps,
        "selected_encoder_family": chosen_family,
        "selected_encoder_impl": encoder_impl,
        "command_encoder_impl": encoder_impl if encoder_impl in args else (args[args.index("-c:v") + 1] if "-c:v" in args and args.index("-c:v") + 1 < len(args) else ""),
        "encoder_command_aligned": bool(encoder_impl in args),
        "crf_or_quality": crf,
        "source_bitrate_class": source_class,
        "metadata": metadata,
        "capability": capability,
        "selection_reason": "; ".join(reason),
        "max_dimension": max_side,
        "audio_bitrate": _normalise_bitrate(audio_bitrate, "160k"),
        "web_optimise": bool(web_optimise),
    }

def _normalise_video_encoder(value: str, fmt: str) -> str:
    encoder = str(value or "auto").strip().lower().replace(".", "")
    aliases = {"automatic": "auto", "x264": "h264", "avc": "h264", "x265": "h265", "hevc": "h265", "vp9": "vp9", "libvpx-vp9": "vp9", "aom-av1": "av1", "svt-av1": "av1"}
    encoder = aliases.get(encoder, encoder)
    if encoder not in VIDEO_ENCODER_OPTIONS:
        return "auto"
    return encoder


def _normalise_video_preset(value: str) -> str:
    preset = str(value or "auto").strip().lower().replace(" ", "")
    return preset if preset in VIDEO_PRESET_OPTIONS else "auto"


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


def _video_codecs(fmt: str, *, source_path: Path | None = None, compress: bool = False, video_crf: int = 23, video_max_dimension: int = 0, audio_bitrate: str = "", audio_sample_rate: str = "", audio_channels: str = "source", playback_speed: str = "1.0", video_encoder: str = "auto", video_preset: str = "auto", video_fps: str = "source", web_optimise: bool = True, optimisation_preset: str = "Optimised", target_file_size_mb: object = "") -> tuple[list[str], dict[str, Any]]:
    encoders = _available_ffmpeg_encoders()
    encoder = _normalise_video_encoder(video_encoder, fmt)
    fps = _normalise_video_fps(video_fps)
    audio_br = _normalise_bitrate(audio_bitrate, "160k" if compress else "192k")

    # R42ET: auto/Optimised is a dynamic matcher. Manual encoder choices still
    # work, but automatic choices are metadata/capability/target-size driven.
    if encoder == "auto" and source_path is not None:
        args, preset = _select_optimised_video_strategy(
            source_path,
            fmt,
            compress=bool(compress),
            target_file_size_mb=target_file_size_mb,
            optimisation_preset=optimisation_preset,
            audio_bitrate=audio_br,
            video_encoder=encoder,
            video_preset=video_preset,
            video_crf=video_crf,
            video_max_dimension=video_max_dimension,
            web_optimise=web_optimise,
        )
    else:
        # Manual Advanced path.
        crf = max(16, min(45, int(video_crf or 23)))
        preset_speed = _normalise_video_preset(video_preset)
        if preset_speed == "auto":
            preset_speed = "fast"
        if fmt == "webm":
            if encoder == "av1" and "libsvtav1" in encoders:
                args = ["-c:v", "libsvtav1", "-preset", "8", "-crf", str(max(26, crf + 6)), "-c:a", "libopus", "-b:a", _normalise_bitrate(audio_bitrate, "128k")]
                selected = "libsvtav1"
            else:
                args = ["-c:v", "libvpx-vp9", "-row-mt", "1", "-crf", str(max(24, crf + 4)), "-b:v", "0", "-c:a", "libopus", "-b:a", _normalise_bitrate(audio_bitrate, "128k")]
                selected = "libvpx-vp9"
        else:
            if encoder == "h265":
                selected = _choose_existing_encoder(encoders, ("hevc_amf", "hevc_mf", "hevc_nvenc", "hevc_qsv", "libx265", "hevc"), "libx265")
            elif encoder == "av1":
                selected = _choose_existing_encoder(encoders, ("av1_amf", "av1_nvenc", "av1_qsv", "libsvtav1", "libsvt_av1", "libaom-av1", "librav1e"), "libsvtav1")
            else:
                selected = _choose_existing_encoder(encoders, ("h264_amf", "h264_mf", "h264_nvenc", "h264_qsv", "libx264", "h264"), "libx264")
            args = _build_video_encoder_args(selected, fmt=fmt, crf=crf, bitrate_kbps=0, speed=preset_speed, audio_br=audio_br, web_optimise=web_optimise)
        max_side = 0
        try:
            max_side = max(0, int(video_max_dimension or 0))
        except Exception:
            max_side = 0
        if max_side:
            scale = f"scale='if(gt(iw,ih),min({max_side},iw),-2)':'if(gt(ih,iw),min({max_side},ih),-2)'"
            args = ["-vf", scale] + args
        preset = {"family": "video", "codec_args": args, "ffmpeg_encoder_count": len(encoders), "compress": bool(compress), "optimisation_preset": str(optimisation_preset or "Optimised"), "optimisation_mode": "manual_advanced", "selected_encoder_family": encoder, "selected_encoder_impl": selected, "command_encoder_impl": selected if selected in args else (args[args.index("-c:v") + 1] if "-c:v" in args and args.index("-c:v") + 1 < len(args) else ""), "encoder_command_aligned": bool(selected in args), "crf_or_quality": crf, "max_dimension": max_side, "audio_bitrate": audio_br, "web_optimise": bool(web_optimise)}

    if fps != "source":
        args += ["-r", fps]
    _append_audio_handling_args(args, fmt="aac" if fmt != "webm" else "opus", bitrate=audio_br, sample_rate=audio_sample_rate, audio_channels=audio_channels, playback_speed=playback_speed)
    preset.update({
        "audio_sample_rate": _normalise_sample_rate(audio_sample_rate) or "source",
        "audio_channels": _normalise_audio_channels(audio_channels),
        "playback_speed": _normalise_playback_speed(playback_speed),
        "video_fps": fps,
    })
    return args, preset


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


def plan_conversion(input_path: str | os.PathLike[str], target_format: str = "auto", *, output_dir: str | os.PathLike[str] | None = None, keep_original: bool = False, overwrite: bool = False, image_quality: int = 92, compress: bool = False, image_max_dimension: int = 0, image_webp_method: int = 4, image_png_compression_level: int = 9, image_jpeg_chroma_subsampling: str = "auto", video_crf: int = 23, video_max_dimension: int = 0, video_encoder: str = "auto", video_preset: str = "auto", video_fps: str = "source", web_optimise: bool = True, audio_bitrate: str = "", audio_sample_rate: str = "", audio_channels: str = "source", playback_speed: str = "1.0", cue_split_mode: str = "off", optimisation_preset: str = "Optimised", target_file_size_mb: object = "", preserve_metadata: bool = True, file_suffix: str = "") -> dict[str, Any]:
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
        ffmpeg = _ffmpeg_path()
        command = [ffmpeg, "-hide_banner", "-y", "-i", str(input_file)]
        if preserve_metadata:
            command += ["-map_metadata", "0"]
        if output_kind == "audio":
            command += ["-vn"]
            args, preset = _audio_codec(fmt, compress=bool(compress), audio_bitrate=audio_bitrate, audio_sample_rate=audio_sample_rate, audio_channels=audio_channels, playback_speed=playback_speed, cue_split_mode=cue_split_mode)
            command += args
        elif output_kind == "video":
            needs_video_transcode = bool(compress) or bool(_target_size_mb_to_float(target_file_size_mb)) or _normalise_video_encoder(video_encoder, fmt) != "auto" or _normalise_video_fps(video_fps) != "source" or _normalise_sample_rate(audio_sample_rate) or _normalise_audio_channels(audio_channels) != "source" or _normalise_playback_speed(playback_speed) not in {"1", "1.0"}
            if input_kind == "video" and not needs_video_transcode:
                # R42ET: normal Convert is mainly remux/copy.  Compression (C),
                # target-size limits, or explicit handling controls trigger a
                # re-encode; otherwise keep original video/audio streams.
                args = ["-c", "copy"]
                if fmt in {"mp4", "mov"} and bool(web_optimise):
                    args += ["-movflags", "+faststart"]
                preset = {"family": "video", "codec_args": args, "compress": False, "optimisation_preset": str(optimisation_preset or "Optimised"), "optimisation_mode": "remux_copy", "stream_copy": True, "selection_reason": "normal conversion prefers remux/copy; C compression or target-size mode triggers transcoding"}
            else:
                args, preset = _video_codecs(fmt, source_path=input_file, compress=bool(compress), video_crf=video_crf, video_max_dimension=video_max_dimension, audio_bitrate=audio_bitrate, audio_sample_rate=audio_sample_rate, audio_channels=audio_channels, playback_speed=playback_speed, video_encoder=video_encoder, video_preset=video_preset, video_fps=video_fps, web_optimise=web_optimise, optimisation_preset=optimisation_preset, target_file_size_mb=target_file_size_mb)
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



# R42FB: no-network cross-capability profile and local efficiency estimator.
def _windows_cim_json(class_name: str, properties: tuple[str, ...], *, timeout: int = 8) -> list[dict[str, Any]]:
    """Read Windows CIM data without adding a dependency.

    The function is best-effort.  It never performs network activity and returns
    an empty list if PowerShell/CIM is unavailable.
    """
    if os.name != "nt":
        return []
    props = ",".join(properties)
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        f"Get-CimInstance {class_name} | Select-Object {props} | ConvertTo-Json -Compress -Depth 3",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    except Exception:
        return []
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return []
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return []
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _memory_total_bytes() -> int:
    try:
        import psutil  # type: ignore
        return int(psutil.virtual_memory().total)
    except Exception:
        pass
    if os.name == "nt":
        rows = _windows_cim_json("Win32_ComputerSystem", ("TotalPhysicalMemory",), timeout=6)
        for row in rows:
            try:
                return int(row.get("TotalPhysicalMemory") or 0)
            except Exception:
                pass
    return 0


def _system_resource_profile() -> dict[str, Any]:
    import platform
    import sys
    memory = _memory_total_bytes()
    gpus: list[dict[str, Any]] = []
    for row in _windows_cim_json("Win32_VideoController", ("Name", "AdapterRAM", "DriverVersion", "VideoProcessor"), timeout=8):
        ram = 0
        try:
            ram = int(row.get("AdapterRAM") or 0)
        except Exception:
            ram = 0
        gpus.append({
            "name": str(row.get("Name") or ""),
            "adapter_ram_bytes": ram,
            "adapter_ram_gb": round(ram / (1024 ** 3), 2) if ram else 0,
            "driver_version": str(row.get("DriverVersion") or ""),
            "video_processor": str(row.get("VideoProcessor") or ""),
        })
    return {
        "schema": R42EH_SCHEMA + ".system_resource_profile",
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count() or 0,
        "processor": platform.processor(),
        "memory_total_bytes": memory,
        "memory_total_gb": round(memory / (1024 ** 3), 2) if memory else 0,
        "gpus": gpus,
        "side_effects": {"network_actions_performed": False, "archive_ph_hit": False, "native_webview2_started": False, "app_started": False},
    }


def _ffmpeg_version_line() -> str:
    ffmpeg = _ffmpeg_path()
    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-version"], capture_output=True, text=True, timeout=8, encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"unavailable: {exc}"
    first = (proc.stdout or proc.stderr or "").splitlines()
    return first[0] if first else ""


def _encoder_family_for_impl(encoder: str) -> str:
    e = str(encoder or "").lower()
    if "265" in e or "hevc" in e:
        return "h265"
    if "vp9" in e:
        return "vp9"
    if "av1" in e or e in {"libsvtav1", "libsvt_av1", "libaom-av1", "librav1e"}:
        return "av1"
    return "h264"


def _default_encoder_probe_order(include_slow: bool = True) -> list[str]:
    order = [
        "h264_amf", "hevc_amf", "av1_amf",
        "h264_mf", "hevc_mf", "av1_mf",
        "h264_nvenc", "hevc_nvenc", "av1_nvenc",
        "h264_qsv", "hevc_qsv", "av1_qsv",
        "h264_vulkan", "hevc_vulkan", "av1_vulkan",
        "libx264", "libx265", "libvpx-vp9", "libsvtav1", "libsvt_av1",
    ]
    if include_slow:
        order += ["libaom-av1", "librav1e"]
    return order


def _benchmark_single_encoder(encoder: str, *, timeout: int = 25, duration_seconds: float = 3.0, width: int = 1280, height: int = 720, fps: int = 30) -> dict[str, Any]:
    import tempfile
    import time
    ffmpeg = _ffmpeg_path()
    args, ext = _quick_encoder_test_args(encoder)
    with tempfile.TemporaryDirectory(prefix="ytce_r42fb_encoder_bench_") as tmp:
        out_path = Path(tmp) / f"bench_{encoder}{ext}"
        cmd = [
            ffmpeg, "-hide_banner", "-y",
            "-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate={fps}",
            "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000",
            "-t", str(duration_seconds),
            *args,
            "-c:a", "aac", "-b:a", "96k",
            str(out_path),
        ]
        start = time.perf_counter()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            elapsed = max(0.001, time.perf_counter() - start)
            ok = proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0
            size = out_path.stat().st_size if out_path.exists() else 0
            speed_multiple = round(duration_seconds / elapsed, 3)
            estimated_3min_1080p_seconds = round((180.0 / max(0.001, speed_multiple)) * 2.25, 1)
            return {
                "encoder": encoder,
                "family": _encoder_family_for_impl(encoder),
                "ok": bool(ok),
                "elapsed_seconds": round(elapsed, 3),
                "source_seconds": duration_seconds,
                "speed_multiple": speed_multiple,
                "output_bytes": int(size),
                "output_mib": round(size / (1024 ** 2), 4) if size else 0,
                "estimated_3min_1080p_seconds": estimated_3min_1080p_seconds,
                "command_encoder_impl": encoder,
                "stderr_tail": (proc.stderr or "")[-1200:],
            }
        except Exception as exc:
            return {"encoder": encoder, "family": _encoder_family_for_impl(encoder), "ok": False, "error": repr(exc)}


def build_converter_optimisation_capability_profile(*, benchmark: bool = False, timeout: int = 45, include_slow: bool = False) -> dict[str, Any]:
    """Build a no-network machine profile for Optimised conversion/compression.

    This is the production-facing capability layer R42FB adds.  It separates:
    - compiled FFmpeg support,
    - encoders that actually run on this PC,
    - rough throughput estimates, and
    - an Optimised recommendation that balances clarity, size, and time.
    """
    encoders = _available_ffmpeg_encoders()
    runnable_probe = _probe_runnable_video_encoders(encoders, timeout=max(3, min(12, int(timeout))), include_slow=include_slow)
    runnable = set(runnable_probe.get("runnable_encoders") or [])
    capability = _system_capability_probe(encoders, runnable)
    benchmarks: list[dict[str, Any]] = []
    if benchmark:
        per_encoder_timeout = max(8, min(30, int(timeout)))
        for encoder in _default_encoder_probe_order(include_slow=include_slow):
            if encoder not in runnable:
                continue
            # Keep the default audit bounded.  Slow AV1 software can be tested by
            # enabling include_slow, but Optimised must not silently choose an
            # absurdly slow path.
            if encoder in {"libaom-av1", "librav1e"} and not include_slow:
                continue
            benchmarks.append(_benchmark_single_encoder(encoder, timeout=per_encoder_timeout, duration_seconds=3.0, width=1280, height=720, fps=30))

    def _rank(item: dict[str, Any]) -> float:
        if not item.get("ok"):
            return -9999.0
        family = str(item.get("family") or "h264")
        quality_size_score = {"av1": 4.0, "h265": 3.4, "vp9": 3.1, "h264": 2.4}.get(family, 2.0)
        speed = float(item.get("speed_multiple") or 0.0)
        runtime = float(item.get("estimated_3min_1080p_seconds") or 9999.0)
        runtime_penalty = 0.0 if runtime <= 360 else min(4.0, (runtime - 360) / 180.0)
        return round(quality_size_score + min(3.0, speed / 2.0) - runtime_penalty, 4)

    ranked = sorted((dict(item, optimisation_score=_rank(item)) for item in benchmarks if item.get("ok")), key=lambda x: x.get("optimisation_score", -9999), reverse=True)
    fastest = sorted((item for item in benchmarks if item.get("ok")), key=lambda x: float(x.get("elapsed_seconds") or 9999))
    default_encoder = ""
    default_reason = ""
    if ranked:
        default_encoder = str(ranked[0].get("encoder") or "")
        default_reason = "benchmark-balanced winner: quality/size proxy plus practical runtime"
    elif runnable:
        default_encoder = _choose_existing_encoder(runnable, ("hevc_amf", "h264_amf", "h264_mf", "hevc_mf", "libx264", "libx265", "libvpx-vp9", "libsvtav1", "libsvt_av1"), "libx264")
        default_reason = "runnable probe available but benchmark disabled/empty; chose safe runnable fallback"
    elif encoders:
        default_encoder = _choose_existing_encoder(encoders, ("libx264", "h264", "h264_mf", "h264_amf"), "libx264")
        default_reason = "compiled encoders only; runnable probe found nothing, so use conservative fallback"
    else:
        default_reason = "no FFmpeg encoders detected"

    return {
        "schema": R42EH_SCHEMA + ".optimisation_capability_profile.r42fb",
        "mode": "NO_NETWORK_LOCAL_CAPABILITY_AND_OPTIONAL_SYNTHETIC_BENCHMARK",
        "system": _system_resource_profile(),
        "ffmpeg": {
            "path": _ffmpeg_path(),
            "ffprobe_path": _ffprobe_path(),
            "version": _ffmpeg_version_line(),
            "compiled_encoder_count": len(encoders),
            "compiled_relevant_encoders": sorted(name for name in encoders if name in set(_default_encoder_probe_order(True))),
        },
        "runnable_probe": runnable_probe,
        "capability": capability,
        "benchmarks": benchmarks,
        "recommendation": {
            "optimised_default_encoder_impl": default_encoder,
            "reason": default_reason,
            "ranked_benchmark_choices": ranked[:8],
            "fastest_benchmark_choices": fastest[:5],
            "runtime_rule": "Optimised may spend more time only while estimated runtime remains practical; Speed uses the quickest readable route.",
        },
        "side_effects": {"network_actions_performed": False, "archive_ph_hit": False, "native_webview2_started": False, "app_started": False},
    }

def probe_environment() -> dict[str, Any]:
    return {
        "schema": R42EH_SCHEMA + ".environment",
        "ffmpeg_path": _ffmpeg_path(),
        "ffprobe_path": _ffprobe_path(),
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
        "optimisation_preset_options": ["Optimised", "Speed"],
        "capability_profile_function": "build_converter_optimisation_capability_profile",
        "side_effects": {"network_actions_performed": False, "archive_ph_hit": False, "native_webview2_started": False, "app_started": False},
    }
