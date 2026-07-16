import os
from pathlib import Path
import tempfile

import main
from transcript_tools import TranscriptSegment


def _app() -> main.App:
    app = main.App.__new__(main.App)
    app.after_callbacks = {}
    app.after_cancelled = []
    app.after_next_id = 1
    app.transcript_playback_after_id = None
    app.transcript_playback_generation = 1
    app.transcript_playback_tick_ms = 30
    app.transcript_playback_backend = "vlc"
    app.transcript_vlc_max_interpolation_lead_seconds = 0.250
    app.transcript_timeline_center_lock_active = False
    app.transcript_authoritative_scrubbing = False
    app.transcript_position_scrubbing = False
    app.transcript_scrub_was_playing = False
    app._updating_transcript_timeline_pan_slider = False
    app.transcript_playback_debug_enabled = False
    app.transcript_playback_debug_ticks = []
    app._get_linked_media_duration_seconds = lambda: None

    def fake_after(_delay: int, callback):
        after_id = f"after-{app.after_next_id}"
        app.after_next_id += 1
        app.after_callbacks[after_id] = callback
        return after_id

    def fake_after_cancel(after_id: str) -> None:
        app.after_cancelled.append(after_id)
        app.after_callbacks.pop(after_id, None)

    app.after = fake_after
    app.after_cancel = fake_after_cancel
    return app


class FakePlayer:
    def __init__(self, times_ms: list[int]) -> None:
        self.times_ms = list(times_ms)
        self.index = 0

    def get_time(self) -> int:
        value = self.times_ms[min(self.index, len(self.times_ms) - 1)]
        self.index += 1
        return value

    def is_playing(self) -> bool:
        return True

    def get_state(self) -> str:
        return "Playing"


class FakeScrubPlayer:
    def __init__(self) -> None:
        self.pauses = 0
        self.plays = 0
        self.seek_times: list[int] = []

    def pause(self) -> None:
        self.pauses += 1

    def play(self) -> None:
        self.plays += 1

    def set_time(self, value: int) -> None:
        self.seek_times.append(value)


class FakeCanvas:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.created: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def delete(self, tag: str) -> None:
        self.deleted.append(tag)

    def create_polygon(self, *args: object, **kwargs: object) -> None:
        self.created.append(("polygon", args, kwargs))

    def create_line(self, *args: object, **kwargs: object) -> None:
        self.created.append(("line", args, kwargs))


def test_playback_scheduler_keeps_one_active_callback() -> None:
    app = _app()

    main.App._schedule_transcript_playback_tick(app)
    first_id = app.transcript_playback_after_id
    main.App._schedule_transcript_playback_tick(app)

    assert first_id in app.after_cancelled
    assert app.transcript_playback_after_id != first_id
    assert len(app.after_callbacks) == 1


def test_stale_playback_callback_is_ignored() -> None:
    app = _app()
    ticks = []
    app._tick_transcript_timeline_playback = lambda *, generation=None: ticks.append(generation)

    main.App._schedule_transcript_playback_tick(app)
    callback = app.after_callbacks[app.transcript_playback_after_id]
    app.transcript_playback_generation += 1
    callback()

    assert ticks == []


def test_center_lock_follow_tracks_playhead_without_threshold() -> None:
    app = _app()
    app._transcript_timeline_view = {
        "min_time": 0.0,
        "max_time": 10.0,
        "full_min_time": 0.0,
        "full_max_time": 100.0,
    }
    view_fractions = []
    position_fractions = []
    app._set_transcript_timeline_view_fraction = lambda fraction: (
        view_fractions.append(fraction),
        setattr(app, "transcript_timeline_view_fraction", fraction),
    )
    app._set_transcript_position_slider = lambda fraction: (
        position_fractions.append(fraction),
        setattr(app, "transcript_position_fraction", fraction),
    )

    moved_first = main.App._keep_transcript_playhead_visible(app, 5.0)
    moved_second = main.App._keep_transcript_playhead_visible(app, 8.0)

    assert moved_first is True
    assert moved_second is True
    assert app.transcript_timeline_center_lock_active is True
    assert app.transcript_timeline_center_time == 8.0
    assert view_fractions and 0.0 < view_fractions[-1] < 1.0
    assert position_fractions and 0.0 < position_fractions[-1] < 1.0


def test_center_playhead_view_fraction_and_position_slider_use_independent_durations() -> None:
    app = _app()
    app._transcript_timeline_view = {
        "min_time": 0.0,
        "max_time": 25.0,
        "full_min_time": 0.0,
        "full_max_time": 200.0,
    }
    app._get_linked_media_duration_seconds = lambda: 100.0
    view_fractions = []
    position_fractions = []
    app._set_transcript_timeline_view_fraction = lambda fraction: (
        view_fractions.append(round(float(fraction), 4)),
        setattr(app, "transcript_timeline_view_fraction", fraction),
    )
    app._set_transcript_position_slider = lambda fraction: (
        position_fractions.append(round(float(fraction), 4)),
        setattr(app, "transcript_position_fraction", fraction),
    )

    main.App._keep_transcript_playhead_visible(app, 50.0)

    assert view_fractions[-1] == 0.25
    assert position_fractions[-1] == 0.5


def test_interpolated_clock_moves_between_repeated_player_timestamps() -> None:
    app = _app()
    now = [10.0]
    app._transcript_playback_clock = lambda: now[0]
    app.transcript_vlc_player = FakePlayer([1000, 1000, 1000, 1100])
    app.transcript_playback_requested_start_seconds = 1.0
    app.transcript_playback_start_wall_time = 10.0
    app.transcript_vlc_clock_anchor_seconds = 1.0
    app.transcript_vlc_clock_anchor_wall_time = 10.0
    app.transcript_vlc_last_reported_seconds = None
    app.transcript_playhead_seconds = 1.0
    app._get_transcript_audio_sync_offset_seconds = lambda: 0.0
    app._get_transcript_timeline_bounds = lambda: (0.0, 10.0)
    app._is_transcript_vlc_playing = lambda: True

    first = main.App._update_transcript_playhead_from_playback_clock(app)
    now[0] = 10.033
    second = main.App._update_transcript_playhead_from_playback_clock(app)
    now[0] = 10.066
    third = main.App._update_transcript_playhead_from_playback_clock(app)

    assert first == 1.0
    assert second is not None and 1.02 < second < 1.05
    assert third is not None and second < third < 1.09


def test_tick_refreshes_when_center_locked_viewport_moves() -> None:
    app = _app()
    app.transcript_vlc_player = FakePlayer([1000])
    app._update_transcript_playhead_from_playback_clock = lambda: 1.25
    app._sync_transcript_selection_to_playback_time = lambda _seconds: None
    app._keep_transcript_playhead_visible = lambda _seconds: True
    app._draw_transcript_playhead_marker = lambda _seconds: True
    full_redraws: list[str] = []
    app._refresh_transcript_timeline = lambda: full_redraws.append("full")
    app._record_transcript_playback_debug_tick = lambda **kwargs: setattr(app, "last_debug", kwargs)
    app.transcript_timeline_zoom_level = 2.0

    main.App._tick_transcript_timeline_playback(app, generation=1)

    assert full_redraws == ["full"]
    assert app.last_debug["redraw_type"] == "viewport move"
    assert len(app.after_callbacks) == 1


def test_marker_draw_uses_fractional_position_without_full_refresh() -> None:
    app = _app()
    app.transcript_timeline_canvas = FakeCanvas()
    app._transcript_timeline_view = {
        "min_time": 0.0,
        "max_time": 10.0,
        "left_margin": 10,
        "top_margin": 20,
        "bottom_margin": 10,
        "timeline_width": 100,
        "canvas_height": 80,
    }

    assert main.App._draw_transcript_playhead_marker(app, 2.5) is True
    assert app.transcript_timeline_canvas.deleted == ["transcript_playhead_marker"]
    line = [item for item in app.transcript_timeline_canvas.created if item[0] == "line"][0]
    assert line[1][0] == 35.0


def test_center_locked_marker_draws_at_fixed_midpoint() -> None:
    app = _app()
    app.transcript_timeline_canvas = FakeCanvas()
    app._transcript_timeline_view = {
        "min_time": 2.0,
        "max_time": 7.0,
        "left_margin": 10,
        "top_margin": 20,
        "bottom_margin": 10,
        "timeline_width": 100,
        "canvas_height": 80,
        "center_lock": True,
    }

    assert main.App._draw_transcript_playhead_marker(app, 3.0) is True
    line = [item for item in app.transcript_timeline_canvas.created if item[0] == "line"][0]
    assert line[1][0] == 60.0


def test_position_slider_scrub_pauses_previews_and_seeks_once() -> None:
    app = _app()
    player = FakeScrubPlayer()
    app.transcript_vlc_player = player
    app.transcript_playback_after_id = "old-after"
    app.after_callbacks["old-after"] = lambda: None
    app._is_transcript_vlc_playing = lambda: True
    app._get_transcript_timeline_bounds = lambda: (0.0, 10.0)
    app._get_transcript_audio_sync_offset_seconds = lambda: 0.0
    app._transcript_playback_now = lambda: 100.0
    app._set_transcript_timeline_pan_slider = lambda fraction: setattr(
        app,
        "transcript_timeline_pan_fraction",
        max(0.0, min(1.0, float(fraction))),
    )
    app._refresh_transcript_timeline = lambda: None
    app._sync_transcript_selection_to_playback_time = lambda seconds: setattr(
        app,
        "synced_seconds",
        seconds,
    )
    app._update_transcript_playback_buttons = lambda playing: setattr(
        app,
        "buttons_playing",
        playing,
    )
    app._schedule_transcript_playback_tick = lambda: setattr(app, "scheduled_after_scrub", True)

    main.App._on_transcript_position_scrub_press(app, None)
    main.App._on_transcript_timeline_pan_changed(app, 50.0)
    main.App._on_transcript_position_scrub_release(app, None)

    assert player.pauses == 1
    assert player.seek_times == [5000]
    assert player.plays == 1
    assert app.synced_seconds == 5.0
    assert app.scheduled_after_scrub is True
    assert app.transcript_position_scrubbing is False


def test_playback_debug_tick_records_render_path_details() -> None:
    app = _app()
    app.transcript_playback_debug_enabled = True
    app._transcript_playback_now = lambda: 12.5
    app._transcript_timeline_view = {
        "min_time": 1.0,
        "max_time": 2.0,
        "left_margin": 20,
        "timeline_width": 200,
    }
    app.transcript_timeline_center_time = 1.5
    app.transcript_timeline_pan_fraction = 0.25

    main.App._record_transcript_playback_debug_tick(
        app,
        raw_seconds=1.0,
        display_seconds=1.25,
        redraw_type="playhead-only",
        viewport_moved=False,
    )

    tick = app.transcript_playback_debug_ticks[-1]
    assert tick["raw_player_time"] == 1.0
    assert tick["display_time"] == 1.25
    assert tick["render_center_time"] == 1.5
    assert tick["center_playhead_x"] == 120.0
    assert tick["redraw_type"] == "playhead-only"


def test_media_duration_uses_ffprobe_identity_instead_of_sixty_second_fallback() -> None:
    app = _app()
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "short.mp4")
        with open(media_path, "wb") as handle:
            handle.write(b"fake media")
        app.linked_transcript_media_path = media_path
        calls: list[list[str]] = []

        class Result:
            returncode = 0
            stdout = "88.566667\n"

        original_run = main.subprocess.run
        main.subprocess.run = lambda command, **_kwargs: calls.append(command) or Result()
        try:
            duration = main.App._get_linked_media_duration_seconds(app)
        finally:
            main.subprocess.run = original_run

    assert duration == 88.566667
    assert calls
    assert calls[0][-1].endswith("short.mp4")


def test_matching_media_and_transcript_duration_does_not_prompt_mismatch() -> None:
    app = _app()
    app.linked_transcript_media_path = "short.mp4"
    app.active_transcript_file_path = "short_eng.txt"
    app._get_linked_media_duration_seconds = lambda: 88.566667
    prompted: list[tuple[float, float]] = []
    app._ask_transcript_media_mismatch_choice = (
        lambda **kwargs: prompted.append(
            (kwargs["media_duration"], kwargs["transcript_duration"])
        )
        or "cancel"
    )
    segments = [
        TranscriptSegment(
            "Speaker 1",
            "00:00:00.579",
            "00:01:28.499",
            "Reference cue",
        )
    ]

    assert main.App._confirm_transcript_media_duration_link(app, segments) is True
    assert prompted == []


def test_position_control_uses_lightweight_canvas_scrubber() -> None:
    source = Path("main.py").read_text(encoding="utf-8")

    assert "class TranscriptPositionScrubber(tk.Canvas):" in source
    assert "self.transcript_timeline_pan_slider = TranscriptPositionScrubber(" in source
    assert "number_of_steps=2000" not in source
    assert "move at most one slider pixel" not in source.lower()


def run_self_test() -> None:
    test_playback_scheduler_keeps_one_active_callback()
    test_stale_playback_callback_is_ignored()
    test_center_lock_follow_tracks_playhead_without_threshold()
    test_center_playhead_view_fraction_and_position_slider_use_independent_durations()
    test_interpolated_clock_moves_between_repeated_player_timestamps()
    test_tick_refreshes_when_center_locked_viewport_moves()
    test_marker_draw_uses_fractional_position_without_full_refresh()
    test_center_locked_marker_draws_at_fixed_midpoint()
    test_position_slider_scrub_pauses_previews_and_seeks_once()
    test_playback_debug_tick_records_render_path_details()
    test_media_duration_uses_ffprobe_identity_instead_of_sixty_second_fallback()
    test_matching_media_and_transcript_duration_does_not_prompt_mismatch()
    test_position_control_uses_lightweight_canvas_scrubber()


if __name__ == "__main__":
    run_self_test()
    print("transcript_playback_scheduler_test.py: OK")
