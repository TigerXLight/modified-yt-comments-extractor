from pathlib import Path
from tempfile import TemporaryDirectory

from profile_media_reddit_r44i_r44j_real_capture_reconciliation_r44k import (
    PASS_STATUS,
    build_reddit_r44i_r44j_real_capture_reconciliation_contract_r44k,
    find_latest_r44i_run_dir_r44k,
    run_self_test,
)


def run_self_check() -> None:
    contract = build_reddit_r44i_r44j_real_capture_reconciliation_contract_r44k()
    assert contract["network_actions_enabled"] is False
    assert contract["browser_profile_file_copying_enabled"] is False
    with TemporaryDirectory() as tmp:
        report = run_self_test(Path(tmp) / "report")
        assert report.status == PASS_STATUS
        sample = report.sample_result
        assert sample["r44j_recovered_comment_count"] == 3
        assert sample["r44i_record_count"] == 5
        assert sample["r44i_minus_r44j_record_delta"] == 2
        assert sample["r44j_minus_reference_delta"] == 0
        assert sample["reddit_reported_minus_r44j_delta"] == 1
        assert Path(sample["r44j_comment_index_path"]).is_file()
        assert not sample["side_effect_flags"]["network_actions_performed"]
    print("profile_media_reddit_r44i_r44j_real_capture_reconciliation_r44k_test: PASS")


if __name__ == "__main__":
    run_self_check()
