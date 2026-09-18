from pathlib import Path

from profile_media_reddit_no_login_complete_comments_r44f import (
    R44F_PASS_STATUS,
    RedditNoLoginCompleteCommentsRequestR44F,
    build_no_login_old_reddit_thread_url_r44f,
    build_ordered_reddit_branch_queue_r44f,
    build_report,
    choose_reddit_comment_capture_strategy_r44f,
    detect_reddit_logged_in_available_r44f,
    extract_and_merge_reddit_comment_index_r44f,
    parse_ordered_reddit_branch_lines_r44f,
    run_reddit_no_login_complete_comments_r44f,
)
from profile_media_reddit_old_reddit_thread_expansion_r44e import (
    R44E_EDSHEERAN_BRANCH_URLS,
    R44E_EDSHEERAN_THREAD_URL,
)


def test_accounts_keys_absent_chooses_no_login_old_reddit() -> None:
    detected, path = detect_reddit_logged_in_available_r44f({})
    assert detected is False
    assert "no_reddit_login" in path
    assert choose_reddit_comment_capture_strategy_r44f(logged_in_account_detected=detected) == "no_login_old_reddit_limit500_branch_queue"


def test_accounts_keys_connected_can_be_detected_without_secret_values() -> None:
    detected, path = detect_reddit_logged_in_available_r44f({"reddit": {"status": "connected", "token": "do_not_copy"}})
    assert detected is True
    assert path == "accounts_keys_state.reddit.status"


def test_old_reddit_url_keeps_limit_500_and_sort_old() -> None:
    url = build_no_login_old_reddit_thread_url_r44f(R44E_EDSHEERAN_THREAD_URL, comment_sort="old")
    assert url.startswith("https://en.reddit.com/r/EdSheeran/comments/1whbgzk/")
    assert "limit=500" in url
    assert "screen_view_count=1" in url
    assert "sort=old" in url


def test_ordered_branch_text_preserves_top_to_bottom_labels() -> None:
    source = "\n".join([
        f"1 - {R44E_EDSHEERAN_BRANCH_URLS[0]}",
        f"2 - {R44E_EDSHEERAN_BRANCH_URLS[1]}",
        f"2.1 - {R44E_EDSHEERAN_BRANCH_URLS[2]}",
    ])
    entries = parse_ordered_reddit_branch_lines_r44f(source)
    assert [e.label for e in entries] == ["1", "2", "2.1"]
    assert entries[2].depth_hint == 1
    assert all("force-legacy-sct=1" in e.url for e in entries)


def test_branch_queue_dedupes_text_and_extra_urls() -> None:
    source = f"1 - {R44E_EDSHEERAN_BRANCH_URLS[0]}"
    queue = build_ordered_reddit_branch_queue_r44f(branch_urls=[R44E_EDSHEERAN_BRANCH_URLS[0], R44E_EDSHEERAN_BRANCH_URLS[1]], ordered_branch_source_text=source)
    assert [e.label for e in queue] == ["1", "2"]
    assert len(queue) == 2


def test_comment_tree_merges_branch_anchor_and_preserves_scores() -> None:
    old_url = build_no_login_old_reddit_thread_url_r44f(R44E_EDSHEERAN_THREAD_URL)
    branch = build_ordered_reddit_branch_queue_r44f(branch_urls=[R44E_EDSHEERAN_BRANCH_URLS[0]])[0]
    pages = [
        {
            "url": old_url,
            "final_url": old_url,
            "html": """
            <html><body>
            <div class="thing comment" id="thing_t1_pa1fs0p" data-fullname="t1_pa1fs0p" data-parent="t3_1whbgzk" data-author="Hassaan18"><span class="score unvoted">49 points</span><div class="usertext-body"><p>parent</p></div></div>
            <div class="thing comment" id="thing_t1_pa15vni" data-fullname="t1_pa15vni" data-parent="t3_1whbgzk" data-author="Wetnorthwest"><span class="score dislikes">-2 points</span><div class="usertext-body"><p>second</p></div></div>
            </body></html>
            """,
        },
        {
            "url": branch.url,
            "final_url": branch.url,
            "html": """
            <html><body>
            <div class="thing comment" id="thing_t1_pa1fs0p" data-fullname="t1_pa1fs0p" data-parent="t3_1whbgzk" data-author="Hassaan18"><span class="score unvoted">49 points</span><div class="usertext-body"><p>duplicate anchor</p></div></div>
            <div class="thing comment" id="thing_t1_pa1child" data-fullname="t1_pa1child" data-parent="t1_pa1fs0p" data-author="ertri"><span class="score hidden">score hidden</span><div class="usertext-body"><p>child</p></div></div>
            </body></html>
            """,
        },
    ]
    nodes = extract_and_merge_reddit_comment_index_r44f(pages, branch_entries=[branch], thread_url=R44E_EDSHEERAN_THREAD_URL)
    ids = [n.comment_id for n in nodes]
    assert ids.count("pa1fs0p") == 1
    assert "pa1child" in ids
    assert any(n.score_value == -2 for n in nodes)
    assert any(n.score_hidden for n in nodes)
    child = [n for n in nodes if n.comment_id == "pa1child"][0]
    assert child.indent_level == 1


def test_fixture_run_writes_comment_tree_and_ledger(tmp_path: Path) -> None:
    source = "\n".join(f"{idx + 1} - {url}" for idx, url in enumerate(R44E_EDSHEERAN_BRANCH_URLS[:3]))
    result = run_reddit_no_login_complete_comments_r44f(
        RedditNoLoginCompleteCommentsRequestR44F(
            thread_url=R44E_EDSHEERAN_THREAD_URL,
            ordered_branch_source_text=source,
            account_handle="r_EdSheeran",
            output_root=str(tmp_path),
            capture_timestamp="20260918T120000Z",
            fixture_mode=True,
            max_items=500,
        )
    )
    assert result.status == R44F_PASS_STATUS
    assert result.strategy == "no_login_old_reddit_limit500_branch_queue"
    assert result.branch_order_labels[:3] == ("1", "2", "3")
    assert result.comment_index_count >= 4
    assert result.max_comment_depth >= 2
    assert result.score_count >= 2
    assert result.negative_score_count >= 1
    assert result.record_count >= 4
    assert result.media_count >= 1
    assert Path(result.comment_tree_markdown_path).is_file()
    assert Path(result.media_index_path).is_file()
    assert not result.browser_session_started
    assert not result.network_actions_performed


def test_report_passes(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.status == R44F_PASS_STATUS
    assert report.passed


def test_r43e_routes_reddit_thread_urls_to_r44f(tmp_path: Path) -> None:
    from profile_media_universal_social_account_tracking_r43e import (
        UniversalSocialAccountTrackingRequestR43E,
        build_universal_social_account_tracking_registry_r43e,
    )

    registry = build_universal_social_account_tracking_registry_r43e(output_root=tmp_path)
    result = registry.run_account_export(
        UniversalSocialAccountTrackingRequestR43E(
            platform_id="reddit",
            account_url=R44E_EDSHEERAN_THREAD_URL,
            account_handle="r_EdSheeran",
            capture_timestamp="20260918T120100Z",
            output_root=str(tmp_path),
            fixture_mode=True,
            include_replies=True,
            max_items=500,
        )
    )
    payload = result.to_dict()
    assert payload["status"] == "PASS_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP"
    assert payload["downstream_status"] == R44F_PASS_STATUS
    assert payload["record_count"] >= 4


def run_self_test() -> None:
    test_accounts_keys_absent_chooses_no_login_old_reddit()
    test_accounts_keys_connected_can_be_detected_without_secret_values()
    test_old_reddit_url_keeps_limit_500_and_sort_old()
    test_ordered_branch_text_preserves_top_to_bottom_labels()
    test_branch_queue_dedupes_text_and_extra_urls()
    test_comment_tree_merges_branch_anchor_and_preserves_scores()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_fixture_run_writes_comment_tree_and_ledger(Path(tmp) / "fixture")
    with tempfile.TemporaryDirectory() as tmp:
        test_report_passes(Path(tmp) / "report")
    with tempfile.TemporaryDirectory() as tmp:
        test_r43e_routes_reddit_thread_urls_to_r44f(Path(tmp) / "route")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_reddit_no_login_complete_comments_r44f_test: PASS")
