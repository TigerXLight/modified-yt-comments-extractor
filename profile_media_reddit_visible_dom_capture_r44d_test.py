from pathlib import Path

from profile_media_reddit_visible_dom_capture_r44d import (
    R44D_PASS_STATUS,
    RedditVisibleDomCaptureRequestR44D,
    build_report,
    build_reddit_visible_navigation_url_r44d,
    build_reddit_visible_dom_capture_contract_r44d,
    extract_reddit_visible_records_from_dom_r44d,
    build_fake_reddit_visible_dom_html_r44d,
    run_reddit_visible_dom_capture_r44d,
)
from profile_media_universal_social_account_ledger_contract_r43u import R43U_PASS_STATUS


def test_navigation_modes() -> None:
    assert build_reddit_visible_navigation_url_r44d('https://www.reddit.com/user/example/', 'example', 'posts_and_crossposts').endswith('/submitted/')
    assert build_reddit_visible_navigation_url_r44d('https://www.reddit.com/user/example/', 'example', 'posts_and_comments').endswith('/comments/')
    post_url = 'https://www.reddit.com/r/example/comments/abc123/title/'
    assert build_reddit_visible_navigation_url_r44d(post_url, 'r_example', 'posts_and_comments') == post_url


def test_fixture_extracts_post_crosspost_comment_and_media() -> None:
    html = build_fake_reddit_visible_dom_html_r44d('example_redditor', 'posts_and_comments')
    records, media = extract_reddit_visible_records_from_dom_r44d(
        html,
        account_handle='example_redditor',
        account_url='https://www.reddit.com/user/example_redditor/',
        navigation_url='https://www.reddit.com/user/example_redditor/comments/',
        capture_timestamp='20260918T103000Z',
        feed_mode='posts_and_comments',
        include_media=True,
        max_items=5,
    )
    record_types = {row.record_type for row in records}
    assert {'post', 'repost_or_reshare', 'reply'} <= record_types
    assert media['bound_media_count'] >= 4
    assert all(item.metadata_only_remote_media_not_downloaded for row in records for item in row.media_items)


def test_run_writes_r43u_ledger() -> None:
    root = Path('profile_media_live_captures/r44d_reddit_visible_dom_capture_test/run')
    result = run_reddit_visible_dom_capture_r44d(
        RedditVisibleDomCaptureRequestR44D(
            account_url='https://www.reddit.com/user/example_redditor/',
            account_handle='example_redditor',
            capture_timestamp='20260918T103000Z',
            output_root=str(root),
            fixture_mode=True,
            feed_mode='posts_and_comments',
            include_comments=True,
            max_items=5,
        )
    )
    assert result.status == R44D_PASS_STATUS, result.to_dict()
    assert result.ledger_status == R43U_PASS_STATUS
    assert result.record_count >= 3
    assert result.media_count >= 4
    assert result.screenshot_count >= 3
    assert Path(result.account_record_path).is_file()
    assert Path(result.media_index_path).is_file()


def test_report_passes_and_route_reaches_reddit_adapter() -> None:
    report = build_report('profile_media_live_captures/r44d_reddit_visible_dom_capture_test/report')
    payload = report.to_dict()
    assert report.status == R44D_PASS_STATUS, payload
    assert payload['route_sample']['platform_id'] == 'reddit'
    assert payload['route_sample']['downstream_status'] == R44D_PASS_STATUS
    assert payload['sample_result']['record_count'] >= 3
    assert payload['sample_result']['media_count'] >= 4


def test_contract_safe_boundaries() -> None:
    contract = build_reddit_visible_dom_capture_contract_r44d()
    assert contract['record_mapping']['reddit_comment'] == 'reply'
    assert contract['record_mapping']['reddit_crosspost'] == 'repost_or_reshare'
    assert contract['no_remote_media_downloads'] is True
    assert contract['no_cookie_token_or_browser_profile_copying'] is True


def run_self_test() -> None:
    test_navigation_modes()
    test_fixture_extracts_post_crosspost_comment_and_media()
    test_run_writes_r43u_ledger()
    test_report_passes_and_route_reaches_reddit_adapter()
    test_contract_safe_boundaries()


if __name__ == '__main__':
    run_self_test()
    print('profile_media_reddit_visible_dom_capture_r44d_test: PASS')
