from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from capture_archive_providers import (
    ARCHIVE_CHALLENGE_USER_HANDOFF,
    ARCHIVE_OPERATION_CHECK,
    ARCHIVE_OPERATION_POLL,
    ARCHIVE_OPERATION_SUBMIT,
    ARCHIVE_PROVIDER_ARCHIVE_TODAY,
    ARCHIVE_PROVIDER_SCOPE,
)
from capture_status import (
    ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER,
    ARCHIVE_STATUS_FORMAT_CHANGED,
    ARCHIVE_STATUS_FOUND,
    ARCHIVE_STATUS_NETWORK_ERROR,
    ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
    ARCHIVE_STATUS_SUBMISSION_STARTED,
    ARCHIVE_STATUS_UNKNOWN,
    ARCHIVE_STATUS_WIP,
)


ArchiveTodayLookup = Callable[[str], Mapping[str, Any]]

ARCHIVE_TODAY_STATE_AVAILABLE = "available"
ARCHIVE_TODAY_STATE_NOT_FOUND = "not_found"
ARCHIVE_TODAY_STATE_SUBMITTED = "submitted"
ARCHIVE_TODAY_STATE_POLLING = "polling"
ARCHIVE_TODAY_STATE_WIP = "WIP"
ARCHIVE_TODAY_STATE_MIRROR_FORMAT_ERROR = "mirror_format_error"
ARCHIVE_TODAY_STATE_CHALLENGE_REQUIRED = "challenge_required"
ARCHIVE_TODAY_STATE_FAILED = "failed"

ARCHIVE_TODAY_STATES = (
    ARCHIVE_TODAY_STATE_AVAILABLE,
    ARCHIVE_TODAY_STATE_NOT_FOUND,
    ARCHIVE_TODAY_STATE_SUBMITTED,
    ARCHIVE_TODAY_STATE_POLLING,
    ARCHIVE_TODAY_STATE_WIP,
    ARCHIVE_TODAY_STATE_MIRROR_FORMAT_ERROR,
    ARCHIVE_TODAY_STATE_CHALLENGE_REQUIRED,
    ARCHIVE_TODAY_STATE_FAILED,
)

_STATE_TO_ARCHIVE_STATUS = {
    ARCHIVE_TODAY_STATE_AVAILABLE: ARCHIVE_STATUS_FOUND,
    ARCHIVE_TODAY_STATE_NOT_FOUND: ARCHIVE_STATUS_NOT_FOUND_CONFIRMED,
    ARCHIVE_TODAY_STATE_SUBMITTED: ARCHIVE_STATUS_SUBMISSION_STARTED,
    ARCHIVE_TODAY_STATE_POLLING: ARCHIVE_STATUS_WIP,
    ARCHIVE_TODAY_STATE_WIP: ARCHIVE_STATUS_WIP,
    ARCHIVE_TODAY_STATE_MIRROR_FORMAT_ERROR: ARCHIVE_STATUS_FORMAT_CHANGED,
    ARCHIVE_TODAY_STATE_CHALLENGE_REQUIRED: ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER,
    ARCHIVE_TODAY_STATE_FAILED: ARCHIVE_STATUS_NETWORK_ERROR,
}


@dataclass(frozen=True)
class ArchiveTodayCheckResult:
    url: str
    archive_status: str
    snapshot_url: str = ""
    saved_at: str = ""
    fixture_state: str = ""
    operation: str = ARCHIVE_OPERATION_CHECK
    challenge_required: bool = False
    challenge_handoff: Mapping[str, Any] | None = None
    warnings: tuple[str, ...] = ()
    provider_id: str = ARCHIVE_PROVIDER_ARCHIVE_TODAY
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_status": self.archive_status,
            "challenge_handoff": dict(self.challenge_handoff or {}),
            "challenge_required": self.challenge_required,
            "fixture_state": self.fixture_state,
            "operation": self.operation,
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
        fixture_state=str(payload.get("fixture_state") or ""),
        operation=str(payload.get("operation") or ARCHIVE_OPERATION_CHECK),
        challenge_required=bool(payload.get("challenge_required"))
        or status == ARCHIVE_STATUS_CHALLENGE_REQUIRES_USER,
        challenge_handoff=payload.get("challenge_handoff")
        if isinstance(payload.get("challenge_handoff"), Mapping)
        else None,
        warnings=tuple(str(warning) for warning in payload.get("warnings", ()) if str(warning)),
    )


@dataclass(frozen=True)
class ArchiveTodaySubmitPlan:
    url: str
    mirror: str = "archive.today"
    operation: str = ARCHIVE_OPERATION_SUBMIT
    explicit_user_intent_required: bool = True
    submission_execution: str = "not executed"
    provider_id: str = ARCHIVE_PROVIDER_ARCHIVE_TODAY
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "explicit_user_intent_required": self.explicit_user_intent_required,
            "mirror": self.mirror,
            "operation": self.operation,
            "provider_id": self.provider_id,
            "scope": self.scope,
            "submission_execution": self.submission_execution,
            "url": self.url,
        }


@dataclass(frozen=True)
class ArchiveTodayChallengeHandoff:
    url: str
    mirror: str
    reason: str
    operation: str = ARCHIVE_OPERATION_POLL
    challenge_mode: str = ARCHIVE_CHALLENGE_USER_HANDOFF
    browser_handoff_only: bool = True
    provider_id: str = ARCHIVE_PROVIDER_ARCHIVE_TODAY
    scope: str = ARCHIVE_PROVIDER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "browser_handoff_only": self.browser_handoff_only,
            "challenge_mode": self.challenge_mode,
            "mirror": self.mirror,
            "operation": self.operation,
            "provider_id": self.provider_id,
            "reason": self.reason,
            "scope": self.scope,
            "url": self.url,
        }


def build_archive_today_submit_plan(
    url: str,
    *,
    mirror: str = "archive.today",
) -> ArchiveTodaySubmitPlan:
    return ArchiveTodaySubmitPlan(url=url, mirror=mirror)


def build_archive_today_challenge_handoff(
    url: str,
    *,
    mirror: str = "archive.today",
    reason: str = "challenge_required",
) -> ArchiveTodayChallengeHandoff:
    return ArchiveTodayChallengeHandoff(url=url, mirror=mirror, reason=reason)


def build_archive_today_mock_result(
    url: str,
    *,
    fixture_state: str,
    snapshot_url: str = "",
    saved_at: str = "",
    mirror: str = "archive.today",
) -> ArchiveTodayCheckResult:
    state = fixture_state if fixture_state in ARCHIVE_TODAY_STATES else ARCHIVE_TODAY_STATE_FAILED
    challenge = state == ARCHIVE_TODAY_STATE_CHALLENGE_REQUIRED
    handoff = build_archive_today_challenge_handoff(url, mirror=mirror).to_dict() if challenge else None
    return ArchiveTodayCheckResult(
        url=url,
        archive_status=_STATE_TO_ARCHIVE_STATUS.get(state, ARCHIVE_STATUS_UNKNOWN),
        snapshot_url=snapshot_url,
        saved_at=saved_at,
        fixture_state=state,
        operation=ARCHIVE_OPERATION_POLL
        if state in {ARCHIVE_TODAY_STATE_POLLING, ARCHIVE_TODAY_STATE_WIP}
        else ARCHIVE_OPERATION_CHECK,
        challenge_required=challenge,
        challenge_handoff=handoff,
        warnings=(
            "archive.today challenge requires normal-browser manual handoff; automated challenge handling is not implemented.",
        )
        if challenge
        else (),
    )
