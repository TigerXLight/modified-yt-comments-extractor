from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any

from evidence_schema import PrimarySourceStatus, SourceRole, utc_now_iso


EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION = "evidence-database-index-v1"

EVIDENCE_DATABASE_INDEX_SCOPE = (
    "local evidence database index metadata only; no broad folder scanning, "
    "no file movement, no folder creation, no automatic classification, no "
    "sensitive-attribute inference, no source fetching, no archive access, "
    "no media download, no browser automation, no scraping, no provider calls, "
    "no credential access, and no GUI behavior"
)

CLASSIFICATION_UNKNOWN = "unknown"
CLASSIFICATION_NOT_EVIDENCED = "not_evidenced"
CLASSIFICATION_USER_CONFIRMED = "user_confirmed"
CLASSIFICATION_PROPOSED = "proposed"
CLASSIFICATION_REJECTED = "rejected"
CLASSIFICATION_SUPERSEDED = "superseded"

PROPOSAL_STATUS_DRY_RUN = "dry_run"
PROPOSAL_STATUS_USER_CONFIRMATION_REQUIRED = "user_confirmation_required"
PROPOSAL_STATUS_REJECTED = "rejected"
PROPOSAL_STATUS_SUPERSEDED = "superseded"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class EvidenceClassificationValue(_StringEnum):
    UNKNOWN = CLASSIFICATION_UNKNOWN
    NOT_EVIDENCED = CLASSIFICATION_NOT_EVIDENCED
    USER_CONFIRMED = CLASSIFICATION_USER_CONFIRMED
    PROPOSED = CLASSIFICATION_PROPOSED
    REJECTED = CLASSIFICATION_REJECTED
    SUPERSEDED = CLASSIFICATION_SUPERSEDED


def _clean(value: object) -> str:
    return str(value or "").strip()


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
        return {str(key): _value_for_dict(item) for key, item in sorted(value.items())}
    return value


def stable_json_dumps(data: Any) -> str:
    return json.dumps(_value_for_dict(data), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_evidence_id(prefix: str, *parts: object) -> str:
    payload = "\n".join(_clean(part).replace("\\", "/") for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
    safe_prefix = "".join(ch for ch in _clean(prefix).lower() if ch.isalnum() or ch == "_")
    return f"{safe_prefix or 'evidence'}_{digest}"


@dataclass(frozen=True)
class EvidenceDatabaseRoot:
    root_id: str
    root_path: str
    label: str = ""
    taxonomy_version_id: str = ""
    registered_at_utc: str = field(default_factory=utc_now_iso)
    dry_run_required: bool = True
    moves_require_explicit_approval: bool = True
    broad_scan_allowed: bool = False
    notes: str = ""
    scope: str = EVIDENCE_DATABASE_INDEX_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceTaxonomyVersion:
    taxonomy_version_id: str
    label: str = ""
    schema_version: str = EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION
    dimension_order: tuple[str, ...] = ()
    unknown_labels: tuple[str, ...] = ("unknown", "not identified", "not evidenced")
    sensitive_dimensions: tuple[str, ...] = (
        "religion_identity_status",
        "ethnicity_identity_status",
        "sex_or_gender_category",
        "relationship_category",
        "adult_or_child",
    )
    created_at_utc: str = field(default_factory=utc_now_iso)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceItemIdentity:
    item_id: str
    display_name: str = ""
    source_url: str = ""
    local_path_hint: str = ""
    export_package_id: str = ""
    manifest_path: str = ""
    queue_item_id: str = ""
    source_row_id: str = ""
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidencePathRecord:
    path_record_id: str
    item_id: str
    current_path: str = ""
    previous_path: str = ""
    proposed_path: str = ""
    path_role: str = "current"
    history_note: str = ""
    recorded_at_utc: str = field(default_factory=utc_now_iso)
    file_operation_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceClassificationState:
    classification_value: EvidenceClassificationValue = EvidenceClassificationValue.UNKNOWN
    dimensions: dict[str, str] = field(default_factory=dict)
    user_confirmed: bool = False
    source_evidenced: bool = False
    sensitive_dimensions_present: tuple[str, ...] = ()
    weak_inference_prohibited: bool = True
    user_confirmation_required: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceBasis:
    basis_id: str
    item_id: str
    basis_type: str = ""
    source_url: str = ""
    source_role: SourceRole = SourceRole.UNKNOWN_SOURCE_ROLE
    source_status: PrimarySourceStatus = PrimarySourceStatus.MANUAL_SOURCE_NOTE
    evidence_text: str = ""
    user_note: str = ""
    confidence: str = ""
    sensitive_basis_confirmed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidencePlacementProposal:
    proposal_id: str
    item_id: str
    database_root_id: str
    current_path: str = ""
    proposed_path: str = ""
    basis_ids: tuple[str, ...] = ()
    status: str = PROPOSAL_STATUS_DRY_RUN
    reason: str = ""
    confidence: str = ""
    user_confirmation_required: bool = True
    file_operation_performed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceReclassificationProposal:
    proposal_id: str
    item_id: str
    previous_path: str = ""
    proposed_path: str = ""
    previous_classification: EvidenceClassificationState = field(
        default_factory=EvidenceClassificationState
    )
    proposed_classification: EvidenceClassificationState = field(
        default_factory=lambda: EvidenceClassificationState(
            classification_value=EvidenceClassificationValue.PROPOSED
        )
    )
    basis_ids: tuple[str, ...] = ()
    status: str = PROPOSAL_STATUS_USER_CONFIRMATION_REQUIRED
    reason: str = ""
    old_new_path_history_preserved: bool = True
    user_confirmation_required: bool = True
    file_operation_performed: bool = False
    created_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceIndexRecord:
    identity: EvidenceItemIdentity
    database_root_id: str = ""
    taxonomy_version_id: str = ""
    path_records: tuple[EvidencePathRecord, ...] = ()
    classification_state: EvidenceClassificationState = field(
        default_factory=EvidenceClassificationState
    )
    evidence_basis: tuple[EvidenceBasis, ...] = ()
    placement_proposals: tuple[EvidencePlacementProposal, ...] = ()
    reclassification_proposals: tuple[EvidenceReclassificationProposal, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class EvidenceIndexManifest:
    manifest_id: str
    schema_version: str = EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION
    database_roots: tuple[EvidenceDatabaseRoot, ...] = ()
    taxonomy_versions: tuple[EvidenceTaxonomyVersion, ...] = ()
    records: tuple[EvidenceIndexRecord, ...] = ()
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    payload_sha256: str = ""
    scope: str = EVIDENCE_DATABASE_INDEX_SCOPE

    def payload_dict(self) -> dict[str, Any]:
        return {
            "created_at_utc": self.created_at_utc,
            "database_roots": [_value_for_dict(item) for item in self.database_roots],
            "manifest_id": self.manifest_id,
            "records": [_value_for_dict(item) for item in self.records],
            "schema_version": self.schema_version,
            "scope": self.scope,
            "taxonomy_versions": [_value_for_dict(item) for item in self.taxonomy_versions],
            "updated_at_utc": self.updated_at_utc,
        }

    def to_dict(self) -> dict[str, Any]:
        data = self.payload_dict()
        data["database_root_count"] = len(self.database_roots)
        data["record_count"] = len(self.records)
        data["taxonomy_version_count"] = len(self.taxonomy_versions)
        data["payload_sha256"] = self.payload_sha256
        return data


def evidence_index_payload_sha256(manifest: EvidenceIndexManifest) -> str:
    return hashlib.sha256(stable_json_dumps(manifest.payload_dict()).encode("utf-8")).hexdigest()


def evidence_index_manifest_with_hash(manifest: EvidenceIndexManifest) -> EvidenceIndexManifest:
    return EvidenceIndexManifest(
        manifest_id=manifest.manifest_id,
        schema_version=manifest.schema_version,
        database_roots=manifest.database_roots,
        taxonomy_versions=manifest.taxonomy_versions,
        records=manifest.records,
        created_at_utc=manifest.created_at_utc,
        updated_at_utc=manifest.updated_at_utc,
        payload_sha256=evidence_index_payload_sha256(manifest),
        scope=manifest.scope,
    )


def build_evidence_item_identity(
    *,
    display_name: str = "",
    source_url: str = "",
    local_path_hint: str = "",
    export_package_id: str = "",
    manifest_path: str = "",
    queue_item_id: str = "",
    source_row_id: str = "",
    item_id: str = "",
) -> EvidenceItemIdentity:
    stable_item_id = item_id or stable_evidence_id(
        "edi",
        source_url,
        local_path_hint,
        export_package_id,
        manifest_path,
        queue_item_id,
        source_row_id,
        display_name,
    )
    return EvidenceItemIdentity(
        item_id=stable_item_id,
        display_name=display_name,
        source_url=source_url,
        local_path_hint=local_path_hint,
        export_package_id=export_package_id,
        manifest_path=manifest_path,
        queue_item_id=queue_item_id,
        source_row_id=source_row_id,
    )
