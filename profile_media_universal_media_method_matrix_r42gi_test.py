from __future__ import annotations

from profile_media_source_map_raw_url_audio_catchup_r42gh import GLOBAL_PLAYER_LBC_FIXTURE_URL, R42GH_PASS_STATUS, validate_source_map_raw_url_audio_catchup
from profile_media_universal_media_method_matrix_r42gi import (
    DISCOVERY_METHODS,
    FAST_QUEUE_POLICY,
    MATERIALIZATION_PLAN_SCHEMA_FIELDS,
    MEDIA_CANDIDATE_SCHEMA_FIELDS,
    MEDIA_KINDS,
    MEDIA_METHOD_SLOTS,
    MEDIA_ROLES,
    R42GI_PASS_STATUS,
    STATUS_METADATA_ONLY_UNTIL_CAPTURED,
    STATUS_REVIEW_REQUIRED,
    build_generic_article_export_layout,
    build_generic_article_sample_media_candidate,
    build_global_player_materialization_plan,
    build_global_player_media_candidate,
    build_public_audio_export_layout,
    build_sample_candidates,
    build_sample_plans,
    build_twitter_sample_media_candidate,
    validate_universal_media_method_matrix,
)
from profile_media_universal_source_map_r42gg import sanitize_source_url


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_taxonomies_include_required_media_kinds_methods_roles() -> None:
    for item in ("image", "video", "audio", "broadcast_catchup_audio", "rss_enclosure", "sidecar_metadata", "page_snapshot"):
        _assert(item in MEDIA_KINDS, f"missing media kind {item}")
    for item in ("dom_img_src", "api3128_jdownloader", "yt_dlp_python_module", "browser_network_observed_media", "screenshot_capture"):
        _assert(item in DISCOVERY_METHODS, f"missing discovery method {item}")
    for item in ("primary_post_media", "article_body_media", "broadcast_episode_audio", "metadata_sidecar", "manual_receipt_file"):
        _assert(item in MEDIA_ROLES, f"missing media role {item}")


def test_candidate_and_plan_schema_fields_are_complete() -> None:
    from profile_media_universal_media_method_matrix_r42gi import MediaCandidate, MediaMaterializationPlan

    _assert(set(MEDIA_CANDIDATE_SCHEMA_FIELDS).issubset(set(MediaCandidate.__dataclass_fields__)), "candidate schema fields")
    _assert(set(MATERIALIZATION_PLAN_SCHEMA_FIELDS).issubset(set(MediaMaterializationPlan.__dataclass_fields__)), "plan schema fields")


def test_global_player_fixture_and_public_audio_plan_are_preserved() -> None:
    candidate = build_global_player_media_candidate()
    plan = build_global_player_materialization_plan()
    _assert(candidate.canonical_source_url == sanitize_source_url(GLOBAL_PLAYER_LBC_FIXTURE_URL), "canonical source URL")
    _assert(candidate.media_kind == "broadcast_catchup_audio", "media kind")
    _assert(candidate.media_role == "broadcast_episode_audio", "media role")
    _assert(candidate.preferred_method == "yt_dlp_python_module", "preferred method")
    _assert(plan.preferred_method == "yt_dlp_python_module", "plan method")
    _assert(plan.preserve_native_container is True, "preserve native")
    _assert(plan.conversion_policy == "preserve_native_no_transcode_for_preservation", "conversion policy")
    _assert("sidecars/info.json" in plan.sidecar_paths, "info sidecar")
    _assert("media/original.m4a" in plan.expected_artifacts, "original m4a")


def test_review_strings_are_plain_and_bridge_source_matching_fields() -> None:
    for candidate in build_sample_candidates():
        item = candidate.with_derived_fields()
        for field in (item.source_url, item.canonical_source_url, item.raw_media_url, item.canonical_media_url, item.relative_output_path):
            _assert(not str(field).startswith("[") and "](" not in str(field), f"markdown leaked: {field}")
        _assert(item.candidate_id in item.review_strings, "candidate id review string")
        _assert(item.media_kind in item.review_strings, "media kind review string")
        _assert(item.media_role in item.review_strings, "media role review string")
        _assert(item.dedupe_key in item.review_strings, "dedupe review string")


def test_metadata_review_required_and_blocked_candidates_are_not_promoted() -> None:
    article = build_generic_article_sample_media_candidate()
    twitter = build_twitter_sample_media_candidate()
    plans = {plan.candidate_id: plan for plan in build_sample_plans()}
    _assert(article.access_status == STATUS_METADATA_ONLY_UNTIL_CAPTURED, "article candidate metadata-only")
    _assert(plans[article.candidate_id].status == STATUS_METADATA_ONLY_UNTIL_CAPTURED, "article plan not promoted")
    _assert(twitter.access_status == STATUS_REVIEW_REQUIRED, "twitter candidate review required")
    _assert(plans[twitter.candidate_id].status == STATUS_REVIEW_REQUIRED, "twitter plan not promoted")


def test_family_media_slots_cover_required_platform_groups() -> None:
    by_family = {slot.source_family: slot for slot in MEDIA_METHOD_SLOTS}
    _assert("universal_media_registry_reference" in by_family, "universal registry reference slot")
    all_kinds = {kind for slot in MEDIA_METHOD_SLOTS for kind in slot.media_kinds}
    all_methods = {method for slot in MEDIA_METHOD_SLOTS for method in slot.discovery_methods}
    all_roles = {role for slot in MEDIA_METHOD_SLOTS for role in slot.media_roles}
    _assert(set(MEDIA_KINDS).issubset(all_kinds), "all media kinds covered by matrix")
    _assert(set(DISCOVERY_METHODS).issubset(all_methods), "all discovery methods covered by matrix")
    _assert(set(MEDIA_ROLES).issubset(all_roles), "all media roles covered by matrix")
    _assert("twitter_x" in by_family, "twitter media slot")
    _assert("browser_network_observed_media" in by_family["twitter_x"].discovery_methods, "twitter browser media")
    _assert("news_websites" in by_family, "generic article media slot")
    _assert("api3128_jdownloader" in by_family["news_websites"].materialization_methods, "API3128 route")
    _assert("public_broadcast_catchup_audio" in by_family, "public audio slot")
    _assert("yt_dlp_python_module" in by_family["public_broadcast_catchup_audio"].materialization_methods, "yt-dlp route")
    _assert("video_platforms" in by_family, "video platform slot")
    _assert("visual_photo_platforms" in by_family, "visual platform slot")
    _assert("community_forums" in by_family, "community slot")
    _assert("professional_workplace" in by_family, "professional/workplace slot")


def test_fast_queue_policy_and_export_layouts_are_present() -> None:
    _assert("text_record_capture_first" in FAST_QUEUE_POLICY, "text first")
    _assert("support_pause_recovery_resume_keys" in FAST_QUEUE_POLICY, "pause recovery")
    _assert("allow_selected_media_only_mode_for_large_pages_accounts" in FAST_QUEUE_POLICY, "selected media only")
    audio_layout = build_public_audio_export_layout()
    article_layout = build_generic_article_export_layout()
    _assert(audio_layout["media_candidates"].endswith("media_candidates.ndjson"), "audio candidates layout")
    _assert(audio_layout["media_download_plan"].endswith("media_download_plan.json"), "audio plan layout")
    _assert(article_layout["media_article"].endswith("media/article/"), "article media layout")
    _assert(article_layout["screenshots"].endswith("screenshots/"), "screenshot layout")


def test_r42gi_report_checks_and_prior_green_layers_pass() -> None:
    report = validate_universal_media_method_matrix(".")
    _assert(report.status == R42GI_PASS_STATUS, report.status)
    checks = {check["name"]: check["status"] for check in report.checks}
    for name in (
        "all_media_kinds_present",
        "all_discovery_methods_present",
        "all_media_roles_present",
        "candidate_schema_complete",
        "materialization_plan_schema_complete",
        "fast_queue_policy_present",
        "twitter_x_media_slots_present",
        "generic_article_media_slots_present",
        "public_audio_media_slots_present",
        "global_player_fixture_preserved",
        "raw_machine_urls_not_markdown",
        "review_string_bridge_present",
        "no_metadata_or_review_required_promotion",
        "side_effect_boundary_declared",
        "r42gg_r42gh_still_green",
    ):
        _assert(checks.get(name) == "pass", f"report check failed: {name}")
    r42gh = validate_source_map_raw_url_audio_catchup(".")
    _assert(r42gh.status == R42GH_PASS_STATUS, "R42GH regression")


def run_tests() -> None:
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"PASS {name}")


if __name__ == "__main__":
    run_tests()
