import json
from pathlib import Path
from tempfile import TemporaryDirectory

import core.settings as settings_module
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


def test_keyring_unavailable_saves_dummy_key_to_json() -> None:
    with TemporaryDirectory() as tmpdir:
        path = _settings_file(tmpdir)
        manager = SettingsManager(path)
        manager._use_keyring = False

        assert manager.save(AppSettings(api_key=DUMMY_API_KEY, min_likes=3))

        data = _read_json(path)
        assert data["api_key"] == DUMMY_API_KEY
        assert data["min_likes"] == 3
        reload_manager = SettingsManager(path)
        reload_manager._use_keyring = False
        assert reload_manager.load().api_key == DUMMY_API_KEY


def test_keyring_set_failure_falls_back_to_json() -> None:
    original_keyring = getattr(settings_module, "keyring", None)
    settings_module.keyring = FakeKeyring(set_error=RuntimeError("keyring write failed"))
    try:
        with TemporaryDirectory() as tmpdir:
            path = _settings_file(tmpdir)
            manager = SettingsManager(path)
            manager._use_keyring = True

            assert manager.save(AppSettings(api_key=DUMMY_API_KEY, min_likes=7))

            data = _read_json(path)
            assert data["api_key"] == DUMMY_API_KEY
            assert data["min_likes"] == 7
            assert not manager.keyring_available
            assert "settings.json" in manager.get_storage_info()
            reload_manager = SettingsManager(path)
            reload_manager._use_keyring = False
            assert reload_manager.load().api_key == DUMMY_API_KEY
    finally:
        if original_keyring is not None:
            settings_module.keyring = original_keyring


def test_keyring_get_failure_loads_json_fallback() -> None:
    original_keyring = getattr(settings_module, "keyring", None)
    settings_module.keyring = FakeKeyring(get_error=RuntimeError("keyring read failed"))
    try:
        with TemporaryDirectory() as tmpdir:
            path = _settings_file(tmpdir)
            with open(path, "w", encoding="utf-8") as file:
                json.dump({"api_key": DUMMY_API_KEY, "min_likes": 11}, file)

            manager = SettingsManager(path)
            manager._use_keyring = True

            loaded = manager.load()

            assert loaded.api_key == DUMMY_API_KEY
            assert loaded.min_likes == 11
            assert not manager.keyring_available
            assert "settings.json" in manager.get_storage_info()
    finally:
        if original_keyring is not None:
            settings_module.keyring = original_keyring


def test_keyring_delete_failure_marks_fallback_state() -> None:
    original_keyring = getattr(settings_module, "keyring", None)
    settings_module.keyring = FakeKeyring(delete_error=RuntimeError("keyring delete failed"))
    try:
        with TemporaryDirectory() as tmpdir:
            manager = SettingsManager(_settings_file(tmpdir))
            manager._use_keyring = True

            assert not manager.delete_api_key()
            assert not manager.keyring_available
            assert "settings.json" in manager.get_storage_info()
    finally:
        if original_keyring is not None:
            settings_module.keyring = original_keyring


def run_self_test() -> None:
    test_keyring_unavailable_saves_dummy_key_to_json()
    test_keyring_set_failure_falls_back_to_json()
    test_keyring_get_failure_loads_json_fallback()
    test_keyring_delete_failure_marks_fallback_state()


if __name__ == "__main__":
    run_self_test()
    print("Settings keyring fallback self-test passed.")
