from capture_archive_providers import (
    ARCHIVE_OPERATION_CHECK,
    ARCHIVE_OPERATION_COMMAND_PLAN,
    ARCHIVE_OPERATION_SUBMIT,
    ARCHIVE_PROVIDER_ARCHIVEBOX,
    ARCHIVE_PROVIDER_ARCHIVE_TODAY,
    ARCHIVE_PROVIDER_SCOPE,
    ARCHIVE_PROVIDER_WAYBACK,
    archive_provider_by_id,
    archive_provider_catalog_to_dict,
    available_archive_providers,
)


def test_archive_provider_catalog_matches_rev4_schema_shape() -> None:
    providers = {provider.provider_id: provider for provider in available_archive_providers()}

    assert set(providers) == {
        ARCHIVE_PROVIDER_WAYBACK,
        ARCHIVE_PROVIDER_ARCHIVE_TODAY,
        ARCHIVE_PROVIDER_ARCHIVEBOX,
    }
    assert ARCHIVE_OPERATION_CHECK in providers[ARCHIVE_PROVIDER_WAYBACK].operations
    assert "SUBMISSION_STARTED" in providers[ARCHIVE_PROVIDER_WAYBACK].statuses
    assert "WIP" in providers[ARCHIVE_PROVIDER_ARCHIVE_TODAY].statuses
    assert ARCHIVE_OPERATION_SUBMIT in providers[ARCHIVE_PROVIDER_ARCHIVEBOX].operations
    assert ARCHIVE_OPERATION_COMMAND_PLAN in providers[ARCHIVE_PROVIDER_ARCHIVEBOX].operations
    assert providers[ARCHIVE_PROVIDER_ARCHIVE_TODAY].challenge_mode == "user_handoff"

    data = archive_provider_catalog_to_dict()
    assert data["scope"] == ARCHIVE_PROVIDER_SCOPE
    assert data["archive_provider_count"] == 3
    assert data["archive_providers"][0]["schema_version"] == "rev4.0"
    assert "no live archive" in data["scope"]


def test_archive_provider_lookup_is_exact() -> None:
    assert archive_provider_by_id("wayback").display_name == "Internet Archive Wayback Machine"
    assert archive_provider_by_id("archive_today").provider_id == ARCHIVE_PROVIDER_ARCHIVE_TODAY
    assert archive_provider_by_id(" archive_today ") is None
    assert archive_provider_by_id("wayback_live") is None


def run_self_test() -> None:
    test_archive_provider_catalog_matches_rev4_schema_shape()
    test_archive_provider_lookup_is_exact()


if __name__ == "__main__":
    run_self_test()
    print("Capture archive providers self-test passed.")
