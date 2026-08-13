from __future__ import annotations

import json
import subprocess
import shutil
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from jdownloader_internal_paths import (
JD_BRIDGE_BUILD_DIR,
    JD_BRIDGE_SRC_DIR,
    JD_MANIFESTS_DIR,
    JD_REQUIRED_YOUTUBE_SOURCE_PATHS,
    JD_RUNTIME_DIR,
    JD_SOURCE_ARCHIVES_DIR,
    JDOWNLOADER_INTERNAL_BACKEND_ID,
    LOCAL_JD_INSTALLED_ROOT,
    YTDLP_FALLBACK_BACKEND_ID,
)


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
JDK21_JAVA_EXE = Path(r"C:\Program Files\Eclipse Adoptium\jdk-21.0.12.8-hotspot\bin\java.exe")


@dataclass(frozen=True)
class JDownloaderInternalCapabilities:
    backend_id: str = JDOWNLOADER_INTERNAL_BACKEND_ID
    vendor_present: bool = False
    runtime_present: bool = False
    source_present: bool = False
    youtube_plugin_source_present: bool = False
    youtube_plugin_runtime_present: bool = False
    remote_api_config_present: bool = False
    ffmpeg_present: bool = False
    primary_runtime_path: str = ""
    installed_external_jdownloader_path: str = str(LOCAL_JD_INSTALLED_ROOT)
    installed_external_is_bootstrap_source_only: bool = True
    ytdlp_fallback_backend_id: str = YTDLP_FALLBACK_BACKEND_ID
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class JDownloaderInternalProbeReport:
    status: str
    capabilities: JDownloaderInternalCapabilities
    manifest_path: str = ""
    bridge_command: tuple[str, ...] = ()
    bridge_stdout: str = ""
    bridge_stderr: str = ""
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class InternalYouTubeDownloadCommand:
    backend_id: str
    source_url: str
    output_dir: str
    package_name: str = ""
    max_height: int = 1080
    video: bool = True
    audio: bool = True
    image: bool = True
    description: bool = True
    manifest_path: str = ""
    command: tuple[str, ...] = ()
    start_runtime: bool = True
    submit_job: bool = True
    wait: bool = False
    timeout_seconds: int = 600
    dry_run: bool = True
    fallback_backend_id: str = YTDLP_FALLBACK_BACKEND_ID
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


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


def detect_jdownloader_internal_capabilities() -> JDownloaderInternalCapabilities:
    source_present = any((JD_SOURCE_ARCHIVES_DIR / name).is_file() for name in ("src.zip", "svn_browser.zip", "svn_utils.zip"))
    runtime_present = (JD_RUNTIME_DIR / "JDownloader.jar").is_file() or (JD_RUNTIME_DIR / "Core.jar").is_file()
    youtube_runtime = (JD_RUNTIME_DIR / "cfg" / "plugins" / "youtube" / "Youtube.json").is_file()
    remote_api = (JD_RUNTIME_DIR / "cfg" / "org.jdownloader.api.RemoteAPIConfig.json").is_file()
    ffmpeg = (JD_RUNTIME_DIR / "tools" / "Windows" / "ffmpeg" / "x64" / "ffmpeg.exe").is_file()
    warnings: list[str] = []
    if not source_present:
        warnings.append("Project-internal JDownloader source archives missing; run tools\\jdownloader\\BOOTSTRAP_JDOWNLOADER_VENDOR.cmd --source-only")
    if not runtime_present:
        warnings.append("Project-internal JDownloader runtime missing; run tools\\jdownloader\\BOOTSTRAP_JDOWNLOADER_VENDOR.cmd --source-and-runtime")
    return JDownloaderInternalCapabilities(
        vendor_present=JD_SOURCE_ARCHIVES_DIR.is_dir() or JD_RUNTIME_DIR.is_dir(),
        runtime_present=runtime_present,
        source_present=source_present,
        youtube_plugin_source_present=source_present,
        youtube_plugin_runtime_present=youtube_runtime,
        remote_api_config_present=remote_api,
        ffmpeg_present=ffmpeg,
        primary_runtime_path=str(JD_RUNTIME_DIR) if runtime_present else "",
        warnings=tuple(warnings),
    )


def preferred_youtube_media_backend() -> str:
    capabilities = detect_jdownloader_internal_capabilities()
    return JDOWNLOADER_INTERNAL_BACKEND_ID if capabilities.runtime_present else YTDLP_FALLBACK_BACKEND_ID


def build_internal_youtube_download_command(
    *,
    source_url: str,
    output_dir: str | Path,
    package_name: str = "",
    max_height: int = 1080,
    video: bool = True,
    audio: bool = True,
    image: bool = True,
    description: bool = True,
    manifest_path: str | Path = "",
    wait: bool = False,
    timeout_seconds: int = 600,
) -> InternalYouTubeDownloadCommand:
    out = Path(output_dir)
    manifest = Path(manifest_path) if manifest_path else out / "jdownloader-internal-download-manifest.json"
    java_exe = shutil.which("java") or (str(JDK21_JAVA_EXE) if JDK21_JAVA_EXE.is_file() else "java")
    command = (
        java_exe,
        "-cp",
        str(JD_BRIDGE_BUILD_DIR),
        "ytce.jdbridge.YtceJDownloaderEngine",
        "--url",
        source_url,
        "--output-dir",
        str(out),
        "--package-name",
        package_name or "YTCE YouTube media",
        "--max-height",
        str(int(max_height or 0)),
        "--manifest",
        str(manifest),
        "--start-runtime",
        "--submit-job",
        "--timeout-seconds",
        str(int(timeout_seconds or 0)),
    )
    flags: list[str] = []
    if video:
        flags.append("--video")
    if audio:
        flags.append("--audio")
    if image:
        flags.append("--image")
    if description:
        flags.append("--description")
    if wait:
        flags.append("--wait")
    return InternalYouTubeDownloadCommand(
        backend_id=JDOWNLOADER_INTERNAL_BACKEND_ID,
        source_url=source_url,
        output_dir=str(out),
        package_name=package_name or "YTCE YouTube media",
        max_height=int(max_height or 0),
        video=video,
        audio=audio,
        image=image,
        description=description,
        manifest_path=str(manifest),
        command=command + tuple(flags),
        start_runtime=True,
        submit_job=True,
        wait=bool(wait),
        timeout_seconds=int(timeout_seconds or 0),
        dry_run=True,
    )


def _default_bridge_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _bridge_class_exists() -> bool:
    return (JD_BRIDGE_BUILD_DIR / "ytce" / "jdbridge" / "YtceJDownloaderEngine.class").is_file()


def _java_exists() -> bool:
    return bool(shutil.which("java") or JDK21_JAVA_EXE.is_file())


def run_internal_jdownloader_probe(*, runner: Runner | None = None, write_report: str | Path = "") -> JDownloaderInternalProbeReport:
    capabilities = detect_jdownloader_internal_capabilities()
    manifest_path = Path(write_report) if write_report else JD_MANIFESTS_DIR / "jdownloader_internal_probe_report.json"
    command = (
        shutil.which("java") or (str(JDK21_JAVA_EXE) if JDK21_JAVA_EXE.is_file() else "java"),
        "-cp",
        str(JD_BRIDGE_BUILD_DIR),
        "ytce.jdbridge.YtceJDownloaderEngine",
        "--probe-only",
        "--manifest",
        str(manifest_path),
    )
    stdout = ""
    stderr = ""
    warnings = list(capabilities.warnings)
    status = "PROBE_BRIDGE_NOT_BUILT"
    active_runner = runner
    if active_runner is None:
        if _bridge_class_exists() and _java_exists():
            active_runner = _default_bridge_runner
        else:
            if not _bridge_class_exists():
                warnings.append("JDownloader bridge class is not built; run tools\\jdownloader\\BUILD_INTERNAL_JDOWNLOADER_RUNTIME.cmd")
            if not _java_exists():
                warnings.append("java was not found on PATH")
    if active_runner is not None:
        completed = active_runner(command)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        status = "PROBE_COMPLETED" if completed.returncode == 0 else "PROBE_FAILED"
    report = JDownloaderInternalProbeReport(
        status=status,
        capabilities=capabilities,
        manifest_path=str(manifest_path),
        bridge_command=command,
        bridge_stdout=stdout,
        bridge_stderr=stderr,
        warnings=tuple(warnings),
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return report
