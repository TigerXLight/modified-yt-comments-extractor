from __future__ import annotations

from profile_media_universal_source_map_r42gg import (
    METHOD_DIMENSIONS,
    R42GG_PASS_STATUS,
    SOURCE_FAMILY_BY_ID,
    SOURCE_GROUPS,
    SOURCE_MAP_FAMILIES,
    STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    STATUS_PROHIBITED_NO_BYPASS,
    STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
    STATUS_RATE_LIMIT_PAUSE_RECOVERY,
    STATUS_REVIEW_REQUIRED,
    TWITTER_X_DYNAMIC_BENCHMARK,
    EvidenceRecord,
    build_capture_plan,
    build_review_strings,
    build_timeline_export_layout,
    detect_source_family,
    render_single_post_card,
    sanitize_source_input,
    sanitize_source_inputs,
    sanitize_source_url,
    validate_universal_source_map,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_universal_source_map_covers_required_source_groups_and_platforms() -> None:
    covered_groups = {group for family in SOURCE_MAP_FAMILIES for group in family.source_groups}
    aliases = {alias for family in SOURCE_MAP_FAMILIES for alias in family.platform_aliases}
    _assert(set(SOURCE_GROUPS).issubset(covered_groups), "all handoff source groups must be represented")
    for alias in (
        "youtube",
        "x.com",
        "twitter.com",
        "instagram",
        "tiktok",
        "twitch",
        "vimeo",
        "reddit",
        "quora",
        "linkedin",
        "slack",
        "podcasts.apple.com",
        "open.spotify.com/episode",
        "web.archive.org",
        "archive.ph",
        "generic_article",
        "source_export",
    ):
        _assert(alias in aliases, f"missing platform alias {alias}")


def test_every_family_has_explicit_method_registry_statuses() -> None:
    expected = set(METHOD_DIMENSIONS)
    for family in SOURCE_MAP_FAMILIES:
        _assert(set(family.method_statuses) == expected, f"{family.family_id} method dimensions incomplete")
        _assert(all(family.method_statuses[dimension] for dimension in METHOD_DIMENSIONS), f"{family.family_id} has blank status")


def test_podcasts_are_public_download_capable_when_source_route_works() -> None:
    apple = SOURCE_FAMILY_BY_ID["apple_podcasts"]
    spotify_podcast = SOURCE_FAMILY_BY_ID["spotify_podcast"]
    spotify_music = SOURCE_FAMILY_BY_ID["spotify_music_drm"]
    for family in (apple, spotify_podcast):
        _assert(
            family.method_statuses["media_download_materialization"] == STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            f"{family.family_id} must not be metadata-only by default",
        )
        _assert(
            family.method_statuses["rss_enclosure"] == STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN
            or family.method_statuses["yt_dlp"] == STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN,
            f"{family.family_id} needs a public-source route slot",
        )
    _assert(
        spotify_music.method_statuses["unsupported_prohibited_no_bypass"] == STATUS_PROHIBITED_NO_BYPASS,
        "Spotify music/DRM must remain unsupported/prohibited",
    )


def test_twitter_x_exposes_dynamic_discovery_rate_limit_and_import_slots() -> None:
    twitter = SOURCE_FAMILY_BY_ID["twitter_x"]
    _assert(twitter.method_statuses["rate_limit_pause_recovery"] == STATUS_RATE_LIMIT_PAUSE_RECOVERY, "rate-limit slot missing")
    _assert(twitter.method_statuses["local_exporter_import"], "local exporter slot missing")
    _assert(twitter.method_statuses["extension_manual_receipt_import"], "manual receipt slot missing")
    _assert(twitter.method_statuses["media_discovery"] == STATUS_PUBLIC_DOWNLOAD_CAPABLE_WHEN_PROVEN, "media discovery slot missing")
    _assert(TWITTER_X_DYNAMIC_BENCHMARK["url"] == "https://x.com/examaddaorg", "benchmark URL changed")
    _assert(TWITTER_X_DYNAMIC_BENCHMARK["hard_coded_record_limit"] is None, "benchmark must not become a hard limit")


def test_url_sanitizer_handles_markdown_wrappers_tracking_and_twitter_normalization() -> None:
    sanitized = sanitize_source_url(r"[post](https://twitter.com/example/status/123?utm_source=x&ref_src=twsrc%5Etfw&s=20)")
    _assert(sanitized == "https://x.com/example/status/123", sanitized)
    escaped = sanitize_source_input(r"https://x.com/example\_name/status/456,")
    _assert(escaped.normalized_url == "https://x.com/example_name/status/456", escaped.normalized_url)
    batch = sanitize_source_inputs("1. [a](https://metro.co.uk/story/?utm_campaign=x)\n<https://x.com/a/status/1>.\n")
    _assert(len(batch) == 2, "TXT line sanitizer should find two URLs")
    _assert(batch[0].normalized_url == "https://metro.co.uk/story", batch[0].normalized_url)
    _assert(batch[1].normalized_url == "https://x.com/a/status/1", batch[1].normalized_url)


def test_family_detection_and_capture_plan_preserve_existing_route_intent() -> None:
    _assert(detect_source_family("https://x.com/example/status/123") == "twitter_x", "X family")
    _assert(detect_source_family("https://podcasts.apple.com/gb/podcast/example/id1") == "apple_podcasts", "Apple family")
    _assert(detect_source_family("https://open.spotify.com/track/abc") == "spotify_music_drm", "Spotify DRM family")
    _assert(detect_source_family("https://web.archive.org/web/20260717224516/https://metro.co.uk/x") == "archive_preservation", "archive family")
    plan = build_capture_plan("https://x.com/examaddaorg?utm_medium=test")
    _assert(plan.family_id == "twitter_x", "capture plan family")
    _assert(plan.sanitized_input.normalized_url == "https://x.com/examaddaorg", "capture plan normalized URL")
    _assert("rate_limit_pause_recovery" in plan.planned_dimensions, "X plan should include rate-limit slot")


def test_canonical_evidence_record_review_strings_and_export_layout() -> None:
    record = EvidenceRecord(
        family_id="twitter_x",
        source_url="https://x.com/example/status/123",
        canonical_url="https://x.com/example/status/123",
        raw_url="https://twitter.com/example/status/123?s=20",
        normalized_url="https://x.com/example/status/123",
        display_name="Example Account",
        handle="@example",
        post_id="123",
        text_body="A compact post body for review matching.",
        created_at_text="2026-09-12 10:00 UTC",
        views="100",
        comments="2",
        reposts="3",
        likes="4",
        bookmarks="5",
        capture_time="2026-09-12T10:05:00Z",
        media_folder="posts/123/media",
        comments_folder="posts/123/comments",
        replies_folder="posts/123/replies",
        media_relative_paths=("posts/123/media/image1.jpg",),
    )
    strings = build_review_strings(record)
    for expected in (
        "https://x.com/example/status/123",
        "@example",
        "Example Account",
        "123",
        "A compact post body for review matching.",
        "views 100 comments 2 reposts 3 likes 4 bookmarks 5",
        "posts/123/media/image1.jpg",
    ):
        _assert(expected in strings, f"missing review string {expected}")
    card = render_single_post_card(record)
    _assert("Source fingerprint" in card and "Review strings" in card, "post card missing evidence/export fields")
    layout = build_timeline_export_layout("twitter_x", "example", "20260912T100500Z")
    _assert(layout["manifest"].endswith("manifest.json"), "manifest path")
    _assert(layout["post_template"]["media_dir"].endswith("posts/<post_id>/media/"), "media folder path")


def test_metadata_only_and_review_required_records_do_not_promote_evidence_or_roles() -> None:
    web = SOURCE_FAMILY_BY_ID["instagram"]
    _assert(web.source_role_effect == "none_registry_only", "registry must not mutate source roles")
    _assert(web.method_statuses["metadata"] in {STATUS_REVIEW_REQUIRED, STATUS_METADATA_ONLY_UNTIL_CAPTURED}, "metadata status")
    report = validate_universal_source_map(".")
    _assert(report.status == R42GG_PASS_STATUS, "validation report should pass")
    _assert("no source-role" in report.side_effect_boundary, "source-role guardrail missing")


def test_existing_r42gc_r42gf_r42ge_r42gd_routes_still_import() -> None:
    from profile_media_bbc_podcast_adapter_r42ge import validate_bbc_podcast_adapter
    from profile_media_generic_article_lane_validation_r42gd import validate_generic_article_lane
    from profile_media_source_family_matrix_r42gc import classify_source_family
    from profile_media_twitter_x_adapter_closeout_r42gf import canonical_twitter_x_url

    _assert(classify_source_family("https://x.com/example/status/123").family_id == "twitter_x", "R42GC X route")
    _assert(canonical_twitter_x_url("https://twitter.com/example/status/123") == "https://twitter.com/example/status/123", "R42GF canonical remains unchanged")
    _assert(validate_bbc_podcast_adapter(source_root=".").marker, "R42GE report import")
    _assert(validate_generic_article_lane(".").marker, "R42GD report import")


def run_tests() -> None:
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"PASS {name}")


if __name__ == "__main__":
    run_tests()
