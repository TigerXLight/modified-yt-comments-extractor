from capture_status import (
    ARCHIVE_STATUS_CODES,
    CAPTURE_STATUS_CODES,
    CAPTURE_STATUS_SUCCESS,
    COMPLETENESS_CODES,
    COMPLETENESS_COMPLETE,
    FIDELITY_CODES,
    FIDELITY_FAITHFUL,
    OPERATIONAL_STATUS_LABELS,
    OPERATIONAL_STATUS_LOCALHOST_FIXTURE_TESTED,
    OPERATIONAL_STATUS_MODEL_ONLY,
    capture_status_catalog_to_dict,
    is_known_capture_status,
    is_known_completeness_status,
    is_known_fidelity_status,
)


def test_rev4_status_catalog_contains_required_statuses() -> None:
    assert OPERATIONAL_STATUS_MODEL_ONLY in OPERATIONAL_STATUS_LABELS
    assert OPERATIONAL_STATUS_LOCALHOST_FIXTURE_TESTED in OPERATIONAL_STATUS_LABELS
    assert CAPTURE_STATUS_SUCCESS in CAPTURE_STATUS_CODES
    assert COMPLETENESS_COMPLETE in COMPLETENESS_CODES
    assert FIDELITY_FAITHFUL in FIDELITY_CODES
    assert "CHALLENGE_REQUIRES_USER" in CAPTURE_STATUS_CODES
    assert "DEPENDENCY_MISSING" in CAPTURE_STATUS_CODES
    assert "DNS_FAILURE" in ARCHIVE_STATUS_CODES


def test_status_catalog_to_dict_is_deterministic_and_primitive() -> None:
    data = capture_status_catalog_to_dict()

    assert data == capture_status_catalog_to_dict()
    assert data["operational_statuses"][0] == OPERATIONAL_STATUS_MODEL_ONLY
    assert data["capture_statuses"] == list(CAPTURE_STATUS_CODES)
    assert data["completeness_statuses"] == list(COMPLETENESS_CODES)
    assert data["fidelity_statuses"] == list(FIDELITY_CODES)


def test_status_lookup_helpers_are_strict_and_local_only() -> None:
    assert is_known_capture_status("success") is True
    assert is_known_completeness_status("complete") is True
    assert is_known_fidelity_status("faithful") is True
    assert is_known_capture_status("download_from_real_site") is False
    assert is_known_completeness_status("") is False
    assert is_known_fidelity_status("requests.get") is False


def run_self_test() -> None:
    test_rev4_status_catalog_contains_required_statuses()
    test_status_catalog_to_dict_is_deterministic_and_primitive()
    test_status_lookup_helpers_are_strict_and_local_only()


if __name__ == "__main__":
    run_self_test()
    print("Capture status self-test passed.")
