from __future__ import annotations

import ast
import json
import os
from pathlib import Path

from access_keys_catalog import build_default_access_keys_catalog_bundle
from access_keys_view_model import build_access_keys_manager_view
from credential_consumption import (
    CloudASRCredentialConsumer,
    CredentialConsumptionProvenance,
    CredentialConsumptionStatus,
    credential_consumption_result_contains_forbidden_fields,
)
from credential_runtime_status import (
    LocalCredentialStatusProvider,
    apply_runtime_credential_statuses,
)
from credential_store import (
    SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS,
    YOUTUBE_CREDENTIAL_ID,
    InMemoryCredentialStore,
    credential_locator_for_id,
)


SECRET_SENTINEL = "ROW2C3-SECRET-MUST-NOT-APPEAR"
ALT_SECRET_SENTINEL = "ROW2C3-ALT-SECRET-MUST-NOT-APPEAR"
SUPPORTED_ID = "elevenlabs_scribe_api_key"


class FakeKeyring:
    def __init__(self, *, fail_get: bool = False) -> None:
        self.fail_get = fail_get
        self.store: dict[tuple[str, str], str] = {}
        self.calls: list[tuple[str, str, str]] = []

    def get_password(self, service_name: str, account_name: str) -> str | None:
        self.calls.append(("get_password", service_name, account_name))
        if self.fail_get:
            raise RuntimeError(SECRET_SENTINEL)
        return self.store.get((service_name, account_name))


def _store_secret(
    fake: FakeKeyring,
    credential_id: str,
    secret: str,
) -> None:
    locator = credential_locator_for_id(credential_id)
    assert locator is not None
    fake.store[(locator.service_name, locator.account_name)] = secret


def _assert_secret_not_exposed(result: object) -> None:
    blob = repr(result) + json.dumps(result.to_dict(), sort_keys=True)
    if SECRET_SENTINEL in blob or ALT_SECRET_SENTINEL in blob:
        raise AssertionError("secret sentinel leaked through public result output")
    assert not credential_consumption_result_contains_forbidden_fields(
        result.to_dict()
    )


def _consumer(
    *,
    fake: FakeKeyring | None = None,
    environ: dict[str, str] | None = None,
) -> CloudASRCredentialConsumer:
    return CloudASRCredentialConsumer(
        keyring_module=fake if fake is not None else FakeKeyring(),
        environ=environ or {},
    )


def test_keyring_secret_is_consumed_only_inside_callback() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_ID, SECRET_SENTINEL)
    seen: list[str] = []

    result = _consumer(fake=fake).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: seen.append(credential),
    )

    assert result.status is CredentialConsumptionStatus.CONSUMED
    assert result.provenance is CredentialConsumptionProvenance.SECURE_KEYRING
    assert result.callback_invoked is True
    assert result.action_succeeded is True
    assert seen == [SECRET_SENTINEL]
    assert len(fake.calls) == 1
    _assert_secret_not_exposed(result)


def test_environment_secret_is_consumed_when_keyring_missing() -> None:
    seen: list[str] = []
    result = _consumer(
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL}
    ).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: seen.append(credential),
    )

    assert result.status is CredentialConsumptionStatus.CONSUMED
    assert result.provenance is CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE
    assert seen == [SECRET_SENTINEL]
    _assert_secret_not_exposed(result)


def test_keyring_takes_precedence_over_environment() -> None:
    fake = FakeKeyring()
    _store_secret(fake, SUPPORTED_ID, SECRET_SENTINEL)
    seen: list[str] = []

    result = _consumer(
        fake=fake,
        environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
    ).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: seen.append(credential),
    )

    assert result.status is CredentialConsumptionStatus.CONSUMED
    assert result.provenance is CredentialConsumptionProvenance.SECURE_KEYRING
    assert seen == [SECRET_SENTINEL]
    _assert_secret_not_exposed(result)


def test_keyring_read_error_allows_environment_fallback() -> None:
    seen: list[str] = []
    result = _consumer(
        fake=FakeKeyring(fail_get=True),
        environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
    ).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: seen.append(credential),
    )

    assert result.status is CredentialConsumptionStatus.CONSUMED
    assert result.provenance is CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE
    assert seen == [ALT_SECRET_SENTINEL]
    _assert_secret_not_exposed(result)


def test_empty_and_whitespace_secure_values_are_invalid() -> None:
    for stored_value in ("", "   "):
        fake = FakeKeyring()
        _store_secret(fake, SUPPORTED_ID, stored_value)
        invoked: list[str] = []

        result = _consumer(
            fake=fake,
            environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
        ).consume_credential(
            SUPPORTED_ID,
            action=lambda credential: invoked.append(credential),
        )

        assert result.status is CredentialConsumptionStatus.STORAGE_ERROR
        assert result.provenance is CredentialConsumptionProvenance.SECURE_KEYRING
        assert result.safe_diagnostic == "invalid_secure_credential_value"
        assert result.callback_invoked is False
        assert invoked == []
        _assert_secret_not_exposed(result)


def test_missing_and_unavailable_do_not_invoke_callback() -> None:
    invoked: list[str] = []

    missing = _consumer().consume_credential(
        SUPPORTED_ID,
        action=lambda credential: invoked.append(credential),
    )
    assert missing.status is CredentialConsumptionStatus.MISSING
    assert missing.callback_invoked is False

    factory_calls: list[str] = []

    def unavailable_factory() -> object:
        factory_calls.append("called")
        raise ImportError(SECRET_SENTINEL)

    consumer = CloudASRCredentialConsumer(
        keyring_module_factory=unavailable_factory,
        environ={},
    )
    assert factory_calls == []
    unavailable = consumer.consume_credential(
        SUPPORTED_ID,
        action=lambda credential: invoked.append(credential),
    )
    assert factory_calls == ["called"]
    assert unavailable.status is CredentialConsumptionStatus.BACKEND_UNAVAILABLE
    assert invoked == []
    _assert_secret_not_exposed(missing)
    _assert_secret_not_exposed(unavailable)


def test_backend_unavailable_allows_environment_fallback() -> None:
    factory_calls: list[str] = []
    seen: list[str] = []

    def unavailable_factory() -> object:
        factory_calls.append("called")
        raise ImportError(SECRET_SENTINEL)

    result = CloudASRCredentialConsumer(
        keyring_module_factory=unavailable_factory,
        environ={"ELEVENLABS_API_KEY": ALT_SECRET_SENTINEL},
    ).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: seen.append(credential),
    )

    assert factory_calls == ["called"]
    assert result.status is CredentialConsumptionStatus.CONSUMED
    assert result.provenance is CredentialConsumptionProvenance.ENVIRONMENT_VARIABLE
    assert seen == [ALT_SECRET_SENTINEL]
    _assert_secret_not_exposed(result)


def test_empty_environment_values_are_missing() -> None:
    invoked: list[str] = []

    result = _consumer(
        environ={"ELEVENLABS_API_KEY": "   "}
    ).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: invoked.append(credential),
    )

    assert result.status is CredentialConsumptionStatus.MISSING
    assert result.callback_invoked is False
    assert invoked == []
    _assert_secret_not_exposed(result)


def test_backend_read_error_without_environment_is_safe() -> None:
    result = _consumer(fake=FakeKeyring(fail_get=True)).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: None,
    )
    assert result.status is CredentialConsumptionStatus.STORAGE_ERROR
    assert result.safe_diagnostic == "secure_credential_read_error"
    assert result.callback_invoked is False
    _assert_secret_not_exposed(result)


def test_unknown_youtube_and_provider_shapes_are_rejected() -> None:
    unknown = _consumer().consume_credential(
        "unknown_provider",
        action=lambda credential: None,
    )
    youtube = _consumer().consume_credential(
        YOUTUBE_CREDENTIAL_ID,
        action=lambda credential: None,
    )
    local_provider = _consumer().consume_provider_credential(
        "whisper_cpp_vulkan_large_v3_turbo",
        action=lambda credential: None,
    )
    unmapped_provider = _consumer().consume_provider_credential(
        "google_stt_latest_long",
        action=lambda credential: None,
    )
    compound_env = _consumer(
        environ={"GOOGLE_APPLICATION_CREDENTIALS": SECRET_SENTINEL}
    ).consume_credential(
        "google_stt_provider_credentials",
        action=lambda credential: None,
    )

    assert unknown.status is CredentialConsumptionStatus.UNKNOWN_CREDENTIAL
    assert youtube.status is CredentialConsumptionStatus.YOUTUBE_CREDENTIAL_REJECTED
    assert local_provider.status is CredentialConsumptionStatus.CREDENTIAL_NOT_REQUIRED
    assert unmapped_provider.status is CredentialConsumptionStatus.NOT_CONSUMABLE
    assert compound_env.status is CredentialConsumptionStatus.NOT_CONSUMABLE
    for result in (
        unknown,
        youtube,
        local_provider,
        unmapped_provider,
        compound_env,
    ):
        assert result.callback_invoked is False
        _assert_secret_not_exposed(result)


def test_action_errors_and_return_values_are_not_exposed() -> None:
    def failing_action(credential: str) -> None:
        raise RuntimeError(SECRET_SENTINEL)

    error = _consumer(
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL}
    ).consume_credential(
        SUPPORTED_ID,
        action=failing_action,
    )
    assert error.status is CredentialConsumptionStatus.ACTION_ERROR
    assert error.callback_invoked is True
    assert error.action_succeeded is False
    _assert_secret_not_exposed(error)

    returned = _consumer(
        environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL}
    ).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: ALT_SECRET_SENTINEL,
    )
    assert returned.status is CredentialConsumptionStatus.CONSUMED
    _assert_secret_not_exposed(returned)


def test_process_control_exceptions_are_not_swallowed() -> None:
    for exception_type in (KeyboardInterrupt, SystemExit, GeneratorExit):
        try:
            _consumer(
                environ={"ELEVENLABS_API_KEY": SECRET_SENTINEL}
            ).consume_credential(
                SUPPORTED_ID,
                action=lambda credential, exc=exception_type: (_ for _ in ()).throw(exc()),
            )
        except exception_type:
            pass
        else:
            raise AssertionError("process-control exception was swallowed")


def test_construction_repr_and_status_view_do_not_touch_keyring() -> None:
    fake = FakeKeyring()
    consumer = CloudASRCredentialConsumer(keyring_module=fake, environ={})
    assert repr(consumer) == "CloudASRCredentialConsumer()"
    assert fake.calls == []

    store = InMemoryCredentialStore()
    statuses = LocalCredentialStatusProvider(
        settings_manager=None,
        youtube_configured=False,
        environ={},
        credential_store=store,
    ).read_statuses()
    bundle = build_default_access_keys_catalog_bundle()
    catalog = apply_runtime_credential_statuses(bundle.catalog, statuses)
    view = build_access_keys_manager_view(catalog, layouts=bundle.layouts)
    assert view.visible_entry_count == len(bundle.catalog.entries)
    assert fake.calls == []


def test_supported_ids_are_deterministic_and_environment_is_not_mutated() -> None:
    before_env = dict(os.environ)
    local_env = {"ELEVENLABS_API_KEY": SECRET_SENTINEL}
    before_local_env = dict(local_env)

    for credential_id in SUPPORTED_CLOUD_ASR_CREDENTIAL_IDS:
        assert credential_locator_for_id(credential_id) is not None

    result = _consumer(environ=local_env).consume_credential(
        SUPPORTED_ID,
        action=lambda credential: None,
    )
    assert result.status is CredentialConsumptionStatus.CONSUMED
    assert local_env == before_local_env
    assert dict(os.environ) == before_env
    _assert_secret_not_exposed(result)


def test_static_safety_no_provider_imports_or_network_calls() -> None:
    source_path = Path("credential_consumption.py")
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
    assert imported_roots.isdisjoint(
        {
            "keyring",
            "requests",
            "urllib",
            "httpx",
            "aiohttp",
            "socket",
            "subprocess",
            "openai",
            "elevenlabs",
            "deepgram",
            "speechmatics",
        }
    )
    assert "print(" not in source
    assert "logging" not in source
    assert "set_password(" not in source
    assert "delete_password(" not in source
    assert "putenv" not in source
    assert "environ[" not in source
    assert "requests." not in source
    assert "urllib.request" not in source


def run_self_test() -> None:
    test_keyring_secret_is_consumed_only_inside_callback()
    test_environment_secret_is_consumed_when_keyring_missing()
    test_keyring_takes_precedence_over_environment()
    test_keyring_read_error_allows_environment_fallback()
    test_empty_and_whitespace_secure_values_are_invalid()
    test_missing_and_unavailable_do_not_invoke_callback()
    test_backend_unavailable_allows_environment_fallback()
    test_empty_environment_values_are_missing()
    test_backend_read_error_without_environment_is_safe()
    test_unknown_youtube_and_provider_shapes_are_rejected()
    test_action_errors_and_return_values_are_not_exposed()
    test_process_control_exceptions_are_not_swallowed()
    test_construction_repr_and_status_view_do_not_touch_keyring()
    test_supported_ids_are_deterministic_and_environment_is_not_mutated()
    test_static_safety_no_provider_imports_or_network_calls()


if __name__ == "__main__":
    run_self_test()
    print("Credential consumption self-test passed.")
