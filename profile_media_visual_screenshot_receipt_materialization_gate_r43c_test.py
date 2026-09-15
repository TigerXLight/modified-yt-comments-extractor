from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_visual_screenshot_receipt_materialization_gate_r43c import (
    R43C_EDGE_R18_BASELINE,
    R43C_MARKER,
    R43C_PASS_STATUS,
    SCREENSHOT_NEEDS_CHECK,
    SCREENSHOT_PASS,
    apply_visual_screenshot_receipt_materialization_gate_r43c,
    build_r43c_contract,
    build_report,
    write_visual_screenshot_receipt_r43c,
)
from profile_media_twitter_x_account_media_ledger_r43a import (
    TwitterXAccountRecordR43A,
    write_twitter_x_account_media_ledger_r43a,
)


def test_twitter_account_capture_receipts_and_links_are_written() -> None:
    with tempfile.TemporaryDirectory(prefix="r43c_gate_") as tmp:
        root = Path(tmp)
        screenshot = root / "shot.png"
        screenshot.write_bytes(b"shot")
        result = write_twitter_x_account_media_ledger_r43a(
            (TwitterXAccountRecordR43A(account_handle="examaddaorg", author_handle="examaddaorg", record_id="1001", record_type="post", source_url="https://x.com/examaddaorg/status/1001", visible_text="post", visible_timestamp="2026-09-15T01:00:00Z", static_screenshot_path=str(screenshot), observed_order=1),),
            output_root=root / "source_exports" / "twitter_x",
            account_handle="examaddaorg",
            capture_timestamp="20260915T010000Z",
        )
        gate = apply_visual_screenshot_receipt_materialization_gate_r43c(result.account_capture_dir, default_context={"platform": "twitter_x", "card_materialized_in_viewport": True})
        capture = Path(result.account_capture_dir)
        receipt = capture / "dates" / "2026-09-15" / "post_1001" / "static_screenshot_receipt.json"
        assert gate.status == R43C_PASS_STATUS
        assert receipt.is_file()
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        assert payload["marker"] == R43C_MARKER
        assert payload["status"] == SCREENSHOT_PASS
        assert payload["complete_enough_for_evidence"] is True
        account_record = (capture / "account_record.md").read_text(encoding="utf-8")
        post_md = (capture / "dates" / "2026-09-15" / "post_1001" / "post.md").read_text(encoding="utf-8")
        manifest = json.loads((capture / "manifest.json").read_text(encoding="utf-8"))
        assert "## Screenshot receipts" in account_record
        assert "static_screenshot_receipt.json" in account_record
        assert "Static screenshot receipt" in post_md
        assert manifest["screenshot_receipt_gate"]["marker"] == R43C_MARKER


def test_youtube_r17_false_clean_is_needs_check_but_r18_passes() -> None:
    with tempfile.TemporaryDirectory(prefix="r43c_youtube_") as tmp:
        root = Path(tmp)
        screenshot = root / "shot.png"
        screenshot.write_bytes(b"shot")
        r17 = write_visual_screenshot_receipt_r43c(root / "r17", platform="youtube", record_id="yt1", record_type="comment_thread", source_url="https://www.youtube.com/watch?v=qDNq3R2b5t8", screenshot_path=screenshot, context={"visual_baseline": "EDGE_R17_FAST_DOM_ONLY", "materialized_in_viewport": False, "materialization_clean": False, "capture_gate": True, "rendered_reply_openers": 0, "rendered_read_more": 0})
        r18 = write_visual_screenshot_receipt_r43c(root / "r18", platform="youtube", record_id="yt2", record_type="comment_thread", source_url="https://www.youtube.com/watch?v=qDNq3R2b5t8", screenshot_path=screenshot, context={"visual_baseline": R43C_EDGE_R18_BASELINE, "materialized_in_viewport": True, "materialization_clean": True, "capture_gate": True, "rendered_reply_openers": 0, "rendered_read_more": 0})
        assert r17.status == SCREENSHOT_NEEDS_CHECK
        assert r17.complete_enough_for_evidence is False
        assert r18.status == SCREENSHOT_PASS
        assert r18.complete_enough_for_evidence is True


def test_contract_records_r18_baseline_and_local_only_boundaries() -> None:
    contract = build_r43c_contract()
    assert contract["marker"] == R43C_MARKER
    assert contract["edge_visual_baseline"] == R43C_EDGE_R18_BASELINE
    assert contract["youtube_hard_gate"]["r17_false_clean_allowed"] is False
    assert contract["account_record_links_receipts"] is True
    assert contract["local_layer_only"] is True
    assert contract["source_role_checks_enabled"] is False
    assert contract["review_window_dependency"] is False
    assert contract["remote_media_downloads_enabled"] is False


def test_report_green() -> None:
    with tempfile.TemporaryDirectory(prefix="r43c_report_") as tmp:
        report = build_report(Path(tmp))
        failed = [dict(check) for check in report.checks if check.get("status") != "pass"]
        assert report.status == R43C_PASS_STATUS, failed
        assert report.passed, failed
        assert report.to_dict()["gate_result"]["receipt_count"] == 1


def run_self_test() -> None:
    test_twitter_account_capture_receipts_and_links_are_written()
    test_youtube_r17_false_clean_is_needs_check_but_r18_passes()
    test_contract_records_r18_baseline_and_local_only_boundaries()
    test_report_green()


if __name__ == "__main__":
    run_self_test()
    print("profile_media_visual_screenshot_receipt_materialization_gate_r43c_test: PASS")
