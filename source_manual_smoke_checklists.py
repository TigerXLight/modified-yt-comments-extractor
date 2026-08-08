from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from source_named_site_method_packs import (
    SourceNamedSiteMethodPackCollection,
    build_source_named_site_method_pack_collection,
)


SOURCE_MANUAL_SMOKE_CHECKLISTS_SCHEMA_VERSION = "source_manual_smoke_checklists_v1"


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


def _stable_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(str(value or "").strip() for value in values if str(value or "").strip()))


CHECKLIST_GROUPS = (
    ("msn_manual_smoke", ("msn_article", "msn_shadow_dom_comments")),
    ("twitter_x_archive_manual_smoke", ("twitter_x_public_post_archive_manual_import", "twitter_x_reply_thread_archive_manual_import")),
    ("youtube_transcript_comment_smoke", ("youtube_media_transcript", "youtube_comments")),
    ("generic_article_comment_smoke", ("generic_article_html", "generic_comments_manual_import", "generic_comments_site_specific_selector")),
    ("archive_only_import_smoke", ("generic_comments_archive_only_import", "archive_only_import")),
)


@dataclass(frozen=True)
class SourceManualSmokeChecklistRow:
    checklist_row_id: str
    checklist_pack_id: str
    method_id: str
    scope: str
    manual_instruction: str
    expected_receipt_refs: tuple[str, ...]
    expected_artifact_refs: tuple[str, ...]
    no_live_execution_status: str = "not_live_executed"
    operator_approval_required: bool = True
    result_placeholder: str = "manual_result_not_recorded"
    metadata_only: bool = True
    executed: bool = False
    completed_evidence_claimed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceManualSmokeChecklistPack:
    checklist_pack_id: str
    group_id: str
    title: str
    rows: tuple[SourceManualSmokeChecklistRow, ...]
    approval_requirement: str = "operator_site_and_action_approval_required"
    no_live_execution_status: str = "no_live_execution_performed"
    metadata_only: bool = True
    user_review_required: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    completed_evidence_claimed: bool = False

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["row_count"] = self.row_count
        return data


@dataclass(frozen=True)
class SourceManualSmokeChecklistCollection:
    collection_id: str
    packs: tuple[SourceManualSmokeChecklistPack, ...]
    schema_version: str = SOURCE_MANUAL_SMOKE_CHECKLISTS_SCHEMA_VERSION
    review_status: str = "USER_REVIEW_REQUIRED"
    approval_status: str = "APPROVAL_REQUIRED"
    metadata_only: bool = True
    local_only: bool = True
    no_live_execution_status: str = "no_live_execution_performed"
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False
    sensitive_inference_prohibited: bool = True

    @property
    def pack_count(self) -> int:
        return len(self.packs)

    @property
    def row_count(self) -> int:
        return sum(pack.row_count for pack in self.packs)

    @property
    def approval_required_count(self) -> int:
        return self.row_count

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["pack_count"] = self.pack_count
        data["row_count"] = self.row_count
        data["approval_required_count"] = self.approval_required_count
        return data


def _instruction_for_method(method_id: str) -> str:
    if method_id == "msn_shadow_dom_comments":
        return "After explicit approval, manually review MSN shadow-DOM comments and record selector/manual-observation receipts."
    if method_id.startswith("twitter_x"):
        return "After explicit approval, review operator-supplied archive/manual import metadata for the X/Twitter source."
    if method_id.startswith("youtube"):
        return "After explicit approval, review existing YouTube transcript/comment metadata without running runtime/API calls."
    if method_id == "generic_comments_site_specific_selector":
        return "After explicit approval, audit the named-site comment selector; do not claim universal selector support."
    if "archive" in method_id:
        return "After explicit approval, review archive-only metadata and original URL linkage without archive provider calls."
    return "After explicit approval, manually review source-method metadata and record review receipts."


def build_source_manual_smoke_checklist_collection(
    named_site_method_packs: SourceNamedSiteMethodPackCollection | None = None,
) -> SourceManualSmokeChecklistCollection:
    source_packs = named_site_method_packs or build_source_named_site_method_pack_collection()
    packs_by_method = {pack.method_id: pack for pack in source_packs.packs}
    checklist_packs: list[SourceManualSmokeChecklistPack] = []
    for group_id, method_ids in CHECKLIST_GROUPS:
        rows: list[SourceManualSmokeChecklistRow] = []
        pack_id = "source_manual_smoke_checklist_" + _sha16((group_id, method_ids))
        for method_id in method_ids:
            source_pack = packs_by_method.get(method_id)
            if source_pack is None:
                continue
            receipt_refs = ("operator_approval_receipt", "manual_smoke_result_receipt", "not_live_executed_receipt")
            if source_pack.selector_audit_required:
                receipt_refs = receipt_refs + ("selector_audit_receipt",)
            row_payload = {"group_id": group_id, "method_id": method_id, "pack_id": pack_id}
            rows.append(
                SourceManualSmokeChecklistRow(
                    checklist_row_id="source_manual_smoke_checklist_row_" + _sha16(row_payload),
                    checklist_pack_id=pack_id,
                    method_id=method_id,
                    scope=source_pack.source_type,
                    manual_instruction=_instruction_for_method(method_id),
                    expected_receipt_refs=_stable_tuple(receipt_refs),
                    expected_artifact_refs=source_pack.expected_artifact_refs,
                )
            )
        checklist_packs.append(
            SourceManualSmokeChecklistPack(
                checklist_pack_id=pack_id,
                group_id=group_id,
                title=group_id.replace("_", " ").title(),
                rows=tuple(rows),
            )
        )
    checklist_packs.sort(key=lambda pack: pack.group_id)
    payload = {
        "checklist_pack_ids": [pack.checklist_pack_id for pack in checklist_packs],
        "schema_version": SOURCE_MANUAL_SMOKE_CHECKLISTS_SCHEMA_VERSION,
    }
    return SourceManualSmokeChecklistCollection(
        collection_id="source_manual_smoke_checklists_" + _sha16(payload),
        packs=tuple(checklist_packs),
    )


def validate_source_manual_smoke_checklist_collection(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_MANUAL_SMOKE_CHECKLISTS_SCHEMA_VERSION:
        raise ValueError("Unsupported manual smoke checklist schema version")
    for required_true in ("metadata_only", "local_only", "sensitive_inference_prohibited"):
        if data.get(required_true) is not True:
            raise ValueError(f"Unsafe manual smoke checklist flag: {required_true}")
    for required_false in (
        "live_execution_performed",
        "browser_automation_performed",
        "provider_call_performed",
        "archive_submission_performed",
        "download_performed",
        "file_move_performed",
        "completed_evidence_claimed",
        "automatic_classification",
    ):
        if data.get(required_false) is not False:
            raise ValueError(f"Unsafe manual smoke checklist flag: {required_false}")
    packs = data.get("packs", ())
    if not isinstance(packs, list) or not packs:
        raise ValueError("Manual smoke checklist collection must contain packs")
    for pack in packs:
        rows = pack.get("rows", ())
        if not isinstance(rows, list) or not rows:
            raise ValueError("Manual smoke checklist pack must contain rows")
        for row in rows:
            if row.get("executed") is not False:
                raise ValueError("Manual smoke checklist rows must not be executed")
            if row.get("operator_approval_required") is not True:
                raise ValueError("Manual smoke checklist rows must require approval")


def source_manual_smoke_checklist_collection_to_json(
    collection: SourceManualSmokeChecklistCollection,
) -> str:
    return _stable_json(collection.to_dict(), pretty=True)
