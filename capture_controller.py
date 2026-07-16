from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from capture_action_log import ACTOR_TYPE_APPLICATION, CaptureActionLogEvent, build_action_log_event
from capture_contracts import (
    ARTIFACT_TYPE_ACCESSIBILITY_TREE,
    ARTIFACT_TYPE_ACTION_LOG,
    ARTIFACT_TYPE_ARTICLE_TEXT,
    ARTIFACT_TYPE_COMMENTS_JSONL,
    ARTIFACT_TYPE_COMMENTS_TEXT,
    ARTIFACT_TYPE_DOM_SNAPSHOT,
    ARTIFACT_TYPE_FINAL_DOM,
    ARTIFACT_TYPE_LIVECHAT_JSONL,
    ARTIFACT_TYPE_LIVECHAT_TEXT,
    ARTIFACT_TYPE_MHTML,
    ARTIFACT_TYPE_PAGE_OUTLINE,
    ARTIFACT_TYPE_RAW_HTML,
    ARTIFACT_TYPE_SCREENSHOT,
    CaptureArtifact,
    build_capture_artifact,
)
from capture_status import COMPLETENESS_COMPLETE, FIDELITY_RAW, OPERATIONAL_STATUS_MODEL_ONLY
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
    declared_artifacts: tuple[CaptureArtifact, ...] = ()
    action_log_artifact: CaptureArtifact | None = None
    warnings: tuple[str, ...] = ()
    scope: str = CAPTURE_CONTROLLER_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_events": [event.to_dict() for event in self.action_events],
            "action_log_artifact": self.action_log_artifact.to_dict()
            if self.action_log_artifact is not None
            else None,
            "declared_artifacts": [artifact.to_dict() for artifact in self.declared_artifacts],
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


def _action_log_jsonl(events: tuple[CaptureActionLogEvent, ...]) -> str:
    return "\n".join(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":")) for event in events) + "\n"


def _action_log_sha256(events: tuple[CaptureActionLogEvent, ...]) -> str:
    return hashlib.sha256(_action_log_jsonl(events).encode("utf-8")).hexdigest()


def _planned_artifact(
    *,
    row: SourceResourceRowState,
    artifact_type: str,
    capture_method: str,
    relative_path: str,
    timestamp_utc: str,
    metadata: dict[str, Any] | None = None,
    transformations: tuple[dict[str, Any], ...] = (),
) -> CaptureArtifact:
    return build_capture_artifact(
        session_id=f"source_row_{row.row_id}",
        source_url=row.canonical_url,
        artifact_type=artifact_type,
        capture_method=capture_method,
        relative_path=relative_path,
        created_at_utc=timestamp_utc,
        source_id=row.row_id,
        canonical_url=row.canonical_url,
        scope="localhost_fixture_plan_only",
        adapter_id=row.adapter_id,
        metadata={
            "execution": "not executed",
            "network_actions_performed": "none",
            "source": "selected source fixture plan",
            **(metadata or {}),
        },
        transformations=transformations,
    )


def _planned_capture_artifacts(
    *,
    row: SourceResourceRowState,
    selected_modes: tuple[str, ...],
    screenshot_intents: tuple[str, ...],
    timestamp_utc: str,
) -> tuple[CaptureArtifact, ...]:
    artifacts: list[CaptureArtifact] = []
    if "webpage" in selected_modes:
        artifacts.extend(
            (
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_RAW_HTML,
                    capture_method="planned_supplied_raw_html_snapshot",
                    relative_path="page/raw.html",
                    timestamp_utc=timestamp_utc,
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_FINAL_DOM,
                    capture_method="planned_supplied_final_dom_snapshot",
                    relative_path="page/final_dom.html",
                    timestamp_utc=timestamp_utc,
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_MHTML,
                    capture_method="planned_mhtml_placeholder_metadata",
                    relative_path="page/page.mhtml",
                    timestamp_utc=timestamp_utc,
                    metadata={"placeholder": True},
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_DOM_SNAPSHOT,
                    capture_method="planned_dom_text_snapshot",
                    relative_path="page/dom_snapshot.json",
                    timestamp_utc=timestamp_utc,
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_ACCESSIBILITY_TREE,
                    capture_method="planned_accessibility_text_snapshot",
                    relative_path="page/accessibility_tree.json",
                    timestamp_utc=timestamp_utc,
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_ARTICLE_TEXT,
                    capture_method="planned_article_semantic_extraction",
                    relative_path="article/article.txt",
                    timestamp_utc=timestamp_utc,
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_PAGE_OUTLINE,
                    capture_method="planned_visible_page_outline",
                    relative_path="page/outline.json",
                    timestamp_utc=timestamp_utc,
                ),
            )
        )
    if "comments" in selected_modes:
        artifacts.extend(
            (
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_COMMENTS_JSONL,
                    capture_method="planned_comments_structured_jsonl",
                    relative_path="comments/comments.jsonl",
                    timestamp_utc=timestamp_utc,
                    metadata={
                        "dedupe_required": True,
                        "nested_replies_supported": True,
                        "text_output_must_not_mix_with_article": True,
                    },
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_COMMENTS_TEXT,
                    capture_method="planned_comments_review_text",
                    relative_path="comments/comments.txt",
                    timestamp_utc=timestamp_utc,
                    metadata={
                        "human_review_output": True,
                        "text_output_must_not_mix_with_article": True,
                    },
                ),
            )
        )
    if "livechat" in selected_modes:
        artifacts.extend(
            (
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_LIVECHAT_JSONL,
                    capture_method="planned_livechat_events_jsonl",
                    relative_path="livechat/livechat.jsonl",
                    timestamp_utc=timestamp_utc,
                    metadata={
                        "bounded_capture_metadata_required": True,
                        "dedupe_required": True,
                        "screenshot_frames_complete_chat_capture": False,
                        "text_events_primary": True,
                    },
                ),
                _planned_artifact(
                    row=row,
                    artifact_type=ARTIFACT_TYPE_LIVECHAT_TEXT,
                    capture_method="planned_livechat_review_text",
                    relative_path="livechat/livechat.txt",
                    timestamp_utc=timestamp_utc,
                    metadata={
                        "human_review_output": True,
                        "screenshot_frames_complete_chat_capture": False,
                    },
                ),
            )
        )
    for intent in screenshot_intents:
        artifacts.append(
            _planned_artifact(
                row=row,
                artifact_type=ARTIFACT_TYPE_SCREENSHOT,
                capture_method=f"planned_{intent}_faithful_screenshot",
                relative_path=f"screenshots/{intent}.png",
                timestamp_utc=timestamp_utc,
                metadata={
                    "fixture_or_supplied_local_input": True,
                    "normal_user_appearance_claim": "planned faithful fixture/local input only",
                    "screenshot_intent": intent,
                    "screenshot_kind": "faithful",
                },
            )
        )
    return tuple(artifacts)


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
    selected_modes_tuple = tuple(selected_modes)
    screenshot_intents_tuple = tuple(screenshot_intents)
    declared_artifacts = _planned_capture_artifacts(
        row=row,
        selected_modes=selected_modes_tuple,
        screenshot_intents=screenshot_intents_tuple,
        timestamp_utc=timestamp_utc,
    )

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
            "selected_modes": selected_modes_tuple,
            "screenshot_intents": screenshot_intents_tuple,
        },
        warnings=tuple(warnings),
    )
    previous_hash = action_event.event_hash
    action_events: list[CaptureActionLogEvent] = [action_event]
    if declared_artifacts:
        declaration_event = build_action_log_event(
            session_id=f"source_row_{row.row_id}",
            actor_type=ACTOR_TYPE_APPLICATION,
            action_type="operational_capture_artifacts_declared",
            result=OPERATIONAL_STATUS_MODEL_ONLY,
            timestamp_utc=timestamp_utc,
            previous_event_hash=previous_hash,
            source_id=row.row_id,
            artifact_ids=tuple(artifact.artifact_id for artifact in declared_artifacts),
            request_summary={
                "artifact_count": len(declared_artifacts),
                "artifact_types": tuple(artifact.artifact_type for artifact in declared_artifacts),
                "write_performed": False,
            },
            warnings=tuple(warnings),
        )
        action_events.append(declaration_event)
        previous_hash = declaration_event.event_hash
    action_log_relative_path = f"capture/{row.row_id}/action_log.jsonl"
    provisional_action_log_artifact = build_capture_artifact(
        session_id=f"source_row_{row.row_id}",
        source_url=row.canonical_url,
        artifact_type=ARTIFACT_TYPE_ACTION_LOG,
        capture_method="operational_capture_plan_action_log",
        relative_path=action_log_relative_path,
        completeness=COMPLETENESS_COMPLETE,
        fidelity=FIDELITY_RAW,
        created_at_utc=timestamp_utc,
        source_id=row.row_id,
        canonical_url=row.canonical_url,
        scope="localhost_fixture_plan_only",
        adapter_id=row.adapter_id,
        metadata={
            "execution": "not executed",
            "network_actions_performed": "none",
            "screenshots_performed": "none",
            "downloads_performed": "none",
            "archives_performed": "none",
        },
    )
    artifact_event = build_action_log_event(
        session_id=f"source_row_{row.row_id}",
        actor_type=ACTOR_TYPE_APPLICATION,
        action_type="operational_capture_action_log_artifact_declared",
        result=OPERATIONAL_STATUS_MODEL_ONLY,
        timestamp_utc=timestamp_utc,
        previous_event_hash=previous_hash,
        source_id=row.row_id,
        target_id=provisional_action_log_artifact.artifact_id,
        artifact_ids=(provisional_action_log_artifact.artifact_id,),
        request_summary={
            "artifact_type": ARTIFACT_TYPE_ACTION_LOG,
            "relative_path": action_log_relative_path,
            "write_performed": False,
        },
        warnings=tuple(warnings),
    )
    action_events.append(artifact_event)
    action_events_tuple = tuple(action_events)
    action_log_artifact = build_capture_artifact(
        session_id=f"source_row_{row.row_id}",
        source_url=row.canonical_url,
        artifact_type=ARTIFACT_TYPE_ACTION_LOG,
        capture_method="operational_capture_plan_action_log",
        relative_path=action_log_relative_path,
        sha256=_action_log_sha256(action_events_tuple),
        completeness=COMPLETENESS_COMPLETE,
        fidelity=FIDELITY_RAW,
        created_at_utc=timestamp_utc,
        source_id=row.row_id,
        canonical_url=row.canonical_url,
        scope="localhost_fixture_plan_only",
        adapter_id=row.adapter_id,
        metadata={
            "execution": "not executed",
            "event_count": len(action_events_tuple),
            "network_actions_performed": "none",
            "screenshots_performed": "none",
            "downloads_performed": "none",
            "archives_performed": "none",
        },
    )

    return OperationalCapturePlanResult(
        source_row_id=row.row_id,
        source_title=row.title,
        adapter_id=row.adapter_id,
        canonical_url=row.canonical_url,
        selected_modes=tuple(selected_modes),
        screenshot_intents=tuple(screenshot_intents),
        action_events=action_events_tuple,
        declared_artifacts=declared_artifacts,
        action_log_artifact=action_log_artifact,
        warnings=tuple(warnings),
    )


def format_operational_capture_plan_message(result: OperationalCapturePlanResult) -> str:
    modes = ", ".join(result.selected_modes) if result.selected_modes else "(none)"
    screenshots = ", ".join(result.screenshot_intents) if result.screenshot_intents else "(none)"
    action_log = (
        f"{result.action_log_artifact.relative_path} "
        f"({result.action_log_artifact.sha256[:12]}...)"
        if result.action_log_artifact is not None
        else "(none)"
    )
    warnings = "\n".join(f"- {warning}" for warning in result.warnings) if result.warnings else "- (none)"
    return "\n".join(
        [
            "Operational site-capture plan",
            f"Source: {result.source_title}",
            f"Adapter: {result.adapter_id}",
            f"Selected modes: {modes}",
            f"Screenshot intents: {screenshots}",
            f"Action log artifact: {action_log}",
            "Network actions performed: none",
            "Screenshots performed: none",
            "Downloads performed: none",
            "Archives performed: none",
            "Warnings:",
            warnings,
        ]
    )
