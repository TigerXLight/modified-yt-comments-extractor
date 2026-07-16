from urllib.error import HTTPError
from urllib.request import Request, urlopen

from capture_fixture_server import (
    CaptureFixtureServer,
    available_capture_fixtures,
    capture_fixture_catalog_to_dict,
    fixture_by_id,
)


def _read_url(url: str, *, method: str = "GET") -> tuple[int, str]:
    request = Request(url, method=method)
    with urlopen(request, timeout=5) as response:
        return response.status, response.read().decode("utf-8")


def test_fixture_catalog_contains_required_rev4_routes() -> None:
    fixture_ids = {fixture.fixture_id for fixture in available_capture_fixtures()}

    for fixture_id in (
        "article_static",
        "comments_challenge",
        "comments_cursor",
        "comments_iframe",
        "comments_load_more",
        "comments_login_required",
        "comments_scroll_container",
        "comments_shadow_closed",
        "comments_shadow_open",
        "comments_virtualized",
        "comments_encoded",
        "livechat_dom",
        "livechat_iframe",
        "livechat_websocket",
        "media_playback",
        "archive_status",
    ):
        assert fixture_id in fixture_ids

    data = capture_fixture_catalog_to_dict()
    assert data["fixture_count"] == len(fixture_ids)
    assert "no external network" in data["scope"]


def test_local_fixture_server_serves_only_localhost_routes() -> None:
    with CaptureFixtureServer() as server:
        assert server.base_url.startswith("http://127.0.0.1:")
        status, body = _read_url(server.url_for_fixture("article_static"))

        assert status == 200
        assert "Static Fixture Article" in body
        assert fixture_by_id("article_static").route == "/article/static"


def test_fixture_server_supports_head_and_expected_404() -> None:
    with CaptureFixtureServer() as server:
        status, body = _read_url(server.url_for_route("/comments/static"), method="HEAD")
        assert status == 200
        assert body == ""

        try:
            _read_url(server.url_for_route("/missing"))
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("missing fixture route should return 404")


def test_error_fixture_returns_expected_local_500() -> None:
    with CaptureFixtureServer() as server:
        try:
            _read_url(server.url_for_fixture("error_500"))
        except HTTPError as exc:
            assert exc.code == 500
            assert exc.read().decode("utf-8") == "server error fixture"
        else:
            raise AssertionError("error fixture should return HTTP 500")


def run_self_test() -> None:
    test_fixture_catalog_contains_required_rev4_routes()
    test_local_fixture_server_serves_only_localhost_routes()
    test_fixture_server_supports_head_and_expected_404()
    test_error_fixture_returns_expected_local_500()


if __name__ == "__main__":
    run_self_test()
    print("Capture fixture server self-test passed.")
