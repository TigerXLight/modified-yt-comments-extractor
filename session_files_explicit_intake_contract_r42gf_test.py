import os
import tempfile

from main import App, SESSION_FILE_KIND_TRANSCRIPT, SessionFileIntakeResult


class FakeEvidenceButton:
    def __init__(self) -> None:
        self.state = ""

    def configure(self, **kwargs: object) -> None:
        self.state = str(kwargs.get("state", self.state))


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
    app.log_message = lambda message, level="info", *_args: app.log_messages.append((message, level))
    app._refresh_session_files_list = lambda: None
    app._refresh_transcript_display = lambda: None
    app._update_transcript_playback_buttons = lambda _playing: None
    app._stop_transcript_playback_process = lambda: None
    app._set_transcript_timeline_pan_slider = lambda _fraction: None
    app._set_linked_transcript_media = lambda path, log=False: setattr(app, "linked_transcript_media_path", path)
    return app


def test_shared_files_intake_is_add_only_even_when_select_first_is_true() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        media_path = os.path.join(tmpdir, "clip.mp4")
        transcript_path = os.path.join(tmpdir, "captions.srt")
        open(media_path, "wb").write(b"not real media")
        open(transcript_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nCaption.\n"
        )
        app = _make_app()

        result = App._intake_session_files(
            app,
            [media_path, transcript_path],
            select_first=True,
            source_label="selected",
        )

        assert isinstance(result, SessionFileIntakeResult)
        assert result.added_paths == (media_path, transcript_path)
        assert result.selected_path == ""
        assert app.selected_session_file_path == ""
        assert app.active_media_file_path == ""
        assert app.active_transcript_file_path == ""
        assert app.linked_transcript_media_path is None
        assert app.last_transcript_source is None
        assert app.transcript_segments == []
        assert [entry.display_name for entry in app.session_files] == ["clip.mp4", "captions.srt"]


def test_transcript_section_drop_remains_explicit_load_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        transcript_path = os.path.join(tmpdir, "captions.srt")
        open(transcript_path, "w", encoding="utf-8").write(
            "1\n00:00:00,000 --> 00:00:01,000\nCaption.\n"
        )
        app = _make_app()

        result = App._handle_transcript_drop_paths(app, [transcript_path])

        assert result.added_paths == (transcript_path,)
        assert result.selected_path == ""
        assert app.last_transcript_source == "Imported file: captions.srt"
        assert app.active_transcript_file_path
        assert [segment.text for segment in app.transcript_segments] == ["Caption."]


def run_self_test() -> None:
    test_shared_files_intake_is_add_only_even_when_select_first_is_true()
    test_transcript_section_drop_remains_explicit_load_path()


if __name__ == "__main__":
    run_self_test()
    print("session_files_explicit_intake_contract_r42gf_test OK")
