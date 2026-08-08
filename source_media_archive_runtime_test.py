from __future__ import annotations

import json

from source_media_archive_runtime import (
    build_fixture_media_archive_runtime_bundle,
    source_media_archive_runtime_bundle_to_json,
    validate_source_media_archive_runtime_bundle,
)


def test_media_archive_bundle_covers_discovery_mux_archive_and_offline_plan() -> None:
    bundle = build_fixture_media_archive_runtime_bundle()
    data = bundle.to_dict()
    assert data["discovered_resource_count"] >= 4
    assert data["mux_plan"]["status"] == "plan_only"
    assert data["archive_provider_result_count"] == 2
    assert data["archivebox_command_plan_count"] == 3
    assert data["offline_bundle_plan"]["offline_bundle"]["bundle_format_id"] == "app_native_sourceweb_zip_v1"
    assert data["external_download_performed"] is False
    assert data["real_ffmpeg_executed"] is False
    assert data["real_ytdlp_executed"] is False


def test_rendered_citation_protected_output_is_blocked_without_bypass() -> None:
    data = build_fixture_media_archive_runtime_bundle().to_dict()
    assert data["protected_output_result"]["status"] == "protected_or_black_output"
    assert data["drm_bypass_attempted"] is False
    assert validate_source_media_archive_runtime_bundle(data) == ()
    unsafe = json.loads(source_media_archive_runtime_bundle_to_json(build_fixture_media_archive_runtime_bundle()))
    unsafe["drm_bypass_attempted"] = True
    unsafe["real_archive_provider_called"] = True
    errors = validate_source_media_archive_runtime_bundle(unsafe)
    assert "unsafe_flag_true:drm_bypass_attempted" in errors
    assert "unsafe_flag_true:real_archive_provider_called" in errors


def test_archivebox_plans_are_non_executable() -> None:
    data = build_fixture_media_archive_runtime_bundle().to_dict()
    assert all(plan["executable"] is False for plan in data["archivebox_command_plans"])
    assert all(plan["command"] or plan["mode"] == "REMOTE_ARCHIVEBOX" for plan in data["archivebox_command_plans"])


def test_serialization_is_deterministic() -> None:
    assert source_media_archive_runtime_bundle_to_json(build_fixture_media_archive_runtime_bundle()) == (
        source_media_archive_runtime_bundle_to_json(build_fixture_media_archive_runtime_bundle())
    )


if __name__ == "__main__":
    test_media_archive_bundle_covers_discovery_mux_archive_and_offline_plan()
    test_rendered_citation_protected_output_is_blocked_without_bypass()
    test_archivebox_plans_are_non_executable()
    test_serialization_is_deterministic()
    print("source_media_archive_runtime_test.py passed")
