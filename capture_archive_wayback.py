from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from capture_archive_providers import (
    ARCHIVE_OPERATION_CHECK,
    ARCHIVE_OPERATION_LIST,
    ARCHIVE_OPERATION_SUBMIT,
    ARCHIVE_PROVIDER_SCOPE,
    ARCHIVE_PROVIDER_WAYBACK,
)
from capture_status import (
    ARCHIVE_STATUS_FOUND,
    ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
    ARCHIVE_STATUS_SUBMISSION_COMPLETED,
    ARCHIVE_STATUS_SUBMISSION_STARTED,
    ARCHIVE_STATUS_UNKNOWN,
)


WaybackLookup = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class WaybackCheckResult:
    url: str
    archive_status: str
    snapshot_url: str = ""
    saved_at: str = ""
    operation: str = ARCHIVE_OPERATION_CHECK
    archive_url: str = ""
    warnings: tuple[str, ...] = ()
    provider_id: str = ARCHIVE_PROVIDER_WAYBACK
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_url": self.archive_url or self.snapshot_url,
            "archive_status": self.archive_status,
            "operation": self.operation,
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


@dataclass(frozen=True)
class WaybackSnapshotRecord:
    url: str
    snapshot_url: str
    saved_at: str
    archive_status: str = ARCHIVE_STATUS_FOUND
    operation: str = ARCHIVE_OPERATION_LIST
    provider_id: str = ARCHIVE_PROVIDER_WAYBACK
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_status": self.archive_status,
            "operation": self.operation,
            "provider_id": self.provider_id,
            "saved_at": self.saved_at,
            "scope": self.scope,
            "snapshot_url": self.snapshot_url,
            "url": self.url,
        }


@dataclass(frozen=True)
class WaybackSubmitPlan:
    url: str
    requested_at_utc: str
    operation: str = ARCHIVE_OPERATION_SUBMIT
    explicit_user_intent_required: bool = True
    submission_execution: str = "not executed"
    provider_id: str = ARCHIVE_PROVIDER_WAYBACK
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "explicit_user_intent_required": self.explicit_user_intent_required,
            "operation": self.operation,
            "provider_id": self.provider_id,
            "requested_at_utc": self.requested_at_utc,
            "scope": self.scope,
            "submission_execution": self.submission_execution,
            "url": self.url,
        }


@dataclass(frozen=True)
class WaybackSubmitMockResult:
    url: str
    archive_status: str
    submitted_at_utc: str
    archive_url: str = ""
    submission_id: str = ""
    operation: str = ARCHIVE_OPERATION_SUBMIT
    warnings: tuple[str, ...] = ()
    provider_id: str = ARCHIVE_PROVIDER_WAYBACK
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_status": self.archive_status,
            "archive_url": self.archive_url,
            "operation": self.operation,
            "provider_id": self.provider_id,
            "scope": self.scope,
            "submission_id": self.submission_id,
            "submitted_at_utc": self.submitted_at_utc,
            "url": self.url,
            "warnings": list(self.warnings),
        }


def list_wayback_snapshots_from_fixture(
    url: str,
    snapshots: tuple[Mapping[str, Any], ...],
) -> tuple[WaybackSnapshotRecord, ...]:
    return tuple(
        WaybackSnapshotRecord(
            url=url,
            snapshot_url=str(snapshot.get("snapshot_url") or snapshot.get("archive_url") or ""),
            saved_at=str(snapshot.get("saved_at") or snapshot.get("timestamp") or ""),
            archive_status=str(snapshot.get("archive_status") or ARCHIVE_STATUS_FOUND),
        )
        for snapshot in snapshots
        if str(snapshot.get("snapshot_url") or snapshot.get("archive_url") or "")
    )


def build_wayback_availability_from_fixture(
    url: str,
    *,
    snapshots: tuple[Mapping[str, Any], ...] = (),
) -> WaybackCheckResult:
    records = list_wayback_snapshots_from_fixture(url, snapshots)
    if not records:
        return WaybackCheckResult(
            url=url,
            archive_status=ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
            operation=ARCHIVE_OPERATION_CHECK,
        )
    newest = sorted(records, key=lambda item: (item.saved_at, item.snapshot_url))[-1]
    return WaybackCheckResult(
        url=url,
        archive_status=ARCHIVE_STATUS_FOUND,
        snapshot_url=newest.snapshot_url,
        archive_url=newest.snapshot_url,
        saved_at=newest.saved_at,
        operation=ARCHIVE_OPERATION_CHECK,
    )


def build_wayback_submit_plan(url: str, *, requested_at_utc: str) -> WaybackSubmitPlan:
    return WaybackSubmitPlan(url=url, requested_at_utc=requested_at_utc)


def build_wayback_mock_submit_result(
    url: str,
    *,
    submitted_at_utc: str,
    archive_url: str = "",
    submission_id: str = "",
    completed: bool = False,
) -> WaybackSubmitMockResult:
    return WaybackSubmitMockResult(
        url=url,
        archive_status=ARCHIVE_STATUS_SUBMISSION_COMPLETED
        if completed
        else ARCHIVE_STATUS_SUBMISSION_STARTED,
        archive_url=archive_url,
        submission_id=submission_id,
        submitted_at_utc=submitted_at_utc,
    )


def mock_found_wayback_result(url: str, *, snapshot_url: str, saved_at: str) -> WaybackCheckResult:
    return WaybackCheckResult(
        url=url,
        archive_status=ARCHIVE_STATUS_FOUND,
        snapshot_url=snapshot_url,
        archive_url=snapshot_url,
        saved_at=saved_at,
    )
