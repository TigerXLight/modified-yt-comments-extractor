"""Canonical source-role policy for Profile/Media Database mode.

V76E settles one pending taxonomy problem before folder-import planning becomes
user-facing: older demo batches used SECONDARY_WITNESS_SOURCE, while the
project's intended role name is SECONDARY_WITNESS_ACCOUNT.  This module keeps
backward compatibility by accepting legacy aliases, but normalizes displayed and
indexed values to the canonical role list.

It never scans folders, creates folders, moves folders, renames folders, copies
media, downloads media, classifies automatically, or infers sensitive
identifiers.  It only normalizes explicit text values already supplied by a
caller, batch JSON file, or dry-run planner.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from profile_media_database import utc_now_iso

PROFILE_MEDIA_SOURCE_ROLE_POLICY_SCHEMA_VERSION = "profile-media-source-role-policy-v76e"

CANONICAL_SOURCE_ROLE_VALUES: tuple[str, ...] = (
    "PRIMARY_SELF_AUTHORED_SCOPE",
    "SECONDARY_WITNESS_ACCOUNT",
    "TERTIARY_PROPAGATED_SOURCE",
    "UNKNOWN_SOURCE_ROLE",
)

SOURCE_ROLE_ALIASES: dict[str, str] = {
    "PRIMARY": "PRIMARY_SELF_AUTHORED_SCOPE",
    "PRIMARY_SOURCE": "PRIMARY_SELF_AUTHORED_SCOPE",
    "PRIMARY_SELF_AUTHORED": "PRIMARY_SELF_AUTHORED_SCOPE",
    "SELF_AUTHORED_SCOPE": "PRIMARY_SELF_AUTHORED_SCOPE",
    "SECONDARY": "SECONDARY_WITNESS_ACCOUNT",
    "SECONDARY_WITNESS": "SECONDARY_WITNESS_ACCOUNT",
    "SECONDARY_WITNESS_SOURCE": "SECONDARY_WITNESS_ACCOUNT",
    "WITNESS_SOURCE": "SECONDARY_WITNESS_ACCOUNT",
    "WITNESS_ACCOUNT": "SECONDARY_WITNESS_ACCOUNT",
    "TERTIARY": "TERTIARY_PROPAGATED_SOURCE",
    "TERTIARY_PROPAGATED": "TERTIARY_PROPAGATED_SOURCE",
    "PROPAGATED_SOURCE": "TERTIARY_PROPAGATED_SOURCE",
    "UNKNOWN": "UNKNOWN_SOURCE_ROLE",
    "UNKNOWN_SOURCE": "UNKNOWN_SOURCE_ROLE",
    "": "UNKNOWN_SOURCE_ROLE",
}


@dataclass(frozen=True)
class SourceRolePolicyDecision:
    """Normalization decision for one explicit source-role value."""

    original_value: str
    normalized_value: str
    canonical: bool
    alias_used: bool = False
    warning: str = ""
    schema_version: str = PROFILE_MEDIA_SOURCE_ROLE_POLICY_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceRolePolicyReport:
    """Batch report for explicit source-role values."""

    decisions: tuple[SourceRolePolicyDecision, ...]
    schema_version: str = PROFILE_MEDIA_SOURCE_ROLE_POLICY_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        warnings = tuple(decision.warning for decision in self.decisions if decision.warning)
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "decisions": [decision.to_dict() for decision in self.decisions],
            "decision_count": len(self.decisions),
            "alias_count": sum(1 for decision in self.decisions if decision.alias_used),
            "unknown_count": sum(1 for decision in self.decisions if decision.normalized_value == "UNKNOWN_SOURCE_ROLE"),
            "warnings": list(warnings),
            "warning_count": len(warnings),
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }


def _key(value: object) -> str:
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def normalize_source_role_value(value: object) -> SourceRolePolicyDecision:
    """Normalize one explicit source-role value to the canonical V76E taxonomy."""

    original = str(value or "").strip()
    key = _key(original)
    if key in CANONICAL_SOURCE_ROLE_VALUES:
        return SourceRolePolicyDecision(original_value=original, normalized_value=key, canonical=True)
    if key in SOURCE_ROLE_ALIASES:
        normalized = SOURCE_ROLE_ALIASES[key]
        warning = "" if normalized == "UNKNOWN_SOURCE_ROLE" and not original else f"source_role_alias_normalized:{original}->{normalized}"
        return SourceRolePolicyDecision(original_value=original, normalized_value=normalized, canonical=True, alias_used=bool(warning), warning=warning)
    return SourceRolePolicyDecision(
        original_value=original,
        normalized_value="UNKNOWN_SOURCE_ROLE",
        canonical=False,
        warning=f"source_role_unknown:{original or '(blank)'}",
    )


def canonical_source_role(value: object) -> str:
    """Return only the normalized canonical string for callers that need a scalar."""

    return normalize_source_role_value(value).normalized_value


def build_source_role_policy_report(values: Iterable[object]) -> SourceRolePolicyReport:
    return SourceRolePolicyReport(decisions=tuple(normalize_source_role_value(value) for value in values))
