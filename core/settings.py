"""
Settings management with secure credential storage.

Provides persistent settings storage with optional keyring integration
for secure API key storage.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from core.constants import (
    SETTINGS_FILE,
    KEYRING_SERVICE_NAME,
    KEYRING_API_KEY_NAME,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_DEFAULT_HEIGHT,
    SortOption,
    SpamFilterStrength,
)

logger = logging.getLogger(__name__)

# Try to import keyring for secure storage
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning("keyring package not installed; secure API-key storage is unavailable.")


YOUTUBE_KEYRING_PRESENT = "present"
YOUTUBE_KEYRING_MISSING = "missing"
YOUTUBE_KEYRING_UNAVAILABLE = "backend_unavailable"
YOUTUBE_KEYRING_ERROR = "backend_error"

YOUTUBE_SAVE_SAVED = "saved"
YOUTUBE_SAVE_UPDATED = "updated"
YOUTUBE_SAVE_EMPTY = "empty_credential_rejected"
YOUTUBE_SAVE_BACKEND_UNAVAILABLE = "backend_unavailable"
YOUTUBE_SAVE_BACKEND_ERROR = "backend_error"
YOUTUBE_SAVE_VERIFICATION_FAILED = "presence_verification_failed"

YOUTUBE_CLEAR_CLEARED = "cleared"
YOUTUBE_CLEAR_NOT_FOUND = "not_found"
YOUTUBE_CLEAR_BACKEND_UNAVAILABLE = "backend_unavailable"
YOUTUBE_CLEAR_BACKEND_ERROR = "backend_error"

_DEFAULT_KEYRING_MODULE = object()


@dataclass
class AppSettings:
    """Application settings data class."""

    # API settings
    api_key: str = ""

    # Filter settings
    filter_spam: bool = False
    spam_threshold: float = SpamFilterStrength.MODERATE.value
    exclude_creator: bool = False
    min_likes: int = 0
    max_comments: Optional[int] = None  # Maximum comments per video (None = unlimited)
    filter_words: str = ""  # Comma-separated words to filter comments

    # Custom spam patterns
    blacklist_patterns: str = ""  # Newline-separated patterns to always flag as spam
    whitelist_patterns: str = ""  # Newline-separated patterns to always allow

    # Sort settings
    sort_by: str = SortOption.DATE_NEWEST.value
    online_asr_provider_id: str = ""
    access_keys_added_provider_ids: tuple[str, ...] = ()
    access_keys_validation_states: dict[str, dict[str, str]] = field(default_factory=dict)

    # Date filter (optional)
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    # UI preferences
    window_width: int = WINDOW_DEFAULT_WIDTH
    window_height: int = WINDOW_DEFAULT_HEIGHT

    def to_dict(self, include_api_key: bool = False) -> dict:
        """
        Convert settings to dictionary.

        Args:
            include_api_key: Whether to include the API key (for non-secure storage)
        """
        data = asdict(self)
        if not include_api_key:
            del data["api_key"]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        """Create settings from dictionary."""
        # Filter to only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        if "access_keys_added_provider_ids" in filtered:
            filtered["access_keys_added_provider_ids"] = tuple(
                str(item)
                for item in filtered["access_keys_added_provider_ids"]
                if str(item or "").strip()
            )
        if "access_keys_validation_states" in filtered:
            states = filtered["access_keys_validation_states"]
            filtered["access_keys_validation_states"] = (
                {
                    str(provider_id): {
                        str(key): str(value)
                        for key, value in record.items()
                        if key in {
                            "provider_id",
                            "state",
                            "checked_at_utc",
                            "safe_diagnostic",
                        }
                    }
                    for provider_id, record in states.items()
                    if str(provider_id or "").strip() and isinstance(record, dict)
                }
                if isinstance(states, dict)
                else {}
            )
        return cls(**filtered)


class SettingsManager:
    """
    Manages application settings with secure credential storage.

    Settings are stored in a JSON file, but the API key is stored
    securely using the system keyring when available.

    Usage:
        manager = SettingsManager()
        settings = manager.load()

        settings.api_key = "new_key"
        settings.filter_spam = False

        manager.save(settings)
    """

    def __init__(
        self,
        settings_file: Optional[str] = None,
        *,
        keyring_module: Any = _DEFAULT_KEYRING_MODULE,
    ):
        """
        Initialize the settings manager.

        Args:
            settings_file: Path to settings file. Defaults to SETTINGS_FILE
                          in the same directory as this module's package.
        """
        if settings_file:
            self.settings_file = Path(settings_file)
        else:
            app_dir = Path(__file__).resolve().parent.parent
            self.settings_file = app_dir / SETTINGS_FILE
        if keyring_module is _DEFAULT_KEYRING_MODULE:
            self._keyring_module = keyring if KEYRING_AVAILABLE else None
        else:
            self._keyring_module = keyring_module
        self._use_keyring = self._keyring_module is not None
        self._last_keyring_error: Optional[str] = None

    @property
    def keyring_available(self) -> bool:
        """Check if secure keyring storage is available."""
        return self._use_keyring

    def load(self) -> AppSettings:
        """
        Load settings from file and keyring.

        Returns:
            AppSettings with loaded values, or defaults if no settings exist
        """
        settings = AppSettings()

        # Load from JSON file
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    settings = AppSettings.from_dict(data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse settings file: {e}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")

        # Load API key from keyring (if available) or from file
        api_key = self._load_api_key()
        if api_key:
            settings.api_key = api_key

        return settings

    def load_preferences_only(self) -> AppSettings:
        """
        Load non-secret preferences from the JSON settings file only.

        This intentionally avoids keyring reads. Action-time credential
        resolution and explicit status refresh paths continue to use load()
        or the dedicated credential status helpers.
        """
        settings = AppSettings()
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    settings = AppSettings.from_dict(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse settings file: {e}")
            except Exception as e:
                logger.error(f"Failed to load settings preferences: {e}")
        settings.api_key = ""
        return settings

    def save(self, settings: AppSettings) -> bool:
        """
        Save settings to file and keyring.

        Args:
            settings: AppSettings to save

        Returns:
            True if saved successfully
        """
        try:
            # Save API key securely. Existing legacy plaintext is preserved
            # unless an explicit migration/clear action removes it.
            if settings.api_key:
                status = self.save_api_key_secure(settings.api_key)
                if status not in {YOUTUBE_SAVE_SAVED, YOUTUBE_SAVE_UPDATED}:
                    return False

            data = settings.to_dict(include_api_key=False)
            legacy_api_key = self.read_legacy_api_key_for_migration()
            if legacy_api_key:
                data["api_key"] = legacy_api_key

            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            return True

        except Exception:
            logger.error("Failed to save settings safely.")
            return False

    def _load_api_key(self) -> Optional[str]:
        """Load API key from keyring or settings file."""
        # Try keyring first
        if self._use_keyring:
            try:
                api_key = self._keyring_module.get_password(
                    KEYRING_SERVICE_NAME,
                    KEYRING_API_KEY_NAME
                )
                if api_key:
                    return api_key
            except Exception:
                logger.warning("Failed to load API key from keyring.")
                self._last_keyring_error = YOUTUBE_KEYRING_ERROR

        # Fall back to settings file
        return self.read_legacy_api_key_for_migration() or None

    def _read_settings_data(self) -> tuple[dict[str, Any], bool]:
        if not self.settings_file.exists():
            return {}, True
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data, True
        except Exception:
            pass
        return {}, False

    def _write_settings_data(self, data: dict[str, Any]) -> bool:
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception:
            logger.error("Failed to update settings file safely.")
            return False

    def read_legacy_api_key_for_migration(self) -> str:
        """Return legacy plaintext only for explicit migration/save compatibility."""
        data, readable = self._read_settings_data()
        if not readable:
            return ""
        value = data.get("api_key", "")
        return str(value).strip() if value else ""

    def legacy_api_key_present(self) -> bool:
        return bool(self.read_legacy_api_key_for_migration())

    def legacy_settings_readable(self) -> bool:
        _data, readable = self._read_settings_data()
        return readable

    def remove_legacy_api_key(self) -> str:
        data, readable = self._read_settings_data()
        if not readable:
            return YOUTUBE_CLEAR_BACKEND_ERROR
        if "api_key" not in data:
            return YOUTUBE_CLEAR_NOT_FOUND
        cleaned = dict(data)
        cleaned.pop("api_key", None)
        if not self._write_settings_data(cleaned):
            return YOUTUBE_CLEAR_BACKEND_ERROR
        return YOUTUBE_CLEAR_CLEARED

    def _save_api_key(self, api_key: str) -> None:
        """Save API key to keyring or settings file."""
        status = self.save_api_key_secure(api_key)
        if status not in {YOUTUBE_SAVE_SAVED, YOUTUBE_SAVE_UPDATED, YOUTUBE_SAVE_EMPTY}:
            raise RuntimeError(status)

    def secure_api_key_presence_status(self) -> str:
        if not self._use_keyring or self._keyring_module is None:
            return YOUTUBE_KEYRING_UNAVAILABLE
        try:
            configured = self._keyring_module.get_password(
                KEYRING_SERVICE_NAME,
                KEYRING_API_KEY_NAME,
            ) is not None
        except Exception:
            self._last_keyring_error = YOUTUBE_KEYRING_ERROR
            return YOUTUBE_KEYRING_ERROR
        self._last_keyring_error = None
        return YOUTUBE_KEYRING_PRESENT if configured else YOUTUBE_KEYRING_MISSING

    def save_api_key_secure(self, api_key: str) -> str:
        api_key = str(api_key or "").strip()
        if not api_key:
            return YOUTUBE_SAVE_EMPTY
        if not self._use_keyring or self._keyring_module is None:
            self._last_keyring_error = YOUTUBE_KEYRING_UNAVAILABLE
            return YOUTUBE_SAVE_BACKEND_UNAVAILABLE
        existing = None
        try:
            existing = self._keyring_module.get_password(
                KEYRING_SERVICE_NAME,
                KEYRING_API_KEY_NAME,
            )
            self._keyring_module.set_password(
                KEYRING_SERVICE_NAME,
                KEYRING_API_KEY_NAME,
                api_key,
            )
        except Exception:
            self._last_keyring_error = YOUTUBE_KEYRING_ERROR
            return YOUTUBE_SAVE_BACKEND_ERROR
        if self.secure_api_key_presence_status() != YOUTUBE_KEYRING_PRESENT:
            self._restore_secure_api_key_after_failed_save(existing)
            self._last_keyring_error = YOUTUBE_SAVE_VERIFICATION_FAILED
            return YOUTUBE_SAVE_VERIFICATION_FAILED
        self._last_keyring_error = None
        return YOUTUBE_SAVE_UPDATED if existing is not None else YOUTUBE_SAVE_SAVED

    def _restore_secure_api_key_after_failed_save(
        self,
        previous_api_key: Optional[str],
    ) -> None:
        if not self._use_keyring or self._keyring_module is None:
            return
        try:
            if previous_api_key is None:
                self._keyring_module.delete_password(
                    KEYRING_SERVICE_NAME,
                    KEYRING_API_KEY_NAME,
                )
            else:
                self._keyring_module.set_password(
                    KEYRING_SERVICE_NAME,
                    KEYRING_API_KEY_NAME,
                    previous_api_key,
                )
        except Exception as exc:
            password_delete_error = getattr(
                getattr(self._keyring_module, "errors", object()),
                "PasswordDeleteError",
                None,
            )
            if password_delete_error is not None and isinstance(exc, password_delete_error):
                return
            logger.error("Failed to restore previous API key state safely.")

    def delete_api_key(self) -> bool:
        """
        Delete the stored API key from keyring and legacy settings.

        Returns:
            True if deleted successfully
        """
        secure = self.clear_secure_api_key()
        legacy = self.remove_legacy_api_key()
        secure_ok = secure in {YOUTUBE_CLEAR_CLEARED, YOUTUBE_CLEAR_NOT_FOUND}
        legacy_ok = legacy in {YOUTUBE_CLEAR_CLEARED, YOUTUBE_CLEAR_NOT_FOUND}
        return secure_ok and legacy_ok

    def clear_secure_api_key(self) -> str:
        if not self._use_keyring or self._keyring_module is None:
            self._last_keyring_error = YOUTUBE_KEYRING_UNAVAILABLE
            return YOUTUBE_CLEAR_BACKEND_UNAVAILABLE
        try:
            self._keyring_module.delete_password(
                KEYRING_SERVICE_NAME,
                KEYRING_API_KEY_NAME,
            )
            self._last_keyring_error = None
            return YOUTUBE_CLEAR_CLEARED
        except Exception as exc:
            password_delete_error = getattr(
                getattr(self._keyring_module, "errors", object()),
                "PasswordDeleteError",
                None,
            )
            if password_delete_error is not None and isinstance(exc, password_delete_error):
                self._last_keyring_error = None
                return YOUTUBE_CLEAR_NOT_FOUND
            self._last_keyring_error = YOUTUBE_KEYRING_ERROR
            logger.error("Failed to clear API key from keyring.")
            return YOUTUBE_CLEAR_BACKEND_ERROR

    def get_storage_info(self) -> str:
        """Get information about how the API key is stored."""
        if self._last_keyring_error == YOUTUBE_KEYRING_ERROR:
            return "API key storage status error"
        secure = self.secure_api_key_presence_status()
        legacy = self.legacy_api_key_present()
        if secure == YOUTUBE_KEYRING_PRESENT and legacy:
            return "API key present in system keyring and legacy settings.json"
        if secure == YOUTUBE_KEYRING_PRESENT:
            return "API key stored securely in system keyring"
        if legacy:
            return "API key stored in legacy settings.json"
        if secure == YOUTUBE_KEYRING_UNAVAILABLE:
            return "API key secure storage unavailable"
        if secure == YOUTUBE_KEYRING_ERROR:
            return "API key storage status error"
        return "API key not configured"
