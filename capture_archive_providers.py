from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ARCHIVE_PROVIDER_WAYBACK = "wayback"
ARCHIVE_PROVIDER_ARCHIVE_TODAY = "archive_today"
ARCHIVE_PROVIDER_ARCHIVEBOX = "archivebox"

ARCHIVE_OPERATION_CHECK = "CHECK"
ARCHIVE_OPERATION_LIST = "LIST"
ARCHIVE_OPERATION_SUBMIT = "SUBMIT"
ARCHIVE_OPERATION_POLL = "POLL"
ARCHIVE_OPERATION_COMMAND_PLAN = "COMMAND_PLAN"

ARCHIVE_CHALLENGE_NONE = "none"
ARCHIVE_CHALLENGE_USER_HANDOFF = "user_handoff"
ARCHIVE_CHALLENGE_LOCAL_PROCESS = "local_process"

ARCHIVE_PROVIDER_SCOPE = (
    "archive provider metadata and injected/mock result model only; no live archive "
    "network call, browser automation, ArchiveBox execution, credential use, scraping, "
    "download, external process, or GUI behavior"
)


@dataclass(frozen=True)
class ArchiveProviderMetadata:
    provider_id: str
    display_name: str
    operations: tuple[str, ...]
    official_api: bool
    authentication: str
    challenge_mode: str
    mirrors: tuple[str, ...] = ()
    cache_ttl_seconds: int = 0
    statuses: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    schema_version: str = "rev4.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "authentication": self.authentication,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "challenge_mode": self.challenge_mode,
            "display_name": self.display_name,
            "limitations": list(self.limitations),
            "mirrors": list(self.mirrors),
            "official_api": self.official_api,
            "operations": list(self.operations),
            "provider_id": self.provider_id,
            "schema_version": self.schema_version,
            "statuses": list(self.statuses),
        }


ARCHIVE_PROVIDER_METADATA: tuple[ArchiveProviderMetadata, ...] = (
    ArchiveProviderMetadata(
        provider_id=ARCHIVE_PROVIDER_WAYBACK,
        display_name="Internet Archive Wayback Machine",
        operations=(ARCHIVE_OPERATION_CHECK, ARCHIVE_OPERATION_LIST, ARCHIVE_OPERATION_SUBMIT),
        official_api=True,
        authentication="none_for_public_availability_api",
        challenge_mode=ARCHIVE_CHALLENGE_NONE,
        cache_ttl_seconds=3600,
        statuses=(
            "FOUND",
            "NOT_FOUND_CONFIRMED",
            "MULTIPLE_FOUND",
            "SUBMISSION_STARTED",
            "SUBMISSION_COMPLETED",
            "NETWORK_ERROR",
            "UNKNOWN",
        ),
        limitations=("Live checks/submissions are not performed by this metadata layer.",),
    ),
    ArchiveProviderMetadata(
        provider_id=ARCHIVE_PROVIDER_ARCHIVE_TODAY,
        display_name="archive.today / archive.ph",
        operations=(ARCHIVE_OPERATION_CHECK, ARCHIVE_OPERATION_LIST, ARCHIVE_OPERATION_SUBMIT, ARCHIVE_OPERATION_POLL),
        official_api=False,
        authentication="none_public_but_challenge_prone",
        challenge_mode=ARCHIVE_CHALLENGE_USER_HANDOFF,
        mirrors=("archive.today", "archive.ph", "archive.is"),
        cache_ttl_seconds=3600,
        statuses=(
            "FOUND",
            "NOT_FOUND_CONFIRMED",
            "SUBMISSION_STARTED",
            "WIP",
            "FORMAT_CHANGED",
            "CHALLENGE_REQUIRES_USER",
            "NETWORK_ERROR",
            "UNKNOWN",
        ),
        limitations=(
            "Challenge-prone service; automated live access remains separately gated.",
            "Challenge handling is normal-browser/manual handoff metadata only.",
        ),
    ),
    ArchiveProviderMetadata(
        provider_id=ARCHIVE_PROVIDER_ARCHIVEBOX,
        display_name="ArchiveBox",
        operations=(ARCHIVE_OPERATION_COMMAND_PLAN, ARCHIVE_OPERATION_SUBMIT, ARCHIVE_OPERATION_POLL),
        official_api=False,
        authentication="local_or_remote_user_configured",
        challenge_mode=ARCHIVE_CHALLENGE_LOCAL_PROCESS,
        statuses=("SUBMISSION_STARTED", "SUBMISSION_COMPLETED", "SERVICE_UNAVAILABLE", "UNKNOWN"),
        limitations=("Docker/WSL/remote/app-native execution is plan-only until explicitly approved.",),
    ),
)


def available_archive_providers() -> tuple[ArchiveProviderMetadata, ...]:
    return ARCHIVE_PROVIDER_METADATA


def archive_provider_by_id(provider_id: str) -> ArchiveProviderMetadata | None:
    normalized = str(provider_id or "")
    return next(
        (provider for provider in ARCHIVE_PROVIDER_METADATA if provider.provider_id == normalized),
        None,
    )


def archive_provider_catalog_to_dict() -> dict[str, Any]:
    return {
        "archive_provider_count": len(ARCHIVE_PROVIDER_METADATA),
        "archive_providers": [provider.to_dict() for provider in ARCHIVE_PROVIDER_METADATA],
        "scope": ARCHIVE_PROVIDER_SCOPE,
    }
