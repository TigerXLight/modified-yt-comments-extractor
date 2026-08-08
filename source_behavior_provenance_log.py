from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable, Mapping


class BehaviorActionType(str, Enum):
    URL_ENTERED = "url_entered"
    GET_CLICKED = "get_clicked"
    POSTS_SELECTED = "posts_selected"
    COMMENTS_SELECTED = "comments_selected"
    LIVECHAT_SELECTED = "livechat_selected"
    MEDIA_SELECTED = "media_selected"
    SCREENSHOT_SELECTED = "screenshot_selected"
    ARCHIVE_CHECK_SELECTED = "archive_check_selected"
    ARCHIVE_SUBMIT_SELECTED = "archive_submit_selected"
    TRANSCRIPT_EDITED = "transcript_edited"
    FILE_INJECTED_INTO_TRANSCRIPT_EDITOR = "file_injected_into_transcript_editor"
    MEDIA_DOWNLOAD_SELECTED = "media_download_selected"
    MANUAL_SOURCE_NOTE_ADDED = "manual_source_note_added"
    DATABASE_REVIEW_PREVIEWED = "database_review_previewed"
    DATABASE_MIGRATION_PREVIEWED = "database_migration_previewed"
    EVIDENCE_MOVEMENT_PREVIEWED = "evidence_movement_previewed"
    EVIDENCE_MOVEMENT_APPROVED = "evidence_movement_approved"
    COMPLETED_EVIDENCE_RECEIPT_GENERATED = "completed_evidence_receipt_generated"
    SOURCE_URL_MEDIA_ROW_CREATED = "source_url_media_row_created"
    OPERATOR_COMMAND_PACK_CREATED = "operator_command_pack_created"
    MANUAL_SMOKE_CHECKLIST_CREATED = "manual_smoke_checklist_created"


@dataclass(frozen=True)
class AccountableWitnessRecord:
    witness_id: str
    witness_role: str
    display_label: str
    observed_or_authored_at_utc: str | None = None
    captured_by_user_at_utc: str | None = None
    source_item_ref: str | None = None
    evidence_proof_ref: str | None = None
    source_role_scope: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BehaviorLogEntry:
    entry_id: str
    timestamp_utc: str
    action_type: BehaviorActionType
    session_id: str
    actor_label: str
    source_url: str | None = None
    item_ref: str | None = None
    details: Mapping[str, object] = field(default_factory=dict)
    previous_entry_hash: str = ""
    redacted: bool = True
    secrets_redacted: bool = True

    def safe_payload(self) -> dict[str, object]:
        details = dict(self.details)
        for key in list(details):
            if any(token in key.lower() for token in ("secret", "cookie", "password", "authorization", "api_key", "token")):
                details[key] = "[REDACTED]"
        return {
            "entry_id": self.entry_id,
            "timestamp_utc": self.timestamp_utc,
            "action_type": self.action_type.value,
            "session_id": self.session_id,
            "actor_label": self.actor_label,
            "source_url": self.source_url,
            "item_ref": self.item_ref,
            "details": details,
            "previous_entry_hash": self.previous_entry_hash,
            "redacted": self.redacted,
            "secrets_redacted": self.secrets_redacted,
        }

    def entry_hash(self) -> str:
        payload = json.dumps(self.safe_payload(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict[str, object]:
        payload = self.safe_payload()
        payload["entry_hash"] = self.entry_hash()
        return payload


@dataclass(frozen=True)
class BehaviorProvenanceLog:
    log_id: str
    entries: tuple[BehaviorLogEntry, ...]
    witnesses: tuple[AccountableWitnessRecord, ...] = ()
    hash_chained: bool = True
    completed_evidence_claimed: bool = False
    file_movement_performed: bool = False

    def validate_chain(self) -> bool:
        previous = ""
        for entry in self.entries:
            if entry.previous_entry_hash != previous:
                return False
            previous = entry.entry_hash()
        return True

    def to_dict(self) -> dict[str, object]:
        return {
            "log_id": self.log_id,
            "entry_count": len(self.entries),
            "witness_count": len(self.witnesses),
            "hash_chained": self.hash_chained,
            "chain_valid": self.validate_chain(),
            "completed_evidence_claimed": self.completed_evidence_claimed,
            "file_movement_performed": self.file_movement_performed,
            "entries": [entry.to_dict() for entry in self.entries],
            "witnesses": [witness.to_dict() for witness in self.witnesses],
        }


def chain_behavior_entries(entries: Iterable[BehaviorLogEntry]) -> tuple[BehaviorLogEntry, ...]:
    chained: list[BehaviorLogEntry] = []
    previous = ""
    for entry in entries:
        chained_entry = BehaviorLogEntry(
            entry_id=entry.entry_id,
            timestamp_utc=entry.timestamp_utc,
            action_type=entry.action_type,
            session_id=entry.session_id,
            actor_label=entry.actor_label,
            source_url=entry.source_url,
            item_ref=entry.item_ref,
            details=entry.details,
            previous_entry_hash=previous,
            redacted=entry.redacted,
            secrets_redacted=entry.secrets_redacted,
        )
        chained.append(chained_entry)
        previous = chained_entry.entry_hash()
    return tuple(chained)


def build_example_behavior_provenance_log() -> BehaviorProvenanceLog:
    raw_entries = (
        BehaviorLogEntry(
            entry_id="entry_url_1",
            timestamp_utc="2026-08-08T18:00:00Z",
            action_type=BehaviorActionType.URL_ENTERED,
            session_id="session_example",
            actor_label="operator",
            source_url="https://news.invalid/story",
        ),
        BehaviorLogEntry(
            entry_id="entry_get_1",
            timestamp_utc="2026-08-08T18:00:10Z",
            action_type=BehaviorActionType.GET_CLICKED,
            session_id="session_example",
            actor_label="operator",
            source_url="https://news.invalid/story",
            details={"capture_options": ["comments", "archive_check", "screenshot"]},
        ),
        BehaviorLogEntry(
            entry_id="entry_note_1",
            timestamp_utc="2026-08-08T18:01:00Z",
            action_type=BehaviorActionType.MANUAL_SOURCE_NOTE_ADDED,
            session_id="session_example",
            actor_label="operator",
            source_url="https://news.invalid/story",
            details={"note": "Publisher byline and visible timestamp recorded."},
        ),
    )
    witnesses = (
        AccountableWitnessRecord(
            witness_id="publisher_byline",
            witness_role="article_author_or_publisher_byline",
            display_label="Visible article byline/publisher author",
            observed_or_authored_at_utc="2026-06-01T12:00:00Z",
            source_item_ref="source_url:https://news.invalid/story",
            source_role_scope="Authored source for the article text/framing, not automatic primary source for every claim.",
        ),
        AccountableWitnessRecord(
            witness_id="software_operator",
            witness_role="software_operator_capture_witness",
            display_label="User/operator who captured the source",
            captured_by_user_at_utc="2026-08-08T18:00:00Z",
            evidence_proof_ref="hash_chain:session_example",
            source_role_scope="Witness to access/capture event and selected capture settings.",
        ),
    )
    return BehaviorProvenanceLog(
        log_id="behavior_log_example",
        entries=chain_behavior_entries(raw_entries),
        witnesses=witnesses,
    )


def build_source_operational_behavior_log(
    *,
    session_id: str,
    source_url: str,
    timestamp_utc: str = "2026-08-08T00:00:00Z",
    actor_label: str = "operator",
    movement_preview_ref: str = "",
    completed_receipt_ref: str = "",
    previous_hash: str = "",
) -> BehaviorProvenanceLog:
    """Build a non-live source workflow action log with redacted hash chaining."""

    raw_entries = (
        BehaviorLogEntry(
            entry_id=f"{session_id}_url_entered",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.URL_ENTERED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            previous_entry_hash=previous_hash,
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_get_clicked",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.GET_CLICKED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            details={"selected_scopes": ["article", "comments", "media", "archive_check"]},
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_media_row",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.SOURCE_URL_MEDIA_ROW_CREATED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            details={"download_selected": False, "injection_separate_from_download": True},
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_comments_selected",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.COMMENTS_SELECTED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            details={"manual_or_fixture_only": True},
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_archive_check_selected",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.ARCHIVE_CHECK_SELECTED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            details={"provider_call_performed": False, "submit_performed": False},
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_movement_previewed",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.EVIDENCE_MOVEMENT_PREVIEWED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            item_ref=movement_preview_ref,
            details={"dry_run": True, "file_movement_performed": False},
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_operator_command_pack",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.OPERATOR_COMMAND_PACK_CREATED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            details={"approval_required": True, "not_live_executed": True},
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_manual_smoke_checklist",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.MANUAL_SMOKE_CHECKLIST_CREATED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            details={"operator_approval_required": True, "not_live_executed": True},
        ),
        BehaviorLogEntry(
            entry_id=f"{session_id}_completed_receipt_placeholder",
            timestamp_utc=timestamp_utc,
            action_type=BehaviorActionType.COMPLETED_EVIDENCE_RECEIPT_GENERATED,
            session_id=session_id,
            actor_label=actor_label,
            source_url=source_url,
            item_ref=completed_receipt_ref,
            details={
                "completed_evidence_claimed": bool(completed_receipt_ref),
                "requires_verified_hash_receipt": True,
            },
        ),
    )
    chained = chain_behavior_entries(raw_entries)
    return BehaviorProvenanceLog(
        log_id=f"source_operational_behavior_log_{session_id}",
        entries=chained,
        witnesses=(
            AccountableWitnessRecord(
                witness_id=f"{session_id}_operator",
                witness_role="operator_review_witness",
                display_label=actor_label,
                captured_by_user_at_utc=timestamp_utc,
                source_item_ref=source_url,
                evidence_proof_ref=f"hash_chain:{session_id}",
            ),
        ),
        completed_evidence_claimed=bool(completed_receipt_ref),
        file_movement_performed=False,
    )
