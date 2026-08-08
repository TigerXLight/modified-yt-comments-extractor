from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from source_site_method_audit_registry import (
    SITE_METHOD_STATUS_LIVE_APPROVED_ONLY,
    SourceSiteMethodAuditRegistry,
    SourceSiteMethodAuditRow,
    build_source_site_method_audit_registry,
)


SOURCE_NAMED_SITE_METHOD_PACK_SCHEMA_VERSION = "source_named_site_method_packs_v1"
NAMED_SITE_PACK_EXECUTION_STATUS = "not_live_executed"
NAMED_SITE_PACK_REVIEW_STATUS = "USER_REVIEW_REQUIRED"
MSN_SOURCE_METHOD_IDS = ("msn_article", "msn_shadow_dom_comments")


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


def _stable_json(data: Any) -> str:
    return json.dumps(_value_for_dict(data), sort_keys=True, separators=(",", ":"))


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(str(item) for item in value if str(item))


def _source_record_reference_mapping(row: SourceSiteMethodAuditRow) -> dict[str, tuple[str, ...]]:
    refs = tuple(sorted(set(_tuple(row.expected_artifact_refs))))

    def matching(*needles: str) -> tuple[str, ...]:
        lowered = tuple(needle.lower() for needle in needles)
        return tuple(ref for ref in refs if any(needle in ref.lower() for needle in lowered))

    article_refs = matching("article", "html", "text", "dom", "canonical")
    comment_refs = matching("comment", "reply", "thread")
    media_refs = matching("media", "video", "runtime_status")
    transcript_refs = matching("transcript", "asr")
    archive_refs = matching("archive", "original_url")
    screenshot_refs = matching("screenshot")
    snapshot_refs = matching("snapshot", "html", "dom")
    manual_refs = matching("manual", "review_signoff")
    provider_refs = matching("provider", "archive", "runtime_status")
    selector_refs = matching("selector", "boundary")
    if row.manual_observation_support:
        manual_refs = tuple(sorted(set(manual_refs + ("manual_observation_reference",))))
    if row.selector_audit_required or "selector" in row.selector_or_strategy:
        selector_refs = tuple(sorted(set(selector_refs + ("selector_audit_reference",))))
    return {
        "article_reference_ids": article_refs,
        "comment_reference_ids": comment_refs,
        "media_reference_ids": media_refs,
        "transcript_reference_ids": transcript_refs,
        "archive_url_references": archive_refs,
        "screenshot_reference_ids": screenshot_refs,
        "snapshot_reference_ids": snapshot_refs,
        "manual_observation_reference_ids": manual_refs,
        "provider_receipt_reference_ids": provider_refs,
        "selector_audit_reference_ids": selector_refs,
    }


def _base_blockers(row: SourceSiteMethodAuditRow) -> tuple[str, ...]:
    blockers = [
        "live_site_execution_not_performed",
        "operator_review_required_before_live_execution",
        "provider_calls_not_performed",
        "evidence_files_not_moved",
        "completed_evidence_not_claimed",
    ]
    if row.selector_audit_required:
        blockers.append("site_specific_selector_audit_required")
    if row.live_approved_only or row.status == SITE_METHOD_STATUS_LIVE_APPROVED_ONLY:
        blockers.append("live_operator_approval_required")
    return tuple(sorted(set(blockers)))


def _site_specific_metadata(row: SourceSiteMethodAuditRow) -> dict[str, Any]:
    method_id = row.method_id
    if method_id == "msn_article":
        return {
            "article_html_snapshot_refs": ("RAW_HTML", "FINAL_DOM", "ARTICLE_TEXT"),
            "manual_operator_notes": (
                "Android/Firefox responsive-design-mode manual observation remains supported.",
                "Article HTML/text capture is represented by supplied fixture/operator metadata only.",
            ),
            "no_live_claim": True,
            "screenshot_snapshot_refs": ("SCREENSHOT", "FINAL_DOM"),
        }
    if method_id == "msn_shadow_dom_comments":
        return {
            "comment_selector_notes": (
                "Inspect social-comment-wc shadow root when a named-site live smoke is approved.",
                "Use .overlay-container scroll/resize/manual operator receipt path for comments.",
            ),
            "manual_operator_notes": (
                "Android/Firefox responsive-design-mode notes are metadata only.",
                "No shadow-DOM browser execution has been performed in this pack.",
            ),
            "shadow_dom_host": "social-comment-wc",
            "shadow_dom_scroll_container": ".overlay-container",
        }
    if method_id == "twitter_x_public_post_archive_manual_import":
        return {
            "archive_fallback_providers": ("archive.ph", "Ghostarchive", "perma.cc", "Wayback"),
            "expected_public_post_metadata": ("original_x_url", "public_post_id", "archive_receipt_ref"),
            "manual_observation_refs": ("manual_observation_reference", "screenshot_reference"),
            "x_twitter_runtime_performed": False,
        }
    if method_id == "twitter_x_reply_thread_archive_manual_import":
        return {
            "archive_fallback_providers": ("archive.ph", "Ghostarchive", "perma.cc", "Wayback"),
            "expected_thread_metadata": (
                "original_x_url",
                "parent_post_id",
                "reply_ids",
                "thread_boundary",
                "archive_receipt_ref",
            ),
            "manual_observation_refs": ("manual_observation_reference", "screenshot_reference"),
            "x_twitter_runtime_performed": False,
        }
    if method_id == "youtube_media_transcript":
        return {
            "expected_video_metadata": ("video_url", "video_id", "media_metadata_ref"),
            "transcript_refs": ("TRANSCRIPT_REFERENCE", "ASR_TRANSCRIPT_REFERENCE"),
            "youtube_runtime_performed": False,
            "yt_dlp_ffmpeg_asr_performed": False,
        }
    if method_id == "youtube_comments":
        return {
            "comment_refs": ("COMMENTS_STATUS_COUNTS", "REPLY_STATUS_COUNTS"),
            "expected_video_metadata": ("video_url", "video_id"),
            "youtube_api_or_runtime_performed": False,
        }
    if method_id == "generic_article_html":
        return {
            "article_capture_refs": (
                "CANONICAL_URL",
                "HTML_SNAPSHOT",
                "TEXT_EXTRACTION_RECEIPT",
                "SCREENSHOT_REFERENCE",
            ),
            "text_extraction_status": "placeholder_receipt_refs_only",
            "universal_site_claimed": False,
        }
    if method_id == "generic_comments_manual_import":
        return {
            "comment_source_boundary": "operator_supplied_comment_tree_or_manual_observation",
            "manual_observation_import_available_now": True,
            "universal_selector_support_claimed": False,
        }
    if method_id == "generic_comments_site_specific_selector":
        return {
            "approval_packet_required": True,
            "manual_observation_import_available_now": True,
            "selector_audit_status": "selector_audit_required",
            "site_specific_selector_required_before_live_execution": True,
            "universal_selector_support_claimed": False,
        }
    if method_id == "generic_comments_archive_only_import":
        return {
            "archive_comment_review_available_now": True,
            "archive_is_primary_source_metadata": True,
            "no_live_site_required": True,
        }
    if method_id == "archive_only_import":
        return {
            "archive_only_metadata_refs": ("ARCHIVE_URL", "ORIGINAL_URL", "ARCHIVE_PROVIDER_TYPE"),
            "retrieved_metadata_refs": ("operator_supplied_archive_metadata",),
            "review_signoff_required": True,
        }
    return {"no_live_claim": True}


def _site_group(row: SourceSiteMethodAuditRow) -> str:
    if row.adapter_id == "msn":
        return "msn"
    if row.adapter_id == "twitter_x":
        return "twitter_x"
    if row.adapter_id == "youtube":
        return "youtube"
    return "generic_archive"


@dataclass(frozen=True)
class SourceNamedSiteMethodPack:
    pack_id: str
    site_method_id: str
    site_profile_id: str
    site_display_name: str
    site_group: str
    adapter_id: str
    source_type: str
    method_profile_id: str
    method_id: str
    selector_strategy: str
    manual_import_strategy: str
    archive_fallback_strategy: str
    expected_artifact_refs: tuple[str, ...]
    required_operator_inputs: tuple[str, ...]
    database_mapping: tuple[str, ...]
    total_export_mapping: tuple[str, ...]
    source_record_typed_reference_mapping: Mapping[str, tuple[str, ...]]
    approval_requirements: tuple[str, ...]
    not_live_executed_status: str
    exact_remaining_audit_blockers: tuple[str, ...]
    status: str
    execution_status: str
    selector_audit_required: bool
    live_approved_only: bool
    selector_approval_packet_ids: tuple[str, ...] = ()
    site_specific_metadata: Mapping[str, Any] | None = None
    schema_version: str = SOURCE_NAMED_SITE_METHOD_PACK_SCHEMA_VERSION
    review_status: str = NAMED_SITE_PACK_REVIEW_STATUS
    metadata_only: bool = True
    local_only: bool = True
    live_execution_performed: bool = False
    browser_automation_performed: bool = False
    provider_call_performed: bool = False
    archive_submission_performed: bool = False
    download_performed: bool = False
    file_move_performed: bool = False
    completed_evidence_claimed: bool = False
    automatic_classification: bool = False
    protected_attribute_inference_performed: bool = False
    sensitive_inference_prohibited: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class SourceNamedSiteMethodPackCollection:
    packs: tuple[SourceNamedSiteMethodPack, ...]
    collection_id: str
    schema_version: str = SOURCE_NAMED_SITE_METHOD_PACK_SCHEMA_VERSION
    review_status: str = NAMED_SITE_PACK_REVIEW_STATUS
    metadata_only: bool = True
    local_only: bool = True
    not_live_executed: bool = True
    approval_required: bool = True
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
    def msn_pack_count(self) -> int:
        return sum(1 for pack in self.packs if pack.site_group == "msn")

    @property
    def twitter_x_pack_count(self) -> int:
        return sum(1 for pack in self.packs if pack.site_group == "twitter_x")

    @property
    def youtube_pack_count(self) -> int:
        return sum(1 for pack in self.packs if pack.site_group == "youtube")

    @property
    def generic_archive_pack_count(self) -> int:
        return sum(1 for pack in self.packs if pack.site_group == "generic_archive")

    @property
    def selector_audit_required_count(self) -> int:
        return sum(1 for pack in self.packs if pack.selector_audit_required)

    @property
    def live_approved_only_count(self) -> int:
        return sum(1 for pack in self.packs if pack.live_approved_only)

    @property
    def no_live_execution_status(self) -> str:
        return "no_live_execution_performed"

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data.update(
            {
                "generic_archive_pack_count": self.generic_archive_pack_count,
                "live_approved_only_count": self.live_approved_only_count,
                "msn_pack_count": self.msn_pack_count,
                "no_live_execution_status": self.no_live_execution_status,
                "pack_count": self.pack_count,
                "selector_audit_required_count": self.selector_audit_required_count,
                "twitter_x_pack_count": self.twitter_x_pack_count,
                "youtube_pack_count": self.youtube_pack_count,
            }
        )
        return data


def build_source_named_site_method_pack(
    row: SourceSiteMethodAuditRow,
    *,
    selector_approval_packet_ids: tuple[str, ...] = (),
) -> SourceNamedSiteMethodPack:
    required_operator_inputs = tuple(
        sorted(
            set(
                (
                    "operator_review_note",
                    "manual_observation_receipt",
                    "approval_before_live_execution",
                )
                + (("named_site_selector_approval_packet",) if row.selector_audit_required else ())
            )
        )
    )
    return SourceNamedSiteMethodPack(
        pack_id=_stable_id("source_named_site_method_pack", row.site_method_id, row.method_id),
        site_method_id=row.site_method_id,
        site_profile_id=row.site_profile_id,
        site_display_name=row.site_display_name,
        site_group=_site_group(row),
        adapter_id=row.adapter_id,
        source_type=row.source_type,
        method_profile_id=row.method_id,
        method_id=row.method_id,
        selector_strategy=row.selector_or_strategy,
        manual_import_strategy=row.manual_observation_support,
        archive_fallback_strategy=row.archive_fallback,
        expected_artifact_refs=tuple(sorted(set(_tuple(row.expected_artifact_refs)))),
        required_operator_inputs=required_operator_inputs,
        database_mapping=tuple(sorted(set(_tuple(row.database_mapping)))),
        total_export_mapping=tuple(sorted(set(_tuple(row.total_export_mapping)))),
        source_record_typed_reference_mapping=_source_record_reference_mapping(row),
        approval_requirements=tuple(sorted(set(_tuple(row.operator_approval_requirement)))),
        not_live_executed_status=NAMED_SITE_PACK_EXECUTION_STATUS,
        exact_remaining_audit_blockers=_base_blockers(row),
        status=row.status,
        execution_status=row.execution_status,
        selector_audit_required=row.selector_audit_required,
        live_approved_only=row.live_approved_only,
        selector_approval_packet_ids=selector_approval_packet_ids,
        site_specific_metadata=_site_specific_metadata(row),
    )


def _selector_packet_ids_by_site_method(selector_approval_packets: Any | None) -> dict[str, tuple[str, ...]]:
    if selector_approval_packets is None:
        return {}
    packets = getattr(selector_approval_packets, "packets", ())
    result: dict[str, list[str]] = {}
    for packet in packets:
        site_method_id = str(getattr(packet, "site_method_id", ""))
        packet_id = str(getattr(packet, "packet_id", ""))
        if site_method_id and packet_id:
            result.setdefault(site_method_id, []).append(packet_id)
    return {key: tuple(sorted(values)) for key, values in result.items()}


def build_source_named_site_method_pack_collection(
    registry: SourceSiteMethodAuditRegistry | None = None,
    *,
    selector_approval_packets: Any | None = None,
) -> SourceNamedSiteMethodPackCollection:
    registry = registry or build_source_site_method_audit_registry()
    packet_ids_by_site_method = _selector_packet_ids_by_site_method(selector_approval_packets)
    packs = tuple(
        build_source_named_site_method_pack(
            row,
            selector_approval_packet_ids=packet_ids_by_site_method.get(row.site_method_id, ()),
        )
        for row in sorted(registry.rows, key=lambda item: (item.site_profile_id, item.method_id))
    )
    collection_id = _stable_id(
        "source_named_site_method_packs",
        registry.registry_id,
        *(pack.pack_id for pack in packs),
    )
    return SourceNamedSiteMethodPackCollection(packs=packs, collection_id=collection_id)


def validate_source_named_site_method_pack_collection(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != SOURCE_NAMED_SITE_METHOD_PACK_SCHEMA_VERSION:
        raise ValueError("Unsupported named-site method pack schema version")
    if data.get("metadata_only") is not True or data.get("local_only") is not True:
        raise ValueError("Named-site method packs must remain metadata-only and local-only")
    for unsafe_flag in (
        "live_execution_performed",
        "browser_automation_performed",
        "provider_call_performed",
        "archive_submission_performed",
        "download_performed",
        "file_move_performed",
        "completed_evidence_claimed",
        "automatic_classification",
    ):
        if data.get(unsafe_flag) is not False:
            raise ValueError(f"Unsafe named-site method pack collection flag: {unsafe_flag}")
    packs = data.get("packs", [])
    if not isinstance(packs, list) or not packs:
        raise ValueError("Named-site method pack collection must include pack rows")
    for pack in packs:
        if not isinstance(pack, dict):
            raise ValueError("Named-site method pack rows must be JSON objects")
        if pack.get("schema_version") != SOURCE_NAMED_SITE_METHOD_PACK_SCHEMA_VERSION:
            raise ValueError("Unsupported named-site method pack row schema version")
        if pack.get("review_status") != NAMED_SITE_PACK_REVIEW_STATUS:
            raise ValueError("Named-site method pack rows must stay USER_REVIEW_REQUIRED")
        for unsafe_flag in (
            "live_execution_performed",
            "browser_automation_performed",
            "provider_call_performed",
            "archive_submission_performed",
            "download_performed",
            "file_move_performed",
            "completed_evidence_claimed",
            "automatic_classification",
            "protected_attribute_inference_performed",
        ):
            if pack.get(unsafe_flag) is not False:
                raise ValueError(f"Unsafe named-site method pack row flag: {unsafe_flag}")
        if pack.get("not_live_executed_status") != NAMED_SITE_PACK_EXECUTION_STATUS:
            raise ValueError("Named-site method packs must keep not-live-executed status")
        blockers = tuple(pack.get("exact_remaining_audit_blockers", ()))
        if "live_site_execution_not_performed" not in blockers:
            raise ValueError("Named-site method pack row must record not-live execution blocker")


def source_named_site_method_pack_collection_to_json(
    collection: SourceNamedSiteMethodPackCollection,
) -> str:
    return json.dumps(collection.to_dict(), indent=2, sort_keys=True)


def source_named_site_method_packs_by_method_id(
    collection: SourceNamedSiteMethodPackCollection,
    method_ids: tuple[str, ...],
) -> tuple[SourceNamedSiteMethodPack, ...]:
    requested = set(method_ids)
    return tuple(pack for pack in collection.packs if pack.method_id in requested)


def build_msn_named_site_method_packs(
    collection: SourceNamedSiteMethodPackCollection | None = None,
) -> tuple[SourceNamedSiteMethodPack, ...]:
    collection = collection or build_source_named_site_method_pack_collection()
    return source_named_site_method_packs_by_method_id(collection, MSN_SOURCE_METHOD_IDS)
