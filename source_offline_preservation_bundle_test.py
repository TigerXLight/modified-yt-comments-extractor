from source_offline_preservation_bundle import (
    ArchiveProviderStatus,
    LocalPreservationBackend,
    build_default_preservation_choice_plan,
)


def test_offline_bundle_is_low_size_windows_openable_zip_contract() -> None:
    plan = build_default_preservation_choice_plan("https://news.invalid/story")
    data = plan.to_dict()
    bundle = data["offline_bundle"]
    assert bundle["suggested_extension"] == ".sourceweb.zip"
    assert bundle["windows_openable_as_zip"] is True
    assert "manifest.json" in bundle["included_items"]
    assert "hashes.json" in bundle["included_items"]
    assert "credential material" in bundle["excluded_by_default"]


def test_archivebox_profiles_do_not_claim_native_windows_cli() -> None:
    plan = build_default_preservation_choice_plan("https://news.invalid/story")
    profiles = plan.archivebox_profiles
    backends = {profile.backend for profile in profiles}
    assert LocalPreservationBackend.ARCHIVEBOX_DOCKER_COMPOSE_LIGHT in backends
    assert LocalPreservationBackend.ARCHIVEBOX_WSL2_CLI_LIGHT in backends
    assert plan.to_dict()["native_windows_archivebox_not_claimed"] is True


def test_archive_today_challenge_is_not_not_found() -> None:
    plan = build_default_preservation_choice_plan("https://news.invalid/story")
    statuses = {result.provider_id: result.status for result in plan.archive_results}
    assert statuses["archive_today"] == ArchiveProviderStatus.UNKNOWN
    challenge = plan.archive_results[1]
    assert challenge.failure_is_not_proof_content_never_existed is True


def test_rendered_citation_boundary_forbids_circumvention() -> None:
    plan = build_default_preservation_choice_plan("https://video.invalid/watch")
    rendered = plan.rendered_citation
    assert rendered.user_triggered is True
    assert rendered.no_key_extraction is True
    assert rendered.no_cdm_patch is True
    assert rendered.no_license_server_impersonation is True
    assert rendered.no_hdcp_defeat is True
    assert rendered.black_or_protected_frame_stops_capture is True


def main() -> None:
    test_offline_bundle_is_low_size_windows_openable_zip_contract()
    test_archivebox_profiles_do_not_claim_native_windows_cli()
    test_archive_today_challenge_is_not_not_found()
    test_rendered_citation_boundary_forbids_circumvention()
    print("source_offline_preservation_bundle_test: OK")


if __name__ == "__main__":
    main()
