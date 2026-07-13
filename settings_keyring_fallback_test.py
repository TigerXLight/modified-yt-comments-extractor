import json
from pathlib import Path
from tempfile import TemporaryDirectory

from core.settings import AppSettings, SettingsManager


DUMMY_API_KEY = "DUMMY_TEST_API_KEY_1234567890"


class FakePasswordDeleteError(Exception):
    pass


class FakeKeyringErrors:
    PasswordDeleteError = FakePasswordDeleteError


class FakeKeyring:
    errors = FakeKeyringErrors

    def __init__(
        self,
        *,
        set_error: Exception | None = None,
        get_error: Exception | None = None,
        delete_error: Exception | None = None,
        stored_password: str = "",
    ) -> None:
        self.set_error = set_error
        self.get_error = get_error
        self.delete_error = delete_error
        self.stored_password = stored_password
        self.set_calls = 0
        self.get_calls = 0
        self.delete_calls = 0

    def set_password(self, _service_name: str, _api_key_name: str, api_key: str) -> None:
        self.set_calls += 1
        if self.set_error:
            raise self.set_error
        self.stored_password = api_key

    def get_password(self, _service_name: str, _api_key_name: str) -> str:
        self.get_calls += 1
        if self.get_error:
            raise self.get_error
        return self.stored_password

    def delete_password(self, _service_name: str, _api_key_name: str) -> None:
        self.delete_calls += 1
        if self.delete_error:
            raise self.delete_error
        self.stored_password = ""


def _settings_file(tmpdir: str) -> str:
    return str(Path(tmpdir) / "settings.json")


def _read_json(path: str) -> dict[str, object]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _assert_dummy_key_preserved(path: str) -> None:
    if _read_json(path).get("api_key") != DUMMY_API_KEY:
        raise AssertionError("legacy API key was not preserved")


def _assert_loaded_key_preserved(manager: SettingsManager) -> None:
    if manager.load().api_key != DUMMY_API_KEY:
        raise AssertionError("legacy API key was not loaded")


def test_keyring_unavailable_rejects_new_plaintext_write() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_file(tmpdir)
        manager = SettingsManager(path, keyring_module=None)

        assert not manager.save(AppSettings(api_key=DUMMY_API_KEY, min_likes=3))
        assert not Path(path).exists()


def test_keyring_set_failure_preserves_legacy_without_plaintext_update() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_file(tmpdir)
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"api_key": DUMMY_API_KEY, "min_likes": 7}, file)
        manager = SettingsManager(
            path,
            keyring_module=FakeKeyring(
                set_error=RuntimeError("safe keyring write failed")
            ),
        )

        assert not manager.save(AppSettings(api_key="replacement", min_likes=9))

        data = _read_json(path)
        _assert_dummy_key_preserved(path)
        assert data["min_likes"] == 7
        assert manager.keyring_available
        assert "storage status error" in manager.get_storage_info()
        reload_manager = SettingsManager(path, keyring_module=None)
        _assert_loaded_key_preserved(reload_manager)


def test_keyring_get_failure_loads_json_fallback() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_file(tmpdir)
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"api_key": DUMMY_API_KEY, "min_likes": 11}, file)

        manager = SettingsManager(
            path,
            keyring_module=FakeKeyring(
                get_error=RuntimeError("safe keyring read failed")
            ),
        )

        loaded = manager.load()

        if loaded.api_key != DUMMY_API_KEY:
            raise AssertionError("legacy API key was not loaded")
        assert loaded.min_likes == 11
        assert manager.keyring_available
        assert "storage status error" in manager.get_storage_info()


def test_keyring_delete_failure_does_not_report_full_clear() -> None:
    with TemporaryDirectory() as tmpdir:
        manager = SettingsManager(
            _settings_file(tmpdir),
            keyring_module=FakeKeyring(
                delete_error=RuntimeError("safe keyring delete failed")
            ),
        )

        assert not manager.delete_api_key()
        assert manager.keyring_available
        assert "storage status error" in manager.get_storage_info()


def run_self_test() -> None:
    test_keyring_unavailable_rejects_new_plaintext_write()
    test_keyring_set_failure_preserves_legacy_without_plaintext_update()
    test_keyring_get_failure_loads_json_fallback()
    test_keyring_delete_failure_does_not_report_full_clear()


if __name__ == "__main__":
    run_self_test()
    print("Settings keyring fallback self-test passed.")
