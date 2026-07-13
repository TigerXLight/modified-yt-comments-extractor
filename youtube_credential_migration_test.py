from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from core.settings import AppSettings, SettingsManager
from youtube_credential_migration import (
    YouTubeCredentialActionStatus,
    YouTubeCredentialMigrationService,
    YouTubeCredentialStorageState,
)


SECRET_SENTINEL = "YOUTUBE-SECRET-MUST-NOT-LEAK"


class FakePasswordDeleteError(Exception):
    pass


class FakeKeyringErrors:
    PasswordDeleteError = FakePasswordDeleteError


class FakeKeyring:
    errors = FakeKeyringErrors

    def __init__(
        self,
        *,
        stored_password: str | None = None,
        fail_get: bool = False,
        fail_set: bool = False,
        fail_delete: bool = False,
        missing_after_set: bool = False,
    ) -> None:
        self.stored_password = stored_password
        self.fail_get = fail_get
        self.fail_set = fail_set
        self.fail_delete = fail_delete
        self.missing_after_set = missing_after_set
        self.calls: list[str] = []
        self.set_calls = 0

    def get_password(self, _service_name: str, _account_name: str) -> str | None:
        self.calls.append("get_password")
        if self.fail_get:
            raise RuntimeError("safe fake get failure")
        return self.stored_password

    def set_password(
        self,
        _service_name: str,
        _account_name: str,
        credential: str,
    ) -> None:
        self.calls.append("set_password")
        self.set_calls += 1
        if self.fail_set:
            raise RuntimeError("safe fake set failure")
        self.stored_password = (
            None
            if self.missing_after_set and self.set_calls == 1
            else credential
        )

    def delete_password(self, _service_name: str, _account_name: str) -> None:
        self.calls.append("delete_password")
        if self.fail_delete:
            raise RuntimeError("safe fake delete failure")
        if self.stored_password is None:
            raise FakePasswordDeleteError()
        self.stored_password = None


class FailingCleanupSettingsManager(SettingsManager):
    def remove_legacy_api_key(self) -> str:
        return "backend_error"


def _settings_path(tmpdir: str) -> str:
    return str(Path(tmpdir) / "settings.json")


def _write_settings(path: str, data: dict[str, object]) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def _read_settings(path: str) -> dict[str, object]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _manager(
    path: str,
    keyring: FakeKeyring | None = None,
) -> SettingsManager:
    return SettingsManager(path, keyring_module=keyring or FakeKeyring())


def _service(manager: SettingsManager) -> YouTubeCredentialMigrationService:
    return YouTubeCredentialMigrationService(manager)


def _assert_fake_keyring_value(
    keyring: FakeKeyring,
    expected: str | None,
) -> None:
    if keyring.stored_password != expected:
        raise AssertionError("fake keyring value mismatch")


def _assert_secret_not_exposed(value: object) -> None:
    rendered = repr(value)
    if hasattr(value, "to_dict"):
        rendered += json.dumps(value.to_dict(), sort_keys=True)
    if SECRET_SENTINEL in rendered:
        raise AssertionError("secret leaked through public result")


def _assert_legacy_present(path: str) -> None:
    data = _read_settings(path)
    if data.get("api_key") != SECRET_SENTINEL:
        raise AssertionError("legacy credential was not preserved")


def _assert_legacy_absent(path: str) -> None:
    if Path(path).exists() and "api_key" in _read_settings(path):
        raise AssertionError("legacy credential was not removed")


def test_safe_storage_state_detection() -> None:
    with TemporaryDirectory() as tmpdir:
        missing = _service(_manager(_settings_path(tmpdir))).storage_status()
        assert missing.state is YouTubeCredentialStorageState.MISSING

    with TemporaryDirectory() as tmpdir:
        secure = _service(
            _manager(_settings_path(tmpdir), FakeKeyring(stored_password=SECRET_SENTINEL))
        ).storage_status()
        assert secure.state is YouTubeCredentialStorageState.SECURE_KEYRING_ONLY

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL, "min_likes": 4})
        legacy = _service(_manager(path)).storage_status()
        assert legacy.state is YouTubeCredentialStorageState.LEGACY_PLAINTEXT_ONLY

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        both = _service(
            _manager(path, FakeKeyring(stored_password=SECRET_SENTINEL))
        ).storage_status()
        assert both.state is YouTubeCredentialStorageState.BOTH_SECURE_AND_LEGACY

    with TemporaryDirectory() as tmpdir:
        unavailable = _service(
            SettingsManager(_settings_path(tmpdir), keyring_module=None)
        ).storage_status()
        assert unavailable.state is YouTubeCredentialStorageState.SECURE_BACKEND_UNAVAILABLE

    with TemporaryDirectory() as tmpdir:
        error = _service(
            _manager(_settings_path(tmpdir), FakeKeyring(fail_get=True))
        ).storage_status()
        assert error.state is YouTubeCredentialStorageState.STATUS_ERROR

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        Path(path).write_text("{not-json", encoding="utf-8")
        malformed = _service(_manager(path)).storage_status()
        assert malformed.state is YouTubeCredentialStorageState.STATUS_ERROR
        _assert_secret_not_exposed(malformed)


def test_explicit_legacy_migration_sequence_and_cleanup() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL, "min_likes": 9})
        keyring = FakeKeyring()
        result = _service(_manager(path, keyring)).migrate_legacy_to_secure()

        assert result.status is YouTubeCredentialActionStatus.MIGRATED
        assert keyring.calls.count("set_password") == 1
        assert keyring.calls.index("set_password") > keyring.calls.index("get_password")
        _assert_fake_keyring_value(keyring, SECRET_SENTINEL)
        _assert_legacy_absent(path)
        data = _read_settings(path)
        assert data["min_likes"] == 9
        assert result.storage_status.state is YouTubeCredentialStorageState.SECURE_KEYRING_ONLY
        _assert_secret_not_exposed(result)


def test_migration_preserves_legacy_on_failures() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL, "min_likes": 1})
        result = _service(_manager(path, FakeKeyring(fail_set=True))).migrate_legacy_to_secure()
        assert result.status is YouTubeCredentialActionStatus.BACKEND_ERROR
        _assert_legacy_present(path)
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        keyring = FakeKeyring(missing_after_set=True)
        result = _service(_manager(path, keyring)).migrate_legacy_to_secure()
        assert result.status is YouTubeCredentialActionStatus.PRESENCE_VERIFICATION_FAILED
        _assert_legacy_present(path)
        _assert_fake_keyring_value(keyring, None)
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        keyring = FakeKeyring(stored_password="previous", missing_after_set=True)
        result = _service(_manager(path, keyring)).save_secure("replacement")
        assert result.status is YouTubeCredentialActionStatus.PRESENCE_VERIFICATION_FAILED
        _assert_fake_keyring_value(keyring, "previous")
        _assert_legacy_present(path)
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        keyring = FakeKeyring()
        manager = FailingCleanupSettingsManager(path, keyring_module=keyring)
        result = _service(manager).migrate_legacy_to_secure()
        assert result.status is YouTubeCredentialActionStatus.LEGACY_CLEANUP_FAILED
        _assert_legacy_present(path)
        _assert_fake_keyring_value(keyring, SECRET_SENTINEL)
        _assert_secret_not_exposed(result)


def test_save_update_is_secure_only_and_fail_closed() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        keyring = FakeKeyring()
        result = _service(_manager(path, keyring)).save_secure(SECRET_SENTINEL)
        assert result.status is YouTubeCredentialActionStatus.SAVED
        _assert_fake_keyring_value(keyring, SECRET_SENTINEL)
        _assert_legacy_absent(path)
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL, "min_likes": 3})
        keyring = FakeKeyring(stored_password="previous", fail_set=True)
        result = _service(_manager(path, keyring)).save_secure("replacement")
        assert result.status is YouTubeCredentialActionStatus.BACKEND_ERROR
        _assert_fake_keyring_value(keyring, "previous")
        _assert_legacy_present(path)
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        manager = SettingsManager(path, keyring_module=None)
        assert not manager.save(AppSettings(api_key=SECRET_SENTINEL, min_likes=8))
        assert not Path(path).exists()


def test_clear_all_states_and_partial_failures() -> None:
    with TemporaryDirectory() as tmpdir:
        keyring = FakeKeyring(stored_password=SECRET_SENTINEL)
        result = _service(_manager(_settings_path(tmpdir), keyring)).clear_all()
        assert result.status is YouTubeCredentialActionStatus.CLEARED
        _assert_fake_keyring_value(keyring, None)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL, "min_likes": 5})
        result = _service(_manager(path)).clear_all()
        assert result.status is YouTubeCredentialActionStatus.CLEARED
        _assert_legacy_absent(path)
        assert _read_settings(path)["min_likes"] == 5

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL, "min_likes": 6})
        manager = SettingsManager(path, keyring_module=None)
        result = _service(manager).clear_all()
        assert result.status is YouTubeCredentialActionStatus.PARTIAL_FAILURE
        _assert_legacy_absent(path)
        assert _read_settings(path)["min_likes"] == 6
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        keyring = FakeKeyring(stored_password=SECRET_SENTINEL)
        result = _service(_manager(path, keyring)).clear_all()
        assert result.status is YouTubeCredentialActionStatus.CLEARED
        _assert_fake_keyring_value(keyring, None)
        _assert_legacy_absent(path)

    with TemporaryDirectory() as tmpdir:
        result = _service(_manager(_settings_path(tmpdir))).clear_all()
        assert result.status is YouTubeCredentialActionStatus.NOT_FOUND

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        keyring = FakeKeyring(stored_password=SECRET_SENTINEL, fail_delete=True)
        result = _service(_manager(path, keyring)).clear_all()
        assert result.status is YouTubeCredentialActionStatus.PARTIAL_FAILURE
        _assert_fake_keyring_value(keyring, SECRET_SENTINEL)
        _assert_legacy_present(path)
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        keyring = FakeKeyring(stored_password=SECRET_SENTINEL)
        manager = FailingCleanupSettingsManager(path, keyring_module=keyring)
        result = _service(manager).clear_all()
        assert result.status is YouTubeCredentialActionStatus.PARTIAL_FAILURE
        _assert_fake_keyring_value(keyring, None)
        _assert_legacy_present(path)
        _assert_secret_not_exposed(result)

    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        Path(path).write_text("{not-json", encoding="utf-8")
        keyring = FakeKeyring(stored_password=SECRET_SENTINEL)
        result = _service(_manager(path, keyring)).clear_all()
        assert result.status is YouTubeCredentialActionStatus.BACKEND_ERROR
        _assert_fake_keyring_value(keyring, SECRET_SENTINEL)
        _assert_secret_not_exposed(result)


def test_migration_is_not_implicit_on_load_or_status() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_path(tmpdir)
        _write_settings(path, {"api_key": SECRET_SENTINEL})
        keyring = FakeKeyring()
        manager = _manager(path, keyring)

        loaded = manager.load()
        if loaded.api_key != SECRET_SENTINEL:
            raise AssertionError("legacy credential was not loaded for compatibility")
        status = _service(manager).storage_status()

        assert status.state is YouTubeCredentialStorageState.LEGACY_PLAINTEXT_ONLY
        assert "set_password" not in keyring.calls
        _assert_legacy_present(path)
        _assert_secret_not_exposed(status)


def run_self_test() -> None:
    test_safe_storage_state_detection()
    test_explicit_legacy_migration_sequence_and_cleanup()
    test_migration_preserves_legacy_on_failures()
    test_save_update_is_secure_only_and_fail_closed()
    test_clear_all_states_and_partial_failures()
    test_migration_is_not_implicit_on_load_or_status()
    print("YouTube credential migration self-test passed.")


if __name__ == "__main__":
    run_self_test()
