from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def main():
    for rel in ("twitter_route_strategy.py","twitter_route_strategy_test.py","twitter_reference_pack_index.py","twitter_reference_pack_index_test.py","tools/build_twitter_route_strategy_v69.py","tools/index_twitter_reference_pack_v69.py"):
        assert (ROOT / rel).exists(), rel
    rs = (ROOT / "twitter_route_strategy.py").read_text(encoding="utf-8")
    assert "strict_user_tweets_rate_limit" in rs
    assert "list_workaround_not_guaranteed_complete" in rs
    assert "stop_when_api_returns_no_next_page_data" in rs
    assert "isolate_test_account_recommended" in rs
    ps = (ROOT / "twitter_reference_pack_index.py").read_text(encoding="utf-8")
    assert "twitter_api_export" in ps
    assert "media_discovery_and_native_helper" in ps
    assert "screenshot_render_pdf" in ps
    print("assert_twitter_route_strategy_and_reference_pack_v69 OK")
if __name__ == "__main__":
    main()
