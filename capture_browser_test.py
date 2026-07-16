from capture_browser import (
    BrowserCaptureRequest,
    BrowserPageSnapshot,
    capture_browser_page,
    is_allowed_browser_capture_url,
)
from capture_fixture_server import CaptureFixtureServer
from capture_status import (
    CAPTURE_STATUS_DEPENDENCY_MISSING,
    CAPTURE_STATUS_FAILED,
    CAPTURE_STATUS_SUCCESS,
    CAPTURE_STATUS_UNSUPPORTED,
)


def test_browser_request_and_snapshot_are_primitive() -> None:
    request = BrowserCaptureRequest(url="http://127.0.0.1:1234/article/static")
    data = request.to_dict()

    assert data["url"] == request.url
    assert data["allowed_hostnames"] == ["127.0.0.1", "localhost", "::1"]

    snapshot = BrowserPageSnapshot(
        status=CAPTURE_STATUS_SUCCESS,
        url=request.url,
        final_url=request.url,
        title="Fixture",
        html="<html></html>",
        text="Fixture text",
        screenshot_png=b"abc",
        status_code=200,
        engine="fake",
    )
    snapshot_data = snapshot.to_dict()
    assert snapshot_data["screenshot_bytes"] == 3
    assert snapshot_data["html"] == "<html></html>"
    assert "no external site access" in snapshot_data["scope"]


def test_browser_capture_rejects_non_localhost_by_default_before_runner() -> None:
    called = {"value": False}

    def runner(request: BrowserCaptureRequest):
        called["value"] = True
        return {"status": CAPTURE_STATUS_SUCCESS}

    snapshot = capture_browser_page(
        BrowserCaptureRequest(url="https://example.com/article"),
        runner=runner,
    )

    assert snapshot.status == CAPTURE_STATUS_UNSUPPORTED
    assert called["value"] is False
    assert "localhost fixture" in snapshot.warnings[0]


def test_browser_capture_uses_injected_runner_for_local_fixture() -> None:
    with CaptureFixtureServer() as server:
        request = BrowserCaptureRequest(url=server.url_for_fixture("article_static"))

        def runner(received: BrowserCaptureRequest):
            assert received == request
            return {
                "status": CAPTURE_STATUS_SUCCESS,
                "final_url": request.url,
                "title": "Static Fixture Article",
                "html": "<main>Static Fixture Article</main>",
                "text": "Static Fixture Article",
                "screenshot_png": b"png",
                "status_code": 200,
                "engine": "fake_playwright",
            }

        snapshot = capture_browser_page(request, runner=runner)

    assert snapshot.status == CAPTURE_STATUS_SUCCESS
    assert snapshot.title == "Static Fixture Article"
    assert snapshot.engine == "fake_playwright"
    assert snapshot.screenshot_png == b"png"


def test_browser_capture_runner_failure_is_non_secret() -> None:
    with CaptureFixtureServer() as server:
        request = BrowserCaptureRequest(url=server.url_for_fixture("article_static"))

        def runner(received: BrowserCaptureRequest):
            raise RuntimeError("secret-token-should-not-escape")

        snapshot = capture_browser_page(request, runner=runner)

    assert snapshot.status == CAPTURE_STATUS_FAILED
    assert snapshot.engine == "injected_runner"
    assert snapshot.warnings == ("Injected browser runner failed with a non-secret exception.",)
    assert "secret-token" not in repr(snapshot.to_dict())


def test_browser_capture_reports_missing_playwright_without_import_side_effects() -> None:
    with CaptureFixtureServer() as server:
        snapshot = capture_browser_page(
            BrowserCaptureRequest(url=server.url_for_fixture("article_static"))
        )

    # The test environment may eventually install Playwright. If so, localhost
    # capture can succeed. If only the package or browser binary is missing, the
    # runtime must still return a fixed safe status rather than raising.
    assert snapshot.status in {
        CAPTURE_STATUS_DEPENDENCY_MISSING,
        CAPTURE_STATUS_FAILED,
        CAPTURE_STATUS_SUCCESS,
    }
    assert snapshot.engine in {"playwright", "playwright_chromium"}


def test_allowed_url_helper_is_strict() -> None:
    assert is_allowed_browser_capture_url(
        "http://127.0.0.1:1000/article/static",
        ("127.0.0.1", "localhost"),
    )
    assert is_allowed_browser_capture_url(
        "http://localhost:1000/article/static",
        ("127.0.0.1", "localhost"),
    )
    assert not is_allowed_browser_capture_url(
        "file:///tmp/article.html",
        ("127.0.0.1", "localhost"),
    )
    assert not is_allowed_browser_capture_url(
        "https://example.com/article",
        ("127.0.0.1", "localhost"),
    )


def run_self_test() -> None:
    test_browser_request_and_snapshot_are_primitive()
    test_browser_capture_rejects_non_localhost_by_default_before_runner()
    test_browser_capture_uses_injected_runner_for_local_fixture()
    test_browser_capture_runner_failure_is_non_secret()
    test_browser_capture_reports_missing_playwright_without_import_side_effects()
    test_allowed_url_helper_is_strict()


if __name__ == "__main__":
    run_self_test()
    print("Capture browser self-test passed.")
