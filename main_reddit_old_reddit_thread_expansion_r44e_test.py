from pathlib import Path


def test_main_registers_r44e() -> None:
    text = Path('main.py').read_text(encoding='utf-8', errors='replace')
    assert 'reddit_old_reddit_thread_expansion_r44e' in text
    assert 'build_reddit_old_reddit_thread_expansion_r44e' in text
    assert 'profile_media_reddit_old_reddit_thread_expansion_r44e' in text


def run_self_test() -> None:
    test_main_registers_r44e()


if __name__ == '__main__':
    run_self_test()
    print('main_reddit_old_reddit_thread_expansion_r44e_test: PASS')
