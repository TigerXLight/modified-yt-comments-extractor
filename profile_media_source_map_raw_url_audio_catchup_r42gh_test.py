from __future__ import annotations

from profile_media_source_map_raw_url_audio_catchup_r42gh import (
    GLOBAL_PLAYER_LBC_FIXTURE_URL,
    GLOBAL_PLAYER_METHOD_METADATA,
    R42GH_PASS_STATUS,
    build_audio_catchup_export_layout,
    build_audio_catchup_plan,
    build_audio_catchup_review_strings,
    build_lbc_global_player_evidence_record,
    is_plain_machine_url,
    sample_url_inputs,
    validate_source_map_raw_url_audio_catchup,
)
from profile_media_universal_source_map_r42gg import (
    SOURCE_FAMILY_BY_ID,
    build_capture_plan,
    detect_source_family,
    sanitize_source_input,
    sanitize_source_url,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_markdown_named_and_raw_urls_normalize_to_plain_machine_urls() -> None:
    cases = {
        "https://x.com/examaddaorg?utm_source=test&s=20": "https://x.com/examaddaorg",
        "[https://x.com/examaddaorg?utm_source=test&s=20](https://x.com/examaddaorg?utm_source=test&s=20)": "https://x.com/examaddaorg",
        "[Example](https://x.com/BBCr4today/status/2097217541416308845?s=20)": "https://x.com/BBCr4today/status/2097217541416308845",
        r"https:\/\/x.com\/BBCr4today\/status\/2097217541416308845?s=20": "https://x.com/BBCr4today/status/2097217541416308845",
        "https://twitter.com/BBCr4today/status/2097217541416308845?s=20": "https://x.com/BBCr4today/status/2097217541416308845",
        "[Metro](https://metro.co.uk/example/?utm_campaign=x)": "https://metro.co.uk/example/",
    }
    for raw, expected in cases.items():
        sanitized = sanitize_source_input(raw)
        _assert(sanitized.extracted_url == expected, f"extracted mismatch {raw}: {sanitized.extracted_url}")
        _assert(sanitized.normalized_url == expected, f"normalized mismatch {raw}: {sanitized.normalized_url}")
        _assert(is_plain_machine_url(sanitized.extracted_url), f"extracted not plain {sanitized.extracted_url}")
        _assert(is_plain_machine_url(sanitized.normalized_url), f"normalized not plain {sanitized.normalized_url}")


def test_global_player_lbc_url_maps_to_public_audio_catchup_family() -> None:
    _assert(detect_source_family(GLOBAL_PLAYER_LBC_FIXTURE_URL) == "public_broadcast_catchup_audio", "family detection")
    plan = build_capture_plan(GLOBAL_PLAYER_LBC_FIXTURE_URL)
    _assert(plan.family_id == "public_broadcast_catchup_audio", "capture plan family")
    family = SOURCE_FAMILY_BY_ID["public_broadcast_catchup_audio"]
    _assert("global_player_audio" in family.platform_aliases, "global player alias")
    _assert(family.method_statuses["metadata"] == "public_download_capable_when_source_route_works", "metadata method status")
    _assert(family.method_statuses["rss_enclosure"] == "not_required_for_global_player_episode", "rss status")


def test_global_player_method_plan_records_python_module_ytdlp_and_native_m4a_policy() -> None:
    plan = build_audio_catchup_plan()
    metadata = plan["method_metadata"]
    _assert(metadata["backend_id"] == "yt_dlp_python_module", "backend id")
    _assert(metadata["preferred_invocation"] == "py -m yt_dlp", "preferred invocation")
    _assert(metadata["avoid_plain_executable_when_path_stale"] is True, "avoid stale executable")
    _assert(metadata["format_probe_required"] is True, "format probe")
    _assert(metadata["native_format_id_observed"] == "0", "native format")
    _assert(metadata["preserve_native_m4a"] is True, "preserve m4a")
    _assert(metadata["write_info_json"] is True and metadata["write_description"] is True and metadata["write_thumbnail"] is True, "sidecars")
    _assert(metadata["no_conversion_for_preservation"] is True, "no conversion")


def test_audio_evidence_export_shape_and_review_strings() -> None:
    record = build_lbc_global_player_evidence_record()
    layout = build_audio_catchup_export_layout("lbc", "20260912T000000Z")
    strings = build_audio_catchup_review_strings(record)
    _assert(layout["manifest"].endswith("manifest.json"), "manifest layout")
    _assert(layout["media_original"].endswith("media/original.m4a"), "media layout")
    _assert(layout["sidecars"]["info_json"].endswith("sidecars/info.json"), "info sidecar")
    for expected in (
        record.canonical_url,
        record.episode_id,
        record.programme_or_show,
        record.station_or_publisher,
        record.episode_title,
        "original.m4a",
        "sidecars/info.json",
        "sidecars/description.txt",
        record.source_fingerprint,
    ):
        _assert(expected in strings, f"missing review string {expected}")


def test_r42gh_report_fails_on_markdown_urls_and_passes_current_samples() -> None:
    for raw in sample_url_inputs():
        plan = build_capture_plan(raw)
        _assert(is_plain_machine_url(plan.sanitized_input.extracted_url), f"sample extracted not plain {plan.sanitized_input.extracted_url}")
        _assert(is_plain_machine_url(plan.sanitized_input.normalized_url), f"sample normalized not plain {plan.sanitized_input.normalized_url}")
        _assert("](" not in plan.sanitized_input.extracted_url, "markdown leaked into extracted URL")
    report = validate_source_map_raw_url_audio_catchup(".")
    _assert(report.status == R42GH_PASS_STATUS, report.status)
    names = {check["name"]: check["status"] for check in report.checks}
    _assert(names["sample_plan_urls_are_plain_not_markdown"] == "pass", "plain URL report check")


def test_r42gg_and_protected_imports_remain_compatible() -> None:
    from profile_media_bbc_podcast_adapter_r42ge import validate_bbc_podcast_adapter
    from profile_media_source_family_matrix_r42gc import classify_source_family
    from profile_media_twitter_x_adapter_closeout_r42gf import canonical_twitter_x_url

    _assert(classify_source_family("https://x.com/example/status/123").family_id == "twitter_x", "R42GC route")
    _assert(canonical_twitter_x_url("https://twitter.com/example/status/123") == "https://twitter.com/example/status/123", "R42GF unchanged")
    _assert(validate_bbc_podcast_adapter(source_root=".").marker, "R42GE import")
    _assert(sanitize_source_url("https://open.spotify.com/track/123") == "https://open.spotify.com/track/123", "Spotify DRM URL still normalizes")


def run_tests() -> None:
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"PASS {name}")


if __name__ == "__main__":
    run_tests()
