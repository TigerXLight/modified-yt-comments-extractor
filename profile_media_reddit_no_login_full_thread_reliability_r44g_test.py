from pathlib import Path
from tempfile import TemporaryDirectory

from profile_media_reddit_no_login_full_thread_reliability_r44g import (
    R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT,
    R44G_EXPECTED_EDSHEERAN_BRANCH_LABELS,
    R44G_PASS_STATUS,
    RedditNoLoginFullThreadReliabilityRequestR44G,
    build_report,
    build_reddit_no_login_full_thread_reliability_contract_r44g,
    build_reddit_no_login_full_thread_reliability_r44g,
    run_reddit_no_login_full_thread_reliability_r44g,
)
from profile_media_reddit_no_login_complete_comments_r44f import build_ordered_reddit_branch_queue_r44f


def test_full_edsheeran_operator_branch_manifest_preserves_labels() -> None:
    queue = build_ordered_reddit_branch_queue_r44f(ordered_branch_source_text=R44G_EDSHEERAN_FULL_BRANCH_SOURCE_TEXT)
    labels = tuple(entry.label for entry in queue)
    assert len(queue) == 27
    assert labels == R44G_EXPECTED_EDSHEERAN_BRANCH_LABELS
    assert labels.index("2") + 1 == labels.index("2.1")
    assert labels.index("8") + 1 == labels.index("8.1")
    assert labels.index("13") + 1 == labels.index("13.1")


def test_r44g_fixture_report_runs_without_network_and_preserves_downstream_chain() -> None:
    with TemporaryDirectory() as tmp:
        report = build_report(Path(tmp) / "report")
        assert report.status == R44G_PASS_STATUS
        sample = report.sample_result
        assert sample["branch_url_count"] == 27
        assert tuple(sample["branch_order_labels"]) == R44G_EXPECTED_EDSHEERAN_BRANCH_LABELS
        assert sample["no_login_route_selected"] is True
        assert sample["logged_in_account_detected"] is False
        assert sample["r44f_status"].startswith("PASS_R44F")
        assert sample["r44d_status"].startswith("PASS_R44D")
        assert sample["ledger_status"].startswith("PASS_R43U")
        assert sample["browser_session_started"] is False
        assert sample["network_actions_performed"] is False
        assert sample["comment_count_gap_recorded_not_invented"] is True


def test_accounts_keys_metadata_is_redacted_and_never_required_for_no_login_route() -> None:
    with TemporaryDirectory() as tmp:
        result = run_reddit_no_login_full_thread_reliability_r44g(
            RedditNoLoginFullThreadReliabilityRequestR44G(
                output_root=str(Path(tmp) / "run"),
                capture_timestamp="20260918T131000Z",
                accounts_keys_state={"reddit": {"status": "not_connected"}, "reddit_token": "do-not-write"},
                fixture_mode=True,
            )
        )
        assert result.status == R44G_PASS_STATUS
        assert result.accounts_keys_detection_path == "no_reddit_login_detected_in_accounts_keys_metadata"
        text = Path(result.request_path).read_text(encoding="utf-8")
        assert "do-not-write" not in text
        assert "<redacted>" in text


def test_builder_and_contract() -> None:
    with TemporaryDirectory() as tmp:
        tool = build_reddit_no_login_full_thread_reliability_r44g(Path(tmp) / "builder")
        result = tool.run_reliability_capture(capture_timestamp="20260918T132000Z", fixture_mode=True)
        assert result.status == R44G_PASS_STATUS
    contract = build_reddit_no_login_full_thread_reliability_contract_r44g()
    assert contract["downstream_chain"] == "R44G -> R44F -> R44D -> R43U"
    assert contract["remote_media_downloads_enabled"] is False


def run_self_test() -> None:
    test_full_edsheeran_operator_branch_manifest_preserves_labels()
    test_r44g_fixture_report_runs_without_network_and_preserves_downstream_chain()
    test_accounts_keys_metadata_is_redacted_and_never_required_for_no_login_route()
    test_builder_and_contract()
    print("profile_media_reddit_no_login_full_thread_reliability_r44g_test: PASS")


if __name__ == "__main__":
    run_self_test()
