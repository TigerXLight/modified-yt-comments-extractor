from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
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

INDEX_STORE_STATUS_OK = "ok"
INDEX_STORE_STATUS_MISSING = "missing"
INDEX_STORE_STATUS_INVALID = "invalid"
INDEX_STORE_STATUS_WRITE_FAILED = "write_failed"


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


@dataclass(frozen=True)
class EvidenceIndexStoreResult:
    status: str
    index_path: str = ""
    manifest: EvidenceIndexManifest | None = None
    payload_sha256: str = ""
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status == INDEX_STORE_STATUS_OK

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": list(self.errors),
            "index_path": self.index_path,
            "ok": self.ok,
            "payload_sha256": self.payload_sha256,
            "status": self.status,
            "warnings": list(self.warnings),
        }


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


def _dict_value(data: dict[str, Any], key: str, default: Any = "") -> Any:
    return data.get(key, default)


def _tuple_str(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(_clean(item) for item in value if _clean(item))
    return (_clean(value),)


def _source_role_from_value(value: Any) -> SourceRole:
    try:
        return SourceRole(value)
    except ValueError:
        return SourceRole.UNKNOWN_SOURCE_ROLE


def _source_status_from_value(value: Any) -> PrimarySourceStatus:
    try:
        return PrimarySourceStatus(value)
    except ValueError:
        return PrimarySourceStatus.MANUAL_SOURCE_NOTE


def _classification_from_dict(data: dict[str, Any] | None) -> EvidenceClassificationState:
    if not isinstance(data, dict):
        return EvidenceClassificationState()
    value = _dict_value(data, "classification_value", CLASSIFICATION_UNKNOWN)
    try:
        classification_value = EvidenceClassificationValue(value)
    except ValueError:
        classification_value = EvidenceClassificationValue.UNKNOWN
    dimensions = _dict_value(data, "dimensions", {})
    if not isinstance(dimensions, dict):
        dimensions = {}
    return EvidenceClassificationState(
        classification_value=classification_value,
        dimensions={_clean(key): _clean(item) for key, item in dimensions.items()},
        user_confirmed=bool(_dict_value(data, "user_confirmed", False)),
        source_evidenced=bool(_dict_value(data, "source_evidenced", False)),
        sensitive_dimensions_present=_tuple_str(
            _dict_value(data, "sensitive_dimensions_present", ())
        ),
        weak_inference_prohibited=bool(
            _dict_value(data, "weak_inference_prohibited", True)
        ),
        user_confirmation_required=bool(
            _dict_value(data, "user_confirmation_required", True)
        ),
        notes=_clean(_dict_value(data, "notes", "")),
    )


def evidence_index_manifest_from_dict(data: dict[str, Any]) -> EvidenceIndexManifest:
    roots = tuple(
        EvidenceDatabaseRoot(
            root_id=_clean(item.get("root_id", "")),
            root_path=_clean(item.get("root_path", "")),
            label=_clean(item.get("label", "")),
            taxonomy_version_id=_clean(item.get("taxonomy_version_id", "")),
            registered_at_utc=_clean(item.get("registered_at_utc", "")),
            dry_run_required=bool(item.get("dry_run_required", True)),
            moves_require_explicit_approval=bool(
                item.get("moves_require_explicit_approval", True)
            ),
            broad_scan_allowed=bool(item.get("broad_scan_allowed", False)),
            notes=_clean(item.get("notes", "")),
            scope=_clean(item.get("scope", EVIDENCE_DATABASE_INDEX_SCOPE)),
        )
        for item in data.get("database_roots", [])
        if isinstance(item, dict)
    )
    taxonomy_versions = tuple(
        EvidenceTaxonomyVersion(
            taxonomy_version_id=_clean(item.get("taxonomy_version_id", "")),
            label=_clean(item.get("label", "")),
            schema_version=_clean(
                item.get("schema_version", EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION)
            ),
            dimension_order=_tuple_str(item.get("dimension_order", ())),
            unknown_labels=_tuple_str(item.get("unknown_labels", ())),
            sensitive_dimensions=_tuple_str(item.get("sensitive_dimensions", ())),
            created_at_utc=_clean(item.get("created_at_utc", "")),
            notes=_clean(item.get("notes", "")),
        )
        for item in data.get("taxonomy_versions", [])
        if isinstance(item, dict)
    )
    records: list[EvidenceIndexRecord] = []
    for item in data.get("records", []):
        if not isinstance(item, dict):
            continue
        identity_data = item.get("identity", {})
        if not isinstance(identity_data, dict):
            identity_data = {}
        identity = EvidenceItemIdentity(
            item_id=_clean(identity_data.get("item_id", "")),
            display_name=_clean(identity_data.get("display_name", "")),
            source_url=_clean(identity_data.get("source_url", "")),
            local_path_hint=_clean(identity_data.get("local_path_hint", "")),
            export_package_id=_clean(identity_data.get("export_package_id", "")),
            manifest_path=_clean(identity_data.get("manifest_path", "")),
            queue_item_id=_clean(identity_data.get("queue_item_id", "")),
            source_row_id=_clean(identity_data.get("source_row_id", "")),
            created_at_utc=_clean(identity_data.get("created_at_utc", "")),
        )
        path_records = tuple(
            EvidencePathRecord(
                path_record_id=_clean(path.get("path_record_id", "")),
                item_id=_clean(path.get("item_id", "")),
                current_path=_clean(path.get("current_path", "")),
                previous_path=_clean(path.get("previous_path", "")),
                proposed_path=_clean(path.get("proposed_path", "")),
                path_role=_clean(path.get("path_role", "current")),
                history_note=_clean(path.get("history_note", "")),
                recorded_at_utc=_clean(path.get("recorded_at_utc", "")),
                file_operation_performed=bool(
                    path.get("file_operation_performed", False)
                ),
            )
            for path in item.get("path_records", [])
            if isinstance(path, dict)
        )
        evidence_basis = tuple(
            EvidenceBasis(
                basis_id=_clean(basis.get("basis_id", "")),
                item_id=_clean(basis.get("item_id", "")),
                basis_type=_clean(basis.get("basis_type", "")),
                source_url=_clean(basis.get("source_url", "")),
                source_role=_source_role_from_value(
                    basis.get("source_role", SourceRole.UNKNOWN_SOURCE_ROLE.value)
                ),
                source_status=_source_status_from_value(
                    basis.get("source_status", PrimarySourceStatus.MANUAL_SOURCE_NOTE.value)
                ),
                evidence_text=_clean(basis.get("evidence_text", "")),
                user_note=_clean(basis.get("user_note", "")),
                confidence=_clean(basis.get("confidence", "")),
                sensitive_basis_confirmed=bool(
                    basis.get("sensitive_basis_confirmed", False)
                ),
                created_at_utc=_clean(basis.get("created_at_utc", "")),
            )
            for basis in item.get("evidence_basis", [])
                if isinstance(basis, dict)
        )
        placement_proposals = tuple(
            EvidencePlacementProposal(
                proposal_id=_clean(proposal.get("proposal_id", "")),
                item_id=_clean(proposal.get("item_id", "")),
                database_root_id=_clean(proposal.get("database_root_id", "")),
                current_path=_clean(proposal.get("current_path", "")),
                proposed_path=_clean(proposal.get("proposed_path", "")),
                basis_ids=_tuple_str(proposal.get("basis_ids", ())),
                status=_clean(proposal.get("status", PROPOSAL_STATUS_DRY_RUN)),
                reason=_clean(proposal.get("reason", "")),
                confidence=_clean(proposal.get("confidence", "")),
                user_confirmation_required=bool(
                    proposal.get("user_confirmation_required", True)
                ),
                file_operation_performed=bool(
                    proposal.get("file_operation_performed", False)
                ),
                created_at_utc=_clean(proposal.get("created_at_utc", "")),
            )
            for proposal in item.get("placement_proposals", [])
            if isinstance(proposal, dict)
        )
        reclassification_proposals = tuple(
            EvidenceReclassificationProposal(
                proposal_id=_clean(proposal.get("proposal_id", "")),
                item_id=_clean(proposal.get("item_id", "")),
                previous_path=_clean(proposal.get("previous_path", "")),
                proposed_path=_clean(proposal.get("proposed_path", "")),
                previous_classification=_classification_from_dict(
                    proposal.get("previous_classification")
                ),
                proposed_classification=_classification_from_dict(
                    proposal.get("proposed_classification")
                ),
                basis_ids=_tuple_str(proposal.get("basis_ids", ())),
                status=_clean(
                    proposal.get("status", PROPOSAL_STATUS_USER_CONFIRMATION_REQUIRED)
                ),
                reason=_clean(proposal.get("reason", "")),
                old_new_path_history_preserved=bool(
                    proposal.get("old_new_path_history_preserved", True)
                ),
                user_confirmation_required=bool(
                    proposal.get("user_confirmation_required", True)
                ),
                file_operation_performed=bool(
                    proposal.get("file_operation_performed", False)
                ),
                created_at_utc=_clean(proposal.get("created_at_utc", "")),
            )
            for proposal in item.get("reclassification_proposals", [])
            if isinstance(proposal, dict)
        )
        records.append(
            EvidenceIndexRecord(
                identity=identity,
                database_root_id=_clean(item.get("database_root_id", "")),
                taxonomy_version_id=_clean(item.get("taxonomy_version_id", "")),
                path_records=path_records,
                classification_state=_classification_from_dict(
                    item.get("classification_state")
                ),
                evidence_basis=evidence_basis,
                placement_proposals=placement_proposals,
                reclassification_proposals=reclassification_proposals,
                created_at_utc=_clean(item.get("created_at_utc", "")),
                updated_at_utc=_clean(item.get("updated_at_utc", "")),
            )
        )
    return EvidenceIndexManifest(
        manifest_id=_clean(data.get("manifest_id", "")),
        schema_version=_clean(
            data.get("schema_version", EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION)
        ),
        database_roots=roots,
        taxonomy_versions=taxonomy_versions,
        records=tuple(records),
        created_at_utc=_clean(data.get("created_at_utc", "")),
        updated_at_utc=_clean(data.get("updated_at_utc", "")),
        payload_sha256=_clean(data.get("payload_sha256", "")),
        scope=_clean(data.get("scope", EVIDENCE_DATABASE_INDEX_SCOPE)),
    )


def validate_evidence_index_manifest(manifest: EvidenceIndexManifest) -> tuple[str, ...]:
    errors: list[str] = []
    if manifest.schema_version != EVIDENCE_DATABASE_INDEX_SCHEMA_VERSION:
        errors.append("unsupported_schema_version")
    if not manifest.manifest_id:
        errors.append("missing_manifest_id")
    if manifest.payload_sha256:
        expected = evidence_index_payload_sha256(manifest)
        if manifest.payload_sha256 != expected:
            errors.append("payload_sha256_mismatch")
    seen_item_ids: set[str] = set()
    for record in manifest.records:
        if not record.identity.item_id:
            errors.append("record_missing_item_id")
            continue
        if record.identity.item_id in seen_item_ids:
            errors.append(f"duplicate_item_id:{record.identity.item_id}")
        seen_item_ids.add(record.identity.item_id)
        for path in record.path_records:
            if path.file_operation_performed:
                errors.append(f"file_operation_flag_set:{record.identity.item_id}")
    return tuple(errors)


def read_evidence_index_file(index_path: str) -> EvidenceIndexStoreResult:
    path = Path(index_path)
    if not path.is_file():
        return EvidenceIndexStoreResult(
            status=INDEX_STORE_STATUS_MISSING,
            index_path=str(path),
            errors=("index_file_missing",),
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("index root must be an object")
        manifest = evidence_index_manifest_from_dict(data)
        errors = validate_evidence_index_manifest(manifest)
        if errors:
            return EvidenceIndexStoreResult(
                status=INDEX_STORE_STATUS_INVALID,
                index_path=str(path),
                manifest=manifest,
                payload_sha256=manifest.payload_sha256,
                errors=errors,
            )
        return EvidenceIndexStoreResult(
            status=INDEX_STORE_STATUS_OK,
            index_path=str(path),
            manifest=manifest,
            payload_sha256=manifest.payload_sha256,
        )
    except Exception as exc:
        return EvidenceIndexStoreResult(
            status=INDEX_STORE_STATUS_INVALID,
            index_path=str(path),
            errors=(f"index_read_failed:{exc.__class__.__name__}",),
        )


def write_evidence_index_file_atomic(
    manifest: EvidenceIndexManifest,
    index_path: str,
    *,
    replace_func: Any = os.replace,
) -> EvidenceIndexStoreResult:
    path = Path(index_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    hashed = evidence_index_manifest_with_hash(manifest)
    errors = validate_evidence_index_manifest(hashed)
    if errors:
        return EvidenceIndexStoreResult(
            status=INDEX_STORE_STATUS_INVALID,
            index_path=str(path),
            manifest=hashed,
            payload_sha256=hashed.payload_sha256,
            errors=errors,
        )
    tmp_path = path.with_name(f".{path.name}.tmp")
    try:
        tmp_path.write_text(
            json.dumps(hashed.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        replace_func(str(tmp_path), str(path))
        return EvidenceIndexStoreResult(
            status=INDEX_STORE_STATUS_OK,
            index_path=str(path),
            manifest=hashed,
            payload_sha256=hashed.payload_sha256,
        )
    except Exception as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        return EvidenceIndexStoreResult(
            status=INDEX_STORE_STATUS_WRITE_FAILED,
            index_path=str(path),
            manifest=hashed,
            payload_sha256=hashed.payload_sha256,
            errors=(f"index_write_failed:{exc.__class__.__name__}",),
        )


def append_or_update_evidence_index_record(
    manifest: EvidenceIndexManifest,
    record: EvidenceIndexRecord,
) -> EvidenceIndexManifest:
    records: list[EvidenceIndexRecord] = []
    replaced = False
    for existing in manifest.records:
        if existing.identity.item_id == record.identity.item_id:
            records.append(record)
            replaced = True
        else:
            records.append(existing)
    if not replaced:
        records.append(record)
    return EvidenceIndexManifest(
        manifest_id=manifest.manifest_id,
        schema_version=manifest.schema_version,
        database_roots=manifest.database_roots,
        taxonomy_versions=manifest.taxonomy_versions,
        records=tuple(records),
        created_at_utc=manifest.created_at_utc,
        updated_at_utc=utc_now_iso(),
        scope=manifest.scope,
    )
