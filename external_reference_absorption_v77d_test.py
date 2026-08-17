from __future__ import annotations

from pathlib import Path

from external_reference_absorption_v77d import (
    build_external_reference_absorption_matrix,
    inspect_reference_paths,
    matrix_to_dict,
    summarize_absorption_matrix,
)


def _by_name():
    return {entry.reference_name: entry for entry in build_external_reference_absorption_matrix()}


def test_required_reference_families_are_concrete() -> None:
    by_name = _by_name()
    required = [
        "GoFullPage 8.6_0.zip",
        "PageCap 1.2.0_0.zip",
        "Twitter Exporter 0.8.58_0.zip",
        "Video Download Helper 10.5.24.2_0.zip",
        "Video Downloader Professional 10.5.24.2_0.zip",
        "prinsss__twitter-web-exporter",
        "annismckenzie__x-article-exporter",
        "RayanIJ__twitter-stream-proxy",
        "mrcoles__full-page-screen-capture-chrome-extension",
        "EverythingSuckz__webshot-api",
        "sea-deep__link-to-screenshot",
        "stratofax__pagecap",
        "myselfshravan__third-eye",
        "copperline-labs__rendex-mcp",
    ]
    for name in required:
        assert name in by_name
        assert by_name[name].detected_files_or_modules
        assert by_name[name].useful_logic_to_absorb


def test_twitter_exporter_entry_names_real_modules_and_blocks_write_actions() -> None:
    entry = _by_name()["prinsss__twitter-web-exporter"]
    text = " ".join(entry.detected_files_or_modules + entry.useful_logic_to_absorb + entry.prohibited_behaviours)
    assert "export-data" in text
    assert "export-media" in text
    assert "database manager" in text
    assert "followers" in text
    assert "following" in text
    assert "likes" in text
    assert "DMs" in text
    assert "posting" in text


def test_proxy_reference_is_restricted_not_absorbed_as_runtime() -> None:
    entry = _by_name()["RayanIJ__twitter-stream-proxy"]
    assert entry.implementation_status == "UNSAFE_OUT_OF_SCOPE"
    assert "proxy/evasion" in " ".join(entry.prohibited_behaviours)
    assert "do not implement proxy/evasion" in entry.safe_absorption_boundary


def test_matrix_safety_invariants() -> None:
    payload = matrix_to_dict()
    flags = payload["safety_invariants"]
    assert flags["no_browser_launch"] is True
    assert flags["no_network"] is True
    assert flags["no_media_download"] is True
    assert flags["human_mediated_access_challenge_allowed"] is True
    assert flags["no_x_twitter_write_actions"] is True
    summary = summarize_absorption_matrix()
    assert summary["reference_count"] >= 25
    assert "UNSAFE_OUT_OF_SCOPE" in summary["statuses"]


def test_reference_path_inspection_is_local_inventory_only() -> None:
    root = Path("external_reference_sources_20260814_234822")
    payload = inspect_reference_paths(root)
    assert payload["repo_reference_inventory_scan"] is True
    assert payload["web_download_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["browser_launch_performed"] is False


if __name__ == "__main__":
    test_required_reference_families_are_concrete()
    test_twitter_exporter_entry_names_real_modules_and_blocks_write_actions()
    test_proxy_reference_is_restricted_not_absorbed_as_runtime()
    test_matrix_safety_invariants()
    test_reference_path_inspection_is_local_inventory_only()
    print("external_reference_absorption_v77d_test OK")
