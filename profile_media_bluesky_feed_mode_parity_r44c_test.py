from pathlib import Path

from profile_media_bluesky_feed_mode_parity_r44c import R44C_PASS_STATUS, build_report


def run_self_test() -> None:
    out = Path('profile_media_live_captures/r44c_bluesky_feed_mode_parity_test')
    report = build_report(out)
    assert report.status == R44C_PASS_STATUS, report.to_dict()
    payload = report.to_dict()
    public = payload['public_appview_sample']
    assert public['repost_record_type'] == 'repost_or_reshare'
    assert public['reply_record_type'] == 'reply'
    assert public['posts_reposts_filter'] == 'posts_and_author_threads'
    assert public['posts_replies_filter'] == 'posts_with_replies'
    assert public['post_url_preserved_in_visible_navigation'].endswith('/post/3lynwu7hy4c2w')
    visible_replies = payload['visible_replies_sample']
    assert visible_replies['feed_mode'] == 'posts_and_replies'
    assert visible_replies['navigation_url'].endswith('/replies')
    assert visible_replies['record_count'] >= 2
    assert visible_replies['media_count'] >= 3
    visible_reposts = payload['visible_reposts_sample']
    assert visible_reposts['feed_mode'] == 'posts_and_reposts'
    assert not visible_reposts['navigation_url'].endswith('/replies')
    assert visible_reposts['record_count'] >= 2
    assert visible_reposts['media_count'] >= 3
    smoke = payload['smoke_request_sample']
    assert smoke['feed_mode'] == 'posts_and_replies'
    assert smoke['navigation_url'].endswith('/replies')


if __name__ == '__main__':
    run_self_test()
    print('profile_media_bluesky_feed_mode_parity_r44c_test: PASS')
