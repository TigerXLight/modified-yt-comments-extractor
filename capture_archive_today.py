from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from capture_archive_providers import ARCHIVE_PROVIDER_ARCHIVE_TODAY, ARCHIVE_PROVIDER_SCOPE
from capture_status import ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER, ARCHIVE_STATUS_UNKNOWN


ArchiveTodayLookup = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class ArchiveTodayCheckResult:
    url: str
    archive_status: str
    snapshot_url: str = ""
    saved_at: str = ""
    challenge_required: bool = False
    warnings: tuple[str, ...] = ()
    provider_id: str = ARCHIVE_PROVIDER_ARCHIVE_TODAY
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_status": self.archive_status,
            "challenge_required": self.challenge_required,
            "provider_id": self.provider_id,
            "saved_at": self.saved_at,
            "scope": self.scope,
            "snapshot_url": self.snapshot_url,
            "url": self.url,
            "warnings": list(self.warnings),
        }


def check_archive_today_with_lookup(
    url: str,
    *,
    lookup: ArchiveTodayLookup | None = None,
) -> ArchiveTodayCheckResult:
    if lookup is None:
        return ArchiveTodayCheckResult(
            url=url,
            archive_status=ARCHIVE_STATUS_UNKNOWN,
            warnings=("No live archive.today lookup is configured in this local-only helper.",),
        )
    try:
        payload = lookup(url)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        raise
    except Exception:
        return ArchiveTodayCheckResult(
            url=url,
            archive_status=ARCHIVE_STATUS_UNKNOWN,
            warnings=("Injected archive.today lookup failed with a non-secret exception.",),
        )
    status = str(payload.get("archive_status") or payload.get("status") or ARCHIVE_STATUS_UNKNOWN)
    return ArchiveTodayCheckResult(
        url=url,
        archive_status=status,
        snapshot_url=str(payload.get("snapshot_url") or ""),
        saved_at=str(payload.get("saved_at") or ""),
        challenge_required=bool(payload.get("challenge_required"))
        or status == ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER,
        warnings=tuple(str(warning) for warning in payload.get("warnings", ()) if str(warning)),
    )
