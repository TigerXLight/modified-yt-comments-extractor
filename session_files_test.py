import os
import tempfile
from pathlib import Path

import main
from main import (
    App,
    SESSION_FILE_KIND_AUDIO,
    SESSION_FILE_KIND_TRANSCRIPT,
    SessionFileIntakeResult,
    SessionFileEntry,
)
from transcript_tools import TranscriptSegment


class FakeEvidenceButton:
    def __init__(self) -> None:
        self.state = ""

    def configure(self, **kwargs: object) -> None:
        self.state = str(kwargs.get("state", self.state))


class MessageBoxRecorder:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []
        self.switch_answer: object = True

    def showerror(self, title: str, message: str) -> None:
        self.errors.append((title, message))

    def showwarning(self, title: str, message: str) -> None:
        self.warnings.append((title, message))

    def askyesnocancel(self, *_args: object, **_kwargs: object) -> object:
        return self.switch_answer

    def askyesno(self, *_args: object, **_kwargs: object) -> bool:
        return True

    def showinfo(self, title: str, message: str) -> None:
        self.warnings.append((title, message))


class FakeTk:
    def splitlist(self, data: str) -> tuple[str, ...]:
        return ("C:/tmp/one file.srt", "C:/tmp/two file.mp4")


class FakeDndWidget:
    def __init__(self) -> None:
        self.registered: list[object] = []
        self.bindings: dict[str, object] = {}

    def drop_target_register(self, drop_type: object) -> None:
        self.registered.append(drop_type)

    def dnd_bind(self, event_name: str, callback: object) -> None:
        self.bindings[event_name] = callback


def _make_app() -> App:
    app = App.__new__(App)
    app.session_files = []
    app.selected_session_file_path = ""
    app.active_media_file_path = ""
    app.active_transcript_file_path = ""
    app.transcript_segments = []
    app.transcript_undo_stack = []
    app.transcript_redo_stack = []
    app.transcript_has_unsaved_edits = False
    app.linked_transcript_media_path = None
    app.last_transcript_source = None
    app.evidence_button = FakeEvidenceButton()
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append(
        (message, level)
    )
    app._set_linked_transcript_media = lambda path, log=False: setattr(
        app,
        "linked_transcript_media_path",
        path,
    )
    app._refresh_transcript_display_calls = 0
    app._refresh_transcript_display = lambda: setattr(
        app,
        "_refresh_transcript_display_calls",
        app._refresh_transcript_display_calls + 1,
    )
    app._refresh_session_files_list = lambda: None
    app._update_transcript_playback_buttons = lambda _playing: None
    app._stop_transcript_playback_process = lambda: setattr(app, "_playback_stopped", True)
    app._set_transcript_timeline_pan_slider = lambda fraction: setattr(
        app,
        "transcript_timeline_pan_fraction",
        fraction,
    )
    return app


def test_session_file_adds_dedupes_and_uses_basename_only() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "clip.srt")
        open(path, "w", encoding="utf-8").write("placeholder")
        app = _make_app()

        first = App._add_session_file(app, path, SESSION_FILE_KIND_TRANSCRIPT)
        second = App._add_session_file(app, path, SESSION_FILE_KIND_TRANSCRIPT)

        assert first == second
        assert len(app.session_files) == 1
        assert app.session_files[0].display_name == "clip.srt"
        assert tmpdir not in app.session_files[0].display_name


def test_transcript_selection_loads_existing_import_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "captions.srt")
        open(path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nHello there.\n"
        )
        app = _make_app()
        entry = App._add_session_file(app, path, SESSION_FILE_KIND_TRANSCRIPT)
        assert entry is not None

        loaded = App._load_session_transcript_file(app, entry)

        assert loaded is True
        assert len(app.transcript_segments) == 1
        assert app.last_transcript_source == "Imported file: captions.srt"
        assert app.transcript_has_unsaved_edits is False
        assert app.evidence_button.state == "normal"
        assert app.selected_session_file_path == entry.normalized_path
        assert app._refresh_transcript_display_calls == 1


def test_media_selection_changes_active_media_without_transcription() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "audio.wav")
        open(path, "wb").write(b"not real audio")
        app = _make_app()
        entry = App._add_session_file(app, path, SESSION_FILE_KIND_AUDIO)
        assert entry is not None

        selected = App._select_session_media_file(app, entry)

        assert selected is True
        assert app.linked_transcript_media_path == path
        assert app.active_media_file_path == entry.normalized_path
        assert app.transcript_segments == []
        assert app.selected_session_file_path == entry.normalized_path


def test_unsaved_transcript_guard_can_cancel_switch() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "next.srt")
        open(path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nNext.\n"
        )
        app = _make_app()
        app.transcript_segments = [
            TranscriptSegment("Speaker", "00:00:00,000", "00:00:01,000", "Current")
        ]
        app.transcript_has_unsaved_edits = True
        recorder = MessageBoxRecorder()
        recorder.switch_answer = None
        original_messagebox = main.messagebox
        main.messagebox = recorder
        try:
            entry = App._add_session_file(app, path, SESSION_FILE_KIND_TRANSCRIPT)
            assert entry is not None
            loaded = App._load_session_transcript_file(app, entry)
        finally:
            main.messagebox = original_messagebox

        assert loaded is False
        assert app.transcript_segments[0].text == "Current"
        assert app.transcript_has_unsaved_edits is True


def test_parse_failure_preserves_current_transcript() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "broken.srt")
        open(path, "w", encoding="utf-8").write("bad")
        app = _make_app()
        app.transcript_segments = [
            TranscriptSegment("Speaker", "00:00:00,000", "00:00:01,000", "Current")
        ]
        recorder = MessageBoxRecorder()
        original_messagebox = main.messagebox
        original_import = main.import_transcript
        original_logger_disabled = main.logger.disabled
        main.messagebox = recorder
        main.logger.disabled = True
        main.import_transcript = lambda _path: (_ for _ in ()).throw(
            ValueError("safe parse error")
        )
        try:
            entry = App._add_session_file(app, path, SESSION_FILE_KIND_TRANSCRIPT)
            assert entry is not None
            loaded = App._load_session_transcript_file(app, entry)
        finally:
            main.messagebox = original_messagebox
            main.import_transcript = original_import
            main.logger.disabled = original_logger_disabled

        assert loaded is False
        assert app.transcript_segments[0].text == "Current"
        assert recorder.errors


def test_detach_never_deletes_disk_file() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "keep.wav")
        open(path, "wb").write(b"keep")
        app = _make_app()
        entry = App._add_session_file(app, path, SESSION_FILE_KIND_AUDIO)
        assert entry is not None

        App._remove_session_file(app, entry.normalized_path)

        assert app.session_files == []
        assert os.path.exists(path)


def test_shared_intake_adds_mixed_files_and_loads_first_transcript() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        transcript_path = os.path.join(tmpdir, "captions.srt")
        open(media_path, "wb").write(b"not real media")
        open(transcript_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nCaption.\n"
        )
        app = _make_app()
        app.transcribe_media_file_called = False

        result = App._intake_session_files(
            app,
            [media_path, transcript_path],
            select_first=True,
            source_label="selected",
        )

        assert isinstance(result, SessionFileIntakeResult)
        assert result.added_paths == (media_path, transcript_path)
        assert result.selected_path == transcript_path
        assert len(app.session_files) == 2
        assert [entry.display_name for entry in app.session_files] == [
            "clip.mp4",
            "captions.srt",
        ]
        assert app.last_transcript_source == "Imported file: captions.srt"
        assert app.linked_transcript_media_path is None
        assert app.active_transcript_file_path
        assert app.transcribe_media_file_called is False


def test_shared_intake_dedupes_and_reports_unsupported_without_blocking_valid() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.wav")
        unsupported_path = os.path.join(tmpdir, "notes.json")
        open(media_path, "wb").write(b"not real audio")
        open(unsupported_path, "w", encoding="utf-8").write("{}")
        app = _make_app()
        recorder = MessageBoxRecorder()
        original_messagebox = main.messagebox
        main.messagebox = recorder
        try:
            result = App._intake_session_files(
                app,
                [media_path, media_path, unsupported_path],
                select_first=False,
                source_label="dropped",
            )
        finally:
            main.messagebox = original_messagebox

        assert result.added_paths == (media_path,)
        assert result.duplicate_paths == (media_path,)
        assert result.unsupported_paths == (unsupported_path,)
        assert len(app.session_files) == 1
        assert app.session_files[0].display_name == "clip.wav"
        assert recorder.warnings


def test_shared_intake_rejects_directories_and_missing_paths() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_path = os.path.join(tmpdir, "missing.mp4")
        app = _make_app()
        recorder = MessageBoxRecorder()
        original_messagebox = main.messagebox
        main.messagebox = recorder
        try:
            result = App._intake_session_files(
                app,
                [tmpdir, missing_path],
                select_first=True,
                source_label="dropped",
            )
        finally:
            main.messagebox = original_messagebox

        assert result.added_paths == ()
        assert result.rejected_paths == (tmpdir, missing_path)
        assert app.session_files == []
        assert recorder.warnings


def test_drop_payload_parser_handles_quoted_paths_with_spaces() -> None:
    app = _make_app()
    app.tk = FakeTk()
    data = "{C:/tmp/one file.srt} {C:/tmp/two file.mp4}"

    paths = App._session_file_paths_from_drop_data(app, data)

    assert paths == ("C:/tmp/one file.srt", "C:/tmp/two file.mp4")


def test_final_files_and_transcript_drop_targets_register_live_widgets() -> None:
    app = _make_app()
    app.file_drag_drop_ready = True
    app._file_drag_drop_type = "DND_FILES"
    app.files_header_frame = FakeDndWidget()
    app.files_frame = FakeDndWidget()
    app.files_list_frame = FakeDndWidget()
    app.files_empty_label = FakeDndWidget()
    app.files_drop_status_label = FakeDndWidget()
    app.transcript_card = FakeDndWidget()
    app.transcript_textbox = FakeDndWidget()
    app.transcript_timeline_canvas = FakeDndWidget()
    transcript_text_widget = FakeDndWidget()
    app._get_transcript_text_widget = lambda: transcript_text_widget

    assert App._bind_final_file_drop_targets(app) is True
    assert app.file_drag_drop_ready is True
    assert app.file_drag_drop_status == "ready"

    for widget in (
        app.files_header_frame,
        app.files_frame,
        app.files_list_frame,
        app.files_empty_label,
        app.files_drop_status_label,
    ):
        assert widget.registered == ["DND_FILES"]
        assert "<<Drop>>" in widget.bindings
        assert "<<DragEnter>>" in widget.bindings
        assert "<<DragLeave>>" in widget.bindings

    for widget in (
        app.transcript_card,
        app.transcript_textbox,
        transcript_text_widget,
        app.transcript_timeline_canvas,
    ):
        assert widget.registered == ["DND_FILES"]
        assert "<<Drop>>" in widget.bindings
        assert "<<DragEnter>>" in widget.bindings
        assert "<<DragLeave>>" in widget.bindings


def test_transcript_selection_preserves_active_media() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        transcript_path = os.path.join(tmpdir, "captions.srt")
        open(media_path, "wb").write(b"media")
        open(transcript_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nCaption.\n"
        )
        app = _make_app()
        media_entry = App._add_session_file(app, media_path, main.SESSION_FILE_KIND_VIDEO)
        transcript_entry = App._add_session_file(app, transcript_path, SESSION_FILE_KIND_TRANSCRIPT)
        assert media_entry is not None
        assert transcript_entry is not None

        App._select_session_media_file(app, media_entry)
        App._load_session_transcript_file(app, transcript_entry)

        assert app.linked_transcript_media_path == media_path
        assert app.active_media_file_path == media_entry.normalized_path
        assert app.active_transcript_file_path == transcript_entry.normalized_path


def test_clear_transcript_preserves_active_media_and_files_row() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        transcript_path = os.path.join(tmpdir, "captions.srt")
        open(media_path, "wb").write(b"media")
        open(transcript_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nCaption.\n"
        )
        app = _make_app()
        app.all_comments = []
        app.attached_screenshots = []
        app._data_lock = type("Lock", (), {"__enter__": lambda self: None, "__exit__": lambda self, *args: None})()
        media_entry = App._add_session_file(app, media_path, main.SESSION_FILE_KIND_VIDEO)
        transcript_entry = App._add_session_file(app, transcript_path, SESSION_FILE_KIND_TRANSCRIPT)
        assert media_entry is not None
        assert transcript_entry is not None
        App._select_session_media_file(app, media_entry)
        App._load_session_transcript_file(app, transcript_entry)
        recorder = MessageBoxRecorder()
        original_messagebox = main.messagebox
        main.messagebox = recorder
        try:
            App.clear_transcript(app)
        finally:
            main.messagebox = original_messagebox

        assert app.transcript_segments == []
        assert app.linked_transcript_media_path == media_path
        assert app.active_media_file_path == media_entry.normalized_path
        assert app.active_transcript_file_path == ""
        assert transcript_entry in app.session_files
        assert os.path.exists(transcript_path)


def test_transcript_section_drop_loads_first_transcript_and_preserves_media() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        first_path = os.path.join(tmpdir, "first.srt")
        second_path = os.path.join(tmpdir, "second.srt")
        open(media_path, "wb").write(b"media")
        open(first_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nFirst.\n"
        )
        open(second_path, "w", encoding="utf-8").write(
            "1\n00:00:01,000 --> 00:00:02,000\nSecond.\n"
        )
        app = _make_app()
        media_entry = App._add_session_file(app, media_path, main.SESSION_FILE_KIND_VIDEO)
        assert media_entry is not None
        App._select_session_media_file(app, media_entry)

        result = App._handle_transcript_drop_paths(app, [first_path, second_path])

        assert result.added_paths == (first_path, second_path)
        assert [segment.text for segment in app.transcript_segments] == ["First."]
        assert app.linked_transcript_media_path == media_path
        assert app.active_media_file_path == media_entry.normalized_path
        assert len(app.session_files) == 3
        assert os.path.exists(second_path)


def test_media_drop_on_transcript_section_adds_to_files_without_replacing_transcript() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        transcript_path = os.path.join(tmpdir, "captions.srt")
        open(media_path, "wb").write(b"media")
        open(transcript_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nCaption.\n"
        )
        app = _make_app()
        transcript_entry = App._add_session_file(app, transcript_path, SESSION_FILE_KIND_TRANSCRIPT)
        assert transcript_entry is not None
        App._load_session_transcript_file(app, transcript_entry)

        result = App._handle_transcript_drop_paths(app, [media_path])

        assert result.added_paths == (media_path,)
        assert [segment.text for segment in app.transcript_segments] == ["Caption."]
        assert app.active_transcript_file_path == transcript_entry.normalized_path
        assert len(app.session_files) == 2


def test_row_local_asr_action_uses_exact_file_without_picker() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        open(media_path, "wb").write(b"media")
        app = _make_app()
        calls: list[dict[str, object]] = []
        app.local_asr_transcribe_clicked = lambda media_file="", force_full=False: calls.append(
            {"media_file": media_file, "force_full": force_full}
        )
        entry = App._add_session_file(app, media_path, main.SESSION_FILE_KIND_VIDEO)
        assert entry is not None

        started = App._start_local_asr_full_for_session_file(app, entry.normalized_path)

        assert started is True
        assert calls == [{"media_file": media_path, "force_full": True}]
        assert app.linked_transcript_media_path == media_path


def test_row_online_asr_action_opens_settings_when_key_missing() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        open(media_path, "wb").write(b"media")
        app = _make_app()
        app._online_asr_provider_option = lambda _provider_id: type(
            "Option",
            (),
            {"provider_id": main.ELEVENLABS_SCRIBE_PROVIDER_ID, "credential_entry_id": "asr:elevenlabs_scribe"},
        )()
        app._get_online_asr_provider_id = lambda: main.ELEVENLABS_SCRIBE_PROVIDER_ID
        app._online_asr_provider_credential_status = lambda _option: None
        app.open_online_asr_settings_clicked_calls = 0
        app.open_online_asr_settings_clicked = lambda: setattr(
            app,
            "open_online_asr_settings_clicked_calls",
            app.open_online_asr_settings_clicked_calls + 1,
        )
        app._start_online_asr_transcription = lambda _path: (_ for _ in ()).throw(
            AssertionError("should not dispatch")
        )
        entry = App._add_session_file(app, media_path, main.SESSION_FILE_KIND_VIDEO)
        assert entry is not None

        started = App._start_online_asr_full_for_session_file(app, entry.normalized_path)

        assert started is False
        assert app.open_online_asr_settings_clicked_calls == 1
        assert app.linked_transcript_media_path == media_path


def test_session_media_options_are_files_backed_and_ordered() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        first_path = os.path.join(tmpdir, "first.mp4")
        second_path = os.path.join(tmpdir, "second.wav")
        transcript_path = os.path.join(tmpdir, "captions.srt")
        open(first_path, "wb").write(b"1")
        open(second_path, "wb").write(b"2")
        open(transcript_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nCaption.\n"
        )
        app = _make_app()
        App._add_session_file(app, first_path, main.SESSION_FILE_KIND_VIDEO)
        App._add_session_file(app, transcript_path, SESSION_FILE_KIND_TRANSCRIPT)
        App._add_session_file(app, second_path, main.SESSION_FILE_KIND_AUDIO)

        options = App._session_media_options(app)

        assert options == (("1. first.mp4", first_path), ("2. second.wav", second_path))


def test_add_session_files_button_uses_multi_select_picker_and_shared_intake() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.webm")
        open(media_path, "wb").write(b"not real media")
        app = _make_app()
        calls: list[tuple[object, ...]] = []
        original_picker = main.filedialog.askopenfilenames
        main.filedialog.askopenfilenames = lambda **kwargs: (
            calls.append((kwargs,)) or (media_path,)
        )
        try:
            App._add_session_files_clicked(app)
        finally:
            main.filedialog.askopenfilenames = original_picker

        assert calls
        filetypes = calls[0][0]["filetypes"]
        assert any("*.srt" in patterns for _label, patterns in filetypes)
        assert any("*.mp4" in patterns for _label, patterns in filetypes)
        assert len(app.session_files) == 1
        assert app.session_files[0].display_name == "clip.webm"
        assert app.linked_transcript_media_path == media_path


def test_txt_export_preserves_timing_cues_without_same_speaker_merge() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = os.path.join(tmpdir, "timed.txt")
        app = _make_app()
        app.transcript_segments = [
            TranscriptSegment("Speaker 1", "00:00:00.000", "00:00:01.000", "One."),
            TranscriptSegment("Speaker 1", "00:00:01.500", "00:00:02.000", "Two."),
            TranscriptSegment("Speaker 1", "00:00:03.000", "00:00:04.000", "Three."),
        ]
        original_save = main.filedialog.asksaveasfilename
        original_info = main.messagebox.showinfo
        main.filedialog.asksaveasfilename = lambda **_kwargs: export_path
        main.messagebox.showinfo = lambda *_args, **_kwargs: None
        try:
            App.export_transcript_file(app, "txt")
        finally:
            main.filedialog.asksaveasfilename = original_save
            main.messagebox.showinfo = original_info

        text = Path(export_path).read_text(encoding="utf-8")
        assert text.count("Speaker 1 [") == 3
        assert "00:00:00.000 - 00:00:04.000" not in text


def test_blank_timing_mode_preserves_draft_cue_boundaries() -> None:
    draft_segments = [
        TranscriptSegment("Speaker 1", "00:00:00.000", "00:00:01.000", "One."),
        TranscriptSegment("Speaker 1", "00:00:01.500", "00:00:02.000", "Two."),
        TranscriptSegment("Speaker 1", "00:00:03.000", "00:00:04.000", "Three."),
    ]

    blank_segments = App._blank_text_preserving_transcript_boundaries(draft_segments)

    assert len(blank_segments) == len(draft_segments)
    assert [(segment.start, segment.end) for segment in blank_segments] == [
        (segment.start, segment.end)
        for segment in draft_segments
    ]
    assert [segment.text for segment in blank_segments] == ["", "", ""]


def test_subtitle_timing_builder_uses_word_timestamp_gaps_without_speaker_merge() -> None:
    app = _make_app()
    raw_segments = [
        TranscriptSegment(
            "Speaker 1",
            "00:00:00.000",
            "00:00:08.000",
            "Alpha beta gamma. Delta epsilon.",
        ),
    ]
    word_timestamps = [
        {"start": 0.10, "end": 0.40, "text": "Alpha"},
        {"start": 0.45, "end": 0.80, "text": "beta"},
        {"start": 0.85, "end": 1.10, "text": "gamma."},
        {"start": 2.00, "end": 2.40, "text": "Delta"},
        {"start": 2.45, "end": 2.90, "text": "epsilon."},
    ]

    draft_cues = App._build_subtitle_timing_cues(
        app,
        raw_segments,
        media_duration_seconds=8.0,
        word_timestamps=word_timestamps,
        max_cue_duration_seconds=6.0,
        max_cue_chars=70,
    )
    blank_cues = App._blank_text_preserving_transcript_boundaries(draft_cues)
    report = App._subtitle_timing_quality_report(
        app,
        draft_cues,
        media_duration_seconds=8.0,
    )

    assert len(draft_cues) == 2
    assert draft_cues[0].text == "Alpha beta gamma."
    assert draft_cues[1].text == "Delta epsilon."
    assert draft_cues[0].end < draft_cues[1].start
    assert report["positive_gap_count"] == 1
    assert report["overlap_count"] == 0
    assert report["malformed_word_cue_count"] == 0
    assert report["coverage_percent"] < 60.0
    assert all(segment.text for segment in draft_cues)
    assert [(segment.start, segment.end) for segment in blank_cues] == [
        (segment.start, segment.end)
        for segment in draft_cues
    ]
    assert all(segment.text == "" for segment in blank_cues)


def test_subtitle_timing_builder_segment_only_fallback_preserves_raw_segments() -> None:
    app = _make_app()
    long_text = (
        "This is a long automatic speech recognition segment that should remain "
        "one raw segment when no word timestamps are available."
    )
    raw_segments = [
        TranscriptSegment("Speaker 1", "00:00:00.000", "00:00:18.000", long_text),
        TranscriptSegment("Speaker 1", "00:00:20.000", "00:00:22.000", "Final cue."),
    ]

    draft_cues = App._build_subtitle_timing_cues(
        app,
        raw_segments,
        media_duration_seconds=22.0,
        max_cue_duration_seconds=6.0,
        max_cue_chars=70,
    )

    assert len(draft_cues) == len(raw_segments)
    assert draft_cues[0].start == "00:00:00.000"
    assert draft_cues[0].end == "00:00:18.000"
    assert draft_cues[1].start == "00:00:20.000"
    assert draft_cues[1].end == "00:00:22.000"


def test_subtitle_timing_quality_warnings_flag_near_continuous_malformed_output() -> None:
    app = _make_app()
    cues = [
        TranscriptSegment("Speaker 1", "00:00:00.000", "00:00:05.000", "Sh ows mith"),
        TranscriptSegment("Speaker 1", "00:00:04.950", "00:00:09.000", "Cal p her is"),
        TranscriptSegment("Speaker 1", "00:00:09.000", "00:00:10.000", "Ny x ara"),
    ]

    report = App._subtitle_timing_quality_report(
        app,
        cues,
        media_duration_seconds=10.0,
    )
    warnings = App._subtitle_timing_quality_warnings(app, report)

    assert report["overlap_count"] == 1
    assert report["positive_gap_count"] == 0
    assert report["coverage_percent"] > 90.0
    assert report["malformed_word_cue_count"] >= 1
    assert warnings


def run_self_test() -> None:
    test_session_file_adds_dedupes_and_uses_basename_only()
    test_transcript_selection_loads_existing_import_path()
    test_media_selection_changes_active_media_without_transcription()
    test_unsaved_transcript_guard_can_cancel_switch()
    test_parse_failure_preserves_current_transcript()
    test_detach_never_deletes_disk_file()
    test_shared_intake_adds_mixed_files_and_loads_first_transcript()
    test_shared_intake_dedupes_and_reports_unsupported_without_blocking_valid()
    test_shared_intake_rejects_directories_and_missing_paths()
    test_drop_payload_parser_handles_quoted_paths_with_spaces()
    test_final_files_and_transcript_drop_targets_register_live_widgets()
    test_add_session_files_button_uses_multi_select_picker_and_shared_intake()
    test_transcript_selection_preserves_active_media()
    test_clear_transcript_preserves_active_media_and_files_row()
    test_transcript_section_drop_loads_first_transcript_and_preserves_media()
    test_media_drop_on_transcript_section_adds_to_files_without_replacing_transcript()
    test_row_local_asr_action_uses_exact_file_without_picker()
    test_row_online_asr_action_opens_settings_when_key_missing()
    test_session_media_options_are_files_backed_and_ordered()
    test_txt_export_preserves_timing_cues_without_same_speaker_merge()
    test_blank_timing_mode_preserves_draft_cue_boundaries()
    test_subtitle_timing_builder_uses_word_timestamp_gaps_without_speaker_merge()
    test_subtitle_timing_builder_segment_only_fallback_preserves_raw_segments()
    test_subtitle_timing_quality_warnings_flag_near_continuous_malformed_output()


if __name__ == "__main__":
    run_self_test()
    print("session_files_test.py: OK")
