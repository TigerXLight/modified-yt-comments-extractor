from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class ArchiveProviderStatus(str, Enum):
    FOUND = "FOUND"
    NOT_FOUND_CONFIRMED_BY_RESPONSE = "NOT_FOUND_CONFIRMED_BY_RESPONSE"
    MULTIPLE_FOUND = "MULTIPLE_FOUND"
    CHALLENGE_REQUIRES_USER = "CHALLENGE_REQUIRES_USER"
    FORMAT_CHANGED = "FORMAT_CHANGED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DNS_FAILURE = "DNS_FAILURE"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"
    SUBMISSION_PENDING = "SUBMISSION_PENDING"
    SUBMISSION_EXPLICITLY_REQUESTED = "SUBMISSION_EXPLICITLY_REQUESTED"


class LocalPreservationBackend(str, Enum):
    APP_NATIVE_LIGHT_BUNDLE = "APP_NATIVE_LIGHT_BUNDLE"
    ARCHIVEBOX_DOCKER_COMPOSE_LIGHT = "ARCHIVEBOX_DOCKER_COMPOSE_LIGHT"
    ARCHIVEBOX_WSL2_CLI_LIGHT = "ARCHIVEBOX_WSL2_CLI_LIGHT"
    REMOTE_ARCHIVEBOX = "REMOTE_ARCHIVEBOX"
    NATIVE_UNIX_ARCHIVEBOX = "NATIVE_UNIX_ARCHIVEBOX"


class RenderedCaptureBoundary(str, Enum):
    STANDARD_RENDERED_CAPTURE_ALLOWED = "STANDARD_RENDERED_CAPTURE_ALLOWED"
    PROTECTED_OR_BLACK_FRAME_STOP = "PROTECTED_OR_BLACK_FRAME_STOP"
    DRM_CIRCUMVENTION_NOT_SUPPORTED = "DRM_CIRCUMVENTION_NOT_SUPPORTED"


@dataclass(frozen=True)
class ArchiveProviderResultPlan:
    provider_id: str
    status: ArchiveProviderStatus
    source_url: str
    archive_url: str | None = None
    checked_at_utc: str | None = None
    last_saved_at_utc: str | None = None
    submit_is_explicit_user_action: bool = True
    failure_is_not_proof_content_never_existed: bool = True
    diagnostic_note: str = ""

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(frozen=True)
class OfflineWebArchiveBundlePlan:
    bundle_format_id: str = "app_native_sourceweb_zip_v1"
    suggested_extension: str = ".sourceweb.zip"
    low_file_size_profile: bool = True
    windows_openable_as_zip: bool = True
    custom_viewer_future: bool = True
    included_items: tuple[str, ...] = (
        "manifest.json",
        "source_provenance.json",
        "article_text.txt",
        "article_text.json",
        "visible_page_outline.txt",
        "html_snapshot.html",
        "resources_manifest.json",
        "selected_screenshots/",
        "selected_comments_or_livechat/",
        "selected_media_metadata.json",
        "archive_results.json",
        "hashes.json",
        "index.html",
    )
    excluded_by_default: tuple[str, ...] = (
        "full unselected media downloads",
        "credential material",
        "browser profile data",
        "challenge tokens",
    )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ArchiveBoxProfilePlan:
    backend: LocalPreservationBackend
    profile_name: str
    concurrency: int
    recursive_crawl_enabled: bool
    media_enabled_by_default: bool
    strict_size_time_caps: bool
    process_exits_when_finished: bool
    storage_note: str
    official_native_windows_supported: bool = False

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["backend"] = self.backend.value
        return data


@dataclass(frozen=True)
class RenderedCitationRecordingPlan:
    user_triggered: bool = True
    still_frame: bool = True
    selected_region: bool = True
    bounded_clip: bool = True
    visible_subtitles: bool = True
    source_url_timestamp_media_position: bool = True
    declared_purpose_recorded: bool = True
    boundary: RenderedCaptureBoundary = RenderedCaptureBoundary.STANDARD_RENDERED_CAPTURE_ALLOWED
    no_key_extraction: bool = True
    no_cdm_patch: bool = True
    no_license_server_impersonation: bool = True
    no_hdcp_defeat: bool = True
    black_or_protected_frame_stops_capture: bool = True

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["boundary"] = self.boundary.value
        return data


@dataclass(frozen=True)
class PreservationChoicePlan:
    archive_results: tuple[ArchiveProviderResultPlan, ...] = field(default_factory=tuple)
    offline_bundle: OfflineWebArchiveBundlePlan = field(default_factory=OfflineWebArchiveBundlePlan)
    archivebox_profiles: tuple[ArchiveBoxProfilePlan, ...] = field(default_factory=tuple)
    rendered_citation: RenderedCitationRecordingPlan = field(default_factory=RenderedCitationRecordingPlan)

    def to_dict(self) -> dict[str, object]:
        return {
            "archive_result_count": len(self.archive_results),
            "archive_results": [result.to_dict() for result in self.archive_results],
            "offline_bundle": self.offline_bundle.to_dict(),
            "archivebox_profiles": [profile.to_dict() for profile in self.archivebox_profiles],
            "rendered_citation": self.rendered_citation.to_dict(),
            "native_windows_archivebox_not_claimed": all(not p.official_native_windows_supported for p in self.archivebox_profiles),
        }


def build_default_archivebox_profile_plans() -> tuple[ArchiveBoxProfilePlan, ...]:
    return (
        ArchiveBoxProfilePlan(
            backend=LocalPreservationBackend.ARCHIVEBOX_DOCKER_COMPOSE_LIGHT,
            profile_name="Light single-URL Docker Compose",
            concurrency=1,
            recursive_crawl_enabled=False,
            media_enabled_by_default=False,
            strict_size_time_caps=True,
            process_exits_when_finished=True,
            storage_note="User-selected Windows folder mounted into Docker/WSL2 backend.",
        ),
        ArchiveBoxProfilePlan(
            backend=LocalPreservationBackend.ARCHIVEBOX_WSL2_CLI_LIGHT,
            profile_name="WSL2 one-shot CLI",
            concurrency=1,
            recursive_crawl_enabled=False,
            media_enabled_by_default=False,
            strict_size_time_caps=True,
            process_exits_when_finished=True,
            storage_note="ArchiveBox runs inside WSL2 and is invoked through argument-safe subprocess calls.",
        ),
        ArchiveBoxProfilePlan(
            backend=LocalPreservationBackend.REMOTE_ARCHIVEBOX,
            profile_name="Remote ArchiveBox",
            concurrency=1,
            recursive_crawl_enabled=False,
            media_enabled_by_default=False,
            strict_size_time_caps=True,
            process_exits_when_finished=False,
            storage_note="Remote NAS/server backend; app records endpoint ID and result receipts only.",
        ),
    )


def build_default_preservation_choice_plan(source_url: str) -> PreservationChoicePlan:
    return PreservationChoicePlan(
        archive_results=(
            ArchiveProviderResultPlan("wayback", ArchiveProviderStatus.UNKNOWN, source_url, submit_is_explicit_user_action=True),
            ArchiveProviderResultPlan("archive_today", ArchiveProviderStatus.UNKNOWN, source_url, submit_is_explicit_user_action=True, diagnostic_note="Challenge/manual handoff state is not converted to not found."),
        ),
        archivebox_profiles=build_default_archivebox_profile_plans(),
    )
