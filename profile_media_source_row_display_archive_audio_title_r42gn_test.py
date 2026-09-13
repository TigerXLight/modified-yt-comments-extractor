from profile_media_source_row_display_archive_audio_title_r42gn import (
    BBC_TWITTER_STATUS_URL,
    GLOBAL_PLAYER_LBC_EPISODE_URL,
    R42GN_PASS_STATUS,
    validate_r42gn_source_row_display_archive_audio_title,
)
from source_resource_state import (
    ARCHIVE_SERVICE_ARCHIVE_TODAY,
    ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE,
    ARCHIVE_SERVICE_WAYBACK,
    ARCHIVE_STATUS_APPROVAL_REQUIRED,
    build_source_resource_row,
)
from source_twitter_compact_row import build_twitter_compact_row_state


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_twitter_row_title_is_compact_but_settings_are_preserved() -> None:
    title = (
        '"I think it carries a real risk of increased chances of attacks on the British Jewish community." '
        "Dr Peter Prinsley tells BBC Radio 4 Today."
    )
    row = build_source_resource_row(BBC_TWITTER_STATUS_URL, title=title)
    state = build_twitter_compact_row_state(row)

    _assert(len(state.display_title) <= 72, "compact title limit")
    _assert(state.title_treatment == "compact_normal_weight_single_line", "compact title treatment")
    _assert(state.dropdown_options == ("Post", "Thread"), "post/thread settings preserved")
    _assert("media" in state.settings_keys, "media setting preserved")


def test_twitter_archive_policy_surfaces_archive_ph_and_local_without_wayback() -> None:
    row = build_source_resource_row(BBC_TWITTER_STATUS_URL)
    services = tuple(status.service_id for status in row.archive_statuses)

    _assert(ARCHIVE_SERVICE_WAYBACK not in services, "wayback omitted for x/twitter")
    _assert(ARCHIVE_SERVICE_ARCHIVE_TODAY in services, "archive.ph surfaced")
    _assert(ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE in services, "local archive surfaced")
    archive_today = next(status for status in row.archive_statuses if status.service_id == ARCHIVE_SERVICE_ARCHIVE_TODAY)
    _assert(archive_today.status == ARCHIVE_STATUS_APPROVAL_REQUIRED, "archive.ph is human/approval guarded")
    _assert("metadata-only" in row.provenance, "archive policy remains metadata-only")


def test_global_player_row_uses_cached_public_audio_title_and_method_metadata() -> None:
    row = build_source_resource_row(GLOBAL_PLAYER_LBC_EPISODE_URL)

    _assert(row.adapter_id == "webpage", "existing generic row path preserved")
    _assert("Tuesday, 08 September" in row.display_title, "cached date title")
    _assert("Nick Ferrari" in row.display_title, "cached show title")
    _assert("2Zgwfmze7Xnlafimvl5Bmhmpeb" not in row.display_title, "opaque id hidden")
    _assert("yt_dlp_python_module" in row.provenance, "R42GH backend metadata")
    _assert("py -m yt_dlp" in row.provenance, "preferred invocation metadata")
    _assert("format 0" in row.provenance, "format metadata")
    _assert("native m4a" in row.provenance, "m4a preservation metadata")
    _assert(any("did not run" in warning for warning in row.warnings), "no download/fetch warning")


def test_r42gn_report_passes_and_preserves_guardrails() -> None:
    report = validate_r42gn_source_row_display_archive_audio_title()

    _assert(report["status"] == R42GN_PASS_STATUS, "R42GN report status")
    guardrails = report["guardrails"]
    _assert(guardrails["yt_dlp_execution"] == "not_run", "yt-dlp not run")
    _assert(guardrails["archive_submission"] == "not_run", "archive submission not run")
    _assert(guardrails["source_role_assignment"] == "not_changed", "source roles not changed")
    _assert(guardrails["metadata_promotion"] == "none", "metadata not promoted")


def run_all_tests() -> None:
    test_twitter_row_title_is_compact_but_settings_are_preserved()
    test_twitter_archive_policy_surfaces_archive_ph_and_local_without_wayback()
    test_global_player_row_uses_cached_public_audio_title_and_method_metadata()
    test_r42gn_report_passes_and_preserves_guardrails()


if __name__ == "__main__":
    run_all_tests()
    print("profile_media_source_row_display_archive_audio_title_r42gn_test: PASS")
