from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from capture_action_log import ACTOR_TYPE_APPLICATION, CaptureActionLogEvent, build_action_log_event
from capture_status import OPERATIONAL_STATUS_MODEL_ONLY
from source_resource_state import DiscussionCaptureOptions, SourceResourceRowState


CAPTURE_CONTROLLER_SCOPE = (
    "operational capture controller plan only; no fetch, browser, screenshot, archive, "
    "download, provider, credential, external process, database, or GUI side effect"
)


@dataclass(frozen=True)
class OperationalCapturePlanResult:
    source_row_id: str
    source_title: str
    adapter_id: str
    canonical_url: str
    selected_modes: tuple[str, ...] = ()
    screenshot_intents: tuple[str, ...] = ()
    operational_status: str = OPERATIONAL_STATUS_MODEL_ONLY
    action_events: tuple[CaptureActionLogEvent, ...] = ()
    warnings: tuple[str, ...] = ()
    scope: str = CAPTURE_CONTROLLER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_events": [event.to_dict() for event in self.action_events],
            "adapter_id": self.adapter_id,
            "canonical_url": self.canonical_url,
            "operational_status": self.operational_status,
            "scope": self.scope,
            "screenshot_intents": list(self.screenshot_intents),
            "selected_modes": list(self.selected_modes),
            "source_row_id": self.source_row_id,
            "source_title": self.source_title,
            "warnings": list(self.warnings),
        }


def build_operational_capture_plan(
    *,
    row: SourceResourceRowState,
    discussion: DiscussionCaptureOptions,
    timestamp_utc: str = "2026-07-16T00:00:00Z",
) -> OperationalCapturePlanResult:
    selected_modes: list[str] = []
    screenshot_intents: list[str] = []
    warnings: list[str] = []

    if discussion.webpage_active:
        selected_modes.append("webpage")
    if discussion.comments_selected and discussion.comments_supported:
        selected_modes.append("comments")
    elif discussion.comments_selected:
        warnings.append("Comments mode is selected but not supported by this source.")
    if discussion.livechat_selected and discussion.livechat_supported:
        selected_modes.append("livechat")
    elif discussion.livechat_selected:
        warnings.append("Livechat mode is selected but not supported by this source.")

    if discussion.webpage_screenshot_active:
        screenshot_intents.append("webpage")
    if discussion.comments_screenshot_active:
        screenshot_intents.append("comments")
    if discussion.livechat_screenshot_active:
        screenshot_intents.append("livechat")

    if not selected_modes:
        warnings.append("No active supported capture mode was selected.")

    action_event = build_action_log_event(
        session_id=f"source_row_{row.row_id}",
        actor_type=ACTOR_TYPE_APPLICATION,
        action_type="operational_capture_plan_created",
        result=OPERATIONAL_STATUS_MODEL_ONLY,
        timestamp_utc=timestamp_utc,
        source_id=row.row_id,
        request_summary={
            "adapter_id": row.adapter_id,
            "canonical_url": row.canonical_url,
            "selected_modes": tuple(selected_modes),
            "screenshot_intents": tuple(screenshot_intents),
        },
        warnings=tuple(warnings),
    )

    return OperationalCapturePlanResult(
        source_row_id=row.row_id,
        source_title=row.title,
        adapter_id=row.adapter_id,
        canonical_url=row.canonical_url,
        selected_modes=tuple(selected_modes),
        screenshot_intents=tuple(screenshot_intents),
        action_events=(action_event,),
        warnings=tuple(warnings),
    )


def format_operational_capture_plan_message(result: OperationalCapturePlanResult) -> str:
    modes = ", ".join(result.selected_modes) if result.selected_modes else "(none)"
    screenshots = ", ".join(result.screenshot_intents) if result.screenshot_intents else "(none)"
    warnings = "\n".join(f"- {warning}" for warning in result.warnings) if result.warnings else "- (none)"
    return "\n".join(
        [
            "Operational site-capture plan",
            f"Source: {result.source_title}",
            f"Adapter: {result.adapter_id}",
            f"Selected modes: {modes}",
            f"Screenshot intents: {screenshots}",
            "Network actions performed: none",
            "Screenshots performed: none",
            "Downloads performed: none",
            "Archives performed: none",
            "Warnings:",
            warnings,
        ]
    )
