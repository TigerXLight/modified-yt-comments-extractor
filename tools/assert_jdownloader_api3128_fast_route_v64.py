"""Source assertions for internal JDownloader API3128 fast route V64."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _git_diff(path: str) -> str:
    return subprocess.check_output(
        ["git", "diff", "--", path],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_api3128_routes_exist() -> None:
    cnl = _read("jdownloader_internal_cnl.py")
    for route in (
        "/linkgrabberv2/addLinks",
        "/linkgrabberv2/queryLinkCrawlerJobs",
        "/linkgrabberv2/queryPackages",
        "/linkgrabberv2/queryLinks",
        "/linkgrabberv2/moveToDownloadlist",
        "/downloadcontroller/start",
    ):
        assert route in cnl, route
    assert "JD_DEPRECATED_API_BASE_URL = \"http://127.0.0.1:3128\"" in cnl
    assert "def submit_api3128_download_route" in cnl
    assert "def submit_api3128_then_flashgot_fallback" in cnl


def test_api3128_addlinks_body_and_completion_wait() -> None:
    cnl = _read("jdownloader_internal_cnl.py")
    assert '"params": list(args)' in cnl
    assert '"links": source_url' in cnl
    assert '"packageName": package_name' in cnl
    assert '"destinationFolder": str(output_dir)' in cnl
    assert '"sourceUrl": source_url' in cnl
    assert '"autostart": False' in cnl
    assert '"overwritePackagizerRules": True' in cnl
    assert '"assignJobID": True' in cnl
    assert "expected_child_count" in cnl
    assert "stable_count >= 2" in cnl


def test_flashgot_fallback_remains() -> None:
    cnl = _read("jdownloader_internal_cnl.py")
    job = _read("jdownloader_internal_job.py")
    assert 'routes=("/flashgot",)' in cnl
    assert "API3128 fast route failed; used /flashgot fallback." in cnl
    assert "submit_api3128_then_flashgot_fallback" in job
    assert "CNL_FLASHGOT_URL = \"http://127.0.0.1:9666/flashgot\"" in job


def test_project_local_deprecated_api_config_enabled() -> None:
    process = _read("jdownloader_internal_process.py")
    for token in (
        "deprecatedapienabled",
        "deprecatedapilocalhostonly",
        "deprecatedapiport",
        "externinterfacelocalhostonly",
        "ensure_project_local_deprecated_api_config",
        "Refusing to edit Deprecated API config outside",
    ):
        assert token in process, token


def test_manifest_fields_present() -> None:
    monitor = _read("jdownloader_internal_download_monitor.py")
    job = _read("jdownloader_internal_job.py")
    for token in (
        "api3128_enabled",
        "api3128_used",
        "api3128_addlinks_ms",
        "api3128_package_complete_ms",
        "api3128_child_count",
        "api3128_move_ms",
        "api3128_start_ms",
        "api3128_first_running_ms",
        "api3128_finished_ms",
        "flashgot_fallback_used",
        "route_used",
        "first_file_seen_ms",
        "pre_download_wait_ms",
        "active_download_ms",
    ):
        assert token in monitor or token in job, token


def test_v62_warm_preresolve_not_reintroduced() -> None:
    combined = "\n".join(
        _read(name)
        for name in (
            "jdownloader_internal_cnl.py",
            "jdownloader_internal_job.py",
            "youtube_gui_media_queue.py",
            "main.py",
        )
    )
    assert "warm_preresolve" not in combined
    assert "shared_output_dir_package" not in combined
    assert "warm_reused" not in combined
    assert "warm_submitted" not in combined


def test_no_unrelated_ui_diff_tokens() -> None:
    main_diff = _git_diff("main.py").lower()
    forbidden = (
        "text_editor",
        "spell",
        "files folder",
        "asr icon",
        "export ui",
    )
    for token in forbidden:
        assert token not in main_diff, token


if __name__ == "__main__":
    for test in (
        test_api3128_routes_exist,
        test_api3128_addlinks_body_and_completion_wait,
        test_flashgot_fallback_remains,
        test_project_local_deprecated_api_config_enabled,
        test_manifest_fields_present,
        test_v62_warm_preresolve_not_reintroduced,
        test_no_unrelated_ui_diff_tokens,
    ):
        test()
    print("internal JDownloader API3128 fast route V64 assertions passed")
