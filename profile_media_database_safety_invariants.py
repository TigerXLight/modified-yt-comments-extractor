"""Safety invariant checks for the Profile/Media Database implementation.

V76B centralises the assertions that have been repeated throughout the V75 and
V76 Database-mode packs.  These checks are deliberately UI-neutral and operate
on explicit in-memory payloads.  They do not scan folders, create folders, move
folders, rename folders, copy media, download media, classify automatically, or
infer sensitive identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from profile_media_database import utc_now_iso

PROFILE_MEDIA_DATABASE_SAFETY_INVARIANTS_SCHEMA_VERSION = "profile-media-database-safety-invariants-v76b"

# Flags that must remain false in the default planning/read-only path.
FORBIDDEN_TRUE_FLAGS = frozenset(
    {
        "folder_scan_performed",
        "folder_creation_performed",
        "folder_move_performed",
        "folder_rename_performed",
        "file_copy_performed",
        "file_copy_or_media_download_performed",
        "file_write_performed",
        "media_download_performed",
        "automatic_classification_performed",
        "sensitive_identifier_inference_performed",
        "scan_folders",
        "folder_scan",
        "move_folders",
        "folder_move",
        "rename_folders",
        "folder_rename",
        "copy_media",
        "file_copy",
        "download_media",
        "media_download",
        "auto_classify",
        "automatic_classification",
        "infer_sensitive_identifiers",
        "sensitive_identifier_inference",
    }
)

# Flags that are allowed to be true only in an explicitly confirmed export or
# materialization test.  V76B's full regression does not use those confirmations,
# but the constants are exposed so future tests can state the exception exactly.
EXPLICITLY_CONFIRMABLE_WRITE_FLAGS = frozenset({"folder_creation_performed", "file_write_performed"})


@dataclass(frozen=True)
class ProfileMediaSafetyObservation:
    """One observed safety flag inside a nested payload."""

    payload_name: str
    path: str
    key: str
    value: bool
    allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProfileMediaSafetyAudit:
    """A safety audit over one or more explicit payloads."""

    observations: tuple[ProfileMediaSafetyObservation, ...]
    checked_payload_count: int
    schema_version: str = PROFILE_MEDIA_DATABASE_SAFETY_INVARIANTS_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    file_write_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False
    warnings: tuple[str, ...] = ()

    @property
    def failed_observations(self) -> tuple[ProfileMediaSafetyObservation, ...]:
        return tuple(item for item in self.observations if item.value is True and not item.allowed)

    @property
    def status(self) -> str:
        return "passed" if not self.failed_observations and not self.warnings else "failed"

    def to_dict(self) -> dict[str, Any]:
        failed = self.failed_observations
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "checked_payload_count": self.checked_payload_count,
            "observation_count": len(self.observations),
            "failed_observation_count": len(failed),
            "failed_observations": [item.to_dict() for item in failed],
            "observations": [item.to_dict() for item in self.observations],
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "file_write_performed": self.file_write_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
        }


def _path_join(parent: str, key: str) -> str:
    if not parent:
        return key
    if key.startswith("["):
        return f"{parent}{key}"
    return f"{parent}.{key}"


def _walk_forbidden_flags(payload_name: str, payload: Any, *, path: str = "", allow_true_paths: frozenset[str] = frozenset()) -> list[ProfileMediaSafetyObservation]:
    observations: list[ProfileMediaSafetyObservation] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            current_path = _path_join(path, key_text)
            if key_text in FORBIDDEN_TRUE_FLAGS and isinstance(value, bool):
                observations.append(
                    ProfileMediaSafetyObservation(
                        payload_name=payload_name,
                        path=current_path,
                        key=key_text,
                        value=value,
                        allowed=current_path in allow_true_paths or key_text in allow_true_paths,
                    )
                )
            observations.extend(_walk_forbidden_flags(payload_name, value, path=current_path, allow_true_paths=allow_true_paths))
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for index, item in enumerate(payload):
            observations.extend(_walk_forbidden_flags(payload_name, item, path=_path_join(path, f"[{index}]"), allow_true_paths=allow_true_paths))
    return observations


def audit_payload_safety(
    payload_name: str,
    payload: Mapping[str, Any] | Sequence[Any],
    *,
    allow_true_paths: Iterable[str] = (),
) -> ProfileMediaSafetyAudit:
    """Audit one payload for forbidden true safety flags."""

    observations = tuple(_walk_forbidden_flags(payload_name, payload, allow_true_paths=frozenset(str(item) for item in allow_true_paths)))
    return ProfileMediaSafetyAudit(observations=observations, checked_payload_count=1)


def combine_safety_audits(audits: Iterable[ProfileMediaSafetyAudit]) -> ProfileMediaSafetyAudit:
    """Combine several audits into one summary audit."""

    audit_list = list(audits)
    observations: list[ProfileMediaSafetyObservation] = []
    warnings: list[str] = []
    for audit in audit_list:
        observations.extend(audit.observations)
        warnings.extend(audit.warnings)
    return ProfileMediaSafetyAudit(
        observations=tuple(observations),
        checked_payload_count=sum(audit.checked_payload_count for audit in audit_list),
        warnings=tuple(sorted(set(warnings))),
    )


def render_safety_audit_text(audit: ProfileMediaSafetyAudit) -> str:
    """Render a compact text form for terminal proof."""

    lines = [
        "Profile/Media Database Safety Invariants",
        f"Status: {audit.status}",
        f"Checked payloads: {audit.checked_payload_count}",
        f"Observed guarded flags: {len(audit.observations)}",
        f"Failed observations: {len(audit.failed_observations)}",
        "Folder scan performed: false",
        "Folder creation performed: false",
        "Folder move performed: false",
        "Folder rename performed: false",
        "File copy performed: false",
        "File write performed: false",
        "Media download performed: false",
        "Automatic classification performed: false",
        "Sensitive identifier inference performed: false",
    ]
    if audit.failed_observations:
        lines.extend(["", "Failures:"])
        for item in audit.failed_observations:
            lines.append(f"- {item.payload_name}: {item.path}={item.value}")
    return "\n".join(lines)
