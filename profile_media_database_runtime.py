"""Runtime state helpers for Profile/Media Database mode.

V75P keeps the left-sidebar Database toggle as a mode switch only.  This
module persists that mode and exposes explicit safety flags for callers that
need to prove no folder scan/move/rename/classification side effect happened.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from profile_media_database_view_model import ProfileMediaViewMode, coerce_profile_media_view_mode

PROFILE_MEDIA_RUNTIME_SCHEMA_VERSION = "profile_media_database_runtime.v75p"


@dataclass(frozen=True)
class ProfileMediaRuntimeState:
    """Persisted mode-only Profile/Media Database runtime state."""

    sidebar_mode: str = ProfileMediaViewMode.FILES.value
    schema_version: str = PROFILE_MEDIA_RUNTIME_SCHEMA_VERSION
    updated_epoch: int = 0
    folder_scan_performed: bool = False
    folder_move_performed: bool = False
    folder_rename_performed: bool = False
    folder_creation_performed: bool = False
    file_copy_performed: bool = False
    automatic_classification_performed: bool = False
    sensitive_identifier_inference_performed: bool = False

    def normalized(self) -> "ProfileMediaRuntimeState":
        """Return a sanitized state with a valid FILES/DATABASE mode."""
        try:
            sidebar_mode = coerce_profile_media_view_mode(self.sidebar_mode).value
        except Exception:
            sidebar_mode = ProfileMediaViewMode.FILES.value
        return ProfileMediaRuntimeState(
            sidebar_mode=sidebar_mode,
            schema_version=PROFILE_MEDIA_RUNTIME_SCHEMA_VERSION,
            updated_epoch=int(self.updated_epoch or 0),
            folder_scan_performed=bool(self.folder_scan_performed),
            folder_move_performed=bool(self.folder_move_performed),
            folder_rename_performed=bool(self.folder_rename_performed),
            folder_creation_performed=bool(self.folder_creation_performed),
            file_copy_performed=bool(self.file_copy_performed),
            automatic_classification_performed=bool(self.automatic_classification_performed),
            sensitive_identifier_inference_performed=bool(self.sensitive_identifier_inference_performed),
        )

    @property
    def filesystem_work_performed(self) -> bool:
        """True if this state records any real filesystem work."""
        return any(
            (
                self.folder_scan_performed,
                self.folder_move_performed,
                self.folder_rename_performed,
                self.folder_creation_performed,
                self.file_copy_performed,
            )
        )

    @property
    def safety_claims(self) -> dict[str, bool]:
        """Return explicit negative side-effect flags for logs/tests."""
        return {
            "folder_scan_performed": self.folder_scan_performed,
            "folder_move_performed": self.folder_move_performed,
            "folder_rename_performed": self.folder_rename_performed,
            "folder_creation_performed": self.folder_creation_performed,
            "file_copy_performed": self.file_copy_performed,
            "automatic_classification_performed": self.automatic_classification_performed,
            "sensitive_identifier_inference_performed": self.sensitive_identifier_inference_performed,
        }


def default_profile_media_runtime_state_path(*, appdata_root: str | os.PathLike[str] | None = None) -> Path:
    """Return the local user runtime state path without creating folders."""
    base = Path(appdata_root) if appdata_root is not None else Path(
        os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home()
    )
    return base / "YTCE" / "profile_media_database_runtime_state.json"


def runtime_state_from_payload(payload: dict[str, Any] | None) -> ProfileMediaRuntimeState:
    """Create a sanitized runtime state from untrusted JSON data."""
    if not isinstance(payload, dict):
        return ProfileMediaRuntimeState(updated_epoch=0)
    return ProfileMediaRuntimeState(
        sidebar_mode=payload.get("sidebar_mode", ProfileMediaViewMode.FILES.value),
        schema_version=PROFILE_MEDIA_RUNTIME_SCHEMA_VERSION,
        updated_epoch=int(payload.get("updated_epoch") or 0),
        folder_scan_performed=bool(payload.get("folder_scan_performed", False)),
        folder_move_performed=bool(payload.get("folder_move_performed", False)),
        folder_rename_performed=bool(payload.get("folder_rename_performed", False)),
        folder_creation_performed=bool(payload.get("folder_creation_performed", False)),
        file_copy_performed=bool(payload.get("file_copy_performed", False)),
        automatic_classification_performed=bool(payload.get("automatic_classification_performed", False)),
        sensitive_identifier_inference_performed=bool(payload.get("sensitive_identifier_inference_performed", False)),
    ).normalized()


def load_profile_media_runtime_state(path: str | os.PathLike[str] | None = None) -> ProfileMediaRuntimeState:
    """Load runtime state, returning safe FILES mode if missing/corrupt."""
    state_path = Path(path) if path is not None else default_profile_media_runtime_state_path()
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ProfileMediaRuntimeState(updated_epoch=0)
    except Exception:
        return ProfileMediaRuntimeState(updated_epoch=0)
    return runtime_state_from_payload(payload)


def save_profile_media_runtime_state(
    state: ProfileMediaRuntimeState,
    path: str | os.PathLike[str] | None = None,
) -> ProfileMediaRuntimeState:
    """Persist runtime mode with atomic replace semantics."""
    state_path = Path(path) if path is not None else default_profile_media_runtime_state_path()
    normalized = state.normalized()
    if normalized.updated_epoch <= 0:
        normalized = ProfileMediaRuntimeState(
            sidebar_mode=normalized.sidebar_mode,
            updated_epoch=int(time.time()),
            folder_scan_performed=normalized.folder_scan_performed,
            folder_move_performed=normalized.folder_move_performed,
            folder_rename_performed=normalized.folder_rename_performed,
            folder_creation_performed=normalized.folder_creation_performed,
            file_copy_performed=normalized.file_copy_performed,
            automatic_classification_performed=normalized.automatic_classification_performed,
            sensitive_identifier_inference_performed=normalized.sensitive_identifier_inference_performed,
        )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(asdict(normalized), indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    tmp_path.replace(state_path)
    return normalized


def build_profile_media_runtime_state(sidebar_mode: object) -> ProfileMediaRuntimeState:
    """Build a side-effect-free runtime state for a FILES/DATABASE mode value."""
    return ProfileMediaRuntimeState(
        sidebar_mode=coerce_profile_media_view_mode(sidebar_mode).value,
        updated_epoch=int(time.time()),
    )
