from __future__ import annotations

import json
import tempfile
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from media_jdownloader_external_config import (
    JDownloaderExternalConfigReport,
    load_jdownloader_external_config,
    resolve_jdownloader_source_path,
)
from jdownloader_internal_backend import (
    detect_jdownloader_internal_capabilities,
    preferred_youtube_media_backend,
)
from shared_media_backend import (
    build_shared_jdownloader_media_request,
    run_shared_jdownloader_media_backend,
)
from jdownloader_internal_paths import (
    JDOWNLOADER_INTERNAL_BACKEND_ID,
    YTDLP_FALLBACK_BACKEND_ID,
)
from jdownloader_route_summary import summarize_jdownloader_route_metadata
from jdownloader_capability_router import build_jdownloader_capability_decision
from source_resource_state import SourceResourceRowState
from youtube_media_download_backend import (
    YouTubeMediaDiscovery,
    build_youtube_ytdlp_download_plan,
    discover_youtube_media_with_ytdlp,
    write_youtube_media_download_plan,
)


YOUTUBE_GUI_MEDIA_QUEUE_STATUS_READY = "ready"
YOUTUBE_GUI_MEDIA_QUEUE_STATUS_NOT_SELECTED = "not_selected"
YOUTUBE_GUI_MEDIA_QUEUE_STATUS_UNSUPPORTED = "unsupported"
YOUTUBE_GUI_MEDIA_QUEUE_STATUS_BACKEND_FAILED = "backend_failed"

YOUTUBE_GUI_QUALITY_PRESETS: tuple[tuple[str, int], ...] = (
    ("4k", 2160),
    ("2k", 1440),
    ("1080", 1080),
    ("720", 720),
    ("480", 480),
    ("360", 360),
    ("240", 240),
    ("144", 144),
)
YOUTUBE_GUI_COMPONENT_VIDEO = "video"
YOUTUBE_GUI_COMPONENT_AUDIO = "audio"
YOUTUBE_GUI_COMPONENT_THUMBNAIL = "thumbnail"
YOUTUBE_GUI_COMPONENT_SUBTITLES = "subtitles"
YOUTUBE_GUI_COMPONENT_AUTO_SUBTITLES = "auto_subtitles"
YOUTUBE_GUI_BACKEND_AUTO = "auto"


@dataclass(frozen=True)
class YouTubeGuiMediaPreferences:
    video_enabled: bool = True
    separate_audio_enabled: bool = True
    thumbnail_enabled: bool = True
    subtitles_enabled: bool = True
    auto_subtitles_enabled: bool = True
    show_quality_dropdown: bool = True
    enabled_quality_labels: tuple[str, ...] = ("4k", "2k", "1080", "720", "480", "360", "240", "144")
    default_quality_label: str = "1080"
    backend_id: str = YOUTUBE_GUI_BACKEND_AUTO


@dataclass(frozen=True)
class YouTubeGuiMediaQueueResult:
    status: str
    message: str
    source_row_id: str = ""
    source_url: str = ""
    selected_quality_label: str = ""
    selected_height: int = 0
    queue_dir: str = ""
    files_to_add: tuple[str, ...] = ()
    metadata_txt_path: str = ""
    manifest_json_path: str = ""
    execution_manifest_path: str = ""
    plan_json_paths: tuple[str, ...] = ()
    selected_components: tuple[str, ...] = ()
    backend_id: str = YTDLP_FALLBACK_BACKEND_ID
    backend_status: str = ""
    engine_status: str = ""
    readiness_status: str = ""
    backend_error_log_path: str = ""
    auto_mux: bool = True
    jdownloader_source: str = ""
    ffmpeg_location: str = ""
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


def default_youtube_gui_media_preferences() -> YouTubeGuiMediaPreferences:
    return YouTubeGuiMediaPreferences()


def normalized_youtube_quality_labels(preferences: YouTubeGuiMediaPreferences | None = None) -> tuple[str, ...]:
    prefs = preferences or default_youtube_gui_media_preferences()
    allowed = {label for label, _height in YOUTUBE_GUI_QUALITY_PRESETS}
    labels = tuple(label for label in prefs.enabled_quality_labels if label in allowed)
    return labels or (prefs.default_quality_label if prefs.default_quality_label in allowed else "1080",)


def youtube_quality_height(label: str) -> int:
    lookup = {name: height for name, height in YOUTUBE_GUI_QUALITY_PRESETS}
    return lookup.get(str(label or "").strip(), 0)


def youtube_available_quality_labels_from_discovery(
    discovery: YouTubeMediaDiscovery | None,
    *,
    fallback: Sequence[str] = (),
) -> tuple[str, ...]:
    """Return row quality labels that are actually present in yt-dlp formats.

    The GUI falls back to the configured preset list until yt-dlp discovery has
    loaded, then narrows the row dropdown to available video heights.
    """
    allowed = {label for label, _height in YOUTUBE_GUI_QUALITY_PRESETS}
    fallback_labels = tuple(label for label in fallback if label in allowed)
    if discovery is None:
        return fallback_labels
    heights: set[int] = set()
    for fmt in discovery.formats:
        height = int(fmt.height or 0)
        if height <= 0:
            continue
        # Skip audio-only entries. Combined or video-only entries both prove the
        # quality exists; muxing is handled by yt-dlp/FFmpeg later.
        if str(fmt.vcodec or "").lower() == "none":
            continue
        heights.add(height)
    if not heights:
        return fallback_labels
    result: list[str] = []
    for label, preset_height in YOUTUBE_GUI_QUALITY_PRESETS:
        if preset_height in heights:
            result.append(label)
            continue
        # Some providers use near-equivalent heights. Keep this conservative.
        if any(abs(height - preset_height) <= 8 for height in heights):
            result.append(label)
    if not result:
        return fallback_labels
    return tuple(result)


def youtube_title_from_discovery(discovery: YouTubeMediaDiscovery | None, fallback: str = "") -> str:
    if discovery is None:
        return fallback
    return (discovery.title or fallback or "").strip()


def selected_youtube_components(preferences: YouTubeGuiMediaPreferences | None = None) -> tuple[str, ...]:
    prefs = preferences or default_youtube_gui_media_preferences()
    components: list[str] = []
    if prefs.video_enabled:
        components.append(YOUTUBE_GUI_COMPONENT_VIDEO)
    if prefs.separate_audio_enabled:
        components.append(YOUTUBE_GUI_COMPONENT_AUDIO)
    if prefs.thumbnail_enabled:
        components.append(YOUTUBE_GUI_COMPONENT_THUMBNAIL)
    if prefs.subtitles_enabled:
        components.append(YOUTUBE_GUI_COMPONENT_SUBTITLES)
    if prefs.auto_subtitles_enabled:
        components.append(YOUTUBE_GUI_COMPONENT_AUTO_SUBTITLES)
    return tuple(components)


def resolve_youtube_gui_backend(preferences: YouTubeGuiMediaPreferences | None = None) -> tuple[str, str, tuple[str, ...]]:
    prefs = preferences or default_youtube_gui_media_preferences()
    requested = str(prefs.backend_id or YOUTUBE_GUI_BACKEND_AUTO)
    capabilities = detect_jdownloader_internal_capabilities()
    if requested == JDOWNLOADER_INTERNAL_BACKEND_ID:
        if capabilities.runtime_present:
            return JDOWNLOADER_INTERNAL_BACKEND_ID, "internal_runtime_ready", capabilities.warnings
        return JDOWNLOADER_INTERNAL_BACKEND_ID, "internal_runtime_missing", capabilities.warnings
    if requested == YTDLP_FALLBACK_BACKEND_ID:
        return YTDLP_FALLBACK_BACKEND_ID, "yt_dlp_fallback_selected", ()
    preferred = preferred_youtube_media_backend()
    if preferred == JDOWNLOADER_INTERNAL_BACKEND_ID:
        return JDOWNLOADER_INTERNAL_BACKEND_ID, "internal_runtime_ready", capabilities.warnings
    return YTDLP_FALLBACK_BACKEND_ID, "internal_missing_using_yt_dlp_fallback", capabilities.warnings


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value or "").strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:96] or "youtube_media"


def _default_queue_root() -> Path:
    return Path(tempfile.gettempdir()) / "ytce_youtube_media_queue"


def _load_optional_jdownloader_config(source: str | Path = "") -> tuple[JDownloaderExternalConfigReport | None, tuple[str, ...]]:
    warnings: list[str] = []
    try:
        resolved = resolve_jdownloader_source_path(source)
        return load_jdownloader_external_config(resolved), tuple(warnings)
    except Exception as exc:
        warnings.append(f"JDownloader config was not imported: {type(exc).__name__}: {exc}")
        return None, tuple(warnings)


def _ffmpeg_location_from_config(config: JDownloaderExternalConfigReport | None) -> str:
    if config is None:
        return ""
    return str(config.ffmpeg_binary_path or "")




def _format_youtube_date(value: str) -> str:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    return text


def _format_int(value: int | None) -> str:
    return f"{value:,}" if isinstance(value, int) else ""


def _metadata_value(value: str) -> str:
    return str(value or "").strip()

def _metadata_txt(*, row: SourceResourceRowState, quality_label: str, components: Sequence[str], plan_paths: Sequence[str], discovery: YouTubeMediaDiscovery | None = None) -> str:
    # This file intentionally mirrors the user's desired description-text shape.
    # Full title/channel/date/views/description are filled by yt-dlp info-json on execution.
    component_labels = {
        YOUTUBE_GUI_COMPONENT_VIDEO: "Muxed video + best audio",
        YOUTUBE_GUI_COMPONENT_AUDIO: "Separate audio file",
        YOUTUBE_GUI_COMPONENT_THUMBNAIL: "Thumbnail / image",
        YOUTUBE_GUI_COMPONENT_SUBTITLES: "Manual subtitles",
        YOUTUBE_GUI_COMPONENT_AUTO_SUBTITLES: "Auto / ASR subtitles",
    }
    title = _metadata_value(discovery.title if discovery else row.title) or (row.title or "")
    channel = _metadata_value((discovery.channel or discovery.uploader) if discovery else "")
    subscribers = _format_int(discovery.channel_follower_count if discovery else None)
    date = _format_youtube_date(discovery.upload_date if discovery else "")
    views = _format_int(discovery.view_count if discovery else None)
    description = _metadata_value(discovery.description if discovery else "")
    lines = [
        "Title: " + title,
        "Channel: " + channel,
        "Subscribers: " + subscribers,
        "Date: " + date,
        "Views: " + views,
        "Description: " + description,
        "Source: " + row.canonical_url,
        "",
        "YTCE YouTube Media Queue",
        "=" * 80,
        "Selected quality: " + quality_label,
        "Selected files/components:",
        *(f"- {component_labels.get(component, component)}" for component in components),
        "",
        "Auto mux: yes" if YOUTUBE_GUI_COMPONENT_VIDEO in components else "Auto mux: no video selected",
        "Mux rule: yt-dlp selects bestvideo+bestaudio at or below the selected quality; FFmpeg merges when YouTube provides separate streams.",
        "Queue behaviour: Go submits the selected YouTube media job to internal JDownloader, waits for completed files, and adds the resulting media plus manifest/metadata files to FILES.",
        "",
        "Plan files:",
        *(f"- {path}" for path in plan_paths),
        "",
        "Metadata note: title/channel/date/views/full description/subtitle files/thumbnails are produced by yt-dlp info-json and selected write flags when the plan is executed.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _load_internal_jdownloader_execution_manifest(manifest_path: str | Path) -> tuple[dict[str, Any], tuple[str, ...]]:
    if not manifest_path:
        return {}, ()
    path = Path(manifest_path)
    if not path.is_file():
        return {}, (f"Internal JDownloader execution manifest was not found: {path}",)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, (f"Internal JDownloader execution manifest could not be read: {type(exc).__name__}: {exc}",)
    if not isinstance(data, dict):
        return {}, (f"Internal JDownloader execution manifest was not a JSON object: {path}",)
    return data, ()


def _completed_internal_jdownloader_file_records(manifest: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    raw_files = manifest.get("files", ())
    if not isinstance(raw_files, list):
        return ()
    for item in raw_files:
        if not isinstance(item, Mapping):
            continue
        file_path = str(item.get("path") or "").strip()
        if not file_path:
            continue
        path = Path(file_path)
        if not path.is_file():
            continue
        records.append(
            {
                "kind": str(item.get("kind") or "unknown"),
                "path": str(path),
                "size": int(item.get("size") or path.stat().st_size),
                "sha256": str(item.get("sha256") or ""),
            }
        )
    return tuple(records)


def _internal_jdownloader_duplicate_state_warning(job_result: InternalJDownloaderJobResult) -> str:
    if job_result.status != "timeout":
        return ""
    if job_result.submission_status != "accepted_or_unknown":
        return ""
    if job_result.files_count:
        return ""
    return (
        "Internal JDownloader accepted the link, but no new files appeared in the YTCE output folder. "
        "The URL may already exist in JDownloader LinkGrabber/Downloads, or JDownloader may have reused "
        "an existing package instead of creating fresh files. Remove duplicate JD packages/list entries or "
        "use a fresh output/link before retrying."
    )


def queue_youtube_gui_source_row_selection(
    *,
    row: SourceResourceRowState,
    quality_label: str,
    preferences: YouTubeGuiMediaPreferences | None = None,
    output_root: str | Path | None = None,
    jdownloader_source: str | Path = "",
    yt_dlp_path: str = "yt-dlp",
    probe_metadata: bool = False,
    discovery: YouTubeMediaDiscovery | None = None,
    internal_job_runner: Any = None,
) -> YouTubeGuiMediaQueueResult:
    if row.adapter_id != "youtube":
        return YouTubeGuiMediaQueueResult(
            status=YOUTUBE_GUI_MEDIA_QUEUE_STATUS_UNSUPPORTED,
            message="YouTube media queueing only applies to YouTube source rows.",
            source_row_id=row.row_id,
            source_url=row.canonical_url,
        )

    prefs = preferences or default_youtube_gui_media_preferences()
    quality_options = normalized_youtube_quality_labels(prefs)
    selected_quality = quality_label if quality_label in quality_options else (prefs.default_quality_label if prefs.default_quality_label in quality_options else quality_options[0])
    height = youtube_quality_height(selected_quality)
    components = selected_youtube_components(prefs)
    backend_id, backend_status, backend_warnings = resolve_youtube_gui_backend(prefs)
    jdownloader_capability_decision = build_jdownloader_capability_decision(
        row.canonical_url,
        capabilities=detect_jdownloader_internal_capabilities(),
    ).to_dict()
    if not components:
        return YouTubeGuiMediaQueueResult(
            status=YOUTUBE_GUI_MEDIA_QUEUE_STATUS_NOT_SELECTED,
            message="Select at least one YouTube media component in the YouTube settings first.",
            source_row_id=row.row_id,
            source_url=row.canonical_url,
            selected_quality_label=selected_quality,
            selected_height=height,
            backend_id=backend_id,
            backend_status=backend_status,
        )

    output_root_path = Path(output_root) if output_root is not None else _default_queue_root()
    run_stamp = time.strftime("%Y%m%d_%H%M%S")
    queue_dir = output_root_path / _safe_name(row.source_id or row.row_id) / run_stamp
    queue_dir.mkdir(parents=True, exist_ok=True)
    display_title = (row.title or row.source_id or "YouTube media").strip()
    job_package_name = f"YTCE - {display_title} - {run_stamp}"

    warnings_list: list[str] = list(backend_warnings)
    # Do not run yt-dlp metadata probing before internal JDownloader jobs.
    # On some YouTube links that pre-probe can hang or delay the GUI worker even
    # though the selected media backend is internal JDownloader.
    if discovery is None and probe_metadata and backend_id == YTDLP_FALLBACK_BACKEND_ID:
        try:
            discovery = discover_youtube_media_with_ytdlp(row.canonical_url, output_dir=queue_dir / "metadata")
        except Exception as exc:
            warnings_list.append(f"YouTube metadata discovery failed: {type(exc).__name__}: {exc}")

    config: JDownloaderExternalConfigReport | None = None
    ffmpeg_location = ""
    if backend_id == YTDLP_FALLBACK_BACKEND_ID:
        config, warnings = _load_optional_jdownloader_config(jdownloader_source)
        warnings = tuple([*warnings_list, *warnings])
        ffmpeg_location = _ffmpeg_location_from_config(config)
    else:
        warnings = tuple(warnings_list)
    plan_paths: list[str] = []
    plan_summaries: list[dict[str, Any]] = []
    execution_manifest_path = ""
    engine_status = ""
    readiness_status = ""
    backend_error_log_path = ""
    backend_failed = False
    internal_jdownloader_execution_manifest: dict[str, Any] = {}
    internal_jdownloader_completed_files: tuple[dict[str, Any], ...] = ()
    internal_jdownloader_route_summary: dict[str, Any] = summarize_jdownloader_route_metadata({}).to_dict()
    internal_jdownloader_duplicate_warning = ""

    if backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID:
        backend_request = build_shared_jdownloader_media_request(
            source_adapter_id=row.adapter_id,
            source_url=row.canonical_url,
            output_dir=queue_dir / "downloads",
            package_name=job_package_name,
            source_title_or_id=f"{display_title} {run_stamp}",
            max_height=height,
            components=components,
            video=YOUTUBE_GUI_COMPONENT_VIDEO in components,
            audio=YOUTUBE_GUI_COMPONENT_AUDIO in components,
            image=YOUTUBE_GUI_COMPONENT_THUMBNAIL in components,
            description=True,
            wait=True,
            timeout_seconds=180,
            monitor_timeout_seconds=120.0,
            overall_timeout_seconds=180.0,
            plan_json_path=queue_dir / "jdownloader-internal-command.json",
        )
        backend_result = run_shared_jdownloader_media_backend(
            backend_request,
            internal_job_runner=internal_job_runner,
        )
        plan_paths.extend(backend_result.plan_json_paths)
        execution_manifest_path = backend_result.execution_manifest_path
        engine_status = backend_result.engine_status
        readiness_status = backend_result.readiness_status
        warnings_list.extend(backend_result.warnings)
        if execution_manifest_path:
            internal_jdownloader_execution_manifest, manifest_warnings = _load_internal_jdownloader_execution_manifest(execution_manifest_path)
            warnings_list.extend(manifest_warnings)
            internal_jdownloader_completed_files = _completed_internal_jdownloader_file_records(internal_jdownloader_execution_manifest)
            internal_jdownloader_route_summary = summarize_jdownloader_route_metadata(
                manifest=internal_jdownloader_execution_manifest
            ).to_dict()
            missing_finished_count = max(0, int(backend_result.files_count or 0) - len(internal_jdownloader_completed_files))
            if backend_result.status == "success" and missing_finished_count:
                warnings_list.append(
                    "Internal JDownloader reported completed files, but one or more manifest file paths were not present on disk."
                )
        if backend_result.internal_job_result is not None:
            internal_jdownloader_duplicate_warning = _internal_jdownloader_duplicate_state_warning(backend_result.internal_job_result)
        if internal_jdownloader_duplicate_warning:
            warnings_list.append(internal_jdownloader_duplicate_warning)
        if backend_result.errors:
            backend_failed = True
            warnings_list.extend(backend_result.errors)
        if backend_result.status == "failed":
            backend_failed = True
        if backend_result.plan_summary:
            plan_summary = dict(backend_result.plan_summary)
            plan_summary["quality"] = selected_quality
            plan_summary["height"] = height
            plan_summaries.append(plan_summary)
    elif YOUTUBE_GUI_COMPONENT_VIDEO in components:
        selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best" if height else "bestvideo+bestaudio/best"
        plan = build_youtube_ytdlp_download_plan(
            row.canonical_url,
            output_dir=queue_dir / "downloads",
            yt_dlp_path=yt_dlp_path,
            ffmpeg_location=ffmpeg_location,
            jdownloader_config=config,
            merge_output_format="mp4",
            format_selector=selector,
            write_thumbnail=YOUTUBE_GUI_COMPONENT_THUMBNAIL in components,
            write_subtitles=YOUTUBE_GUI_COMPONENT_SUBTITLES in components,
            write_auto_subtitles=YOUTUBE_GUI_COMPONENT_AUTO_SUBTITLES in components,
            extract_audio=False,
            dry_run=True,
        )
        path = queue_dir / f"youtube-video-mux-plan-{_safe_name(selected_quality)}.json"
        write_youtube_media_download_plan(plan, path)
        plan_paths.append(str(path))
        plan_summaries.append({"component": YOUTUBE_GUI_COMPONENT_VIDEO, "quality": selected_quality, "height": height, "format_selector": plan.format_selector, "command": list(plan.command), "auto_mux": True, "plan_json": str(path)})

    if backend_id == YTDLP_FALLBACK_BACKEND_ID and YOUTUBE_GUI_COMPONENT_AUDIO in components:
        plan = build_youtube_ytdlp_download_plan(
            row.canonical_url,
            output_dir=queue_dir / "downloads",
            yt_dlp_path=yt_dlp_path,
            ffmpeg_location=ffmpeg_location,
            jdownloader_config=config,
            format_selector="bestaudio[ext=m4a]/bestaudio/best",
            write_thumbnail=False,
            write_subtitles=False,
            write_auto_subtitles=False,
            extract_audio=True,
            audio_format="m4a",
            dry_run=True,
        )
        path = queue_dir / "youtube-audio-extract-plan-m4a.json"
        write_youtube_media_download_plan(plan, path)
        plan_paths.append(str(path))
        plan_summaries.append({"component": YOUTUBE_GUI_COMPONENT_AUDIO, "quality": "audio", "format_selector": plan.format_selector, "command": list(plan.command), "extract_audio": True, "plan_json": str(path)})

    warnings = tuple(warnings_list)
    queue_status = YOUTUBE_GUI_MEDIA_QUEUE_STATUS_BACKEND_FAILED if backend_failed else YOUTUBE_GUI_MEDIA_QUEUE_STATUS_READY
    manifest = {
        "status": queue_status,
        "source_row_id": row.row_id,
        "source_url": row.canonical_url,
        "title": (discovery.title if discovery and discovery.title else row.title),
        "channel": (discovery.channel if discovery else ""),
        "upload_date": (discovery.upload_date if discovery else ""),
        "view_count": (discovery.view_count if discovery else None),
        "selected_quality_label": selected_quality,
        "selected_height": height,
        "selected_components": list(components),
        "backend_id": backend_id,
        "backend_status": backend_status,
        "engine_status": engine_status,
        "readiness_status": readiness_status,
        "execution_manifest_path": execution_manifest_path,
        "jdownloader_package_name": job_package_name if backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID else "",
        "jdownloader_completed_files": list(internal_jdownloader_completed_files),
        "jdownloader_completed_file_count": len(internal_jdownloader_completed_files),
        "jdownloader_capability_decision": jdownloader_capability_decision,
        "jdownloader_capability_status": jdownloader_capability_decision.get("capability_status", ""),
        "jdownloader_recommended_backend_id": jdownloader_capability_decision.get("recommended_backend_id", ""),
        "jdownloader_domain_likely_supported": bool(jdownloader_capability_decision.get("domain_likely_supported", False)),
        "jdownloader_route_summary": internal_jdownloader_route_summary,
        "jdownloader_route_used": internal_jdownloader_route_summary.get("route_used", ""),
        "jdownloader_route_label": internal_jdownloader_route_summary.get("route_label", ""),
        "jdownloader_api3128_used": bool(internal_jdownloader_route_summary.get("api3128_used", False)),
        "jdownloader_yt_dlp_role": internal_jdownloader_route_summary.get("yt_dlp_role", ""),
        "jdownloader_duplicate_state_suspected": bool(internal_jdownloader_duplicate_warning),
        "auto_mux": YOUTUBE_GUI_COMPONENT_VIDEO in components,
        "jdownloader_source": config.source_path if config else "",
        "ffmpeg_location": ffmpeg_location,
        "plans": plan_summaries,
        "warnings": list(warnings),
    }
    manifest_path = queue_dir / "youtube-media-selection-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    metadata_path = queue_dir / "youtube-video-metadata.txt"
    metadata_path.write_text(
        _metadata_txt(row=row, quality_label=selected_quality, components=components, plan_paths=plan_paths, discovery=discovery),
        encoding="utf-8",
        newline="\n",
    )

    internal_jdownloader_file_paths = [str(item["path"]) for item in internal_jdownloader_completed_files]
    # User-facing FILES should contain downloaded media and a lightweight
    # provenance text file by default. Technical JSON manifests/command files
    # are still written beside the run for debugging, but are not exported unless
    # the user manually adds them.
    files_to_add = [*internal_jdownloader_file_paths, str(metadata_path)]
    message = (
        "YouTube media downloaded and added to FILES by Go.\n\n"
        f"Quality: {selected_quality}\n"
        f"Components: {', '.join(components)}\n"
        f"Auto mux: {'yes' if YOUTUBE_GUI_COMPONENT_VIDEO in components else 'no video selected'}\n"
        f"FILES added: {len(files_to_add)}\n\n"
    )
    if backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID:
        route_label = str(internal_jdownloader_route_summary.get("route_label", "") or "JDownloader route not yet resolved")
        message += f"Backend: internal JDownloader ({route_label})\n"
        message += f"JD capability: {jdownloader_capability_decision.get('decision_label', '')}\n"
    if backend_id == JDOWNLOADER_INTERNAL_BACKEND_ID:
        message += (
            "Starting internal JDownloader engine...\n"
            "Internal JDownloader engine ready.\n"
            "Submitting YouTube job to internal JDownloader...\n"
            "Waiting for internal JDownloader output...\n"
            f"Manifest: {execution_manifest_path or manifest_path}\n"
            f"Internal JDownloader completed files added: {len(internal_jdownloader_completed_files)}\n"
            + (
                "Possible duplicate/list-state: JD accepted the link but no new files appeared in the requested output folder.\n\n"
                if internal_jdownloader_duplicate_warning
                else ("Internal JDownloader job needs review; see manifest/errors.\n\n" if backend_failed else "Added internal JDownloader files to FILES.\n\n")
            )
        )
    message += (
        "Export will copy the downloaded media files plus youtube-video-metadata.txt."
    )
    return YouTubeGuiMediaQueueResult(
        status=queue_status,
        message=message,
        source_row_id=row.row_id,
        source_url=row.canonical_url,
        selected_quality_label=selected_quality,
        selected_height=height,
        queue_dir=str(queue_dir),
        files_to_add=tuple(files_to_add),
        metadata_txt_path=str(metadata_path),
        manifest_json_path=str(manifest_path),
        execution_manifest_path=execution_manifest_path,
        plan_json_paths=tuple(plan_paths),
        selected_components=tuple(components),
        backend_id=backend_id,
        backend_status=backend_status,
        engine_status=engine_status,
        readiness_status=readiness_status,
        backend_error_log_path=backend_error_log_path,
        auto_mux=YOUTUBE_GUI_COMPONENT_VIDEO in components,
        jdownloader_source=config.source_path if config else "",
        ffmpeg_location=ffmpeg_location,
        warnings=tuple(warnings),
    )
