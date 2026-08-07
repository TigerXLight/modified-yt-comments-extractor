from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path

from capture_manual_live_smoke_approval_packet_store_cli import (
    build_capture_manual_live_smoke_approval_packet_store_cli_result,
    capture_manual_live_smoke_approval_packet_store_cli_result_to_json,
    run_capture_manual_live_smoke_approval_packet_store_cli,
)


def test_store_cli_builds_safe_result() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = build_capture_manual_live_smoke_approval_packet_store_cli_result(
            [
                {
                    "site_id": "msn",
                    "display_name": "MSN manual comments",
                    "requested_action": "manual_comment_scroll_check",
                },
                {
                    "site_id": "ghostarchive",
                    "requested_action": "manual_archive_lookup",
                },
            ],
            temp_dir,
            packet_id="packet-cli-test",
        )
        data = result.to_dict()
        assert data["schema_version"] == "capture_manual_live_smoke_approval_packet_store_cli_v1"
        assert data["target_count"] == 2
        assert data["stored_file_count"] == 1
        assert data["review_status"] == "APPROVAL_REQUIRED"
        assert data["execution_mode"] == "MANUAL_OPERATOR_ONLY"
        assert data["live_network_request_performed"] is False
        assert data["browser_automation_performed"] is False
        assert data["completed_capture_claimed"] is False
        payload = capture_manual_live_smoke_approval_packet_store_cli_result_to_json(result)
        assert temp_dir not in payload
        assert "packet-cli-test" in payload


def test_store_cli_runner_accepts_targets_json_and_summary() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target_file = Path(temp_dir) / "targets.json"
        target_file.write_text(
            json.dumps(
                {
                    "targets": [
                        {
                            "site_id": "wayback",
                            "requested_action": "manual_wayback_lookup",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        output_dir = Path(temp_dir) / "out"
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_capture_manual_live_smoke_approval_packet_store_cli(
            [
                "--packet-id",
                "runner-test",
                "--targets-json",
                str(target_file),
                "--target",
                "archive-ph|manual_archive_lookup|archive.ph",
                "--output-directory",
                str(output_dir),
                "--summary",
            ],
            stdout=stdout,
            stderr=stderr,
        )
        assert code == 0, stderr.getvalue()
        assert "Targets: 2" in stdout.getvalue()
        assert "MANUAL_OPERATOR_ONLY" in stdout.getvalue()
        assert (output_dir / "capture_manual_live_smoke_approval_packet.json").exists()


def test_store_cli_rejects_secret_like_json() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target_file = Path(temp_dir) / "targets.json"
        target_file.write_text(
            json.dumps({"targets": [{"site_id": "x", "requested_action": "y", "token": "bad"}]}),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = run_capture_manual_live_smoke_approval_packet_store_cli(
            ["--targets-json", str(target_file), "--output-directory", str(Path(temp_dir) / "out")],
            stdout=stdout,
            stderr=stderr,
        )
        assert code == 2
        assert "secret-like field" in stderr.getvalue()


if __name__ == "__main__":
    test_store_cli_builds_safe_result()
    test_store_cli_runner_accepts_targets_json_and_summary()
    test_store_cli_rejects_secret_like_json()
    print("Manual live smoke approval packet store CLI self-test passed.")
