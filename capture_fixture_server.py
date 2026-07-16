from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import urlsplit


FIXTURE_SERVER_SCOPE = (
    "localhost fixture server only; no external network, scraping, browser automation, "
    "download, archive, credential, provider, or GUI behavior"
)


@dataclass(frozen=True)
class CaptureFixture:
    fixture_id: str
    route: str
    expected: str
    status: str = "REQUIRED"
    content_type: str = "text/html; charset=utf-8"
    body: str = ""
    binary_body: bytes = b""

    def to_dict(self) -> dict[str, Any]:
        return {
            "body": self.body,
            "content_type": self.content_type,
            "expected": self.expected,
            "fixture_id": self.fixture_id,
            "route": self.route,
            "status": self.status,
        }

    @property
    def payload(self) -> bytes:
        return self.binary_body if self.binary_body else self.body.encode("utf-8")


def _html(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head>"
        f"<title>{title}</title>"
        "<meta charset=\"utf-8\">"
        "</head><body>"
        f"{body}"
        "</body></html>"
    )


CAPTURE_FIXTURES: tuple[CaptureFixture, ...] = (
    CaptureFixture(
        fixture_id="article_static",
        route="/article/static",
        expected="article semantic + outline + faithful screenshot",
        body=_html(
            "Static Fixture Article",
            "<main><article><h1>Static Fixture Article</h1><p>Alpha article paragraph.</p></article></main>",
        ),
    ),
    CaptureFixture(
        fixture_id="article_js",
        route="/article/js",
        expected="rendered article",
        body=_html(
            "Rendered Fixture Article",
            "<main id=\"app\"><article><h1>Rendered Fixture Article</h1><p>Rendered content placeholder.</p></article></main>",
        ),
    ),
    CaptureFixture(
        fixture_id="article_chrome_heavy",
        route="/article/chrome-heavy",
        expected="exclude chrome/ads/comments",
        body=_html(
            "Chrome Heavy Fixture",
            "<nav>Navigation</nav>"
            "<main><article><h1>Chrome Heavy Fixture</h1><p>Primary story.</p></article></main>"
            "<aside class=\"advert\">Advertisement</aside>"
            "<section id=\"comments\"><p>Fixture comment should not be article text.</p></section>",
        ),
    ),
    CaptureFixture(
        fixture_id="article_low_confidence",
        route="/article/low-confidence",
        expected="reviewable low confidence",
        body=_html("Low Confidence Fixture", "<div><span>Loose text without article semantics.</span></div>"),
    ),
    CaptureFixture(
        fixture_id="paywall",
        route="/article/paywall",
        expected="visible preview/paywall only",
        body=_html("Paywall Fixture", "<main><p>Preview paragraph.</p><div data-paywall=\"true\">Subscribe to continue.</div></main>"),
    ),
    CaptureFixture(
        fixture_id="comments_static",
        route="/comments/static",
        expected="threaded comments",
        body=_html(
            "Comments Static Fixture",
            """
            <section id="comments">
              <article data-comment-id="c1" data-thread-id="t1" data-author="Alice"
                data-posted-at="2026-07-16T10:00:00Z" data-reactions="3"
                data-reply-count="1" data-permalink="/comments/c1" data-source-order="1">
                First comment
              </article>
              <article data-comment-id="c2" data-thread-id="t1" data-author="Bob"
                data-parent-id="c1" data-depth="1" data-posted-at="2026-07-16T10:01:00Z"
                data-permalink="/comments/c2" data-source-order="2">
                Reply comment
              </article>
            </section>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_load_more",
        route="/comments/load-more",
        expected="load-more loop",
        body=_html(
            "Load More Comments Fixture",
            """
            <section id="comments">
              <article data-comment-id="lm1" data-loaded-order="1">Loaded first page</article>
            </section>
            <button id="load-more" data-load-more="true">Load more</button>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_cursor",
        route="/comments/cursor",
        expected="cursor exhaustion",
        body=_html(
            "Cursor Comments Fixture",
            """
            <article data-comment-id="cur1" data-loaded-order="2">Cursor page comment</article>
            <script type="application/json" id="cursor-state">{"cursor":"end","stop_reason":"cursor_exhausted"}</script>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_infinite",
        route="/comments/infinite",
        expected="no-new-ID stop",
        body=_html(
            "Infinite Comments Fixture",
            """
            <section id="infinite-comments" data-stop="no-new-id">
              <article data-comment-id="inf1" data-loaded-order="3">Infinite first</article>
              <article data-comment-id="inf2" data-loaded-order="4">Infinite second</article>
            </section>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_iframe",
        route="/comments/iframe",
        expected="frame capture",
        body=_html("Iframe Comments Fixture", "<iframe src=\"/comments/static\" title=\"comments\"></iframe>"),
    ),
    CaptureFixture(
        fixture_id="comments_shadow_open",
        route="/comments/shadow-open",
        expected="open root",
        body=_html(
            "Open Shadow Fixture",
            "<div id=\"shadow-host\" data-shadow=\"open\"><article data-comment-id=\"sh-open-1\">Open shadow comment</article></div>",
        ),
    ),
    CaptureFixture(
        fixture_id="comments_shadow_closed",
        route="/comments/shadow-closed",
        expected="early hook/extension fallback",
        body=_html(
            "Closed Shadow Fixture",
            """
            <div id="shadow-host" data-shadow="closed">Closed shadow host</div>
            <script type="application/json" id="closed-shadow-comments">{"comments":[{"id":"sh-closed-1","text":"Closed shadow payload comment","capture_method":"adapter_scoped_payload"}]}</script>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_virtualized",
        route="/comments/virtualized",
        expected="recycled DOM incremental persistence",
        body=_html(
            "Virtualized Comments Fixture",
            """
            <section data-virtualized="true">
              <article data-comment-id="visible-1" data-loaded-order="1">Visible recycled row</article>
              <article data-comment-id="visible-1" data-loaded-order="2">Visible recycled duplicate</article>
              <article data-comment-id="visible-2" data-loaded-order="3">Second persisted row</article>
            </section>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_disappearing",
        route="/comments/disappearing",
        expected="tombstones/first-last seen",
        body=_html(
            "Disappearing Comments Fixture",
            """
            <section data-disappearing="true">
              <article data-comment-id="gone-1" data-state="deleted">Comment deleted by author</article>
            </section>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_encoded",
        route="/comments/encoded",
        expected="page-decoded structured state",
        body=_html(
            "Encoded Comments Fixture",
            """
            <script type="application/json" id="encoded-comments">{"comments":[{"id":"encoded-1","author":"Encoded User","text":"Encoded decoded comment","permalink":"/comments/encoded-1"}]}</script>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_scroll_container",
        route="/comments/scroll-container",
        expected="nested scrollable container",
        body=_html(
            "Nested Container Comments Fixture",
            """
            <div id="comments-scroll-container" data-scroll-container="true">
              <article data-comment-id="nested-1">Nested container comment</article>
            </div>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="comments_login_required",
        route="/comments/login-required",
        expected="login required detected without bypass",
        body=_html(
            "Login Required Comments Fixture",
            "<main data-login-required=\"true\"><h1>Sign in to view comments</h1></main>",
        ),
    ),
    CaptureFixture(
        fixture_id="comments_challenge",
        route="/comments/challenge",
        expected="challenge detected without bypass",
        body=_html(
            "Challenge Comments Fixture",
            "<main data-challenge-required=\"true\"><h1>Challenge required</h1></main>",
        ),
    ),
    CaptureFixture(
        fixture_id="challenge",
        route="/challenge",
        expected="pause/resume manual simulation",
        body=_html("Challenge Fixture", "<main><h1>Challenge simulation</h1><button>Continue</button></main>"),
    ),
    CaptureFixture(
        fixture_id="livechat_dom",
        route="/livechat/dom",
        expected="bounded DOM mutation stream",
        body=_html(
            "Livechat DOM Fixture",
            """
            <section id="livechat" data-duration-limit-seconds="120" data-message-limit="100">
              <p data-event-id="m1" data-author="Alice" data-timestamp="00:01" data-service-timestamp="1.0">Hello chat</p>
              <p data-event-id="m2" data-author="Bob" data-timestamp="00:02" data-event-type="reconnect">Reconnected</p>
              <p data-event-id="m3" data-author="Mod" data-event-type="removed" data-removed="true">Removed message</p>
            </section>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="livechat_websocket",
        route="/livechat/websocket",
        expected="bounded WebSocket stream",
        body=_html("Livechat WebSocket Fixture", "<script>window.fixtureWebSocketRoute='/ws/livechat';</script>"),
    ),
    CaptureFixture(
        fixture_id="livechat_iframe",
        route="/livechat/iframe",
        expected="frame-hosted bounded livechat",
        body=_html("Livechat Iframe Fixture", "<iframe src=\"/livechat/dom\" title=\"livechat\"></iframe>"),
    ),
    CaptureFixture(
        fixture_id="media_basic",
        route="/media/basic",
        expected="direct DOM media references",
        body=_html(
            "Media Basic Fixture",
            """
            <video src="/media/sample-video.mp4" poster="/media/poster.jpg" type="video/mp4"></video>
            <audio src="/media/sample-audio.m4a" type="audio/mp4"></audio>
            <img src="/media/still.jpg" alt="Fixture still">
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="media_srcset",
        route="/media/srcset",
        expected="picture/srcset references",
        body=_html(
            "Media Srcset Fixture",
            """
            <picture>
              <source srcset="/media/still-large.webp 2x, /media/still-small.webp 1x" type="image/webp">
              <img src="/media/still.jpg" alt="Responsive still">
            </picture>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="media_css",
        route="/media/css",
        expected="CSS media reference fixture for future parser coverage",
        body=_html("Media CSS Fixture", "<div class=\"hero\" style=\"background-image:url('/media/still.jpg')\">Hero</div>"),
    ),
    CaptureFixture(
        fixture_id="media_iframe",
        route="/media/iframe",
        expected="iframe/embed/object media candidates",
        body=_html(
            "Media Iframe Fixture",
            """
            <iframe src="/media/player-frame.html" title="fixture player"></iframe>
            <embed src="/media/embedded-player.swf" type="application/x-shockwave-flash">
            <object data="/media/object-video.mp4" type="video/mp4"></object>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="media_playback",
        route="/media/playback",
        expected="playback-triggered discovery",
        body=_html(
            "Media Playback Fixture",
            """
            <video controls data-playback-required="true" src="/media/sample-video.mp4"></video>
            <script type="application/json" id="playback-events">[{"event_id":"playback-1","url":"/media/segment-1.m4s","mime_type":"video/iso.segment","component_role":"video"}]</script>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="media_blob",
        route="/media/blob",
        expected="blob/MediaSource route",
        body=_html("Media Blob Fixture", "<video controls data-fixture=\"blob\"></video>"),
    ),
    CaptureFixture(
        fixture_id="media_mse",
        route="/media/mse",
        expected="MediaSource segments",
        body=_html("MediaSource Fixture", "<video controls data-fixture=\"mse\"></video>"),
    ),
    CaptureFixture(
        fixture_id="media_hls",
        route="/media/hls",
        expected="synthetic HLS manifest reference",
        body=_html("Media HLS Fixture", "<video controls><source src=\"/media/playlist.m3u8\" type=\"application/vnd.apple.mpegurl\" data-presentation-id=\"hls-main\"></video>"),
    ),
    CaptureFixture(
        fixture_id="media_dash",
        route="/media/dash",
        expected="synthetic DASH manifest reference",
        body=_html("Media DASH Fixture", "<video controls><source src=\"/media/manifest.mpd\" type=\"application/dash+xml\" data-presentation-id=\"dash-main\"></video>"),
    ),
    CaptureFixture(
        fixture_id="media_separate_av",
        route="/media/separate-av",
        expected="separate audio/video components",
        body=_html(
            "Separate A/V Fixture",
            """
            <video data-component-role="video" data-presentation-id="presentation-1">
              <source src="/media/video-track.mp4" type="video/mp4" data-component-role="video" data-codec="avc1" data-resolution="1920x1080">
            </video>
            <audio data-component-role="audio" data-presentation-id="presentation-1">
              <source src="/media/audio-track.m4a" type="audio/mp4" data-component-role="audio" data-language="en">
            </audio>
            """,
        ),
    ),
    CaptureFixture(
        fixture_id="media_signed",
        route="/media/signed",
        expected="signed expiring URL metadata",
        body=_html(
            "Signed Media Fixture",
            "<video src=\"/media/signed-video.mp4?sig=fixture\" data-signed-url=\"true\" data-expiry-hint=\"2026-07-16T12:00:00Z\"></video>",
        ),
    ),
    CaptureFixture(
        fixture_id="media_drm_simulated",
        route="/media/drm-simulated",
        expected="simulated protected output marker",
        body=_html("DRM Simulated Media Fixture", "<video data-fixture=\"mse\" data-drm-state=\"suspected\"></video>"),
    ),
    CaptureFixture(
        fixture_id="media_audio_video_split",
        route="/media/audio-video-split",
        expected="separate audio/video components",
        body=_html("Split Media Fixture", "<video data-video-track=\"v1\" data-audio-track=\"a1\"></video>"),
    ),
    CaptureFixture(
        fixture_id="media_player_frame",
        route="/media/player-frame.html",
        expected="local player iframe fixture",
        body=_html("Player Frame", "<video src=\"/media/sample-video.mp4\"></video>"),
    ),
    CaptureFixture(
        fixture_id="media_playlist_m3u8",
        route="/media/playlist.m3u8",
        expected="synthetic HLS manifest payload",
        content_type="application/vnd.apple.mpegurl",
        body="#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1280000\n/media/hls-video.m3u8\n",
    ),
    CaptureFixture(
        fixture_id="media_manifest_mpd",
        route="/media/manifest.mpd",
        expected="synthetic DASH manifest payload",
        content_type="application/dash+xml",
        body="<MPD><Period><AdaptationSet mimeType=\"video/mp4\" /></Period></MPD>",
    ),
    CaptureFixture(
        fixture_id="sample_video_mp4",
        route="/media/sample-video.mp4",
        expected="tiny local fixture media payload",
        content_type="video/mp4",
        binary_body=b"fixture-video-bytes",
    ),
    CaptureFixture(
        fixture_id="sample_audio_m4a",
        route="/media/sample-audio.m4a",
        expected="tiny local fixture audio payload",
        content_type="audio/mp4",
        binary_body=b"fixture-audio-bytes",
    ),
    CaptureFixture(
        fixture_id="sample_video_track_mp4",
        route="/media/video-track.mp4",
        expected="tiny local fixture video component",
        content_type="video/mp4",
        binary_body=b"fixture-video-component-bytes",
    ),
    CaptureFixture(
        fixture_id="sample_audio_track_m4a",
        route="/media/audio-track.m4a",
        expected="tiny local fixture audio component",
        content_type="audio/mp4",
        binary_body=b"fixture-audio-component-bytes",
    ),
    CaptureFixture(
        fixture_id="sample_still_jpg",
        route="/media/still.jpg",
        expected="tiny local fixture still payload",
        content_type="image/jpeg",
        binary_body=b"fixture-jpeg-bytes",
    ),
    CaptureFixture(
        fixture_id="sample_poster_jpg",
        route="/media/poster.jpg",
        expected="tiny local fixture poster payload",
        content_type="image/jpeg",
        binary_body=b"fixture-poster-bytes",
    ),
    CaptureFixture(
        fixture_id="sample_signed_video_mp4",
        route="/media/signed-video.mp4",
        expected="tiny local signed fixture media payload",
        content_type="video/mp4",
        binary_body=b"fixture-signed-video-bytes",
    ),
    CaptureFixture(
        fixture_id="archive_status",
        route="/archive/status",
        expected="mock archive status responses",
        content_type="application/json; charset=utf-8",
        body="{\"wayback\":\"FOUND\",\"archive_today\":\"NOT_FOUND_CONFIRMED\"}",
    ),
    CaptureFixture(
        fixture_id="archive_challenge",
        route="/archive/challenge",
        expected="mock archive challenge",
        body=_html("Archive Challenge Fixture", "<main><h1>Archive challenge</h1></main>"),
    ),
    CaptureFixture(
        fixture_id="snapshot_mismatch",
        route="/snapshot/mismatch",
        expected="detect unstable page",
        body=_html("Snapshot Mismatch Fixture", "<main data-version=\"1\">Versioned content</main>"),
    ),
    CaptureFixture(
        fixture_id="error_500",
        route="/error/500",
        expected="load error",
        status="REQUIRED",
        body="server error fixture",
    ),
)

_FIXTURES_BY_ROUTE = {fixture.route: fixture for fixture in CAPTURE_FIXTURES}


class _CaptureFixtureRequestHandler(BaseHTTPRequestHandler):
    server_version = "CaptureFixtureServer/1.0"

    def _send_fixture(self, fixture: CaptureFixture, *, body: bool) -> None:
        status_code = 500 if fixture.route == "/error/500" else 200
        payload = fixture.payload
        self.send_response(status_code)
        self.send_header("Content-Type", fixture.content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if body:
            self.wfile.write(payload)

    def do_GET(self) -> None:
        route = urlsplit(self.path).path
        fixture = _FIXTURES_BY_ROUTE.get(route)
        if fixture is None:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"fixture not found")
            return
        self._send_fixture(fixture, body=True)

    def do_HEAD(self) -> None:
        route = urlsplit(self.path).path
        fixture = _FIXTURES_BY_ROUTE.get(route)
        if fixture is None:
            self.send_response(404)
            self.end_headers()
            return
        self._send_fixture(fixture, body=False)

    def log_message(self, format: str, *args: object) -> None:
        return


class CaptureFixtureServer:
    def __init__(self) -> None:
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            return ""
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> "CaptureFixtureServer":
        if self._server is not None:
            return self
        server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureFixtureRequestHandler)
        thread = Thread(target=server.serve_forever, name="capture-fixture-server", daemon=True)
        thread.start()
        self._server = server
        self._thread = thread
        return self

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=5)

    def url_for_route(self, route: str) -> str:
        normalized = route if route.startswith("/") else "/" + route
        return self.base_url + normalized

    def url_for_fixture(self, fixture_id: str) -> str:
        fixture = fixture_by_id(fixture_id)
        if fixture is None:
            raise ValueError(f"Unknown capture fixture id: {fixture_id}")
        return self.url_for_route(fixture.route)

    def __enter__(self) -> "CaptureFixtureServer":
        return self.start()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()


def available_capture_fixtures() -> tuple[CaptureFixture, ...]:
    return CAPTURE_FIXTURES


def fixture_by_id(fixture_id: str) -> CaptureFixture | None:
    normalized = str(fixture_id or "").strip()
    return next((fixture for fixture in CAPTURE_FIXTURES if fixture.fixture_id == normalized), None)


def capture_fixture_catalog_to_dict() -> dict[str, Any]:
    return {
        "fixture_count": len(CAPTURE_FIXTURES),
        "fixtures": [fixture.to_dict() for fixture in CAPTURE_FIXTURES],
        "scope": FIXTURE_SERVER_SCOPE,
    }
