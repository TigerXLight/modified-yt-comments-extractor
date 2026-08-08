from access_keys_catalog import build_default_access_keys_catalog
from access_provider_gate import (
    access_provider_gate_summary_to_json,
    build_access_provider_gate_summary,
    validate_access_provider_gate_summary,
)


def test_access_provider_gate_summary_is_non_secret_and_approval_required() -> None:
    summary = build_access_provider_gate_summary(build_default_access_keys_catalog())
    data = summary.to_dict()

    assert summary.record_count > 0
    assert summary.asr_provider_count > 0
    assert summary.source_adapter_count > 0
    assert summary.archive_service_count > 0
    assert summary.approval_required_count > 0
    assert summary.review_status == "USER_REVIEW_REQUIRED"
    assert summary.credential_value_included is False
    assert summary.credential_lookup_performed is False
    assert summary.provider_call_performed is False
    assert summary.browser_profile_access_performed is False
    assert summary.archive_provider_call_performed is False
    assert summary.download_performed is False
    assert summary.automatic_classification is False
    assert all(record["credential_value_included"] is False for record in data["records"])
    assert any(record["entry_id"] == "source:youtube" for record in data["records"])
    assert any(record["entry_id"] == "asr:elevenlabs_scribe" for record in data["records"])
    validate_access_provider_gate_summary(data)

    rendered = access_provider_gate_summary_to_json(summary)
    assert rendered == access_provider_gate_summary_to_json(summary)
    for forbidden in ("api_key_value", "Authorization", "Cookie", "C:\\Users\\fahad"):
        assert forbidden not in rendered


def test_access_provider_gate_validation_rejects_provider_calls() -> None:
    data = build_access_provider_gate_summary(build_default_access_keys_catalog()).to_dict()
    data["provider_call_performed"] = True
    try:
        validate_access_provider_gate_summary(data)
    except ValueError as error:
        assert "provider_call_performed" in str(error)
    else:
        raise AssertionError("Provider-call claim should be rejected")


def run_self_test() -> None:
    test_access_provider_gate_summary_is_non_secret_and_approval_required()
    test_access_provider_gate_validation_rejects_provider_calls()


if __name__ == "__main__":
    run_self_test()
    print("Access provider gate self-test passed.")
