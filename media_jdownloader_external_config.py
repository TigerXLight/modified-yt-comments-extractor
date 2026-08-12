from __future__ import annotations

import json
import os
import zipfile
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


JD_YOUTUBE_CONFIG_MAIN = "cfg/plugins/youtube/Youtube.json"
JD_FFMPEG_SETUP_CONFIG = "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.json"
JD_MUX_TO_MP4_CONFIG = "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.muxtomp4command.json"
JD_MUX_TO_MKV_CONFIG = "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.muxtomkvcommand.json"
JD_DASH_TO_M4A_CONFIG = "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.dash2m4acommand.json"
JD_DASH_TO_OPUS_CONFIG = "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.dash2opusaudiocommand.json"
JD_DEMUX_TO_M4A_CONFIG = "cfg/org.jdownloader.controlling.ffmpeg.FFmpegSetup.demux2m4acommand.json"
JD_EXTRACTION_EXTENSION_CONFIG = "cfg/org.jdownloader.extensions.extraction.ExtractionExtension.json"


@dataclass(frozen=True)
class JDownloaderExternalConfigReport:
    """Clean-room importer for user-supplied JDownloader configuration.

    This object uses JDownloader as an external reference/config source only. It
    does not copy or decompile JDownloader Java implementation code.
    """

    source_path: str
    source_kind: str
    youtube_main_config_path: str = ""
    youtube_main_config: Mapping[str, Any] = field(default_factory=dict)
    youtube_config_files: tuple[str, ...] = ()
    ffmpeg_binary_path: str = ""
    ffprobe_binary_path: str = ""
    mux_to_mp4_command_template: tuple[str, ...] = ()
    mux_to_mkv_command_template: tuple[str, ...] = ()
    dash_to_m4a_command_template: tuple[str, ...] = ()
    dash_to_opus_command_template: tuple[str, ...] = ()
    demux_to_m4a_command_template: tuple[str, ...] = ()
    extraction_extension_config: Mapping[str, Any] = field(default_factory=dict)
    extraction_extension_enabled: bool = False
    plugin_class_count: int = 0
    youtube_plugin_class_count: int = 0
    captcha_method_count: int = 0
    libs_count: int = 0
    ffmpeg_license_files: tuple[str, ...] = ()
    root_license_present: bool = False
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

    @property
    def max_video_resolution(self) -> str:
        return str(self.youtube_main_config.get("maxvideoresolution") or "")

    @property
    def dash_muxing_enabled(self) -> bool:
        return bool(self.youtube_main_config.get("dashmuxingenabled", False))

    @property
    def segment_loading_enabled(self) -> bool:
        return bool(self.youtube_main_config.get("segmentloadingenabled", False))

    @property
    def metadata_enabled(self) -> bool:
        return bool(self.youtube_main_config.get("metadataenabled", False))

    @property
    def image_filename_pattern(self) -> str:
        return str(self.youtube_main_config.get("imagefilenamepattern") or "")

    @property
    def video_filename_pattern(self) -> str:
        return str(self.youtube_main_config.get("videofilenamepattern2") or "")

    @property
    def audio_filename_pattern(self) -> str:
        return str(self.youtube_main_config.get("audiofilenamepattern2") or "")

    @property
    def subtitle_filename_pattern(self) -> str:
        return str(self.youtube_main_config.get("subtitlefilenamepattern2") or "")


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


def _candidate_is_jdownloader_source(path: Path) -> bool:
    return bool((path.is_file() and path.suffix.lower() == ".zip") or path.is_dir())


def _expanded_path_from_cli(value: str | Path) -> Path:
    text = str(value or "").strip().strip('"').strip("'")
    return Path(os.path.expandvars(os.path.expanduser(text)))


def _looks_like_placeholder_path(value: str | Path) -> bool:
    text = str(value or "").strip().strip('"').strip("'")
    upper = text.upper()
    return bool(
        not text
        or "PASTE_REAL_JDOWNLOADER_ZIP_PATH_HERE" in upper
        or "PASTE_REAL" in upper
        or "<REAL" in upper
        or "<PASTE" in upper
    )


def candidate_jdownloader_source_paths(source: str | Path = "") -> tuple[Path, ...]:
    """Return likely local JDownloader source locations.

    The CLI often receives Windows paths with environment variables, a ZIP name
    copied from chat, or the local AppData installation layout.  This helper
    checks explicit paths first, then known AppData ZIP/folder locations.
    """
    candidates: list[Path] = []
    text = str(source or "").strip().strip('"').strip("'")
    if text and not _looks_like_placeholder_path(text):
        expanded = _expanded_path_from_cli(text)
        candidates.append(expanded)
        name = expanded.name
        if name:
            home_downloads = Path.home() / "Downloads"
            candidates.append(home_downloads / name)
            userprofile = os.environ.get("USERPROFILE")
            if userprofile:
                candidates.append(Path(userprofile) / "Downloads" / name)

    local = os.environ.get("LOCALAPPDATA")
    if local:
        local_root = Path(local)
        candidates.append(local_root / "JDownloader 2" / "JDownloader 2.zip")
        candidates.append(local_root / "JDownloader 2.0" / "JDownloader 2.0.zip")
        candidates.append(local_root / "JDownloader 2")
        candidates.append(local_root / "JDownloader 2.0")

    for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.environ.get(env_name)
        if root:
            candidates.append(Path(root) / "JDownloader 2")
            candidates.append(Path(root) / "JDownloader 2.0")

    for base in (Path.home() / "Downloads", Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Downloads"):
        candidates.append(base / "JDownloader 2.zip")
        candidates.append(base / "JDownloader 2.0.zip")
        if base.is_dir():
            try:
                candidates.extend(sorted(base.glob("JDownloader*.zip")))
            except OSError:
                pass

    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            deduped.append(candidate)
    return tuple(deduped)


def resolve_jdownloader_source_path(source: str | Path = "") -> Path:
    if str(source or "").strip() and _looks_like_placeholder_path(source):
        raise FileNotFoundError(
            "JDownloader source path is still a placeholder. Pass the real local ZIP/folder path, for example:\n"
            r'"C:\Users\fahad\AppData\Local\JDownloader 2\JDownloader 2.zip"' "\n"
            r'"C:\Users\fahad\AppData\Local\JDownloader 2.0\JDownloader 2.0.zip"'
        )
    checked = candidate_jdownloader_source_paths(source)
    for candidate in checked:
        if _candidate_is_jdownloader_source(candidate):
            return candidate
    checked_text = "\n".join(f"- {path}" for path in checked) or "- <no candidates>"
    raise FileNotFoundError(
        "JDownloader path is not an existing ZIP file or directory.\n"
        f"Requested: {source}\n"
        "Checked candidates:\n"
        f"{checked_text}\n"
        "Run these in CMD to check the expected local ZIPs:\n"
        r'dir /b "%LOCALAPPDATA%\JDownloader 2\JDownloader 2.zip"' "\n"
        r'dir /b "%LOCALAPPDATA%\JDownloader 2.0\JDownloader 2.0.zip"'
    )


def _normalize_zip_name(name: str) -> str:
    return str(name).replace("\\", "/").lstrip("./")


class _JDownloaderConfigReader:
    def __init__(self, source: str | Path) -> None:
        self.requested_source = str(source)
        self.source = resolve_jdownloader_source_path(source)
        self.warnings: list[str] = []
        if self.source.is_file() and self.source.suffix.lower() == ".zip":
            self.kind = "zip"
            self._zip = zipfile.ZipFile(self.source)
            self._names = tuple(_normalize_zip_name(name) for name in self._zip.namelist())
            self._name_map = {_normalize_zip_name(name): name for name in self._zip.namelist()}
        elif self.source.is_dir():
            self.kind = "directory"
            self._zip = None
            self._names = tuple(
                str(path.relative_to(self.source)).replace("\\", "/")
                for path in self.source.rglob("*")
                if path.is_file()
            )
            self._name_map = {name: name for name in self._names}
        else:
            raise FileNotFoundError(f"JDownloader path is not a ZIP file or directory: {self.source}")

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def names(self) -> tuple[str, ...]:
        return self._names

    def exists(self, relative_path: str) -> bool:
        return _normalize_zip_name(relative_path) in self._name_map

    def read_text(self, relative_path: str) -> str | None:
        name = _normalize_zip_name(relative_path)
        if name not in self._name_map:
            self.warnings.append(f"Missing JDownloader config path: {relative_path}")
            return None
        if self._zip is not None:
            with self._zip.open(self._name_map[name]) as fh:
                return fh.read().decode("utf-8", "replace")
        return (self.source / self._name_map[name]).read_text(encoding="utf-8", errors="replace")

    def read_json(self, relative_path: str) -> Any:
        text = self.read_text(relative_path)
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            self.warnings.append(f"Invalid JSON in {relative_path}: {exc}")
            return None


def _tuple_from_json_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def load_jdownloader_external_config(source: str | Path) -> JDownloaderExternalConfigReport:
    reader = _JDownloaderConfigReader(source)
    try:
        names = reader.names()
        youtube_main = reader.read_json(JD_YOUTUBE_CONFIG_MAIN)
        if not isinstance(youtube_main, Mapping):
            youtube_main = {}
        ffmpeg_setup = reader.read_json(JD_FFMPEG_SETUP_CONFIG)
        if not isinstance(ffmpeg_setup, Mapping):
            ffmpeg_setup = {}
        extraction = reader.read_json(JD_EXTRACTION_EXTENSION_CONFIG)
        if not isinstance(extraction, Mapping):
            extraction = {}
        youtube_config_files = tuple(
            sorted(name for name in names if name.startswith("cfg/plugins/youtube/") and name.endswith(".json"))
        )
        ffmpeg_license_files = tuple(
            sorted(name for name in names if name.startswith("tools/Windows/ffmpeg/licenses/") and name.lower().endswith(".txt"))
        )
        report = JDownloaderExternalConfigReport(
            source_path=str(reader.source),
            source_kind=reader.kind,
            youtube_main_config_path=JD_YOUTUBE_CONFIG_MAIN if reader.exists(JD_YOUTUBE_CONFIG_MAIN) else "",
            youtube_main_config=dict(youtube_main),
            youtube_config_files=youtube_config_files,
            ffmpeg_binary_path=str(ffmpeg_setup.get("binarypath") or ""),
            ffprobe_binary_path=str(ffmpeg_setup.get("binarypathprobe") or ""),
            mux_to_mp4_command_template=_tuple_from_json_list(reader.read_json(JD_MUX_TO_MP4_CONFIG)),
            mux_to_mkv_command_template=_tuple_from_json_list(reader.read_json(JD_MUX_TO_MKV_CONFIG)),
            dash_to_m4a_command_template=_tuple_from_json_list(reader.read_json(JD_DASH_TO_M4A_CONFIG)),
            dash_to_opus_command_template=_tuple_from_json_list(reader.read_json(JD_DASH_TO_OPUS_CONFIG)),
            demux_to_m4a_command_template=_tuple_from_json_list(reader.read_json(JD_DEMUX_TO_M4A_CONFIG)),
            extraction_extension_config=dict(extraction),
            extraction_extension_enabled=bool(extraction.get("enabled", False)),
            plugin_class_count=sum(1 for name in names if name.startswith("jd/plugins/") and name.endswith(".class")),
            youtube_plugin_class_count=sum(1 for name in names if "youtube" in name.lower() and name.endswith(".class")),
            captcha_method_count=sum(1 for name in names if name.startswith("jd/captcha/methods/") and name.endswith(".class")),
            libs_count=sum(1 for name in names if name.startswith("libs/") and not name.endswith("/")),
            ffmpeg_license_files=ffmpeg_license_files,
            root_license_present=reader.exists("license.txt"),
            warnings=tuple(reader.warnings),
        )
        return report
    finally:
        reader.close()


def write_jdownloader_external_config_report(
    source: str | Path,
    output_path: str | Path,
) -> JDownloaderExternalConfigReport:
    report = load_jdownloader_external_config(source)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def jdownloader_resolution_to_height(value: str, default: int = 4320) -> int:
    text = str(value or "").upper().strip()
    if text.startswith("P_"):
        text = text[2:]
    try:
        height = int(text)
    except ValueError:
        return default
    return max(0, height)
