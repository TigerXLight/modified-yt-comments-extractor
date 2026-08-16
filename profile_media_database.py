from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


PROFILE_MEDIA_DATABASE_SCHEMA_VERSION = "profile-media-database-v75g"

PROFILE_MEDIA_DATABASE_SCOPE = (
    "local profile/media database planning schema plus source/container import planning plus case repository path planning plus review/audit queue planning; "
    "no folder scanning, no folder creation, no file copying, no file movement, "
    "no automatic classification, no sensitive-attribute inference, no source fetching, "
    "no archive access, no media download, no browser automation, no credentials, "
    "no GUI wiring; review-gated folder operation execution is available only when explicitly called with execute=True and approved review records; manifest JSON persistence and hierarchy-correct tree-view rows are read/write helpers, not classifiers"
)


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ProfileSourceRole(_StringEnum):
    PRIMARY_SELF_AUTHORED_SCOPE = "PRIMARY_SELF_AUTHORED_SCOPE"
    SECONDARY_WITNESS_ACCOUNT = "SECONDARY_WITNESS_ACCOUNT"
    TERTIARY_PROPAGATED_SOURCE = "TERTIARY_PROPAGATED_SOURCE"
    UNKNOWN_SOURCE_ROLE = "UNKNOWN_SOURCE_ROLE"


class ClaimBasis(_StringEnum):
    SELF_AUTHORED_EXPERIENCE = "SELF_AUTHORED_EXPERIENCE"
    WITNESS_ACCOUNT = "WITNESS_ACCOUNT"
    FAMILY_OR_AUTHORITY_CLAIM = "FAMILY_OR_AUTHORITY_CLAIM"
    AGENCY_OR_OUTSIDE_RETELLING = "AGENCY_OR_OUTSIDE_RETELLING"
    APPEARANCE_CLAIM = "APPEARANCE_CLAIM"
    IDENTITY_CLAIM = "IDENTITY_CLAIM"
    USER_ENTERED_NOTE = "USER_ENTERED_NOTE"
    UNKNOWN_CLAIM_BASIS = "UNKNOWN_CLAIM_BASIS"


class CurrentnessStatus(_StringEnum):
    CURRENT = "CURRENT"
    HISTORICAL = "HISTORICAL"
    UNDATED = "UNDATED"
    UNKNOWN = "UNKNOWN"


class MediaBucket(_StringEnum):
    ARTICLES = "Articles"
    SOCIAL_MEDIA_ONLINE = "Social Media/Online"
    SOCIAL_MEDIA_OFFLINE = "Social Media/Offline"
    INTERNAL_MEDIA = "Internal Media"
    REFERENCE_EXTANTS = "Reference Extants"
    PEOPLE = "People"
    CASE_PROFILES = "Profiles"
    GLOBAL_PROFILES = "Profiles"


class ProfileCollectionLevel(_StringEnum):
    GLOBAL_HEADER_PROFILES = "GLOBAL_HEADER_PROFILES"
    CASE_LOCAL_PROFILES = "CASE_LOCAL_PROFILES"


class MediaOrigin(_StringEnum):
    EXTERNAL_MEDIA = "EXTERNAL_MEDIA"
    INTERNAL_MEDIA = "INTERNAL_MEDIA"


class MovePlanStatus(_StringEnum):
    DRY_RUN_ONLY = "DRY_RUN_ONLY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NO_CHANGE = "NO_CHANGE"


class ReviewItemType(_StringEnum):
    FOLDER_MOVE = "FOLDER_MOVE"
    CASE_REPOSITORY_PATH_CHANGE = "CASE_REPOSITORY_PATH_CHANGE"
    IDENTIFIER_UPDATE = "IDENTIFIER_UPDATE"
    SOURCE_CLAIM_EVALUATION = "SOURCE_CLAIM_EVALUATION"


class ReviewItemStatus(_StringEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED_FOR_ACTION = "APPROVED_FOR_ACTION"
    REJECTED = "REJECTED"
    DEFERRED = "DEFERRED"
    NO_CHANGE = "NO_CHANGE"
    SUPERSEDED = "SUPERSEDED"


class AuditEventType(_StringEnum):
    REVIEW_ITEM_CREATED = "REVIEW_ITEM_CREATED"
    REVIEW_DECISION_RECORDED = "REVIEW_DECISION_RECORDED"
    MOVE_PLAN_CREATED = "MOVE_PLAN_CREATED"
    CLASSIFICATION_PATH_CHANGED = "CLASSIFICATION_PATH_CHANGED"
    IDENTIFIER_PROFILE_UPDATED = "IDENTIFIER_PROFILE_UPDATED"
    FOLDER_OPERATION_PLANNED = "FOLDER_OPERATION_PLANNED"
    FOLDER_OPERATION_APPLIED = "FOLDER_OPERATION_APPLIED"


class FolderOperationType(_StringEnum):
    CREATE_PARENT_FOLDER = "CREATE_PARENT_FOLDER"
    MOVE_OR_RENAME_FOLDER = "MOVE_OR_RENAME_FOLDER"


class FolderOperationStatus(_StringEnum):
    PLANNED_DRY_RUN = "PLANNED_DRY_RUN"
    BLOCKED_REVIEW_NOT_APPROVED = "BLOCKED_REVIEW_NOT_APPROVED"
    BLOCKED_SOURCE_MISSING = "BLOCKED_SOURCE_MISSING"
    BLOCKED_DESTINATION_EXISTS = "BLOCKED_DESTINATION_EXISTS"
    BLOCKED_PARENT_MISSING = "BLOCKED_PARENT_MISSING"
    READY_TO_APPLY = "READY_TO_APPLY"
    APPLIED = "APPLIED"
    NO_CHANGE = "NO_CHANGE"
    ERROR = "ERROR"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def stable_json_dumps(data: Any) -> str:
    return json.dumps(_value_for_dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_profile_id(prefix: str, *parts: object) -> str:
    payload = "\n".join(str(part or "").strip().replace("\\", "/") for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    safe_prefix = re.sub(r"[^a-z0-9_]+", "_", str(prefix or "profile").lower()).strip("_")
    return f"{safe_prefix or 'profile'}_{digest}"


def sanitize_path_part(value: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]+", " - ", str(value or "")).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned[:120] or fallback


def _split_identifier_text(value: str) -> tuple[str, ...]:
    text = str(value or "").strip()
    if not text:
        return ()
    parts = []
    for line in text.splitlines():
        line = line.strip().strip("-• ")
        if line:
            parts.append(line)
    if len(parts) <= 1:
        comma_parts = [part.strip() for part in re.split(r";|,", text) if part.strip()]
        if len(comma_parts) > 1:
            parts = comma_parts
    return tuple(parts or (text,))


@dataclass(frozen=True)
class SourceClaimEvaluation:
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    disputed_framing: bool = False
    notes_on_context_dispute: str = ""
    source_chain_gap: bool = False
    confidence_or_verification_notes: str = ""
    family_or_authority_claim_basis: str = ""
    identity_claim_basis: str = ""
    appearance_claim_basis: str = ""
    collaboration_or_corroboration_notes: str = ""
    sensitive_identifier_source_evidenced_only: bool = True
    weak_sensitive_inference_prohibited: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MediaImportPlan:
    plan_id: str
    case_id: str
    case_root: str
    source_page: str
    source_bucket: MediaBucket | str
    media_origin: MediaOrigin
    proposed_local_address: str
    required_parent_path: str
    source_title: str = ""
    source_filename: str = ""
    source_claim_evaluation: SourceClaimEvaluation = field(default_factory=SourceClaimEvaluation)
    warnings: tuple[str, ...] = ()
    folder_creation_performed: bool = False
    file_copy_performed: bool = False
    file_move_performed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class IdentifierClaim:
    identifier_type: str
    value: str = ""
    date: str = ""
    source_name: str = ""
    source_page: str = ""
    local_address: str = ""
    text: str = ""
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    disputed_framing: bool = False
    notes_on_context_dispute: str = ""
    source_chain_gap: bool = False
    confidence_or_verification_notes: str = ""
    sensitive_identifier: bool = False
    source_evidenced_only: bool = True
    weak_inference_prohibited: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ProfileTextBlock:
    name: str = ""
    date: str = ""
    text: str = ""
    identifiers: tuple[str, ...] = ()
    local_address: str = ""
    source_page: str = ""
    source_bucket: str = ""
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    parsed_at_utc: str = field(default_factory=utc_now_iso)
    parser_warnings: tuple[str, ...] = ()

    def to_identifier_claims(self) -> tuple[IdentifierClaim, ...]:
        claims: list[IdentifierClaim] = []
        for identifier in self.identifiers:
            claims.append(
                IdentifierClaim(
                    identifier_type="freeform_identifier",
                    value=identifier,
                    date=self.date,
                    source_name=self.source_page,
                    source_page=self.source_page,
                    local_address=self.local_address,
                    text=self.text,
                    source_role=self.source_role,
                    claim_basis=self.claim_basis,
                    currentness_status=self.currentness_status,
                    sensitive_identifier=_identifier_looks_sensitive(identifier),
                )
            )
        return tuple(claims)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ProfileRecord:
    profile_id: str
    canonical_name: str
    collection_level: ProfileCollectionLevel
    case_id: str = ""
    text_blocks: tuple[ProfileTextBlock, ...] = ()
    identifiers: tuple[IdentifierClaim, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    sort_policy: str = "newest_to_oldest"
    no_automatic_sensitive_inference: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MediaSourceRecord:
    source_id: str
    source_page: str
    source_bucket: MediaBucket | str
    local_address: str = ""
    title: str = ""
    captured_or_recorded_date: str = ""
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    source_chain_gap: bool = False
    disputed_framing: bool = False
    notes_on_context_dispute: str = ""
    confidence_or_verification_notes: str = ""
    source_claim_evaluation: SourceClaimEvaluation | None = None

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class CaseFolderLayout:
    case_root: str
    case_profiles_path: str
    people_path: str
    sources_path: str
    articles_path: str
    social_media_path: str
    social_media_offline_path: str
    social_media_online_path: str
    internal_media_path: str
    reference_extants_path: str
    folder_creation_performed: bool = False
    file_move_performed: bool = False

    @property
    def required_paths(self) -> tuple[str, ...]:
        return (
            self.case_profiles_path,
            self.people_path,
            self.sources_path,
            self.articles_path,
            self.social_media_path,
            self.social_media_offline_path,
            self.social_media_online_path,
            self.internal_media_path,
            self.reference_extants_path,
        )

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["required_paths"] = list(self.required_paths)
        return data




@dataclass(frozen=True)
class CaseRepositoryClassification:
    """Dry-run classification facets used to plan where a case folder should live.

    These values are path-planning metadata only. They do not prove an allegation,
    do not classify a person automatically, and do not move any folder.
    """

    domain: str
    conduct: tuple[str, ...] = ()
    location_type: str = ""
    relationship_or_context: str = ""
    sex_or_gender_pattern: str = ""
    action_type: str = ""
    religious_identity_bucket: str = "Non-religious or not identified"
    date_bucket: str = "Undated"
    source_name: str = "Unknown Source"
    case_title: str = "Untitled Case"
    source_basis: str = ""
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    sensitive_bucket_source_evidenced_only: bool = True
    weak_sensitive_inference_prohibited: bool = True
    warnings: tuple[str, ...] = ()

    def path_parts(self) -> tuple[str, ...]:
        parts: list[str] = [self.domain]
        parts.extend(part for part in self.conduct if part)
        for value in (
            self.location_type,
            self.relationship_or_context,
            self.sex_or_gender_pattern,
            self.action_type,
            self.religious_identity_bucket,
            self.date_bucket,
            self.source_name,
            self.case_title,
        ):
            if value:
                parts.append(value)
        return tuple(sanitize_path_part(part) for part in parts if sanitize_path_part(part))

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["path_parts"] = list(self.path_parts())
        return data


@dataclass(frozen=True)
class CaseRepositoryPathPlan:
    plan_id: str
    database_root: str
    classification: CaseRepositoryClassification
    proposed_case_root: str
    layout: CaseFolderLayout
    current_case_root: str = ""
    move_plan: FolderMovePlan | None = None
    status: MovePlanStatus = MovePlanStatus.REVIEW_REQUIRED
    required_review: bool = True
    created_folders: bool = False
    moved_or_renamed_folders: bool = False
    audit_note: str = "dry-run repository path plan only; no folder was created, moved, or renamed"
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

@dataclass(frozen=True)
class CaseRecord:
    case_id: str
    case_title: str
    case_root: str
    layout: CaseFolderLayout
    profiles: tuple[ProfileRecord, ...] = ()
    media_sources: tuple[MediaSourceRecord, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class FolderMovePlan:
    plan_id: str
    current_path: str
    proposed_path: str
    reason: str
    source_basis: str = ""
    status: MovePlanStatus = MovePlanStatus.REVIEW_REQUIRED
    user_confirmation_required: bool = True
    file_move_performed: bool = False
    folder_creation_performed: bool = False
    audit_note: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)



@dataclass(frozen=True)
class ProfileMediaReviewItem:
    review_id: str
    item_type: ReviewItemType
    title: str
    case_id: str = ""
    case_title: str = ""
    current_path: str = ""
    proposed_path: str = ""
    reason: str = ""
    source_basis: str = ""
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    source_chain_gap: bool = False
    disputed_framing: bool = False
    sensitive_review_required: bool = False
    required_actions: tuple[str, ...] = ()
    status: ReviewItemStatus = ReviewItemStatus.PENDING_REVIEW
    reviewer_note: str = ""
    reviewed_by: str = ""
    user_confirmation_recorded: bool = False
    folder_creation_performed: bool = False
    file_move_performed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)
    reviewed_at_utc: str = ""
    audit_note: str = "review queue item only; no folder was created, moved, copied, or renamed"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ProfileMediaReviewQueue:
    queue_id: str
    items: tuple[ProfileMediaReviewItem, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    schema_version: str = PROFILE_MEDIA_DATABASE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["item_count"] = len(self.items)
        data["pending_count"] = sum(1 for item in self.items if item.status == ReviewItemStatus.PENDING_REVIEW)
        data["approved_count"] = sum(1 for item in self.items if item.status == ReviewItemStatus.APPROVED_FOR_ACTION)
        data["rejected_count"] = sum(1 for item in self.items if item.status == ReviewItemStatus.REJECTED)
        return data


@dataclass(frozen=True)
class ProfileMediaAuditEvent:
    event_id: str
    event_type: AuditEventType
    subject_id: str
    case_id: str = ""
    previous_value: str = ""
    new_value: str = ""
    reason: str = ""
    source_basis: str = ""
    review_id: str = ""
    performed: bool = False
    folder_creation_performed: bool = False
    file_move_performed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)
    audit_note: str = "audit/planning record only unless performed is explicitly true"

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ProfileMediaFolderOperation:
    operation_id: str
    operation_type: FolderOperationType
    source_path: str = ""
    destination_path: str = ""
    required_parent_path: str = ""
    case_id: str = ""
    review_id: str = ""
    reason: str = ""
    source_basis: str = ""
    review_status: ReviewItemStatus = ReviewItemStatus.PENDING_REVIEW
    dry_run_only: bool = True
    user_confirmation_required: bool = True
    allowed_to_execute: bool = False
    warnings: tuple[str, ...] = ()
    folder_creation_performed: bool = False
    file_move_performed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ProfileMediaFolderOperationResult:
    operation_id: str
    status: FolderOperationStatus
    source_path: str = ""
    destination_path: str = ""
    performed: bool = False
    dry_run: bool = True
    created_parent: bool = False
    moved_or_renamed_folder: bool = False
    warnings: tuple[str, ...] = ()
    error: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)




@dataclass(frozen=True)
class ProfileMediaTreeRow:
    row_id: str
    row_type: str
    label: str
    path: str
    level: int = 0
    parent_row_id: str = ""
    display_order: int = 0
    case_id: str = ""
    case_title: str = ""
    source_bucket: str = ""
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN
    source_chain_gap: bool = False
    disputed_framing: bool = False
    sensitive_identifier_source_evidenced_only: bool = True
    weak_sensitive_inference_prohibited: bool = True

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)

@dataclass(frozen=True)
class ProfileMediaDatabaseManifest:
    manifest_id: str
    database_root: str
    global_profiles_path: str
    cases: tuple[CaseRecord, ...] = ()
    global_profiles: tuple[ProfileRecord, ...] = ()
    move_plans: tuple[FolderMovePlan, ...] = ()
    review_queue: ProfileMediaReviewQueue | None = None
    audit_events: tuple[ProfileMediaAuditEvent, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_SCHEMA_VERSION
    scope: str = PROFILE_MEDIA_DATABASE_SCOPE
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    payload_sha256: str = ""

    def payload_dict(self) -> dict[str, Any]:
        return {
            "cases": [_value_for_dict(case) for case in self.cases],
            "database_root": self.database_root,
            "global_profiles": [_value_for_dict(profile) for profile in self.global_profiles],
            "global_profiles_path": self.global_profiles_path,
            "manifest_id": self.manifest_id,
            "move_plans": [_value_for_dict(plan) for plan in self.move_plans],
            "review_queue": _value_for_dict(self.review_queue) if self.review_queue is not None else None,
            "audit_events": [_value_for_dict(event) for event in self.audit_events],
            "schema_version": self.schema_version,
            "scope": self.scope,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
        }

    def to_dict(self) -> dict[str, Any]:
        data = self.payload_dict()
        data["case_count"] = len(self.cases)
        data["global_profile_count"] = len(self.global_profiles)
        data["move_plan_count"] = len(self.move_plans)
        data["review_queue_count"] = len(self.review_queue.items) if self.review_queue is not None else 0
        data["audit_event_count"] = len(self.audit_events)
        data["payload_sha256"] = self.payload_sha256
        return data


def _identifier_looks_sensitive(identifier: str) -> bool:
    lowered = identifier.lower()
    return any(
        token in lowered
        for token in (
            "religion",
            "religious",
            "muslim",
            "christian",
            "jewish",
            "hindu",
            "sikh",
            "skin colour",
            "skin color",
            "ethnicity",
            "race",
            "association",
        )
    )


def build_case_folder_layout(case_root: str) -> CaseFolderLayout:
    root = Path(case_root)
    sources = root / "Sources"
    social = sources / "Social Media"
    return CaseFolderLayout(
        case_root=str(root),
        case_profiles_path=str(root / "Profiles"),
        people_path=str(root / "People"),
        sources_path=str(sources),
        articles_path=str(sources / "Articles"),
        social_media_path=str(social),
        social_media_offline_path=str(social / "Offline"),
        social_media_online_path=str(social / "Online"),
        internal_media_path=str(sources / "Internal Media"),
        reference_extants_path=str(root / "Reference Extants"),
    )


def build_global_profiles_path(database_root: str) -> str:
    return str(Path(database_root) / "Profiles")


_MEDIA_BUCKET_ALIASES = {
    "articles": MediaBucket.ARTICLES,
    "article": MediaBucket.ARTICLES,
    "sources/articles": MediaBucket.ARTICLES,
    "social media": MediaBucket.SOCIAL_MEDIA_ONLINE,
    "social media/online": MediaBucket.SOCIAL_MEDIA_ONLINE,
    "social media online": MediaBucket.SOCIAL_MEDIA_ONLINE,
    "online social media": MediaBucket.SOCIAL_MEDIA_ONLINE,
    "social media/offline": MediaBucket.SOCIAL_MEDIA_OFFLINE,
    "social media offline": MediaBucket.SOCIAL_MEDIA_OFFLINE,
    "offline social media": MediaBucket.SOCIAL_MEDIA_OFFLINE,
    "internal media": MediaBucket.INTERNAL_MEDIA,
    "sources/internal media": MediaBucket.INTERNAL_MEDIA,
    "reference extants": MediaBucket.REFERENCE_EXTANTS,
    "people": MediaBucket.PEOPLE,
    "case profiles": MediaBucket.CASE_PROFILES,
    "profiles": MediaBucket.CASE_PROFILES,
    "global profiles": MediaBucket.GLOBAL_PROFILES,
}


def normalize_media_bucket(value: MediaBucket | str, *, default: MediaBucket = MediaBucket.ARTICLES) -> MediaBucket:
    if isinstance(value, MediaBucket):
        return value
    raw = str(value or "").strip().replace("\\", "/")
    key = re.sub(r"\s+", " ", raw.lower()).strip(" /")
    key = key.replace(" / ", "/")
    return _MEDIA_BUCKET_ALIASES.get(key, default)


def case_source_bucket_path(layout: CaseFolderLayout, source_bucket: MediaBucket | str) -> str:
    bucket = normalize_media_bucket(source_bucket)
    if bucket == MediaBucket.ARTICLES:
        return layout.articles_path
    if bucket == MediaBucket.SOCIAL_MEDIA_ONLINE:
        return layout.social_media_online_path
    if bucket == MediaBucket.SOCIAL_MEDIA_OFFLINE:
        return layout.social_media_offline_path
    if bucket == MediaBucket.INTERNAL_MEDIA:
        return layout.internal_media_path
    if bucket == MediaBucket.REFERENCE_EXTANTS:
        return layout.reference_extants_path
    if bucket == MediaBucket.PEOPLE:
        return layout.people_path
    if bucket == MediaBucket.CASE_PROFILES:
        return layout.case_profiles_path
    return layout.sources_path


def media_origin_for_bucket(source_bucket: MediaBucket | str) -> MediaOrigin:
    return MediaOrigin.INTERNAL_MEDIA if normalize_media_bucket(source_bucket) == MediaBucket.INTERNAL_MEDIA else MediaOrigin.EXTERNAL_MEDIA


def _planned_media_filename(*, source_page: str, title: str = "", source_filename: str = "", default_extension: str = ".txt") -> str:
    chosen = source_filename or title or source_page or "media-source"
    cleaned = sanitize_path_part(chosen, fallback="media-source")
    suffix = Path(cleaned).suffix
    if default_extension and not suffix:
        cleaned = f"{cleaned}{default_extension if default_extension.startswith('.') else '.' + default_extension}"
    return cleaned


def build_source_claim_evaluation(
    *,
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN,
    disputed_framing: bool = False,
    notes_on_context_dispute: str = "",
    source_chain_gap: bool = False,
    confidence_or_verification_notes: str = "",
    family_or_authority_claim_basis: str = "",
    identity_claim_basis: str = "",
    appearance_claim_basis: str = "",
    collaboration_or_corroboration_notes: str = "",
) -> SourceClaimEvaluation:
    return SourceClaimEvaluation(
        source_role=source_role,
        claim_basis=claim_basis,
        currentness_status=currentness_status,
        disputed_framing=disputed_framing,
        notes_on_context_dispute=notes_on_context_dispute,
        source_chain_gap=source_chain_gap,
        confidence_or_verification_notes=confidence_or_verification_notes,
        family_or_authority_claim_basis=family_or_authority_claim_basis,
        identity_claim_basis=identity_claim_basis,
        appearance_claim_basis=appearance_claim_basis,
        collaboration_or_corroboration_notes=collaboration_or_corroboration_notes,
    )


def plan_media_import(
    *,
    case_root: str,
    source_page: str,
    source_bucket: MediaBucket | str,
    case_id: str = "",
    source_title: str = "",
    source_filename: str = "",
    default_extension: str = ".txt",
    source_claim_evaluation: SourceClaimEvaluation | None = None,
) -> MediaImportPlan:
    layout = build_case_folder_layout(case_root)
    bucket = normalize_media_bucket(source_bucket)
    parent = Path(case_source_bucket_path(layout, bucket))
    filename = _planned_media_filename(
        source_page=source_page,
        title=source_title,
        source_filename=source_filename,
        default_extension=default_extension,
    )
    warnings: list[str] = []
    if not source_page:
        warnings.append("missing_source_page")
    if bucket == MediaBucket.CASE_PROFILES:
        warnings.append("case_profiles_are_extracted_profile_outputs_not_original_media")
    proposed = str(parent / filename)
    return MediaImportPlan(
        plan_id=stable_profile_id("media_import", case_id, case_root, bucket.value, source_page, source_title, filename),
        case_id=case_id,
        case_root=str(Path(case_root)),
        source_page=source_page,
        source_bucket=bucket,
        media_origin=media_origin_for_bucket(bucket),
        proposed_local_address=proposed,
        required_parent_path=str(parent),
        source_title=source_title,
        source_filename=filename,
        source_claim_evaluation=source_claim_evaluation or SourceClaimEvaluation(),
        warnings=tuple(warnings),
    )


def build_media_source_record_from_import_plan(plan: MediaImportPlan, *, source_id: str = "") -> MediaSourceRecord:
    return build_media_source_record(
        source_page=plan.source_page,
        source_bucket=plan.source_bucket,
        local_address=plan.proposed_local_address,
        title=plan.source_title or plan.source_filename,
        source_role=plan.source_claim_evaluation.source_role,
        claim_basis=plan.source_claim_evaluation.claim_basis,
        currentness_status=plan.source_claim_evaluation.currentness_status,
        source_claim_evaluation=plan.source_claim_evaluation,
        source_id=source_id,
    )


def build_case_local_profile_from_text(
    *,
    case_id: str,
    text: str,
    canonical_name: str = "",
    default_source_bucket: MediaBucket | str = MediaBucket.ARTICLES,
    default_source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    default_claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    default_currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN,
) -> ProfileRecord:
    blocks = parse_profile_text_blocks(
        text,
        default_source_bucket=normalize_media_bucket(default_source_bucket).value,
        default_source_role=default_source_role,
        default_claim_basis=default_claim_basis,
        default_currentness_status=default_currentness_status,
    )
    name = canonical_name or next((block.name for block in blocks if block.name), "")
    return build_profile_record(
        canonical_name=name,
        text_blocks=blocks,
        collection_level=ProfileCollectionLevel.CASE_LOCAL_PROFILES,
        case_id=case_id,
    )


def build_global_profile_from_case_profile(case_profile: ProfileRecord, *, profile_id: str = "") -> ProfileRecord:
    return build_profile_record(
        canonical_name=case_profile.canonical_name,
        text_blocks=case_profile.text_blocks,
        collection_level=ProfileCollectionLevel.GLOBAL_HEADER_PROFILES,
        profile_id=profile_id,
    )


def build_profile_record(
    *,
    canonical_name: str,
    text_blocks: Iterable[ProfileTextBlock] = (),
    collection_level: ProfileCollectionLevel = ProfileCollectionLevel.GLOBAL_HEADER_PROFILES,
    case_id: str = "",
    profile_id: str = "",
) -> ProfileRecord:
    blocks = tuple(text_blocks)
    identifiers: list[IdentifierClaim] = []
    for block in blocks:
        identifiers.extend(block.to_identifier_claims())
    stable_id = profile_id or stable_profile_id("profile", collection_level.value, case_id, canonical_name)
    return ProfileRecord(
        profile_id=stable_id,
        canonical_name=canonical_name,
        collection_level=collection_level,
        case_id=case_id,
        text_blocks=blocks,
        identifiers=tuple(identifiers),
    )


def build_media_source_record(
    *,
    source_page: str,
    source_bucket: MediaBucket | str,
    local_address: str = "",
    title: str = "",
    captured_or_recorded_date: str = "",
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN,
    source_claim_evaluation: SourceClaimEvaluation | None = None,
    source_id: str = "",
) -> MediaSourceRecord:
    stable_id = source_id or stable_profile_id("media", source_page, source_bucket, local_address, title)
    return MediaSourceRecord(
        source_id=stable_id,
        source_page=source_page,
        source_bucket=source_bucket,
        local_address=local_address,
        title=title,
        captured_or_recorded_date=captured_or_recorded_date,
        source_role=source_role,
        claim_basis=claim_basis,
        currentness_status=currentness_status,
        source_claim_evaluation=source_claim_evaluation,
    )


def build_case_record(
    *,
    database_root: str,
    case_title: str,
    profiles: Iterable[ProfileRecord] = (),
    media_sources: Iterable[MediaSourceRecord] = (),
    case_id: str = "",
    case_root: str = "",
) -> CaseRecord:
    stable_case_id = case_id or stable_profile_id("case", case_title)
    root = case_root or str(Path(database_root) / "Cases" / sanitize_path_part(case_title))
    return CaseRecord(
        case_id=stable_case_id,
        case_title=case_title,
        case_root=root,
        layout=build_case_folder_layout(root),
        profiles=tuple(profiles),
        media_sources=tuple(media_sources),
    )


def manifest_payload_sha256(manifest: ProfileMediaDatabaseManifest) -> str:
    return hashlib.sha256(stable_json_dumps(manifest.payload_dict()).encode("utf-8")).hexdigest()


def manifest_with_hash(manifest: ProfileMediaDatabaseManifest) -> ProfileMediaDatabaseManifest:
    return ProfileMediaDatabaseManifest(
        manifest_id=manifest.manifest_id,
        database_root=manifest.database_root,
        global_profiles_path=manifest.global_profiles_path,
        cases=manifest.cases,
        global_profiles=manifest.global_profiles,
        move_plans=manifest.move_plans,
        review_queue=manifest.review_queue,
        audit_events=manifest.audit_events,
        schema_version=manifest.schema_version,
        scope=manifest.scope,
        created_at_utc=manifest.created_at_utc,
        updated_at_utc=manifest.updated_at_utc,
        payload_sha256=manifest_payload_sha256(manifest),
    )


def build_manifest(
    *,
    database_root: str,
    cases: Iterable[CaseRecord] = (),
    global_profiles: Iterable[ProfileRecord] = (),
    move_plans: Iterable[FolderMovePlan] = (),
    review_queue: ProfileMediaReviewQueue | None = None,
    audit_events: Iterable[ProfileMediaAuditEvent] = (),
    manifest_id: str = "",
) -> ProfileMediaDatabaseManifest:
    stable_id = manifest_id or stable_profile_id("pmdb", database_root)
    manifest = ProfileMediaDatabaseManifest(
        manifest_id=stable_id,
        database_root=database_root,
        global_profiles_path=build_global_profiles_path(database_root),
        cases=tuple(cases),
        global_profiles=tuple(global_profiles),
        move_plans=tuple(move_plans),
        review_queue=review_queue,
        audit_events=tuple(audit_events),
    )
    return manifest_with_hash(manifest)




def write_json_payload(path: str | Path, payload: Any, *, create_parent: bool = False, overwrite: bool = True) -> dict[str, Any]:
    """Write a JSON payload to disk with explicit, narrow permissions.

    This helper may create a manifest/tree text file, but it never moves,
    renames, copies, classifies, scans, or creates case folders. Parent folder
    creation is opt-in through create_parent=True.
    """

    target = Path(path)
    warnings: list[str] = []
    if target.exists() and not overwrite:
        return {
            "status": "blocked_destination_exists",
            "path": str(target),
            "performed": False,
            "warnings": ("destination_exists_overwrite_false",),
        }
    if not target.parent.exists():
        if create_parent:
            target.parent.mkdir(parents=True, exist_ok=True)
            warnings.append("created_parent_folder_for_json_payload")
        else:
            return {
                "status": "blocked_parent_missing",
                "path": str(target),
                "performed": False,
                "warnings": ("parent_folder_missing",),
            }
    text = json.dumps(_value_for_dict(payload), ensure_ascii=False, indent=2, sort_keys=True)
    target.write_text(text + "\n", encoding="utf-8")
    return {
        "status": "written",
        "path": str(target),
        "performed": True,
        "bytes": target.stat().st_size,
        "warnings": tuple(warnings),
    }


def read_json_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_manifest_json(
    manifest: ProfileMediaDatabaseManifest,
    path: str | Path,
    *,
    create_parent: bool = False,
    overwrite: bool = True,
) -> dict[str, Any]:
    return write_json_payload(path, manifest.to_dict(), create_parent=create_parent, overwrite=overwrite)


def _media_source_parent_for_bucket(
    bucket: MediaBucket,
    container_row_ids: dict[str, str],
) -> tuple[str, int]:
    if bucket == MediaBucket.ARTICLES:
        return container_row_ids.get("articles", ""), 4
    if bucket == MediaBucket.SOCIAL_MEDIA_ONLINE:
        return container_row_ids.get("social_media_online", ""), 5
    if bucket == MediaBucket.SOCIAL_MEDIA_OFFLINE:
        return container_row_ids.get("social_media_offline", ""), 5
    if bucket == MediaBucket.INTERNAL_MEDIA:
        return container_row_ids.get("internal_media", ""), 4
    if bucket == MediaBucket.REFERENCE_EXTANTS:
        return container_row_ids.get("reference_extants", ""), 3
    if bucket == MediaBucket.PEOPLE:
        return container_row_ids.get("people", ""), 3
    if bucket == MediaBucket.CASE_PROFILES:
        return container_row_ids.get("case_profiles", ""), 3
    return container_row_ids.get("sources", ""), 3


def build_database_tree_rows(manifest: ProfileMediaDatabaseManifest) -> tuple[ProfileMediaTreeRow, ...]:
    """Build a lightweight hierarchy-correct tree view model for Database mode.

    The tree is a view over the manifest. It does not scan folders, create folders,
    move folders, rename folders, or infer classifications/identifiers.
    """

    rows: list[ProfileMediaTreeRow] = []
    order = 0

    def next_order() -> int:
        nonlocal order
        value = order
        order += 1
        return value

    database_row_id = stable_profile_id("tree", manifest.manifest_id, "database")
    rows.append(
        ProfileMediaTreeRow(
            row_id=database_row_id,
            row_type="database_root",
            label=Path(manifest.database_root).name or manifest.database_root,
            path=manifest.database_root,
            level=0,
            display_order=next_order(),
        )
    )

    global_profiles_row_id = stable_profile_id("tree", manifest.manifest_id, "global_profiles")
    rows.append(
        ProfileMediaTreeRow(
            row_id=global_profiles_row_id,
            row_type="global_profiles",
            label="Profiles",
            path=manifest.global_profiles_path,
            level=1,
            parent_row_id=database_row_id,
            display_order=next_order(),
        )
    )

    for profile in manifest.global_profiles:
        rows.append(
            ProfileMediaTreeRow(
                row_id=stable_profile_id("tree_profile", profile.profile_id),
                row_type="profile",
                label=profile.canonical_name or profile.profile_id,
                path=str(Path(manifest.global_profiles_path) / sanitize_path_part(profile.canonical_name or profile.profile_id)),
                level=2,
                parent_row_id=global_profiles_row_id,
                display_order=next_order(),
                sensitive_identifier_source_evidenced_only=profile.no_automatic_sensitive_inference,
                weak_sensitive_inference_prohibited=profile.no_automatic_sensitive_inference,
            )
        )

    for case in manifest.cases:
        case_row_id = stable_profile_id("tree_case", case.case_id)
        rows.append(
            ProfileMediaTreeRow(
                row_id=case_row_id,
                row_type="case",
                label=case.case_title,
                path=case.case_root,
                level=1,
                parent_row_id=database_row_id,
                display_order=next_order(),
                case_id=case.case_id,
                case_title=case.case_title,
            )
        )

        container_row_ids: dict[str, str] = {}

        def add_container(row_type: str, label: str, path: str, level: int, parent_row_id: str) -> str:
            row_id = stable_profile_id("tree_case_child", case.case_id, row_type, path)
            container_row_ids[row_type] = row_id
            rows.append(
                ProfileMediaTreeRow(
                    row_id=row_id,
                    row_type=row_type,
                    label=label,
                    path=path,
                    level=level,
                    parent_row_id=parent_row_id,
                    display_order=next_order(),
                    case_id=case.case_id,
                    case_title=case.case_title,
                )
            )
            return row_id

        def add_media_sources_for_bucket(bucket: MediaBucket) -> None:
            for source in case.media_sources:
                normalized_bucket = normalize_media_bucket(source.source_bucket)
                if normalized_bucket != bucket:
                    continue
                parent_row_id, level = _media_source_parent_for_bucket(normalized_bucket, container_row_ids)
                rows.append(
                    ProfileMediaTreeRow(
                        row_id=stable_profile_id("tree_media_source", case.case_id, source.source_id),
                        row_type="media_source",
                        label=source.title or source.source_page or source.source_id,
                        path=source.local_address,
                        level=level,
                        parent_row_id=parent_row_id,
                        display_order=next_order(),
                        case_id=case.case_id,
                        case_title=case.case_title,
                        source_bucket=normalized_bucket.value,
                        source_role=source.source_role,
                        claim_basis=source.claim_basis,
                        currentness_status=source.currentness_status,
                        source_chain_gap=source.source_chain_gap,
                        disputed_framing=source.disputed_framing,
                    )
                )

        add_container("case_profiles", "Profiles", case.layout.case_profiles_path, 2, case_row_id)
        for profile in case.profiles:
            rows.append(
                ProfileMediaTreeRow(
                    row_id=stable_profile_id("tree_case_profile", case.case_id, profile.profile_id),
                    row_type="case_profile_record",
                    label=profile.canonical_name or profile.profile_id,
                    path=str(Path(case.layout.case_profiles_path) / sanitize_path_part(profile.canonical_name or profile.profile_id)),
                    level=3,
                    parent_row_id=container_row_ids["case_profiles"],
                    display_order=next_order(),
                    case_id=case.case_id,
                    case_title=case.case_title,
                    sensitive_identifier_source_evidenced_only=profile.no_automatic_sensitive_inference,
                    weak_sensitive_inference_prohibited=profile.no_automatic_sensitive_inference,
                )
            )

        add_container("people", "People", case.layout.people_path, 2, case_row_id)
        add_media_sources_for_bucket(MediaBucket.PEOPLE)

        sources_row_id = add_container("sources", "Sources", case.layout.sources_path, 2, case_row_id)
        add_container("articles", "Articles", case.layout.articles_path, 3, sources_row_id)
        add_media_sources_for_bucket(MediaBucket.ARTICLES)
        social_media_row_id = add_container("social_media", "Social Media", case.layout.social_media_path, 3, sources_row_id)
        add_container("social_media_offline", "Offline", case.layout.social_media_offline_path, 4, social_media_row_id)
        add_media_sources_for_bucket(MediaBucket.SOCIAL_MEDIA_OFFLINE)
        add_container("social_media_online", "Online", case.layout.social_media_online_path, 4, social_media_row_id)
        add_media_sources_for_bucket(MediaBucket.SOCIAL_MEDIA_ONLINE)
        add_container("internal_media", "Internal Media", case.layout.internal_media_path, 3, sources_row_id)
        add_media_sources_for_bucket(MediaBucket.INTERNAL_MEDIA)

        add_container("reference_extants", "Reference Extants", case.layout.reference_extants_path, 2, case_row_id)
        add_media_sources_for_bucket(MediaBucket.REFERENCE_EXTANTS)

        emitted_source_ids = {row.row_id for row in rows if row.row_type == "media_source" and row.case_id == case.case_id}
        for source in case.media_sources:
            row_id = stable_profile_id("tree_media_source", case.case_id, source.source_id)
            if row_id in emitted_source_ids:
                continue
            bucket = normalize_media_bucket(source.source_bucket)
            parent_row_id, level = _media_source_parent_for_bucket(bucket, container_row_ids)
            rows.append(
                ProfileMediaTreeRow(
                    row_id=row_id,
                    row_type="media_source",
                    label=source.title or source.source_page or source.source_id,
                    path=source.local_address,
                    level=level,
                    parent_row_id=parent_row_id,
                    display_order=next_order(),
                    case_id=case.case_id,
                    case_title=case.case_title,
                    source_bucket=bucket.value,
                    source_role=source.source_role,
                    claim_basis=source.claim_basis,
                    currentness_status=source.currentness_status,
                    source_chain_gap=source.source_chain_gap,
                    disputed_framing=source.disputed_framing,
                )
            )
    return tuple(rows)

def render_database_tree_text(rows: Iterable[ProfileMediaTreeRow]) -> str:
    lines: list[str] = []
    for row in rows:
        indent = "  " * max(0, row.level)
        label = row.label or row.path or row.row_id
        suffix = f" [{row.row_type}]"
        lines.append(f"{indent}{label}{suffix}")
    return "\n".join(lines)


def write_database_tree_text(
    manifest: ProfileMediaDatabaseManifest,
    path: str | Path,
    *,
    create_parent: bool = False,
    overwrite: bool = True,
) -> dict[str, Any]:
    target = Path(path)
    warnings: list[str] = []
    if target.exists() and not overwrite:
        return {"status": "blocked_destination_exists", "path": str(target), "performed": False, "warnings": ("destination_exists_overwrite_false",)}
    if not target.parent.exists():
        if create_parent:
            target.parent.mkdir(parents=True, exist_ok=True)
            warnings.append("created_parent_folder_for_tree_text")
        else:
            return {"status": "blocked_parent_missing", "path": str(target), "performed": False, "warnings": ("parent_folder_missing",)}
    rows = build_database_tree_rows(manifest)
    target.write_text(render_database_tree_text(rows) + "\n", encoding="utf-8")
    return {"status": "written", "path": str(target), "performed": True, "bytes": target.stat().st_size, "row_count": len(rows), "warnings": tuple(warnings)}

def parse_profile_text_blocks(
    text: str,
    *,
    default_source_bucket: str = "",
    default_source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    default_claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    default_currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN,
) -> tuple[ProfileTextBlock, ...]:
    records: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] = {}
    current_key = ""
    key_map = {
        "name": "name",
        "date": "date",
        "text": "text",
        "identifiers": "identifiers",
        "address": "local_address",
        "source": "source_page",
    }

    def flush() -> None:
        nonlocal current, current_key
        if any(v for v in current.values()):
            records.append(current)
        current = {}
        current_key = ""

    for raw_line in str(text or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or re.fullmatch(r"[-—_]{3,}", stripped):
            if current:
                flush()
            continue
        match = re.match(r"^(Name|Date|Text|Identifiers|Address|Source)\s*:\s*(.*)$", stripped, re.I)
        if match:
            label = match.group(1).lower()
            value = match.group(2).strip()
            current_key = key_map[label]
            current.setdefault(current_key, [])
            if value:
                current[current_key].append(value)
            continue
        if current_key:
            current.setdefault(current_key, []).append(stripped)
    flush()

    blocks: list[ProfileTextBlock] = []
    for rec in records:
        name = "\n".join(rec.get("name", ())).strip()
        date = "\n".join(rec.get("date", ())).strip()
        block_text = "\n".join(rec.get("text", ())).strip()
        identifiers_text = "\n".join(rec.get("identifiers", ())).strip()
        local_address = "\n".join(rec.get("local_address", ())).strip()
        source_page = "\n".join(rec.get("source_page", ())).strip()
        warnings: list[str] = []
        if not source_page:
            warnings.append("missing_source_page")
        if not local_address:
            warnings.append("missing_local_address")
        if not block_text:
            warnings.append("missing_text")
        blocks.append(
            ProfileTextBlock(
                name=name,
                date=date,
                text=block_text,
                identifiers=_split_identifier_text(identifiers_text),
                local_address=local_address,
                source_page=source_page,
                source_bucket=default_source_bucket,
                source_role=default_source_role,
                claim_basis=default_claim_basis,
                currentness_status=default_currentness_status,
                parser_warnings=tuple(warnings),
            )
        )
    return tuple(blocks)


def plan_folder_move(
    *,
    current_path: str,
    proposed_path: str,
    reason: str,
    source_basis: str = "",
    status: MovePlanStatus = MovePlanStatus.REVIEW_REQUIRED,
) -> FolderMovePlan:
    return FolderMovePlan(
        plan_id=stable_profile_id("move", current_path, proposed_path, reason, source_basis),
        current_path=current_path,
        proposed_path=proposed_path,
        reason=reason,
        source_basis=source_basis,
        status=status,
        audit_note="dry-run plan only; no folder was moved or renamed",
    )



def build_review_item_from_folder_move(
    move_plan: FolderMovePlan,
    *,
    case_id: str = "",
    case_title: str = "",
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN,
    source_chain_gap: bool = False,
    disputed_framing: bool = False,
    sensitive_review_required: bool = False,
    required_actions: Iterable[str] = (),
) -> ProfileMediaReviewItem:
    actions = tuple(required_actions) or ("review_current_path", "review_proposed_path", "confirm_before_any_folder_move")
    return ProfileMediaReviewItem(
        review_id=stable_profile_id("review", move_plan.plan_id, case_id, case_title, move_plan.current_path, move_plan.proposed_path),
        item_type=ReviewItemType.FOLDER_MOVE,
        title=f"Review folder move: {sanitize_path_part(case_title or Path(move_plan.proposed_path).name)}",
        case_id=case_id,
        case_title=case_title,
        current_path=move_plan.current_path,
        proposed_path=move_plan.proposed_path,
        reason=move_plan.reason,
        source_basis=move_plan.source_basis,
        source_role=source_role,
        claim_basis=claim_basis,
        currentness_status=currentness_status,
        source_chain_gap=source_chain_gap,
        disputed_framing=disputed_framing,
        sensitive_review_required=sensitive_review_required,
        required_actions=actions,
        status=ReviewItemStatus.PENDING_REVIEW if move_plan.status != MovePlanStatus.NO_CHANGE else ReviewItemStatus.NO_CHANGE,
    )


def build_review_items_from_case_repository_path_plan(plan: CaseRepositoryPathPlan) -> tuple[ProfileMediaReviewItem, ...]:
    items: list[ProfileMediaReviewItem] = []
    sensitive_required = any(repository_bucket_looks_sensitive(part) for part in plan.classification.path_parts())
    if plan.move_plan is not None:
        items.append(
            build_review_item_from_folder_move(
                plan.move_plan,
                case_id=stable_profile_id("case", plan.proposed_case_root, plan.classification.case_title),
                case_title=plan.classification.case_title,
                source_role=plan.classification.source_role,
                claim_basis=plan.classification.claim_basis,
                currentness_status=plan.classification.currentness_status,
                source_chain_gap=False,
                disputed_framing=False,
                sensitive_review_required=sensitive_required,
                required_actions=(
                    "review_classification_facets",
                    "review_source_basis",
                    "confirm_folder_rename_or_move_separately",
                ),
            )
        )
    for warning in plan.classification.warnings:
        items.append(
            ProfileMediaReviewItem(
                review_id=stable_profile_id("review_warning", plan.plan_id, warning),
                item_type=ReviewItemType.CASE_REPOSITORY_PATH_CHANGE,
                title=f"Review classification warning: {warning}",
                case_id=stable_profile_id("case", plan.proposed_case_root, plan.classification.case_title),
                case_title=plan.classification.case_title,
                proposed_path=plan.proposed_case_root,
                reason=warning,
                source_basis=plan.classification.source_basis,
                source_role=plan.classification.source_role,
                claim_basis=plan.classification.claim_basis,
                currentness_status=plan.classification.currentness_status,
                sensitive_review_required=True,
                required_actions=("add_source_basis_or_reclassify", "do_not_move_until_reviewed"),
            )
        )
    return tuple(items)


def build_review_queue(items: Iterable[ProfileMediaReviewItem], *, queue_id: str = "") -> ProfileMediaReviewQueue:
    item_tuple = tuple(items)
    stable_id = queue_id or stable_profile_id("review_queue", *(item.review_id for item in item_tuple))
    return ProfileMediaReviewQueue(queue_id=stable_id, items=item_tuple)


def mark_review_item_decision(
    item: ProfileMediaReviewItem,
    *,
    approved: bool,
    reviewer_note: str = "",
    reviewed_by: str = "",
) -> ProfileMediaReviewItem:
    return ProfileMediaReviewItem(
        review_id=item.review_id,
        item_type=item.item_type,
        title=item.title,
        case_id=item.case_id,
        case_title=item.case_title,
        current_path=item.current_path,
        proposed_path=item.proposed_path,
        reason=item.reason,
        source_basis=item.source_basis,
        source_role=item.source_role,
        claim_basis=item.claim_basis,
        currentness_status=item.currentness_status,
        source_chain_gap=item.source_chain_gap,
        disputed_framing=item.disputed_framing,
        sensitive_review_required=item.sensitive_review_required,
        required_actions=item.required_actions,
        status=ReviewItemStatus.APPROVED_FOR_ACTION if approved else ReviewItemStatus.REJECTED,
        reviewer_note=reviewer_note,
        reviewed_by=reviewed_by,
        user_confirmation_recorded=True,
        folder_creation_performed=False,
        file_move_performed=False,
        created_at_utc=item.created_at_utc,
        reviewed_at_utc=utc_now_iso(),
        audit_note="review decision recorded only; no folder was created, moved, copied, or renamed",
    )


def build_audit_event(
    *,
    event_type: AuditEventType,
    subject_id: str,
    case_id: str = "",
    previous_value: str = "",
    new_value: str = "",
    reason: str = "",
    source_basis: str = "",
    review_id: str = "",
    performed: bool = False,
) -> ProfileMediaAuditEvent:
    return ProfileMediaAuditEvent(
        event_id=stable_profile_id("audit", event_type.value, subject_id, previous_value, new_value, reason, source_basis, review_id, performed),
        event_type=event_type,
        subject_id=subject_id,
        case_id=case_id,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        source_basis=source_basis,
        review_id=review_id,
        performed=performed,
        folder_creation_performed=False,
        file_move_performed=False,
    )


def build_audit_event_for_review_decision(item: ProfileMediaReviewItem) -> ProfileMediaAuditEvent:
    return build_audit_event(
        event_type=AuditEventType.REVIEW_DECISION_RECORDED,
        subject_id=item.review_id,
        case_id=item.case_id,
        previous_value=item.current_path,
        new_value=item.proposed_path,
        reason=item.reason or item.status.value,
        source_basis=item.source_basis,
        review_id=item.review_id,
        performed=False,
    )


def build_folder_operation_from_review_item(
    item: ProfileMediaReviewItem,
    *,
    dry_run_only: bool = True,
    allow_execute: bool = False,
) -> ProfileMediaFolderOperation:
    """Build a review-gated folder operation from an approved review item.

    The operation is inert by default. Even an approved review item only becomes
    executable when allow_execute=True and dry_run_only=False are both supplied.
    """

    warnings: list[str] = []
    if item.item_type != ReviewItemType.FOLDER_MOVE:
        warnings.append("unsupported_review_item_type_for_folder_move")
    if item.status != ReviewItemStatus.APPROVED_FOR_ACTION or not item.user_confirmation_recorded:
        warnings.append("review_not_approved_or_confirmation_missing")
    if not item.current_path:
        warnings.append("missing_current_path")
    if not item.proposed_path:
        warnings.append("missing_proposed_path")

    allowed = (
        item.item_type == ReviewItemType.FOLDER_MOVE
        and item.status == ReviewItemStatus.APPROVED_FOR_ACTION
        and item.user_confirmation_recorded
        and bool(item.current_path)
        and bool(item.proposed_path)
        and allow_execute
        and not dry_run_only
    )
    return ProfileMediaFolderOperation(
        operation_id=stable_profile_id("folder_operation", item.review_id, item.current_path, item.proposed_path, dry_run_only, allow_execute),
        operation_type=FolderOperationType.MOVE_OR_RENAME_FOLDER,
        source_path=item.current_path,
        destination_path=item.proposed_path,
        required_parent_path=str(Path(item.proposed_path).parent) if item.proposed_path else "",
        case_id=item.case_id,
        review_id=item.review_id,
        reason=item.reason,
        source_basis=item.source_basis,
        review_status=item.status,
        dry_run_only=dry_run_only,
        user_confirmation_required=True,
        allowed_to_execute=allowed,
        warnings=tuple(warnings),
    )


def build_folder_operations_from_review_queue(
    queue: ProfileMediaReviewQueue,
    *,
    dry_run_only: bool = True,
    allow_execute: bool = False,
) -> tuple[ProfileMediaFolderOperation, ...]:
    return tuple(
        build_folder_operation_from_review_item(item, dry_run_only=dry_run_only, allow_execute=allow_execute)
        for item in queue.items
        if item.item_type == ReviewItemType.FOLDER_MOVE
    )


def _folder_operation_ready_status(operation: ProfileMediaFolderOperation) -> FolderOperationStatus:
    if operation.source_path and operation.destination_path:
        if operation.source_path.replace("/", "\\").lower() == operation.destination_path.replace("/", "\\").lower():
            return FolderOperationStatus.NO_CHANGE
    if operation.review_status != ReviewItemStatus.APPROVED_FOR_ACTION or not operation.allowed_to_execute:
        return FolderOperationStatus.BLOCKED_REVIEW_NOT_APPROVED
    return FolderOperationStatus.READY_TO_APPLY


def validate_folder_operation_preconditions(operation: ProfileMediaFolderOperation) -> ProfileMediaFolderOperationResult:
    warnings = list(operation.warnings)
    status = _folder_operation_ready_status(operation)
    if status == FolderOperationStatus.NO_CHANGE:
        return ProfileMediaFolderOperationResult(
            operation_id=operation.operation_id,
            status=status,
            source_path=operation.source_path,
            destination_path=operation.destination_path,
            warnings=tuple(warnings),
        )
    if operation.dry_run_only:
        warnings.append("dry_run_only_no_filesystem_change_allowed")
        return ProfileMediaFolderOperationResult(
            operation_id=operation.operation_id,
            status=FolderOperationStatus.PLANNED_DRY_RUN,
            source_path=operation.source_path,
            destination_path=operation.destination_path,
            warnings=tuple(warnings),
        )
    if status != FolderOperationStatus.READY_TO_APPLY:
        return ProfileMediaFolderOperationResult(
            operation_id=operation.operation_id,
            status=status,
            source_path=operation.source_path,
            destination_path=operation.destination_path,
            warnings=tuple(warnings),
        )
    source = Path(operation.source_path)
    destination = Path(operation.destination_path)
    if not source.exists():
        warnings.append("source_path_does_not_exist")
        return ProfileMediaFolderOperationResult(
            operation_id=operation.operation_id,
            status=FolderOperationStatus.BLOCKED_SOURCE_MISSING,
            source_path=str(source),
            destination_path=str(destination),
            warnings=tuple(warnings),
        )
    if destination.exists():
        warnings.append("destination_path_already_exists")
        return ProfileMediaFolderOperationResult(
            operation_id=operation.operation_id,
            status=FolderOperationStatus.BLOCKED_DESTINATION_EXISTS,
            source_path=str(source),
            destination_path=str(destination),
            warnings=tuple(warnings),
        )
    if not destination.parent.exists():
        warnings.append("destination_parent_missing")
        return ProfileMediaFolderOperationResult(
            operation_id=operation.operation_id,
            status=FolderOperationStatus.BLOCKED_PARENT_MISSING,
            source_path=str(source),
            destination_path=str(destination),
            warnings=tuple(warnings),
        )
    return ProfileMediaFolderOperationResult(
        operation_id=operation.operation_id,
        status=FolderOperationStatus.READY_TO_APPLY,
        source_path=str(source),
        destination_path=str(destination),
        warnings=tuple(warnings),
    )


def apply_folder_operation(
    operation: ProfileMediaFolderOperation,
    *,
    execute: bool = False,
    create_parent: bool = False,
) -> ProfileMediaFolderOperationResult:
    """Apply a reviewed folder move/rename only when explicitly enabled.

    Defaults are deliberately inert. No folder is moved unless execute=True,
    operation.dry_run_only is False, operation.allowed_to_execute is True, and
    the review status is APPROVED_FOR_ACTION.
    """

    if not execute or operation.dry_run_only:
        result = validate_folder_operation_preconditions(
            ProfileMediaFolderOperation(
                operation_id=operation.operation_id,
                operation_type=operation.operation_type,
                source_path=operation.source_path,
                destination_path=operation.destination_path,
                required_parent_path=operation.required_parent_path,
                case_id=operation.case_id,
                review_id=operation.review_id,
                reason=operation.reason,
                source_basis=operation.source_basis,
                review_status=operation.review_status,
                dry_run_only=True,
                user_confirmation_required=operation.user_confirmation_required,
                allowed_to_execute=False,
                warnings=operation.warnings,
            )
        )
        return ProfileMediaFolderOperationResult(
            operation_id=result.operation_id,
            status=FolderOperationStatus.PLANNED_DRY_RUN if result.status != FolderOperationStatus.NO_CHANGE else result.status,
            source_path=result.source_path,
            destination_path=result.destination_path,
            performed=False,
            dry_run=True,
            warnings=result.warnings,
            error=result.error,
        )

    source = Path(operation.source_path)
    destination = Path(operation.destination_path)
    if create_parent and not destination.parent.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)

    preflight = validate_folder_operation_preconditions(operation)
    if preflight.status != FolderOperationStatus.READY_TO_APPLY:
        return preflight
    try:
        shutil.move(str(source), str(destination))
    except Exception as exc:  # pragma: no cover - defensive safety surface
        return ProfileMediaFolderOperationResult(
            operation_id=operation.operation_id,
            status=FolderOperationStatus.ERROR,
            source_path=str(source),
            destination_path=str(destination),
            performed=False,
            dry_run=False,
            warnings=preflight.warnings,
            error=str(exc),
        )
    return ProfileMediaFolderOperationResult(
        operation_id=operation.operation_id,
        status=FolderOperationStatus.APPLIED,
        source_path=str(source),
        destination_path=str(destination),
        performed=True,
        dry_run=False,
        created_parent=False,
        moved_or_renamed_folder=True,
        warnings=preflight.warnings,
    )


def build_audit_event_for_folder_operation_result(
    operation: ProfileMediaFolderOperation,
    result: ProfileMediaFolderOperationResult,
) -> ProfileMediaAuditEvent:
    return build_audit_event(
        event_type=AuditEventType.FOLDER_OPERATION_APPLIED if result.performed else AuditEventType.FOLDER_OPERATION_PLANNED,
        subject_id=operation.operation_id,
        case_id=operation.case_id,
        previous_value=operation.source_path,
        new_value=operation.destination_path,
        reason=operation.reason or result.status.value,
        source_basis=operation.source_basis,
        review_id=operation.review_id,
        performed=result.performed,
    )


_SENSITIVE_REPOSITORY_BUCKET_TOKENS = (
    "religious identity",
    "religion",
    "muslim",
    "christian",
    "jewish",
    "hindu",
    "sikh",
    "ethnicity",
    "skin colour",
    "skin color",
)


def repository_bucket_looks_sensitive(value: str) -> bool:
    lowered = str(value or "").lower()
    return any(token in lowered for token in _SENSITIVE_REPOSITORY_BUCKET_TOKENS)


def normalize_classification_parts(*parts: str) -> tuple[str, ...]:
    return tuple(sanitize_path_part(part) for part in parts if str(part or "").strip())


def build_case_repository_classification(
    *,
    domain: str,
    conduct: Iterable[str] = (),
    location_type: str = "",
    relationship_or_context: str = "",
    sex_or_gender_pattern: str = "",
    action_type: str = "",
    religious_identity_bucket: str = "Non-religious or not identified",
    date_bucket: str = "Undated",
    source_name: str = "Unknown Source",
    case_title: str = "Untitled Case",
    source_basis: str = "",
    claim_basis: ClaimBasis = ClaimBasis.UNKNOWN_CLAIM_BASIS,
    source_role: ProfileSourceRole = ProfileSourceRole.UNKNOWN_SOURCE_ROLE,
    currentness_status: CurrentnessStatus = CurrentnessStatus.UNKNOWN,
) -> CaseRepositoryClassification:
    warnings: list[str] = []
    if not domain:
        warnings.append("missing_domain")
    if not case_title:
        warnings.append("missing_case_title")
    if repository_bucket_looks_sensitive(religious_identity_bucket) and not source_basis:
        warnings.append("sensitive_repository_bucket_without_source_basis")
    return CaseRepositoryClassification(
        domain=domain or "Unclassified",
        conduct=tuple(str(part).strip() for part in conduct if str(part).strip()),
        location_type=location_type,
        relationship_or_context=relationship_or_context,
        sex_or_gender_pattern=sex_or_gender_pattern,
        action_type=action_type,
        religious_identity_bucket=religious_identity_bucket or "Non-religious or not identified",
        date_bucket=date_bucket or "Undated",
        source_name=source_name or "Unknown Source",
        case_title=case_title or "Untitled Case",
        source_basis=source_basis,
        claim_basis=claim_basis,
        source_role=source_role,
        currentness_status=currentness_status,
        warnings=tuple(warnings),
    )


def build_case_repository_path(database_root: str, classification: CaseRepositoryClassification) -> str:
    root = Path(database_root)
    path = root
    for part in classification.path_parts():
        path = path / part
    return str(path)


def plan_case_repository_location(
    *,
    database_root: str,
    classification: CaseRepositoryClassification,
    current_case_root: str = "",
    source_basis: str = "",
) -> CaseRepositoryPathPlan:
    proposed = build_case_repository_path(database_root, classification)
    normalized_current = str(Path(current_case_root)) if current_case_root else ""
    normalized_proposed = str(Path(proposed))
    move_plan: FolderMovePlan | None = None
    status = MovePlanStatus.REVIEW_REQUIRED
    if normalized_current:
        if normalized_current.replace("/", "\\").lower() == normalized_proposed.replace("/", "\\").lower():
            status = MovePlanStatus.NO_CHANGE
        else:
            move_plan = plan_folder_move(
                current_path=normalized_current,
                proposed_path=normalized_proposed,
                reason="case repository classification path changed",
                source_basis=source_basis or classification.source_basis,
                status=MovePlanStatus.REVIEW_REQUIRED,
            )
    plan = CaseRepositoryPathPlan(
        plan_id=stable_profile_id("case_path", database_root, normalized_current, normalized_proposed, classification.source_basis),
        database_root=str(Path(database_root)),
        classification=classification,
        current_case_root=normalized_current,
        proposed_case_root=normalized_proposed,
        layout=build_case_folder_layout(normalized_proposed),
        move_plan=move_plan,
        status=status,
        required_review=status != MovePlanStatus.NO_CHANGE,
    )
    return plan


def build_case_record_from_repository_plan(
    *,
    plan: CaseRepositoryPathPlan,
    profiles: Iterable[ProfileRecord] = (),
    media_sources: Iterable[MediaSourceRecord] = (),
    case_id: str = "",
) -> CaseRecord:
    stable_case_id = case_id or stable_profile_id("case", plan.proposed_case_root, plan.classification.case_title)
    return CaseRecord(
        case_id=stable_case_id,
        case_title=plan.classification.case_title,
        case_root=plan.proposed_case_root,
        layout=plan.layout,
        profiles=tuple(profiles),
        media_sources=tuple(media_sources),
    )
