import os
import tempfile

import main
from main import (
    App,
    SESSION_FILE_KIND_AUDIO,
    SESSION_FILE_KIND_TRANSCRIPT,
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


def _make_app() -> App:
    app = App.__new__(App)
    app.session_files = []
    app.selected_session_file_path = ""
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


def run_self_test() -> None:
    test_session_file_adds_dedupes_and_uses_basename_only()
    test_transcript_selection_loads_existing_import_path()
    test_media_selection_changes_active_media_without_transcription()
    test_unsaved_transcript_guard_can_cancel_switch()
    test_parse_failure_preserves_current_transcript()
    test_detach_never_deletes_disk_file()


if __name__ == "__main__":
    run_self_test()
    print("session_files_test.py: OK")
