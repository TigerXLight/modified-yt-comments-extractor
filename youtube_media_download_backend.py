from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from media_jdownloader_external_config import (
    JDownloaderExternalConfigReport,
    jdownloader_resolution_to_height,
)

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class ExternalCommandResolution:
    requested: str
    command: tuple[str, ...]
    source: str

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _is_sequence_command(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, Path))


def _command_prefix(value: str | Path | Sequence[str]) -> tuple[str, ...]:
    if _is_sequence_command(value):
        return tuple(str(item) for item in value if str(item))
    text = str(value or "").strip()
    return (text or "yt-dlp",)


def resolve_ytdlp_command(
    requested: str | Path | Sequence[str] = "auto",
    *,
    repo_root: str | Path | None = None,
    python_executable: str | Path | None = None,
) -> ExternalCommandResolution:
    """Resolve yt-dlp to an executable command tuple.

    This avoids raw ``FileNotFoundError`` during real downloads.  It supports:
    - an explicit yt-dlp executable path
    - a command on PATH
    - ``venv\\Scripts\\yt-dlp.exe`` under the repo
    - ``python -m yt_dlp`` when the module is installed in the active venv
    """

    if _is_sequence_command(requested):
        command = tuple(str(item) for item in requested if str(item))
        if not command:
            raise FileNotFoundError("Empty yt-dlp command.")
        first = command[0]
        if Path(first).is_file() or shutil.which(first):
            return ExternalCommandResolution(requested=" ".join(command), command=command, source="explicit-sequence")
        raise FileNotFoundError(
            "yt-dlp command was not found: "
            + " ".join(command)
            + ". Install it with: venv\\Scripts\\python.exe -m pip install -U yt-dlp"
        )

    requested_text = str(requested or "auto").strip().strip('"').strip("'")
    candidates: list[tuple[str, tuple[str, ...]]] = []

    if requested_text and requested_text.lower() not in {"auto", "yt-dlp"}:
        candidates.append(("explicit", (requested_text,)))

    candidates.append(("path", ("yt-dlp",)))

    roots: list[Path] = []
    if repo_root:
        roots.append(Path(repo_root))
    roots.append(Path.cwd())
    for root in roots:
        candidates.extend(
            (
                ("repo-venv", (str(root / "venv" / "Scripts" / "yt-dlp.exe"),)),
                ("repo-dotvenv", (str(root / ".venv" / "Scripts" / "yt-dlp.exe"),)),
            )
        )

    for source, command in candidates:
        first = command[0]
        if Path(first).is_file():
            return ExternalCommandResolution(requested=requested_text, command=command, source=source)
        found = shutil.which(first)
        if found:
            return ExternalCommandResolution(requested=requested_text, command=(found,), source=source)

    py = str(python_executable or sys.executable)
    if importlib.util.find_spec("yt_dlp") is not None:
        return ExternalCommandResolution(requested=requested_text, command=(py, "-m", "yt_dlp"), source="python-module")

    raise FileNotFoundError(
        "yt-dlp was not found. Install it into this repo venv with: "
        "venv\\Scripts\\python.exe -m pip install -U yt-dlp "
        "or pass --yt-dlp C:\\path\\to\\yt-dlp.exe"
    )


@dataclass(frozen=True)
class YouTubeMediaFormat:
    format_id: str
    ext: str = ""
    vcodec: str = ""
    acodec: str = ""
    height: int | None = None
    width: int | None = None
    fps: float | None = None
    abr: float | None = None
    tbr: float | None = None
    filesize: int | None = None
    filesize_approx: int | None = None
    protocol: str = ""
    url_present: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class YouTubeMediaDiscovery:
    source_url: str
    title: str = ""
    uploader: str = ""
    channel: str = ""
    channel_follower_count: int | None = None
    upload_date: str = ""
    view_count: int | None = None
    description: str = ""
    duration: float | None = None
    thumbnail: str = ""
    webpage_url: str = ""
    formats: tuple[YouTubeMediaFormat, ...] = ()
    subtitles: Mapping[str, Any] = field(default_factory=dict)
    automatic_captions: Mapping[str, Any] = field(default_factory=dict)
    raw_info_json_path: str = ""
    yt_dlp_command: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class YouTubeMediaDownloadPlan:
    source_url: str
    output_dir: str
    format_selector: str
    merge_output_format: str
    output_template: str
    command: tuple[str, ...]
    ffmpeg_location: str = ""
    write_info_json: bool = True
    write_thumbnail: bool = True
    write_subtitles: bool = True
    write_auto_subtitles: bool = False
    extract_audio: bool = False
    audio_format: str = "m4a"
    dry_run: bool = True
    jdownloader_max_resolution: str = ""
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def normalize_media_source_url_arg(value: str | Path) -> str:
    """Return a raw http(s) URL from CLI/chat/Markdown input.

    This intentionally handles messy command-paste cases, including nested
    Markdown links copied back out of chat logs.  It extracts all visible URLs
    after neutralizing Markdown brackets and returns the last one, because the
    href part of [label](href) is the authoritative URL.
    """
    text = str(value or "").strip()
    if not text:
        return ""

    while len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        text = text[1:-1].strip()

    unescaped = _normalize_chat_url_escapes(text)
    # Turn Markdown syntax into separators.  This converts both normal and
    # nested/broken links into a plain stream of candidate URLs.
    separators = unescaped
    for token in ("](", "[", "]", "(", ")", "<", ">"):
        separators = separators.replace(token, " ")

    candidates = [_clean_url_candidate(item) for item in re.findall(r"https?://[^\s\"']+", separators)]
    candidates = [item for item in candidates if item.lower().startswith(("http://", "https://"))]
    if candidates:
        return candidates[-1]

    return _clean_url_candidate(unescaped)


def normalize_media_source_url_arg_strict(value: str | Path) -> str:
    """Normalize a media source URL and fail on unsupported wrappers."""
    normalized = normalize_media_source_url_arg(value)
    if not normalized:
        raise ValueError("Empty media source URL.")
    if not normalized.lower().startswith(("http://", "https://")):
        raise ValueError(f"Media source URL must be a raw http(s) URL: {normalized}")
    if any(marker in normalized for marker in ("[", "]", "](", "\\(" , "\\)")):
        raise ValueError(f"Media source URL was not normalized to a raw URL: {normalized}")
    return normalized


def _clean_url_candidate(value: str) -> str:
    text = _normalize_chat_url_escapes(value).strip().strip('"').strip("'").strip()
    # Strip punctuation that usually belongs to Markdown/prose, not to the URL.
    while text and text[-1] in ").,;:\\":
        text = text[:-1].strip()
    while text and text[0] in "([<":
        text = text[1:].strip()
    return text

def _normalize_chat_url_escapes(value: str) -> str:
    # Chat/Markdown escaping can insert backslashes before underscores and other
    # URL-safe punctuation. Keep this conservative; do not percent-decode.
    text = str(value or "").strip()
    for ch in ("_", "-", ".", "~", "(", ")"):
        text = text.replace("\\" + ch, ch)
    return text


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _default_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"External command not found: {command[0] if command else '<empty>'}. "
            "Install yt-dlp with: venv\\Scripts\\python.exe -m pip install -U yt-dlp"
        ) from exc


def _format_from_dict(data: Mapping[str, Any]) -> YouTubeMediaFormat:
    def int_or_none(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def float_or_none(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return YouTubeMediaFormat(
        format_id=str(data.get("format_id") or ""),
        ext=str(data.get("ext") or ""),
        vcodec=str(data.get("vcodec") or ""),
        acodec=str(data.get("acodec") or ""),
        height=int_or_none(data.get("height")),
        width=int_or_none(data.get("width")),
        fps=float_or_none(data.get("fps")),
        abr=float_or_none(data.get("abr")),
        tbr=float_or_none(data.get("tbr")),
        filesize=int_or_none(data.get("filesize")),
        filesize_approx=int_or_none(data.get("filesize_approx")),
        protocol=str(data.get("protocol") or ""),
        url_present=bool(data.get("url")),
    )


def discover_youtube_media_with_ytdlp(
    source_url: str,
    *,
    yt_dlp_path: str | Path | Sequence[str] = "yt-dlp",
    output_dir: str | Path | None = None,
    runner: Runner | None = None,
) -> YouTubeMediaDiscovery:
    normalized_source_url = normalize_media_source_url_arg_strict(source_url)
    command = _command_prefix(yt_dlp_path) + (
        "--dump-single-json",
        "--skip-download",
        "--no-warnings",
        normalized_source_url,
    )
    run = runner or _default_runner
    completed = run(command)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "yt-dlp discovery failed").strip())
    data = json.loads(completed.stdout or "{}")

    def int_or_none(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    raw_path = ""
    if output_dir is not None:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        raw = target_dir / "youtube-media-discovery.raw-info.json"
        raw.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        raw_path = str(raw)
    formats = tuple(_format_from_dict(item) for item in data.get("formats") or () if isinstance(item, Mapping))
    return YouTubeMediaDiscovery(
        source_url=normalized_source_url,
        title=str(data.get("title") or ""),
        uploader=str(data.get("uploader") or data.get("channel") or ""),
        channel=str(data.get("channel") or data.get("uploader") or ""),
        channel_follower_count=int_or_none(data.get("channel_follower_count") or data.get("uploader_subscriber_count")),
        upload_date=str(data.get("upload_date") or data.get("release_date") or ""),
        view_count=int_or_none(data.get("view_count")),
        description=str(data.get("description") or ""),
        duration=data.get("duration") if isinstance(data.get("duration"), (int, float)) else None,
        thumbnail=str(data.get("thumbnail") or ""),
        webpage_url=str(data.get("webpage_url") or normalized_source_url),
        formats=formats,
        subtitles=data.get("subtitles") if isinstance(data.get("subtitles"), Mapping) else {},
        automatic_captions=data.get("automatic_captions") if isinstance(data.get("automatic_captions"), Mapping) else {},
        raw_info_json_path=raw_path,
        yt_dlp_command=command,
    )


def youtube_format_selector_from_jdownloader(
    config: JDownloaderExternalConfigReport | None = None,
    *,
    max_height: int | None = None,
) -> str:
    if max_height is None:
        max_height = jdownloader_resolution_to_height(config.max_video_resolution if config else "", default=4320)
    max_height = max(0, int(max_height or 0))
    height_filter = f"[height<={max_height}]" if max_height else ""
    return f"bestvideo{height_filter}+bestaudio/best{height_filter}/best"


def build_youtube_ytdlp_download_plan(
    source_url: str,
    *,
    output_dir: str | Path,
    yt_dlp_path: str | Path | Sequence[str] = "yt-dlp",
    ffmpeg_location: str | Path = "",
    jdownloader_config: JDownloaderExternalConfigReport | None = None,
    merge_output_format: str = "mp4",
    format_selector: str = "",
    write_info_json: bool = True,
    write_thumbnail: bool = True,
    write_subtitles: bool = True,
    write_auto_subtitles: bool = False,
    extract_audio: bool = False,
    audio_format: str = "m4a",
    dry_run: bool = True,
) -> YouTubeMediaDownloadPlan:
    normalized_source_url = normalize_media_source_url_arg_strict(source_url)
    target_dir = Path(output_dir)
    output_template = str(target_dir / "%(title).200B [%(id)s].%(ext)s")
    selector = format_selector or youtube_format_selector_from_jdownloader(jdownloader_config)
    command: list[str] = [
        *_command_prefix(yt_dlp_path),
        "--no-playlist",
        "--newline",
        "-f",
        selector,
        "-o",
        output_template,
    ]
    if write_info_json:
        command.append("--write-info-json")
    if write_thumbnail:
        command.append("--write-thumbnail")
    if write_subtitles:
        command.extend(("--write-subs", "--sub-langs", "all,-live_chat"))
    if write_auto_subtitles:
        command.append("--write-auto-subs")
    if extract_audio:
        command.extend(("-x", "--audio-format", str(audio_format or "m4a")))
    else:
        command.extend(("--merge-output-format", str(merge_output_format or "mp4")))
    if ffmpeg_location:
        command.extend(("--ffmpeg-location", str(ffmpeg_location)))
    if dry_run:
        command.append("--simulate")
    command.append(normalized_source_url)
    notes = [
        "yt-dlp is used as the external media backend; FFmpeg handles muxing through yt-dlp when needed.",
        "Downloads require explicit user selection/execution; dry_run=True adds --simulate.",
    ]
    if jdownloader_config is not None:
        notes.append("JDownloader YouTube config imported for max resolution / muxing preference mapping.")
    return YouTubeMediaDownloadPlan(
        source_url=normalized_source_url,
        output_dir=str(target_dir),
        format_selector=selector,
        merge_output_format=str(merge_output_format or "mp4"),
        output_template=output_template,
        command=tuple(command),
        ffmpeg_location=str(ffmpeg_location or ""),
        write_thumbnail=write_thumbnail,
        write_subtitles=write_subtitles,
        write_auto_subtitles=write_auto_subtitles,
        extract_audio=extract_audio,
        audio_format=str(audio_format or "m4a"),
        dry_run=dry_run,
        jdownloader_max_resolution=(jdownloader_config.max_video_resolution if jdownloader_config else ""),
        notes=tuple(notes),
    )


def run_youtube_ytdlp_download_plan(
    plan: YouTubeMediaDownloadPlan,
    *,
    runner: Runner | None = None,
) -> subprocess.CompletedProcess[str]:
    run = runner or _default_runner
    Path(plan.output_dir).mkdir(parents=True, exist_ok=True)
    return run(plan.command)


def write_youtube_media_download_plan(plan: YouTubeMediaDownloadPlan, output_path: str | Path) -> None:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
