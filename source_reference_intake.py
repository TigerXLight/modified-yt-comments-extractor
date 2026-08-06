from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping


REFERENCE_INTAKE_SCHEMA_VERSION = "source_reference_intake_v1"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ReferencePackKind(_StringEnum):
    REV4_PREPARATION_PACK = "REV4_PREPARATION_PACK"
    BROWSER_EXTENSION_REFERENCE = "BROWSER_EXTENSION_REFERENCE"


class ReferenceUseBoundary(_StringEnum):
    ARCHITECTURE_REFERENCE_ONLY = "ARCHITECTURE_REFERENCE_ONLY"
    LOCAL_FIXTURE_GUIDANCE = "LOCAL_FIXTURE_GUIDANCE"
    LICENCE_SECURITY_REVIEW_REQUIRED = "LICENCE_SECURITY_REVIEW_REQUIRED"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            key: _value_for_dict(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _value_for_dict(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    return value


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


@dataclass(frozen=True)
class ReferencePackIntakeRecord:
    pack_id: str
    display_name: str
    supplied_name: str
    sha256: str
    kind: ReferencePackKind
    apparent_identity: str
    entry_count: int
    inspected_surfaces: tuple[str, ...] = ()
    architecture_patterns: tuple[str, ...] = ()
    allowed_use: tuple[ReferenceUseBoundary, ...] = (
        ReferenceUseBoundary.ARCHITECTURE_REFERENCE_ONLY,
    )
    prohibited_use: tuple[str, ...] = (
        "copy_proprietary_or_minified_code",
        "port_extension_internals",
        "bundle_extension_assets",
        "execute_extension_code",
        "browse_live_services",
        "use_credentials_cookies_or_profiles",
    )
    licensing_boundary: str = "reference_only_no_code_reuse_without_separate_review"
    security_notes: tuple[str, ...] = ()
    reference_only: bool = True
    code_copying_allowed: bool = False
    runtime_execution_allowed: bool = False
    live_network_allowed: bool = False
    credential_or_profile_use_allowed: bool = False
    raw_source_included: bool = False
    full_local_path_included: bool = False
    schema_version: str = REFERENCE_INTAKE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class ReferencePackIntakeSummary:
    summary_id: str
    status: str
    record_count: int
    pack_ids: tuple[str, ...]
    supplied_names: tuple[str, ...]
    sha256_values: tuple[str, ...]
    architecture_pattern_count: int
    reference_only: bool = True
    code_copying_allowed: bool = False
    runtime_execution_allowed: bool = False
    live_network_allowed: bool = False
    credential_or_profile_use_allowed: bool = False
    raw_source_included: bool = False
    full_local_path_included: bool = False
    licence_security_review_required: bool = True
    note: str = (
        "Reference intake records only; ZIP contents are used for architecture, "
        "schema, manifest, dependency, security, and licensing boundaries without "
        "copying proprietary/minified code or executing live capture behavior."
    )
    schema_version: str = REFERENCE_INTAKE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


REFERENCE_PACK_INTAKE_RECORDS: tuple[ReferencePackIntakeRecord, ...] = (
    ReferencePackIntakeRecord(
        pack_id="rev4_site_capture_preparation_pack",
        display_name="REV4 operational site-capture preparation pack",
        supplied_name="SITE_CAPTURE_PREPARATION_PACK_REV4.zip",
        sha256="bd326f07958380ceb572cdaeabb32d3cb9f9d29286642491605f6e3b5635787b",
        kind=ReferencePackKind.REV4_PREPARATION_PACK,
        apparent_identity="REV4 Source Evidence operational-capture planning pack",
        entry_count=32,
        inspected_surfaces=(
            "numbered_design_markdown",
            "json_schemas",
            "status_dependency_fixture_site_license_matrices",
        ),
        architecture_patterns=(
            "separate_article_outline_comments_livechat_media_archive_artifacts",
            "explicit_action_log_and_artifact_contracts",
            "localhost_fixture_first_test_matrix",
            "manual_live_site_smoke_approval_gate",
            "optional_dependencies_fail_gracefully",
        ),
        allowed_use=(
            ReferenceUseBoundary.ARCHITECTURE_REFERENCE_ONLY,
            ReferenceUseBoundary.LOCAL_FIXTURE_GUIDANCE,
        ),
        licensing_boundary="project_supplied_rev4_pack_governs_local_fixture_and_mock_design",
        security_notes=(
            "live_external_network_false_by_default",
            "real_site_tests_not_performed_by_automation",
            "database_phase_separated_from_capture_runtime",
        ),
    ),
    ReferencePackIntakeRecord(
        pack_id="extension_reference_1_unknown_background_bundle",
        display_name="Supplied extension ZIP 1 reference",
        supplied_name="1.zip",
        sha256="b6ae72c127dd8ba5d976e48879c973829d936d7e813e8f3d9e5d771683bfe337",
        kind=ReferencePackKind.BROWSER_EXTENSION_REFERENCE,
        apparent_identity="unknown large background-only browser-extension bundle",
        entry_count=3,
        inspected_surfaces=("zip_inventory",),
        architecture_patterns=(
            "large_background_script_surface",
            "absent_manifest_in_supplied_archive",
        ),
        allowed_use=(
            ReferenceUseBoundary.ARCHITECTURE_REFERENCE_ONLY,
            ReferenceUseBoundary.LICENCE_SECURITY_REVIEW_REQUIRED,
        ),
        security_notes=(
            "treat_as_unknown_proprietary_or_minified_reference",
            "no_runtime_reuse_without_manifest_license_security_review",
        ),
    ),
    ReferencePackIntakeRecord(
        pack_id="extension_reference_2_mv3_offscreen_managed_schema",
        display_name="Supplied extension ZIP 2 reference",
        supplied_name="2.zip",
        sha256="ae051be084b285a0881fb77f88cf851285ae320cb1af0e187bb81078790596ab",
        kind=ReferencePackKind.BROWSER_EXTENSION_REFERENCE,
        apparent_identity="Manifest V3 service-worker/offscreen-document extension",
        entry_count=172,
        inspected_surfaces=(
            "manifest_json",
            "managed_settings_schema",
            "offscreen_document_html",
            "javascript_inventory_only",
        ),
        architecture_patterns=(
            "manifest_v3_service_worker",
            "offscreen_document_for_background_tasks",
            "managed_policy_schema",
            "web_accessible_page_embed_script",
            "domain_scoped_host_permissions",
        ),
        allowed_use=(
            ReferenceUseBoundary.ARCHITECTURE_REFERENCE_ONLY,
            ReferenceUseBoundary.LICENCE_SECURITY_REVIEW_REQUIRED,
        ),
        security_notes=(
            "offscreen_background_work_requires_explicit_optional_runtime_gate",
            "host_permissions_must_not_be_broadened_without_user_approval",
        ),
    ),
    ReferencePackIntakeRecord(
        pack_id="extension_reference_3_pdf_capture_style_surface",
        display_name="Supplied extension ZIP 3 reference",
        supplied_name="3.zip",
        sha256="dfb5aa35ad28178e913c08a060dd6d3176a168b8d09c282fa09318e9a0f6501d",
        kind=ReferencePackKind.BROWSER_EXTENSION_REFERENCE,
        apparent_identity="Manifest V3 PDF/web capture-style extension surface",
        entry_count=845,
        inspected_surfaces=(
            "manifest_json_selected_keys",
            "policy_schema",
            "service_worker_and_content_script_inventory_only",
        ),
        architecture_patterns=(
            "manifest_v3_module_service_worker",
            "content_script_routing",
            "native_messaging_permission_surface",
            "downloads_and_file_system_permission_surface",
            "viewer_and_web_accessible_resource_surface",
            "managed_policy_disable_flags",
        ),
        allowed_use=(
            ReferenceUseBoundary.ARCHITECTURE_REFERENCE_ONLY,
            ReferenceUseBoundary.LICENCE_SECURITY_REVIEW_REQUIRED,
        ),
        security_notes=(
            "broad_permissions_require_strict_approval_and_mock_first_gates",
            "native_messaging_downloads_cookies_identity_surfaces_are_not_reused",
            "no_pdf_or_browser_extension_code_is_copied_or_executed",
        ),
    ),
)


def validate_reference_pack_intake_records(
    records: tuple[ReferencePackIntakeRecord, ...],
) -> None:
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for record in records:
        if not record.pack_id:
            raise ValueError("reference pack id is required")
        if record.pack_id in seen_ids:
            raise ValueError(f"duplicate reference pack id: {record.pack_id}")
        seen_ids.add(record.pack_id)
        if len(record.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in record.sha256):
            raise ValueError(f"reference pack sha256 must be lowercase hex: {record.pack_id}")
        if record.sha256 in seen_hashes:
            raise ValueError(f"duplicate reference pack sha256: {record.pack_id}")
        seen_hashes.add(record.sha256)
        if record.full_local_path_included:
            raise ValueError(f"full local path must not be included: {record.pack_id}")
        if record.raw_source_included:
            raise ValueError(f"raw source code must not be included: {record.pack_id}")
        if record.code_copying_allowed:
            raise ValueError(f"code copying must remain disallowed: {record.pack_id}")
        if record.runtime_execution_allowed:
            raise ValueError(f"runtime execution must remain disallowed: {record.pack_id}")
        if record.live_network_allowed:
            raise ValueError(f"live network use must remain disallowed: {record.pack_id}")
        if record.credential_or_profile_use_allowed:
            raise ValueError(f"credential/profile use must remain disallowed: {record.pack_id}")


def reference_pack_intake_records() -> tuple[ReferencePackIntakeRecord, ...]:
    validate_reference_pack_intake_records(REFERENCE_PACK_INTAKE_RECORDS)
    return tuple(sorted(REFERENCE_PACK_INTAKE_RECORDS, key=lambda record: record.pack_id))


def reference_pack_intake_summary_id(
    records: tuple[ReferencePackIntakeRecord, ...],
) -> str:
    payload = {
        "pack_ids": [record.pack_id for record in records],
        "sha256_values": [record.sha256 for record in records],
        "summary_kind": "source_reference_intake",
    }
    return "source_reference_intake_" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()[:16]


def build_reference_pack_intake_summary(
    records: tuple[ReferencePackIntakeRecord, ...] | None = None,
) -> ReferencePackIntakeSummary:
    ordered = tuple(records) if records is not None else reference_pack_intake_records()
    ordered = tuple(sorted(ordered, key=lambda record: record.pack_id))
    validate_reference_pack_intake_records(ordered)
    pattern_count = sum(len(record.architecture_patterns) for record in ordered)
    return ReferencePackIntakeSummary(
        summary_id=reference_pack_intake_summary_id(ordered),
        status="REFERENCE_INTAKE_RECORDED" if ordered else "NO_REFERENCE_PACKS",
        record_count=len(ordered),
        pack_ids=tuple(record.pack_id for record in ordered),
        supplied_names=tuple(record.supplied_name for record in ordered),
        sha256_values=tuple(record.sha256 for record in ordered),
        architecture_pattern_count=pattern_count,
        licence_security_review_required=any(
            ReferenceUseBoundary.LICENCE_SECURITY_REVIEW_REQUIRED in record.allowed_use
            for record in ordered
        ),
    )


def reference_pack_intake_record_to_json(record: ReferencePackIntakeRecord) -> str:
    return json.dumps(record.to_dict(), indent=2, sort_keys=True)


def reference_pack_intake_summary_to_json(summary: ReferencePackIntakeSummary) -> str:
    return json.dumps(summary.to_dict(), indent=2, sort_keys=True)


def build_reference_pack_intake_summary_text(
    summary: ReferencePackIntakeSummary,
) -> str:
    return "\n".join(
        [
            "Source reference intake summary",
            f"Summary ID: {summary.summary_id}",
            f"Status: {summary.status}",
            f"Reference packs: {summary.record_count}",
            f"Architecture patterns recorded: {summary.architecture_pattern_count}",
            "Reference only: yes",
            "Code copying allowed: false",
            "Runtime execution allowed: false",
            "Live network allowed: false",
            "Credential/profile use allowed: false",
            "Raw source included: false",
            "Full local paths included: false",
            "Licence/security review required for extension reuse: yes",
        ]
    )
