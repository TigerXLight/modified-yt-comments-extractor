from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace

from credential_architecture import build_row2a_credential_architecture
from credential_store import (
    KEYRING_SERVICE_NAME,
    SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS,
    YOUTUBE_CREDENTIAL_ID,
    CredentialStoreBackend,
    CredentialStoreOperation,
    CredentialStoreStatus,
    InMemoryCredentialStore,
    SystemKeyringCredentialStore,
    credential_locator_for_id,
    credential_store_result_contains_forbidden_fields,
    supported_credential_locators,
)


SECRET_SENTINEL = "ROW2C1-SECRET-MUST-NOT-APPEAR"
SUPPORTED_ID = "elevenlabs_scribe_api_key"


class FakePasswordDeleteError(Exception):
    pass


class FakeKeyring:
    def __init__(
        self,
        *,
        fail_get: bool = False,
        fail_set: bool = False,
        fail_delete: bool = False,
    ) -> None:
        self.errors = SimpleNamespace(
            PasswordDeleteError=FakePasswordDeleteError,
        )
        self.fail_get = fail_get
        self.fail_set = fail_set
        self.fail_delete = fail_delete
        self.store: dict[tuple[str, str], str] = {}
        self.calls: list[str] = []

    def get_password(self, service_name: str, account_name: str) -> str | None:
        self.calls.append("get_password")
        if self.fail_get:
            raise RuntimeError(SECRET_SENTINEL)
        return self.store.get((service_name, account_name))

    def set_password(
        self,
        service_name: str,
        account_name: str,
        credential: str,
    ) -> None:
        self.calls.append("set_password")
        if self.fail_set:
            raise RuntimeError(SECRET_SENTINEL)
        self.store[(service_name, account_name)] = credential

    def delete_password(self, service_name: str, account_name: str) -> None:
        self.calls.append("delete_password")
        if self.fail_delete:
            raise RuntimeError(SECRET_SENTINEL)
        key = (service_name, account_name)
        if key not in self.store:
            raise FakePasswordDeleteError("missing")
        del self.store[key]


def _result_blob(result: object) -> str:
    return repr(result) + json.dumps(result.to_dict(), sort_keys=True)


def _assert_secret_not_exposed(result: object) -> None:
    blob = _result_blob(result)
    if SECRET_SENTINEL in blob:
        raise AssertionError("secret sentinel leaked through result output")
    assert not credential_store_result_contains_forbidden_fields(
        result.to_dict()
    )


def _assert_test_store_value(
    store: InMemoryCredentialStore,
    credential_id: str,
    expected_value: str | None,
) -> None:
    if store._test_only_stored_credential(credential_id) != expected_value:
        raise AssertionError("test-only memory store value mismatch")


def _assert_fake_keyring_value(
    fake: FakeKeyring,
    service_name: str,
    account_name: str,
    expected_value: str,
) -> None:
    if fake.store.get((service_name, account_name)) != expected_value:
        raise AssertionError("fake keyring stored value mismatch")


def test_supported_locator_mapping_and_uniqueness() -> None:
    plan = build_row2a_credential_architecture()
    descriptor_ids = tuple(item.credential_id for item in plan.descriptors)
    expected = tuple(
        credential_id
        for credential_id in descriptor_ids
        if credential_id != YOUTUBE_CREDENTIAL_ID
    )
    assert SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS == expected

    locators = supported_credential_locators()
    assert tuple(item.credential_id for item in locators) == expected
    assert all(item.service_name == KEYRING_SERVICE_NAME for item in locators)

    account_names = [item.account_name for item in locators]
    assert len(account_names) == len(set(account_names))
    assert all(item.startswith("asr.") for item in account_names)
    assert all("\\" not in item and "/" not in item for item in account_names)

    assert credential_locator_for_id(SUPPORTED_ID).to_dict() == {
        "credential_id": SUPPORTED_ID,
        "service_name": KEYRING_SERVICE_NAME,
        "account_name": f"asr.{SUPPORTED_ID}",
    }


def test_unknown_and_youtube_credentials_are_rejected() -> None:
    memory = InMemoryCredentialStore()
    unknown = memory.save_credential("unknown_provider", SECRET_SENTINEL)
    youtube_save = memory.save_credential(YOUTUBE_CREDENTIAL_ID, SECRET_SENTINEL)
    youtube_clear = memory.clear_credential(YOUTUBE_CREDENTIAL_ID)
    youtube_presence = memory.credential_present(YOUTUBE_CREDENTIAL_ID)

    assert unknown.status is CredentialStoreStatus.UNSUPPORTED_CREDENTIAL
    assert youtube_save.status is CredentialStoreStatus.YOUTUBE_CREDENTIAL_EXCLUDED
    assert youtube_clear.status is CredentialStoreStatus.YOUTUBE_CREDENTIAL_EXCLUDED
    assert youtube_presence.status is CredentialStoreStatus.YOUTUBE_CREDENTIAL_EXCLUDED
    _assert_test_store_value(memory, SUPPORTED_ID, None)
    _assert_secret_not_exposed(unknown)
    _assert_secret_not_exposed(youtube_save)


def test_in_memory_save_overwrite_and_clear() -> None:
    memory = InMemoryCredentialStore()

    absent = memory.credential_present(SUPPORTED_ID)
    assert absent.operation is CredentialStoreOperation.PRESENCE
    assert absent.status is CredentialStoreStatus.NOT_FOUND
    _assert_secret_not_exposed(absent)

    first = memory.save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    assert first.status is CredentialStoreStatus.SAVED
    assert first.changed is True
    _assert_test_store_value(memory, SUPPORTED_ID, SECRET_SENTINEL)
    _assert_secret_not_exposed(first)

    present = memory.credential_present(SUPPORTED_ID)
    assert present.status is CredentialStoreStatus.PRESENT
    _assert_secret_not_exposed(present)

    second = memory.save_credential(SUPPORTED_ID, "replacement")
    assert second.status is CredentialStoreStatus.UPDATED
    assert second.changed is True
    _assert_test_store_value(memory, SUPPORTED_ID, "replacement")
    _assert_secret_not_exposed(second)

    cleared = memory.clear_credential(SUPPORTED_ID)
    assert cleared.status is CredentialStoreStatus.CLEARED
    assert cleared.changed is True
    _assert_test_store_value(memory, SUPPORTED_ID, None)
    _assert_secret_not_exposed(cleared)

    missing = memory.clear_credential(SUPPORTED_ID)
    assert missing.status is CredentialStoreStatus.NOT_FOUND
    assert missing.changed is False
    _assert_secret_not_exposed(missing)


def test_in_memory_simulated_failures() -> None:
    unavailable = InMemoryCredentialStore(available=False)
    presence_unavailable = unavailable.credential_present(SUPPORTED_ID)
    save_unavailable = unavailable.save_credential(
        SUPPORTED_ID,
        SECRET_SENTINEL,
    )
    clear_unavailable = unavailable.clear_credential(SUPPORTED_ID)
    assert presence_unavailable.status is CredentialStoreStatus.BACKEND_UNAVAILABLE
    assert save_unavailable.status is CredentialStoreStatus.BACKEND_UNAVAILABLE
    assert clear_unavailable.status is CredentialStoreStatus.BACKEND_UNAVAILABLE
    _assert_secret_not_exposed(presence_unavailable)
    _assert_secret_not_exposed(save_unavailable)

    presence_error = InMemoryCredentialStore(
        fail_presence=True
    ).credential_present(SUPPORTED_ID)
    save_error = InMemoryCredentialStore(fail_save=True).save_credential(
        SUPPORTED_ID,
        SECRET_SENTINEL,
    )
    clear_error = InMemoryCredentialStore(fail_clear=True).clear_credential(
        SUPPORTED_ID
    )
    assert presence_error.status is CredentialStoreStatus.BACKEND_ERROR
    assert save_error.status is CredentialStoreStatus.BACKEND_ERROR
    assert clear_error.status is CredentialStoreStatus.BACKEND_ERROR
    _assert_secret_not_exposed(presence_error)
    _assert_secret_not_exposed(save_error)
    _assert_secret_not_exposed(clear_error)


def test_system_keyring_save_update_clear_and_missing() -> None:
    fake = FakeKeyring()
    store = SystemKeyringCredentialStore(keyring_module=fake)
    locator = credential_locator_for_id(SUPPORTED_ID)
    assert locator is not None

    first = store.save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    assert first.status is CredentialStoreStatus.SAVED
    _assert_fake_keyring_value(
        fake,
        locator.service_name,
        locator.account_name,
        SECRET_SENTINEL,
    )
    assert fake.calls == ["get_password", "set_password"]
    _assert_secret_not_exposed(first)

    present = store.credential_present(SUPPORTED_ID)
    assert present.status is CredentialStoreStatus.PRESENT
    _assert_secret_not_exposed(present)

    second = store.save_credential(SUPPORTED_ID, "replacement")
    assert second.status is CredentialStoreStatus.UPDATED
    _assert_fake_keyring_value(
        fake,
        locator.service_name,
        locator.account_name,
        "replacement",
    )
    _assert_secret_not_exposed(second)

    cleared = store.clear_credential(SUPPORTED_ID)
    assert cleared.status is CredentialStoreStatus.CLEARED
    assert cleared.changed is True
    assert (locator.service_name, locator.account_name) not in fake.store
    _assert_secret_not_exposed(cleared)

    absent = store.credential_present(SUPPORTED_ID)
    assert absent.status is CredentialStoreStatus.NOT_FOUND
    _assert_secret_not_exposed(absent)

    missing = store.clear_credential(SUPPORTED_ID)
    assert missing.status is CredentialStoreStatus.NOT_FOUND
    assert missing.changed is False
    _assert_secret_not_exposed(missing)


def test_system_keyring_unavailable_and_failures_are_safe() -> None:
    factory_calls: list[str] = []

    def unavailable_factory() -> object:
        factory_calls.append("called")
        raise ImportError(SECRET_SENTINEL)

    store = SystemKeyringCredentialStore(
        keyring_module_factory=unavailable_factory,
    )
    assert factory_calls == []
    unavailable = store.save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    assert factory_calls == ["called"]
    assert unavailable.status is CredentialStoreStatus.BACKEND_UNAVAILABLE
    _assert_secret_not_exposed(unavailable)

    set_failure = SystemKeyringCredentialStore(
        keyring_module=FakeKeyring(fail_set=True),
    ).save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    assert set_failure.status is CredentialStoreStatus.BACKEND_ERROR
    _assert_secret_not_exposed(set_failure)

    get_failure = SystemKeyringCredentialStore(
        keyring_module=FakeKeyring(fail_get=True),
    ).save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    assert get_failure.status is CredentialStoreStatus.BACKEND_ERROR
    _assert_secret_not_exposed(get_failure)

    presence_failure = SystemKeyringCredentialStore(
        keyring_module=FakeKeyring(fail_get=True),
    ).credential_present(SUPPORTED_ID)
    assert presence_failure.status is CredentialStoreStatus.BACKEND_ERROR
    _assert_secret_not_exposed(presence_failure)

    delete_failure = SystemKeyringCredentialStore(
        keyring_module=FakeKeyring(fail_delete=True),
    ).clear_credential(SUPPORTED_ID)
    assert delete_failure.status is CredentialStoreStatus.BACKEND_ERROR
    _assert_secret_not_exposed(delete_failure)


def test_no_plaintext_fallback_environment_or_file_writes() -> None:
    source = Path("credential_store.py").read_text(encoding="utf-8")
    forbidden_fragments = (
        "settings.json",
        "SettingsManager",
        "core.settings",
        "open(",
        "Path(",
        "json.dump",
        "os.environ",
        "getenv",
        "putenv",
    )
    for fragment in forbidden_fragments:
        assert fragment not in source

    before_env = dict(os.environ)
    watched_files = (
        Path("main.py"),
        Path("core/settings.py"),
        Path("access_keys_dialog.py"),
        Path("access_keys_catalog.py"),
        Path("access_keys_view_model.py"),
    )
    before_bytes = {path: path.read_bytes() for path in watched_files}

    memory = InMemoryCredentialStore()
    memory.save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    memory.clear_credential(SUPPORTED_ID)
    keyring = SystemKeyringCredentialStore(keyring_module=FakeKeyring())
    keyring.save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    keyring.clear_credential(SUPPORTED_ID)

    assert dict(os.environ) == before_env
    assert {path: path.read_bytes() for path in watched_files} == before_bytes


def test_row2c2_integration_is_limited_to_main_and_dialog() -> None:
    main_source = Path("main.py").read_text(encoding="utf-8")
    dialog_source = Path("access_keys_dialog.py").read_text(encoding="utf-8")
    assert "SystemKeyringCredentialStore" in main_source
    assert "credential_store=credential_store" in main_source
    assert "CredentialStore" in dialog_source
    assert "save_credential" in dialog_source
    assert "clear_credential" in dialog_source

    for filename in (
        "core/settings.py",
        "access_keys_catalog.py",
        "access_keys_view_model.py",
    ):
        source = Path(filename).read_text(encoding="utf-8")
        assert "credential_store" not in source
        assert "InMemoryCredentialStore" not in source
        assert "SystemKeyringCredentialStore" not in source


def test_static_safety_and_no_import_time_keyring_call() -> None:
    source_path = Path("credential_store.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert "keyring" not in imported_roots

    module_level_calls = [
        node
        for node in tree.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    ]
    assert module_level_calls == []

    factory_calls: list[str] = []
    store = SystemKeyringCredentialStore(
        keyring_module_factory=lambda: factory_calls.append("called") or FakeKeyring()
    )
    assert factory_calls == []
    assert repr(store) == "SystemKeyringCredentialStore()"
    result = store.save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    assert factory_calls == ["called"]
    _assert_secret_not_exposed(result)


def test_result_objects_do_not_leak_values_or_exception_text() -> None:
    fake = FakeKeyring(fail_set=True)
    result = SystemKeyringCredentialStore(keyring_module=fake).save_credential(
        SUPPORTED_ID,
        SECRET_SENTINEL,
    )
    assert result.operation is CredentialStoreOperation.SAVE
    assert result.backend is CredentialStoreBackend.SYSTEM_KEYRING
    assert result.status is CredentialStoreStatus.BACKEND_ERROR
    _assert_secret_not_exposed(result)

    memory = InMemoryCredentialStore()
    memory.save_credential(SUPPORTED_ID, SECRET_SENTINEL)
    if SECRET_SENTINEL in repr(memory):
        raise AssertionError("secret sentinel leaked through memory repr")


def run_self_test() -> None:
    test_supported_locator_mapping_and_uniqueness()
    test_unknown_and_youtube_credentials_are_rejected()
    test_in_memory_save_overwrite_and_clear()
    test_in_memory_simulated_failures()
    test_system_keyring_save_update_clear_and_missing()
    test_system_keyring_unavailable_and_failures_are_safe()
    test_no_plaintext_fallback_environment_or_file_writes()
    test_row2c2_integration_is_limited_to_main_and_dialog()
    test_static_safety_and_no_import_time_keyring_call()
    test_result_objects_do_not_leak_values_or_exception_text()


if __name__ == "__main__":
    run_self_test()
    print("Credential store self-test passed.")
