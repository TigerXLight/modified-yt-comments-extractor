"""Persistent GUI state store for Profile/Media Database mode.

V76D stores only explicit GUI configuration: selected batch JSON files,
database root text, and active Database-mode query values.  It is not a case
folder materializer.  It never scans database folders, creates case folders,
moves/renames folders, copies media, downloads media, classifies rows, or infers
sensitive identifiers.

Write operations are guarded by an explicit confirmation phrase so tests and
CLI runs stay dry-run by default.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from profile_media_database import utc_now_iso
from profile_media_database_session import ProfileMediaDatabaseSessionConfig

PROFILE_MEDIA_DATABASE_GUI_STATE_SCHEMA_VERSION = "profile-media-database-gui-state-v76d"
PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION = "SAVE_PROFILE_MEDIA_GUI_STATE"
PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION = "CLEAR_PROFILE_MEDIA_GUI_STATE"

_QUERY_KEYS = (
    "profile_name",
    "case_title",
    "source_bucket",
    "source_role",
    "claim_basis",
    "currentness_status",
    "text",
    "source_chain_gap",
    "disputed_framing",
    "has_parser_warnings",
    "limit",
)


@dataclass(frozen=True)
class ProfileMediaDatabaseGuiStateConfig:
    """Explicit Database workbench configuration persisted for the GUI."""

    database_root: str = ""
    batch_json_files: tuple[str, ...] = ()
    mode: str = "DATABASE"
    profile_name: str = ""
    case_title: str = ""
    source_bucket: str = ""
    source_role: str = ""
    claim_basis: str = ""
    currentness_status: str = ""
    text: str = ""
    source_chain_gap: bool | None = None
    disputed_framing: bool | None = None
    has_parser_warnings: bool | None = None
    limit: int = 0
    last_import_status: str = ""
    schema_version: str = PROFILE_MEDIA_DATABASE_GUI_STATE_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    updated_at_utc: str = field(default_factory=utc_now_iso)
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_session_config(self) -> ProfileMediaDatabaseSessionConfig:
        return ProfileMediaDatabaseSessionConfig(
            database_root=self.database_root,
            batch_json_files=self.batch_json_files,
            mode=self.mode,
            profile_name=self.profile_name,
            case_title=self.case_title,
            source_bucket=self.source_bucket,
            source_role=self.source_role,
            claim_basis=self.claim_basis,
            currentness_status=self.currentness_status,
            text=self.text,
            source_chain_gap=self.source_chain_gap,
            disputed_framing=self.disputed_framing,
            has_parser_warnings=self.has_parser_warnings,
            limit=self.limit,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["batch_json_files"] = list(self.batch_json_files)
        return payload


@dataclass(frozen=True)
class ProfileMediaDatabaseGuiStateIoResult:
    """Result from loading, saving, or clearing GUI state."""

    status: str
    path: str
    config: ProfileMediaDatabaseGuiStateConfig | None = None
    warnings: tuple[str, ...] = ()
    schema_version: str = PROFILE_MEDIA_DATABASE_GUI_STATE_SCHEMA_VERSION
    created_at_utc: str = field(default_factory=utc_now_iso)
    file_write_performed: bool = False
    config_file_write_performed: bool = False
    config_file_delete_performed: bool = False
    folder_scan_performed: bool = False
    folder_creation_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    file_copy_performed: bool = False
    media_download_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at_utc": self.created_at_utc,
            "status": self.status,
            "path": self.path,
            "config": self.config.to_dict() if self.config else None,
            "warnings": list(self.warnings),
            "warning_count": len(self.warnings),
            "file_write_performed": self.file_write_performed,
            "config_file_write_performed": self.config_file_write_performed,
            "config_file_delete_performed": self.config_file_delete_performed,
            "folder_scan_performed": self.folder_scan_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "file_copy_performed": self.file_copy_performed,
            "media_download_performed": self.media_download_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }


def _normalise_paths(batch_json_files: Iterable[object] | None) -> tuple[str, ...]:
    if not batch_json_files:
        return ()
    output: list[str] = []
    seen: set[str] = set()
    for value in batch_json_files:
        text = str(value or "").strip()
        if not text:
            continue
        key = str(Path(text))
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
    return tuple(output)


def _coerce_optional_bool(value: object) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return None


def default_profile_media_database_gui_state_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "YTCE" / "profile_media_database_gui_state_v76d.json"


def build_gui_state_config(
    *,
    database_root: object = "",
    batch_json_files: Iterable[object] | None = None,
    mode: object = "DATABASE",
    profile_name: object = "",
    case_title: object = "",
    source_bucket: object = "",
    source_role: object = "",
    claim_basis: object = "",
    currentness_status: object = "",
    text: object = "",
    source_chain_gap: object = None,
    disputed_framing: object = None,
    has_parser_warnings: object = None,
    limit: object = 0,
    last_import_status: object = "",
) -> ProfileMediaDatabaseGuiStateConfig:
    try:
        numeric_limit = max(0, int(limit or 0))
    except Exception:
        numeric_limit = 0
    return ProfileMediaDatabaseGuiStateConfig(
        database_root=str(database_root or ""),
        batch_json_files=_normalise_paths(batch_json_files),
        mode="DATABASE" if str(mode or "DATABASE").upper() == "DATABASE" else "FILES",
        profile_name=str(profile_name or ""),
        case_title=str(case_title or ""),
        source_bucket=str(source_bucket or ""),
        source_role=str(source_role or ""),
        claim_basis=str(claim_basis or ""),
        currentness_status=str(currentness_status or ""),
        text=str(text or ""),
        source_chain_gap=_coerce_optional_bool(source_chain_gap),
        disputed_framing=_coerce_optional_bool(disputed_framing),
        has_parser_warnings=_coerce_optional_bool(has_parser_warnings),
        limit=numeric_limit,
        last_import_status=str(last_import_status or ""),
    )


def gui_state_payload(config: ProfileMediaDatabaseGuiStateConfig) -> dict[str, Any]:
    return config.to_dict()


def _config_from_mapping(payload: Mapping[str, Any]) -> ProfileMediaDatabaseGuiStateConfig:
    return build_gui_state_config(
        database_root=payload.get("database_root", ""),
        batch_json_files=payload.get("batch_json_files", ()),
        mode=payload.get("mode", "DATABASE"),
        profile_name=payload.get("profile_name", ""),
        case_title=payload.get("case_title", ""),
        source_bucket=payload.get("source_bucket", ""),
        source_role=payload.get("source_role", ""),
        claim_basis=payload.get("claim_basis", ""),
        currentness_status=payload.get("currentness_status", ""),
        text=payload.get("text", ""),
        source_chain_gap=payload.get("source_chain_gap", None),
        disputed_framing=payload.get("disputed_framing", None),
        has_parser_warnings=payload.get("has_parser_warnings", None),
        limit=payload.get("limit", 0),
        last_import_status=payload.get("last_import_status", ""),
    )


def load_gui_state_config(path: object | None = None) -> ProfileMediaDatabaseGuiStateIoResult:
    """Load one exact GUI state file without scanning surrounding folders."""

    state_path = Path(path) if path else default_profile_media_database_gui_state_path()
    if not state_path.exists():
        return ProfileMediaDatabaseGuiStateIoResult(status="missing_state_file", path=str(state_path))
    if not state_path.is_file():
        return ProfileMediaDatabaseGuiStateIoResult(status="state_path_not_file", path=str(state_path), warnings=("state_path_not_file",))
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ProfileMediaDatabaseGuiStateIoResult(status="state_json_parse_error", path=str(state_path), warnings=(f"json_parse_error:{exc.__class__.__name__}",))
    if not isinstance(raw, Mapping):
        return ProfileMediaDatabaseGuiStateIoResult(status="state_json_root_not_object", path=str(state_path), warnings=("json_root_not_object",))
    config = _config_from_mapping(raw)
    warnings: list[str] = []
    if raw.get("schema_version") not in {PROFILE_MEDIA_DATABASE_GUI_STATE_SCHEMA_VERSION, None, ""}:
        warnings.append("state_schema_version_mismatch")
    return ProfileMediaDatabaseGuiStateIoResult(status="success", path=str(state_path), config=config, warnings=tuple(warnings))


def save_gui_state_config(
    config: ProfileMediaDatabaseGuiStateConfig,
    path: object | None = None,
    *,
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaDatabaseGuiStateIoResult:
    """Save explicit GUI state only when confirmation is supplied."""

    state_path = Path(path) if path else default_profile_media_database_gui_state_path()
    if not execute:
        return ProfileMediaDatabaseGuiStateIoResult(status="planned_dry_run_no_state_written", path=str(state_path), config=config)
    if confirmation_phrase != PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION:
        return ProfileMediaDatabaseGuiStateIoResult(status="blocked_missing_save_confirmation", path=str(state_path), config=config, warnings=("missing_save_confirmation",))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.to_dict()
    payload["updated_at_utc"] = utc_now_iso()
    state_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return ProfileMediaDatabaseGuiStateIoResult(
        status="state_saved",
        path=str(state_path),
        config=config,
        file_write_performed=True,
        config_file_write_performed=True,
    )


def clear_gui_state_config(
    path: object | None = None,
    *,
    execute: bool = False,
    confirmation_phrase: str = "",
) -> ProfileMediaDatabaseGuiStateIoResult:
    """Clear the GUI state file only when confirmation is supplied."""

    state_path = Path(path) if path else default_profile_media_database_gui_state_path()
    if not execute:
        return ProfileMediaDatabaseGuiStateIoResult(status="planned_dry_run_no_state_cleared", path=str(state_path))
    if confirmation_phrase != PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION:
        return ProfileMediaDatabaseGuiStateIoResult(status="blocked_missing_clear_confirmation", path=str(state_path), warnings=("missing_clear_confirmation",))
    if state_path.exists() and state_path.is_file():
        state_path.unlink()
        return ProfileMediaDatabaseGuiStateIoResult(status="state_cleared", path=str(state_path), config_file_delete_performed=True)
    return ProfileMediaDatabaseGuiStateIoResult(status="state_already_missing", path=str(state_path))


def render_gui_state_text(config: ProfileMediaDatabaseGuiStateConfig) -> str:
    lines = [
        "Profile/Media Database GUI State",
        f"Mode: {config.mode}",
        f"Database root: {config.database_root or '(not configured)'}",
        f"Batch JSON files: {len(config.batch_json_files)}",
        f"Last import status: {config.last_import_status or '(none)'}",
    ]
    active = []
    for key in _QUERY_KEYS:
        value = getattr(config, key)
        if value not in (None, "", 0):
            active.append(f"- {key}: {value}")
    if active:
        lines.append("")
        lines.append("Active query:")
        lines.extend(active)
    lines.append("")
    lines.append("Safety:")
    lines.append(f"- Folder scan performed: {config.folder_scan_performed}")
    lines.append(f"- Folder creation performed: {config.folder_creation_performed}")
    lines.append(f"- Folder move performed: {config.folder_move_performed}")
    lines.append(f"- Folder rename performed: {config.folder_rename_performed}")
    lines.append(f"- File copy performed: {config.file_copy_performed}")
    lines.append(f"- Media download performed: {config.media_download_performed}")
    lines.append(f"- Automatic classification performed: {config.automatic_classification_performed}")
    lines.append(f"- Sensitive identifier inference performed: {config.sensitive_identifier_inference_performed}")
    return "\n".join(lines)
