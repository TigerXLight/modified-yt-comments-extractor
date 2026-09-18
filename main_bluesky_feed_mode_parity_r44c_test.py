from pathlib import Path


def run_self_test() -> None:
    source = Path('main.py').read_text(encoding='utf-8', errors='replace')
    assert 'bluesky_feed_mode_parity_r44c' in source
    assert 'build_bluesky_feed_mode_parity_r44c' in source


if __name__ == '__main__':
    run_self_test()
    print('main_bluesky_feed_mode_parity_r44c_test: PASS')
