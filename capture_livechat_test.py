from urllib.request import urlopen

from capture_fixture_server import CaptureFixtureServer
from capture_fixture_server import fixture_by_id
from capture_livechat import (
    LIVECHAT_STOP_MESSAGE_LIMIT,
    LivechatScreenshotFrame,
    extract_livechat_events_from_html,
)
from capture_status import CAPTURE_STATUS_PARTIAL, CAPTURE_STATUS_SUCCESS


def test_extract_livechat_events_from_supplied_html() -> None:
    result = extract_livechat_events_from_html(
        """
        <section id="livechat">
          <p data-event-id="m1" data-author="Alice" data-timestamp="00:01"
            data-service-timestamp="1.0" data-observed-at="2026-07-16T10:00:01Z">Hello chat</p>
          <p data-event-id="m2" data-author="Bob" data-event-type="paid">Pinned message</p>
        </section>
        """,
        source_url="http://127.0.0.1/livechat/dom",
    )

    assert result.status == CAPTURE_STATUS_SUCCESS
    assert [event.event_id for event in result.events] == ["m1", "m2"]
    assert result.events[0].author == "Alice"
    assert result.events[0].timestamp_label == "00:01"
    assert result.events[0].service_timestamp == "1.0"
    assert result.events[0].observed_at == "2026-07-16T10:00:01Z"
    assert result.events[1].event_type == "paid"
    assert result.events[1].ordinal == 2
    assert "no fetch" in result.scope


def test_extract_livechat_detects_duplicates_and_ignores_scripts() -> None:
    result = extract_livechat_events_from_html(
        """
        <p data-event-id="m1">Keep this</p>
        <p data-event-id="m1">Duplicate this</p>
        <script><p data-event-id="hidden">Hidden</p></script>
        """
    )

    assert [event.event_id for event in result.events] == ["m1"]
    assert result.duplicate_event_ids == ("m1",)
    assert "hidden" not in repr(result.to_dict())
    assert any("Duplicate livechat event IDs" in warning for warning in result.warnings)


def test_extract_livechat_reports_empty_html_as_partial() -> None:
    result = extract_livechat_events_from_html("<html><body>No chat here</body></html>")

    assert result.status == CAPTURE_STATUS_PARTIAL
    assert result.events == ()
    assert "No livechat events found" in result.warnings[0]


def test_extract_livechat_from_localhost_fixture() -> None:
    with CaptureFixtureServer() as server:
        url = server.url_for_fixture("livechat_dom")
        with urlopen(url, timeout=5) as response:
            html = response.read().decode("utf-8")

    result = extract_livechat_events_from_html(html, source_url=url)
    assert [event.message for event in result.events] == ["Hello chat", "Reconnected", "Removed message"]
    assert result.reconnect_count == 1
    assert result.removed_event_ids == ("m3",)


def test_extract_livechat_records_bounds_reconnect_and_removal_metadata() -> None:
    result = extract_livechat_events_from_html(
        """
        <section id="livechat">
          <p data-event-id="m1">First</p>
          <p data-event-id="m1">Duplicate first</p>
          <p data-event-id="m2" data-event-type="reconnect">Reconnect</p>
          <p data-event-id="m3" data-event-type="removed" data-removed="true">Removed</p>
          <p data-event-id="m4">Past limit</p>
        </section>
        """,
        duration_limit_seconds=60,
        message_limit=3,
    )

    assert [event.event_id for event in result.events] == ["m1", "m2", "m3"]
    assert result.duplicate_event_ids == ("m1",)
    assert result.duration_limit_seconds == 60
    assert result.message_limit == 3
    assert result.stop_reason == LIVECHAT_STOP_MESSAGE_LIMIT
    assert result.reconnect_count == 1
    assert result.removed_event_ids == ("m3",)


def test_livechat_screenshot_frames_are_supporting_metadata_only() -> None:
    frame = LivechatScreenshotFrame(
        frame_id="frame-1",
        timestamp_label="00:10",
        relative_path="livechat/frames/frame-1.png",
        sha256="abc123",
        complete_chat_capture=True,
    )
    result = extract_livechat_events_from_html(
        fixture_by_id("livechat_dom").body,
        screenshot_frames=(frame,),
    )

    assert result.screenshot_frames[0].complete_chat_capture is False
    assert "not a complete livechat capture" in result.screenshot_frames[0].note
    assert any("not complete chat capture" in warning for warning in result.warnings)


def run_self_test() -> None:
    test_extract_livechat_events_from_supplied_html()
    test_extract_livechat_detects_duplicates_and_ignores_scripts()
    test_extract_livechat_reports_empty_html_as_partial()
    test_extract_livechat_from_localhost_fixture()
    test_extract_livechat_records_bounds_reconnect_and_removal_metadata()
    test_livechat_screenshot_frames_are_supporting_metadata_only()


if __name__ == "__main__":
    run_self_test()
    print("Capture livechat self-test passed.")
