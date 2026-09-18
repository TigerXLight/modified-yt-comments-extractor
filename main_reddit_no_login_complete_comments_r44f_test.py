from pathlib import Path


def test_main_registers_r44f() -> None:
    text = Path('main.py').read_text(encoding='utf-8', errors='replace')
    assert 'reddit_no_login_complete_comments_r44f' in text
    assert 'build_reddit_no_login_complete_comments_r44f' in text
    assert 'profile_media_reddit_no_login_complete_comments_r44f' in text


def run_self_test() -> None:
    test_main_registers_r44f()


if __name__ == '__main__':
    run_self_test()
    print('main_reddit_no_login_complete_comments_r44f_test: PASS')
