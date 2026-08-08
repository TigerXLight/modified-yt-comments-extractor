from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from capture_archivebox import build_archivebox_command_plan
from capture_media_discovery import discover_media_resources_from_html
from capture_media_download import build_media_mux_plan
from capture_rendered_citation import mark_protected_or_black_output, plan_rendered_citation_session
from source_offline_preservation_bundle import build_default_preservation_choice_plan


SOURCE_MEDIA_ARCHIVE_RUNTIME_SCHEMA_VERSION = "source_media_archive_runtime_v1"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _stable_json(data: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(data), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _sha16(data: Any) -> str:
    return hashlib.sha256(_stable_json(data).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ArchiveProviderMockResult:
    provider_id: str
    status: str
    source_url: str
    archive_url: str = ""
    challenge_handoff_required: bool = False
    dns_diagnostic: str = ""
    cache_key: str = ""
    provider_call_performed: bool = False
    submit_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceMediaArchiveRuntimeBundle:
    bundle_id: str
    source_url: str
    media_discovery_result: Mapping[str, Any]
    mux_plan: Mapping[str, Any]
    rendered_citation_plan: Mapping[str, Any]
    protected_output_result: Mapping[str, Any]
    archive_provider_results: tuple[ArchiveProviderMockResult, ...]
    archivebox_command_plans: tuple[Mapping[str, Any], ...]
    offline_bundle_plan: Mapping[str, Any]
    no_live_execution: bool = True
    external_download_performed: bool = False
    real_ffmpeg_executed: bool = False
    real_ytdlp_executed: bool = False
    real_archivebox_executed: bool = False
    real_archive_provider_called: bool = False
    real_screen_recording_performed: bool = False
    drm_bypass_attempted: bool = False
    schema_version: str = SOURCE_MEDIA_ARCHIVE_RUNTIME_SCHEMA_VERSION

    @property
    def discovered_resource_count(self) -> int:
        return int(
            self.media_discovery_result.get(
                "resource_count",
                len(self.media_discovery_result.get("resources", ())),
            )
        )

    @property
    def archive_provider_result_count(self) -> int:
        return len(self.archive_provider_results)

    @property
    def archivebox_command_plan_count(self) -> int:
        return len(self.archivebox_command_plans)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["discovered_resource_count"] = self.discovered_resource_count
        data["archive_provider_result_count"] = self.archive_provider_result_count
        data["archivebox_command_plan_count"] = self.archivebox_command_plan_count
        return data


def build_fixture_media_archive_runtime_bundle(
    *,
    source_url: str = "https://example.invalid/source",
) -> SourceMediaArchiveRuntimeBundle:
    html = """
    <html><head>
      <meta property="og:image" content="https://example.invalid/og.jpg">
      <style>.hero{background-image:url('/bg.jpg')}</style>
    </head><body>
      <picture><source srcset="/hero-2x.jpg 2x"><img src="/hero.jpg" alt="Hero"></picture>
      <video src="/video.mp4" poster="/poster.jpg"><source src="/video-1080.mp4" type="video/mp4"><track src="/captions.vtt" kind="subtitles" srclang="en"></video>
      <audio><source src="/audio.m4a" type="audio/mp4"></audio>
      <a href="/stream.m3u8">HLS</a><a href="/manifest.mpd">DASH</a>
    </body></html>
    """
    media = discover_media_resources_from_html(html, source_url=source_url)
    mux_plan = build_media_mux_plan(
        video_resource_id="fixture_video_only",
        audio_resource_id="fixture_audio_only",
        output_filename="fixture_muxed_output.mp4",
    ).to_dict()
    rendered = plan_rendered_citation_session(
        source_url=source_url,
        source_label="Fixture source",
        purpose="research",
        time_range_start_seconds=0,
        time_range_end_seconds=5,
        selected_display_label="fixture_display",
    )
    protected = mark_protected_or_black_output(rendered, reason="fixture_black_frame_detected")
    archive_results = (
        ArchiveProviderMockResult(
            provider_id="wayback",
            status="found",
            source_url=source_url,
            archive_url="https://webcache.invalid/snapshot",
            cache_key="wayback:" + _sha16(source_url),
        ),
        ArchiveProviderMockResult(
            provider_id="archive_today",
            status="challenge",
            source_url=source_url,
            challenge_handoff_required=True,
            dns_diagnostic="fixture_mirror_check_required",
            cache_key="archive_today:" + _sha16(source_url),
        ),
    )
    archivebox_plans = tuple(
        build_archivebox_command_plan(
            url=source_url,
            mode=mode,
        ).to_dict()
        for mode in ("WINDOWS_DOCKER_COMPOSE", "WINDOWS_WSL2_CLI", "REMOTE_ARCHIVEBOX")
    )
    offline = build_default_preservation_choice_plan(source_url).to_dict()
    return SourceMediaArchiveRuntimeBundle(
        bundle_id="source_media_archive_runtime_" + _sha16((source_url, media.to_dict(), mux_plan)),
        source_url=source_url,
        media_discovery_result=media.to_dict(),
        mux_plan=mux_plan,
        rendered_citation_plan=rendered.to_dict(),
        protected_output_result=protected.to_dict(),
        archive_provider_results=archive_results,
        archivebox_command_plans=archivebox_plans,
        offline_bundle_plan=offline,
    )


def validate_source_media_archive_runtime_bundle(
    bundle: SourceMediaArchiveRuntimeBundle | Mapping[str, Any],
) -> tuple[str, ...]:
    data = bundle.to_dict() if hasattr(bundle, "to_dict") else dict(bundle)
    errors: list[str] = []
    for key in (
        "external_download_performed",
        "real_ffmpeg_executed",
        "real_ytdlp_executed",
        "real_archivebox_executed",
        "real_archive_provider_called",
        "real_screen_recording_performed",
        "drm_bypass_attempted",
    ):
        if bool(data.get(key, False)):
            errors.append(f"unsafe_flag_true:{key}")
    if not bool(data.get("no_live_execution", False)):
        errors.append("no_live_execution_must_be_true")
    protected = data.get("protected_output_result", {})
    if protected.get("status") not in {"protected_or_black_output", "failed", "blocked"}:
        errors.append("protected_output_must_be_blocked_or_failed")
    return tuple(errors)


def source_media_archive_runtime_bundle_to_json(bundle: SourceMediaArchiveRuntimeBundle) -> str:
    return _stable_json(bundle.to_dict(), pretty=True)
