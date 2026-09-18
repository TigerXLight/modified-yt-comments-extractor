from pathlib import Path


def test_main_registers_r44d() -> None:
    text = Path('main.py').read_text(encoding='utf-8', errors='replace')
    assert 'reddit_visible_dom_capture_r44d' in text
    assert 'build_reddit_visible_dom_capture_r44d' in text
    assert 'profile_media_reddit_visible_dom_capture_r44d' in text


def run_self_test() -> None:
    test_main_registers_r44d()


if __name__ == '__main__':
    run_self_test()
    print('main_reddit_visible_dom_capture_r44d_test: PASS')
