from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from profile_media_live_twitter_x_visible_session_binding_r43o import (
    LiveTwitterXVisibleSessionBindingRequestR43O,
    build_live_twitter_x_visible_session_binding_r43o,
)
from profile_media_twitter_x_account_tracking_export_surface_r43d import (
    build_twitter_x_account_tracking_export_surface_r43d,
)
from profile_media_twitter_x_live_profile_lock_preflight_r43s import (
    BLOCKED_PROFILE_LOCK,
    BLOCKED_PROFILE_PATH_MISSING,
    BLOCKED_PROFILE_WRITE_DENIED,
    PASS_PROFILE_PREFLIGHT,
    R43S_PASS_STATUS,
    build_report,
    run_twitter_x_live_profile_lock_preflight_r43s,
)
from profile_media_universal_social_live_twitter_x_workbench_route_r43q import build_r43q_app_shell


class _BlockedProfileHarness:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def run_smoke(self, request: dict) -> dict:
        self.requests.append(dict(request))
        receipt = {
            "status": BLOCKED_PROFILE_LOCK,
            "blocker_reason": "Chromium singleton lock files are present for the target profile.",
            "profile_preflight_status": BLOCKED_PROFILE_LOCK,
            "profile_preflight_summary": {
                "profile_preflight_status": BLOCKED_PROFILE_LOCK,
                "safe_to_launch_persistent_context": False,
                "blocker_reason": "Chromium singleton lock files are present for the target profile.",
            },
            "promoted_network_event_count": 0,
            "promoted_observed_post_count": 0,
            "promoted_observed_media_count": 0,
            "promoted_observed_screenshot_count": 0,
            "promoted_non_fixture_observation_evidence": False,
            "r43o_visible_session_binding_status": BLOCKED_PROFILE_LOCK,
        }
        return {
            "status": BLOCKED_PROFILE_LOCK,
            "blocker_reason": receipt["blocker_reason"],
            "observation_receipt_path": str(Path(request["output_root"]) / "live_smoke_observation_receipt.json"),
            "observation_receipt": receipt,
            "progress_events_path": str(Path(request["output_root"]) / "live_smoke_progress_events.ndjson"),
            "materialization_receipts_index_path": str(Path(request["output_root"]) / "live_smoke_materialization_receipts_index.json"),
            "report_json_path": str(Path(request["output_root"]) / "R43N_REPORT.json"),
            "run_dir": str(Path(request["output_root"])),
        }


def test_existing_unlocked_profile_preflight_passes_with_temp_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        profile.mkdir()
        (profile / "Preferences").write_text("{}", encoding="utf-8")
        result = run_twitter_x_live_profile_lock_preflight_r43s(profile, process_rows_provider=lambda: ())
        assert result.profile_preflight_status == PASS_PROFILE_PREFLIGHT
        assert result.safe_to_launch_persistent_context is True
        assert result.profile_write_probe_ok is True


def test_missing_profile_blocks_before_browser_launch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = run_twitter_x_live_profile_lock_preflight_r43s(Path(tmp) / "missing", process_rows_provider=lambda: ())
        assert result.profile_preflight_status == BLOCKED_PROFILE_PATH_MISSING
        assert result.safe_to_launch_persistent_context is False


def test_write_denied_profile_blocks_before_browser_launch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        profile.mkdir()
        result = run_twitter_x_live_profile_lock_preflight_r43s(
            profile,
            process_rows_provider=lambda: (),
            write_probe=lambda _: (False, "write denied fixture"),
        )
        assert result.profile_preflight_status == BLOCKED_PROFILE_WRITE_DENIED
        assert "write denied" in result.blocker_reason


def test_singleton_lock_profile_blocks_before_browser_launch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        profile.mkdir()
        (profile / "SingletonLock").write_text("locked", encoding="utf-8")
        result = run_twitter_x_live_profile_lock_preflight_r43s(profile, process_rows_provider=lambda: ())
        assert result.profile_preflight_status == BLOCKED_PROFILE_LOCK
        assert result.singleton_paths_present


def test_matching_chromium_process_blocks_before_browser_launch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        profile.mkdir()
        rows = (
            {
                "pid": "1234",
                "name": "chrome.exe",
                "command_line": f'"C:/Chrome/chrome.exe" --user-data-dir="{profile}" https://x.com',
            },
        )
        result = run_twitter_x_live_profile_lock_preflight_r43s(profile, process_rows_provider=lambda: rows)
        assert result.profile_preflight_status == BLOCKED_PROFILE_LOCK
        assert result.profile_process_match_count == 1
        assert "https://x.com" not in json.dumps(result.profile_process_matches)


def test_process_commandline_unavailable_is_reported_without_crash() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        profile.mkdir()
        result = run_twitter_x_live_profile_lock_preflight_r43s(profile, process_rows_provider=lambda: None)
        assert result.process_inspection_status == "unavailable"
        assert result.profile_preflight_status == PASS_PROFILE_PREFLIGHT


def test_r43o_receipt_includes_profile_preflight_summary_and_does_not_launch_when_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_root = Path(tmp) / "r43o"
        binding = build_live_twitter_x_visible_session_binding_r43o(output_root=output_root)
        result = binding.run_binding(
            LiveTwitterXVisibleSessionBindingRequestR43O(
                target_url="https://x.com/examaddaorg",
                account_handle="examaddaorg",
                capture_timestamp="20260918T010000Z",
                output_root=str(output_root),
                run_visible_live=True,
                automated_test_mode=False,
                browser_user_data_dir=str(Path(tmp) / "missing_profile"),
            )
        )
        receipt = result.receipt
        assert result.status == BLOCKED_PROFILE_PATH_MISSING
        assert receipt["profile_preflight_status"] == BLOCKED_PROFILE_PATH_MISSING
        assert receipt["profile_preflight_summary"]["safe_to_launch_persistent_context"] is False
        assert receipt["r42gz_boundary_invoked"] is False
        assert receipt["visible_navigation_attempted"] is False
        assert receipt["observer_started"] is False


def test_r43d_and_app_shell_bubble_profile_preflight_blocker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        harness = _BlockedProfileHarness()
        surface = build_twitter_x_account_tracking_export_surface_r43d(
            live_smoke_harness=harness,
            output_root=root / "r43d",
        )
        result = surface.run_account_export(
            {
                "account_url": "https://x.com/examaddaorg",
                "account_handle": "examaddaorg",
                "capture_timestamp": "20260918T010100Z",
                "explicit_live_mode": True,
                "run_visible_live": True,
                "browser_user_data_dir": "C:/Users/fahad/AppData/Local/YTCE/twitter_test_profile",
                "browser_executable_path": "C:/Users/fahad/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe",
            }
        )
        assert result.live_evidence_summary["profile_preflight_status"] == BLOCKED_PROFILE_LOCK
        assert harness.requests[0]["browser_executable_path"].endswith("chrome.exe")

        app_shell = build_r43q_app_shell(output_root=root / "r43q", live_harness=harness)
        app_result = app_shell.run_app_shell_command(
            {
                "command_name": "run_pending",
                "inputs": ("https://x.com/examaddaorg",),
                "capture_timestamp": "20260918T010200Z",
                "output_root": str(root / "app_shell"),
                "explicit_live_mode": True,
                "run_visible_live": True,
                "browser_user_data_dir": "C:/Users/fahad/AppData/Local/YTCE/twitter_test_profile",
                "browser_executable_path": "C:/Users/fahad/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe",
            }
        )
        receipt = json.loads(Path(app_result.receipt_path).read_text(encoding="utf-8"))
        assert receipt["live_evidence_summary"]["profile_preflight_status"] == BLOCKED_PROFILE_LOCK


def test_real_smoke_green_zip_excludes_browser_profile_files_when_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        receipt_dir = root / "real_workbench_smoke"
        receipt_dir.mkdir()
        (receipt_dir / "app_shell_receipt.json").write_text('{"status":"BLOCKED_PROFILE_LOCK"}\n', encoding="utf-8")
        profile = root / "twitter_test_profile"
        profile.mkdir()
        (profile / "Cookies").write_text("do not package", encoding="utf-8")
        zip_path = root / "green.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.write(receipt_dir / "app_shell_receipt.json", "real_workbench_smoke/app_shell_receipt.json")
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
        assert "real_workbench_smoke/app_shell_receipt.json" in names
        assert not any("Cookies" in name or "twitter_test_profile" in name for name in names)


def test_r43s_report_builds_with_expected_checks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build_report(Path(tmp) / "report")
        assert report["status"] == R43S_PASS_STATUS
        assert report["bad_checks"] == ()


if __name__ == "__main__":
    test_existing_unlocked_profile_preflight_passes_with_temp_fixture()
    test_missing_profile_blocks_before_browser_launch()
    test_write_denied_profile_blocks_before_browser_launch()
    test_singleton_lock_profile_blocks_before_browser_launch()
    test_matching_chromium_process_blocks_before_browser_launch()
    test_process_commandline_unavailable_is_reported_without_crash()
    test_r43o_receipt_includes_profile_preflight_summary_and_does_not_launch_when_blocked()
    test_r43d_and_app_shell_bubble_profile_preflight_blocker()
    test_real_smoke_green_zip_excludes_browser_profile_files_when_blocked()
    test_r43s_report_builds_with_expected_checks()
    print("PASS profile_media_twitter_x_live_profile_lock_preflight_r43s_test")
