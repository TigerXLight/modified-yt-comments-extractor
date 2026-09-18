from pathlib import Path

from profile_media_reddit_old_reddit_thread_expansion_r44e import (
    R44E_EDSHEERAN_BRANCH_URLS,
    R44E_EDSHEERAN_OLD_REDDIT_URL,
    R44E_EDSHEERAN_THREAD_URL,
    R44E_PASS_STATUS,
    RedditOldThreadExpansionRequestR44E,
    build_old_reddit_capture_plan_urls_r44e,
    build_report,
    canonicalize_old_reddit_thread_url_r44e,
    extract_continue_thread_urls_from_old_reddit_html_r44e,
    normalize_reddit_branch_urls_r44e,
    run_reddit_old_reddit_thread_expansion_r44e,
)
from profile_media_reddit_visible_dom_capture_r44d import extract_reddit_visible_records_from_dom_r44d


def test_old_reddit_canonical_url_prefers_limit_500() -> None:
    url = canonicalize_old_reddit_thread_url_r44e(R44E_EDSHEERAN_THREAD_URL)
    assert url.startswith("https://en.reddit.com/r/EdSheeran/comments/1whbgzk/")
    assert "sort=old" in url
    assert "limit=500" in url
    assert "screen_view_count=1" in url
    assert "ext-referrer=DIRECT" in url


def test_branch_urls_are_deduped_and_legacy_forced() -> None:
    urls = normalize_reddit_branch_urls_r44e([R44E_EDSHEERAN_BRANCH_URLS[0], R44E_EDSHEERAN_BRANCH_URLS[0]])
    assert len(urls) == 1
    assert urls[0].startswith("https://en.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/")
    assert "force-legacy-sct=1" in urls[0]


def test_capture_plan_includes_old_page_then_branch_pages() -> None:
    plan = build_old_reddit_capture_plan_urls_r44e(R44E_EDSHEERAN_THREAD_URL, R44E_EDSHEERAN_OLD_REDDIT_URL, R44E_EDSHEERAN_BRANCH_URLS)
    assert plan[0] == R44E_EDSHEERAN_OLD_REDDIT_URL
    assert len(plan) == 1 + len(R44E_EDSHEERAN_BRANCH_URLS)
    assert all("force-legacy-sct=1" in url for url in plan[1:])


def test_old_reddit_thing_blocks_parse_through_r44d() -> None:
    html = """
    <div class="thing link" id="thing_t3_1whbgzk" data-fullname="t3_1whbgzk" data-author="Stonerthrowaway710" data-type="link">
      <a class="title" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/">Thread title</a>
      <time datetime="2026-09-15T20:12:09Z">1d ago</time>
      <div class="usertext-body"><p>Thread selftext</p><a href="https://i.redd.it/example.jpg">image</a></div>
    </div>
    <div class="thing comment" id="thing_t1_pa1fs0p" data-fullname="t1_pa1fs0p" data-author="Hassaan18" data-type="comment">
      <a class="bylink" href="/r/EdSheeran/comments/1whbgzk/eds_got_a_show_in_4_days_no_band_no_openers_what/pa1fs0p/">permalink</a>
      <a class="author">Hassaan18</a>
      <time datetime="2026-09-15T20:20:00Z">1d ago</time>
      <div class="usertext-body"><p>He can do the show.</p></div>
    </div>
    """
    records, meta = extract_reddit_visible_records_from_dom_r44d(
        html,
        account_handle="r_EdSheeran",
        account_url=R44E_EDSHEERAN_THREAD_URL,
        navigation_url=R44E_EDSHEERAN_OLD_REDDIT_URL,
        capture_timestamp="20260918T110000Z",
        html_receipt_path="visible_dom.html",
        screenshot_path="screenshot.png",
        feed_mode="single_thread",
        max_items=20,
    )
    assert len(records) == 2
    assert records[0].record_type == "post"
    assert records[1].record_type == "reply"
    assert records[1].record_id == "pa1fs0p"
    assert records[1].author_handle == "Hassaan18"
    assert meta["media_candidate_count"] >= 1


def test_continue_urls_are_discovered_from_old_reddit_labels() -> None:
    html = '<a href="/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/">continue this thread</a>'
    urls = extract_continue_thread_urls_from_old_reddit_html_r44e(html)
    assert len(urls) == 1
    assert urls[0].startswith("https://en.reddit.com/r/EdSheeran/comments/1whbgzk/comment/pa1fs0p/")
    assert "force-legacy-sct=1" in urls[0]


def test_fixture_run_writes_r44d_r43u_ledger(tmp_path: Path) -> None:
    result = run_reddit_old_reddit_thread_expansion_r44e(
        RedditOldThreadExpansionRequestR44E(
            thread_url=R44E_EDSHEERAN_THREAD_URL,
            old_reddit_url=R44E_EDSHEERAN_OLD_REDDIT_URL,
            branch_urls=R44E_EDSHEERAN_BRANCH_URLS,
            account_handle="r_EdSheeran",
            output_root=str(tmp_path),
            capture_timestamp="20260918T110000Z",
            fixture_mode=True,
            max_items=500,
        )
    )
    assert result.status == R44E_PASS_STATUS
    assert result.r44d_status.endswith("REDDIT_VISIBLE_DOM_CAPTURE_ADAPTER")
    assert result.record_count >= 3
    assert result.media_count >= 1
    assert result.screenshot_count >= 1
    assert result.branch_url_count == len(R44E_EDSHEERAN_BRANCH_URLS)
    assert not result.browser_session_started
    assert not result.network_actions_performed
    assert Path(result.media_index_path).is_file()


def test_report_passes(tmp_path: Path) -> None:
    report = build_report(tmp_path)
    assert report.status == R44E_PASS_STATUS
    assert report.passed


def test_r43e_routes_reddit_thread_urls_to_current_reliable_thread_adapter(tmp_path: Path) -> None:
    from profile_media_universal_social_account_tracking_r43e import (
        UniversalSocialAccountTrackingRequestR43E,
        build_universal_social_account_tracking_registry_r43e,
    )

    expected_downstream_statuses = {R44E_PASS_STATUS}
    try:
        from profile_media_reddit_no_login_complete_comments_r44f import R44F_PASS_STATUS

        # R44F is the newer reliability layer. Once installed, the R43E route
        # intentionally prefers the no-login old-Reddit limit=500 + ordered
        # branch queue path over routing directly to R44E. R44E remains the
        # old/en Reddit page-expansion adapter used underneath the newer route.
        expected_downstream_statuses.add(R44F_PASS_STATUS)
    except Exception:
        pass

    registry = build_universal_social_account_tracking_registry_r43e(output_root=tmp_path)
    result = registry.run_account_export(
        UniversalSocialAccountTrackingRequestR43E(
            platform_id="reddit",
            account_url=R44E_EDSHEERAN_THREAD_URL,
            account_handle="r_EdSheeran",
            capture_timestamp="20260918T110100Z",
            output_root=str(tmp_path),
            fixture_mode=True,
            include_replies=True,
            max_items=500,
        )
    )
    payload = result.to_dict()
    assert payload["status"] == "PASS_R43E_UNIVERSAL_SOCIAL_ACCOUNT_TRACKING_CONTRACT_ADAPTER_MAP"
    assert payload["downstream_status"] in expected_downstream_statuses
    assert payload["record_count"] >= 3


def run_self_test() -> None:
    test_old_reddit_canonical_url_prefers_limit_500()
    test_branch_urls_are_deduped_and_legacy_forced()
    test_capture_plan_includes_old_page_then_branch_pages()
    test_old_reddit_thing_blocks_parse_through_r44d()
    test_continue_urls_are_discovered_from_old_reddit_labels()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_fixture_run_writes_r44d_r43u_ledger(Path(tmp) / "fixture")
    with tempfile.TemporaryDirectory() as tmp:
        test_report_passes(Path(tmp) / "report")
    with tempfile.TemporaryDirectory() as tmp:
        test_r43e_routes_reddit_thread_urls_to_current_reliable_thread_adapter(Path(tmp) / "route")


if __name__ == "__main__":
    run_self_test()
    print("profile_media_reddit_old_reddit_thread_expansion_r44e_test: PASS")
