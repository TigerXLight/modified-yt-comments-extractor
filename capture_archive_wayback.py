from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from capture_archive_providers import ARCHIVE_PROVIDER_WAYBACK, ARCHIVE_PROVIDER_SCOPE
from capture_status import ARCHIVE_STATUS_FOUND, ARCHIVE_STATUS_UNKNOWN


WaybackLookup = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class WaybackCheckResult:
    url: str
    archive_status: str
    snapshot_url: str = ""
    saved_at: str = ""
    warnings: tuple[str, ...] = ()
    provider_id: str = ARCHIVE_PROVIDER_WAYBACK
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_status": self.archive_status,
            "provider_id": self.provider_id,
            "saved_at": self.saved_at,
            "scope": self.scope,
            "snapshot_url": self.snapshot_url,
            "url": self.url,
            "warnings": list(self.warnings),
        }


def check_wayback_with_lookup(url: str, *, lookup: WaybackLookup | None = None) -> WaybackCheckResult:
    if lookup is None:
        return WaybackCheckResult(
            url=url,
            archive_status=ARCHIVE_STATUS_UNKNOWN,
            warnings=("No live Wayback lookup is configured in this local-only helper.",),
        )
    try:
        payload = lookup(url)
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        raise
    except Exception:
        return WaybackCheckResult(
            url=url,
            archive_status=ARCHIVE_STATUS_UNKNOWN,
            warnings=("Injected Wayback lookup failed with a non-secret exception.",),
        )
    status = str(payload.get("archive_status") or payload.get("status") or ARCHIVE_STATUS_UNKNOWN)
    return WaybackCheckResult(
        url=url,
        archive_status=status,
        snapshot_url=str(payload.get("snapshot_url") or ""),
        saved_at=str(payload.get("saved_at") or ""),
        warnings=tuple(str(warning) for warning in payload.get("warnings", ()) if str(warning)),
    )


def mock_found_wayback_result(url: str, *, snapshot_url: str, saved_at: str) -> WaybackCheckResult:
    return WaybackCheckResult(
        url=url,
        archive_status=ARCHIVE_STATUS_FOUND,
        snapshot_url=snapshot_url,
        saved_at=saved_at,
    )
