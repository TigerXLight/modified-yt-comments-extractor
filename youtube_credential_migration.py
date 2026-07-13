from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from core.settings import (
    SettingsManager,
    YOUTUBE_CLEAR_BACKEND_ERROR,
    YOUTUBE_CLEAR_BACKEND_UNAVAILABLE,
    YOUTUBE_CLEAR_CLEARED,
    YOUTUBE_CLEAR_NOT_FOUND,
    YOUTUBE_KEYRING_ERROR,
    YOUTUBE_KEYRING_MISSING,
    YOUTUBE_KEYRING_PRESENT,
    YOUTUBE_KEYRING_UNAVAILABLE,
    YOUTUBE_SAVE_BACKEND_ERROR,
    YOUTUBE_SAVE_BACKEND_UNAVAILABLE,
    YOUTUBE_SAVE_EMPTY,
    YOUTUBE_SAVE_SAVED,
    YOUTUBE_SAVE_UPDATED,
    YOUTUBE_SAVE_VERIFICATION_FAILED,
)


YOUTUBE_CREDENTIAL_MIGRATION_SCOPE = (
    "explicit YouTube credential migration and cleanup only; no automatic "
    "migration, no plaintext fallback for new writes, no reveal/copy, no "
    "provider/API calls, and no credential values in public results"
)


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class YouTubeCredentialStorageState(_StringEnum):
    MISSING = "missing"
    SECURE_KEYRING_ONLY = "secure_keyring_only"
    LEGACY_PLAINTEXT_ONLY = "legacy_plaintext_only"
    BOTH_SECURE_AND_LEGACY = "both_secure_and_legacy"
    SECURE_BACKEND_UNAVAILABLE = "secure_backend_unavailable"
    STATUS_ERROR = "status_error"


class YouTubeCredentialAction(_StringEnum):
    STATUS = "status"
    SAVE = "save"
    MIGRATE = "migrate"
    CLEAR = "clear"


class YouTubeCredentialActionStatus(_StringEnum):
    PRESENT = "present"
    SAVED = "saved"
    UPDATED = "updated"
    MIGRATED = "migrated"
    CLEARED = "cleared"
    NOT_FOUND = "not_found"
    PARTIAL_FAILURE = "partial_failure"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    BACKEND_ERROR = "backend_error"
    LEGACY_CLEANUP_FAILED = "legacy_cleanup_failed"
    EMPTY_CREDENTIAL_REJECTED = "empty_credential_rejected"
    PRESENCE_VERIFICATION_FAILED = "presence_verification_failed"


@dataclass(frozen=True)
class YouTubeCredentialStorageStatus:
    state: YouTubeCredentialStorageState
    secure_present: bool = False
    legacy_present: bool = False
    safe_diagnostic: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


@dataclass(frozen=True)
class YouTubeCredentialActionResult:
    action: YouTubeCredentialAction
    status: YouTubeCredentialActionStatus
    storage_status: YouTubeCredentialStorageStatus
    changed_secure: bool = False
    changed_legacy: bool = False
    safe_diagnostic: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action"] = self.action.value
        data["status"] = self.status.value
        data["storage_status"] = self.storage_status.to_dict()
        return data


class YouTubeCredentialMigrationService:
    def __init__(self, settings_manager: SettingsManager) -> None:
        self._settings_manager = settings_manager

    def storage_status(self) -> YouTubeCredentialStorageStatus:
        if not self._settings_manager.legacy_settings_readable():
            return YouTubeCredentialStorageStatus(
                state=YouTubeCredentialStorageState.STATUS_ERROR,
                safe_diagnostic="legacy_settings_unreadable",
            )

        secure_status = self._settings_manager.secure_api_key_presence_status()
        legacy_present = self._settings_manager.legacy_api_key_present()

        if secure_status == YOUTUBE_KEYRING_PRESENT and legacy_present:
            return YouTubeCredentialStorageStatus(
                state=YouTubeCredentialStorageState.BOTH_SECURE_AND_LEGACY,
                secure_present=True,
                legacy_present=True,
                safe_diagnostic="secure_and_legacy_copies_present",
            )
        if secure_status == YOUTUBE_KEYRING_PRESENT:
            return YouTubeCredentialStorageStatus(
                state=YouTubeCredentialStorageState.SECURE_KEYRING_ONLY,
                secure_present=True,
                safe_diagnostic="secure_keyring_copy_present",
            )
        if secure_status == YOUTUBE_KEYRING_MISSING and legacy_present:
            return YouTubeCredentialStorageStatus(
                state=YouTubeCredentialStorageState.LEGACY_PLAINTEXT_ONLY,
                legacy_present=True,
                safe_diagnostic="legacy_plaintext_copy_present",
            )
        if secure_status == YOUTUBE_KEYRING_MISSING:
            return YouTubeCredentialStorageStatus(
                state=YouTubeCredentialStorageState.MISSING,
                safe_diagnostic="credential_missing",
            )
        if secure_status == YOUTUBE_KEYRING_UNAVAILABLE:
            return YouTubeCredentialStorageStatus(
                state=YouTubeCredentialStorageState.SECURE_BACKEND_UNAVAILABLE,
                legacy_present=legacy_present,
                safe_diagnostic="secure_backend_unavailable",
            )
        return YouTubeCredentialStorageStatus(
            state=YouTubeCredentialStorageState.STATUS_ERROR,
            legacy_present=legacy_present,
            safe_diagnostic="secure_status_error",
        )

    def save_secure(self, credential: str) -> YouTubeCredentialActionResult:
        status = self._settings_manager.save_api_key_secure(credential)
        storage = self.storage_status()
        if status == YOUTUBE_SAVE_SAVED:
            action_status = YouTubeCredentialActionStatus.SAVED
        elif status == YOUTUBE_SAVE_UPDATED:
            action_status = YouTubeCredentialActionStatus.UPDATED
        elif status == YOUTUBE_SAVE_EMPTY:
            action_status = YouTubeCredentialActionStatus.EMPTY_CREDENTIAL_REJECTED
        elif status == YOUTUBE_SAVE_BACKEND_UNAVAILABLE:
            action_status = YouTubeCredentialActionStatus.BACKEND_UNAVAILABLE
        elif status == YOUTUBE_SAVE_VERIFICATION_FAILED:
            action_status = YouTubeCredentialActionStatus.PRESENCE_VERIFICATION_FAILED
        else:
            action_status = YouTubeCredentialActionStatus.BACKEND_ERROR
        return YouTubeCredentialActionResult(
            action=YouTubeCredentialAction.SAVE,
            status=action_status,
            storage_status=storage,
            changed_secure=action_status in {
                YouTubeCredentialActionStatus.SAVED,
                YouTubeCredentialActionStatus.UPDATED,
            },
            safe_diagnostic=action_status.value,
        )

    def migrate_legacy_to_secure(self) -> YouTubeCredentialActionResult:
        before = self.storage_status()
        if not before.legacy_present:
            return YouTubeCredentialActionResult(
                action=YouTubeCredentialAction.MIGRATE,
                status=YouTubeCredentialActionStatus.NOT_FOUND,
                storage_status=before,
                safe_diagnostic="no_legacy_plaintext_copy",
            )

        legacy_credential = self._settings_manager.read_legacy_api_key_for_migration()
        try:
            save_status = self._settings_manager.save_api_key_secure(legacy_credential)
        finally:
            legacy_credential = ""

        if save_status not in {YOUTUBE_SAVE_SAVED, YOUTUBE_SAVE_UPDATED}:
            return YouTubeCredentialActionResult(
                action=YouTubeCredentialAction.MIGRATE,
                status=_save_failure_status(save_status),
                storage_status=self.storage_status(),
                safe_diagnostic="secure_save_failed_legacy_preserved",
            )

        if self._settings_manager.secure_api_key_presence_status() != YOUTUBE_KEYRING_PRESENT:
            return YouTubeCredentialActionResult(
                action=YouTubeCredentialAction.MIGRATE,
                status=YouTubeCredentialActionStatus.PRESENCE_VERIFICATION_FAILED,
                storage_status=self.storage_status(),
                changed_secure=True,
                safe_diagnostic="secure_presence_verification_failed_legacy_preserved",
            )

        cleanup_status = self._settings_manager.remove_legacy_api_key()
        if cleanup_status != YOUTUBE_CLEAR_CLEARED:
            return YouTubeCredentialActionResult(
                action=YouTubeCredentialAction.MIGRATE,
                status=YouTubeCredentialActionStatus.LEGACY_CLEANUP_FAILED,
                storage_status=self.storage_status(),
                changed_secure=True,
                safe_diagnostic="legacy_cleanup_failed_secure_preserved",
            )

        return YouTubeCredentialActionResult(
            action=YouTubeCredentialAction.MIGRATE,
            status=YouTubeCredentialActionStatus.MIGRATED,
            storage_status=self.storage_status(),
            changed_secure=True,
            changed_legacy=True,
            safe_diagnostic="migrated_to_secure_storage",
        )

    def clear_all(self) -> YouTubeCredentialActionResult:
        before = self.storage_status()
        if before.state is YouTubeCredentialStorageState.STATUS_ERROR:
            return YouTubeCredentialActionResult(
                action=YouTubeCredentialAction.CLEAR,
                status=YouTubeCredentialActionStatus.BACKEND_ERROR,
                storage_status=before,
                safe_diagnostic="storage_status_error_clear_not_attempted",
            )
        if (
            before.state is YouTubeCredentialStorageState.MISSING
            or (
                not before.secure_present
                and not before.legacy_present
                and before.state
                not in {
                    YouTubeCredentialStorageState.SECURE_BACKEND_UNAVAILABLE,
                    YouTubeCredentialStorageState.STATUS_ERROR,
                }
            )
        ):
            return YouTubeCredentialActionResult(
                action=YouTubeCredentialAction.CLEAR,
                status=YouTubeCredentialActionStatus.NOT_FOUND,
                storage_status=before,
                safe_diagnostic="credential_already_missing",
            )

        secure_status = self._settings_manager.clear_secure_api_key()
        legacy_status = (
            self._settings_manager.remove_legacy_api_key()
            if before.legacy_present
            and secure_status != YOUTUBE_CLEAR_BACKEND_ERROR
            else YOUTUBE_CLEAR_NOT_FOUND
        )
        after = self.storage_status()

        secure_ok = secure_status in {YOUTUBE_CLEAR_CLEARED, YOUTUBE_CLEAR_NOT_FOUND}
        legacy_ok = legacy_status in {YOUTUBE_CLEAR_CLEARED, YOUTUBE_CLEAR_NOT_FOUND}
        changed_secure = secure_status == YOUTUBE_CLEAR_CLEARED
        changed_legacy = legacy_status == YOUTUBE_CLEAR_CLEARED

        if secure_ok and legacy_ok and not after.secure_present and not after.legacy_present:
            status = (
                YouTubeCredentialActionStatus.CLEARED
                if changed_secure or changed_legacy
                else YouTubeCredentialActionStatus.NOT_FOUND
            )
        elif secure_status == YOUTUBE_CLEAR_BACKEND_UNAVAILABLE and changed_legacy:
            status = YouTubeCredentialActionStatus.PARTIAL_FAILURE
        elif secure_status == YOUTUBE_CLEAR_BACKEND_UNAVAILABLE:
            status = YouTubeCredentialActionStatus.BACKEND_UNAVAILABLE
        elif secure_status == YOUTUBE_CLEAR_BACKEND_ERROR and not legacy_ok:
            status = YouTubeCredentialActionStatus.PARTIAL_FAILURE
        elif not secure_ok or not legacy_ok or after.secure_present or after.legacy_present:
            status = YouTubeCredentialActionStatus.PARTIAL_FAILURE
        else:
            status = YouTubeCredentialActionStatus.CLEARED

        return YouTubeCredentialActionResult(
            action=YouTubeCredentialAction.CLEAR,
            status=status,
            storage_status=after,
            changed_secure=changed_secure,
            changed_legacy=changed_legacy,
            safe_diagnostic=status.value,
        )


def _save_failure_status(status: str) -> YouTubeCredentialActionStatus:
    if status == YOUTUBE_SAVE_BACKEND_UNAVAILABLE:
        return YouTubeCredentialActionStatus.BACKEND_UNAVAILABLE
    if status == YOUTUBE_SAVE_EMPTY:
        return YouTubeCredentialActionStatus.EMPTY_CREDENTIAL_REJECTED
    if status == YOUTUBE_SAVE_VERIFICATION_FAILED:
        return YouTubeCredentialActionStatus.PRESENCE_VERIFICATION_FAILED
    return YouTubeCredentialActionStatus.BACKEND_ERROR
