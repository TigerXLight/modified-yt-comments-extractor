import os
import tempfile

import main
import asr_whispercpp
from main import App
from transcript_tools import TranscriptSegment


class FakeButton:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.config.update(kwargs)


class FakeMessageBox:
    infos: list[tuple[str, str]] = []
    errors: list[tuple[str, str]] = []

    @classmethod
    def showinfo(cls, title: str, message: str) -> None:
        cls.infos.append((title, message))

    @classmethod
    def showerror(cls, title: str, message: str) -> None:
        cls.errors.append((title, message))

    @classmethod
    def showwarning(cls, _title: str, _message: str) -> None:
        pass


class ImmediateThread:
    def __init__(self, *, target: object, daemon: bool) -> None:
        self.target = target
        self.daemon = daemon

    def start(self) -> None:
        self.target()


def _app() -> App:
    app = App.__new__(App)
    app.transcript_segments = []
    app.last_transcript_source = ""
    app.last_youtube_video_info = None
    app.last_asr_metadata = {}
    app.linked_transcript_media_path = None
    app.transcript_asr_button = FakeButton()
    app.evidence_button = FakeButton()
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    app.after = lambda _delay, callback: callback()
    app._add_session_file = lambda *_args, **_kwargs: None
    app._session_file_kind_for_path = lambda _path: main.SESSION_FILE_KIND_AUDIO
    app._collect_asr_topic_resolver_context = lambda _language: {}
    app._set_linked_transcript_media = lambda path: setattr(app, "linked_transcript_media_path", path)
    app._refresh_transcript_display = lambda: setattr(app, "refreshed", True)
    return app


def test_local_asr_whispercpp_selection_reaches_existing_dispatch_wrapper() -> None:
    original_ask = main.ask_asr_settings
    original_load = main.load_asr_defaults
    original_save = main.save_asr_defaults
    original_askopenfilename = main.filedialog.askopenfilename
    original_thread = main.threading.Thread
    original_messagebox = main.messagebox
    original_transcribe = main.transcribe_media_file
    original_resolver = main.resolve_asr_topic_glossary
    calls: list[dict[str, object]] = []
    saved: list[dict[str, object]] = []

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as handle:
        media_file = handle.name

    try:
        main.ask_asr_settings = lambda *_args, **_kwargs: {
            "engine": "whispercpp_vulkan",
            "profile_name": "Best-tested local profile",
            "model_name": "large-v3",
            "speaker_name": "Speaker 1",
            "language": "en",
            "initial_prompt": "Caltheris",
            "device": "vulkan",
            "compute_type": "",
            "media_file": media_file,
        }
        main.load_asr_defaults = lambda: {}
        main.save_asr_defaults = lambda **kwargs: saved.append(dict(kwargs))
        main.filedialog.askopenfilename = lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("Local ASR should use FILES media, not File Explorer")
        )
        main.threading.Thread = ImmediateThread
        main.messagebox = FakeMessageBox
        FakeMessageBox.infos = []
        FakeMessageBox.errors = []
        main.resolve_asr_topic_glossary = lambda *_args, **_kwargs: {}

        def fake_transcribe(media_path: str, **kwargs: object):
            calls.append({"media_path": media_path, **kwargs})
            return (
                [TranscriptSegment("Speaker 1", "00:00:00,000", "00:00:01,000", "Hello")],
                {
                    "model_name": kwargs.get("model_name"),
                    "device": kwargs.get("device"),
                    "compute_type": kwargs.get("compute_type"),
                    "language": "en",
                    "language_probability": 0.99,
                },
            )

        main.transcribe_media_file = fake_transcribe

        app = _app()
        App.local_asr_transcribe_clicked(app)
    finally:
        main.ask_asr_settings = original_ask
        main.load_asr_defaults = original_load
        main.save_asr_defaults = original_save
        main.filedialog.askopenfilename = original_askopenfilename
        main.threading.Thread = original_thread
        main.messagebox = original_messagebox
        main.transcribe_media_file = original_transcribe
        main.resolve_asr_topic_glossary = original_resolver
        os.unlink(media_file)

    assert len(calls) == 1
    assert calls[0]["model_name"] == "large-v3"
    assert calls[0]["device"] == "vulkan"
    assert calls[0]["compute_type"] == ""
    assert saved[0]["engine"] == "whispercpp_vulkan"
    assert saved[0]["profile_name"] == "Best-tested local profile"
    assert app.last_asr_metadata["selected_asr_engine"] == "whispercpp_vulkan"
    assert "using whisper.cpp / Vulkan large-v3" in app.last_transcript_source
    assert FakeMessageBox.infos
    assert "Language used/requested: en" in FakeMessageBox.infos[0][1]
    assert "Detected language" not in FakeMessageBox.infos[0][1]
    assert "Language confidence" not in FakeMessageBox.infos[0][1]
    assert not FakeMessageBox.errors


def test_local_asr_language_completion_lines_for_auto_detect_confidence() -> None:
    app = _app()

    lines = App._asr_language_completion_lines(
        app,
        {"language": "en", "language_probability": 0.875},
        requested_language=None,
    )

    assert lines == ["Detected language: en", "Language confidence: 87.50%"]


def test_local_asr_language_completion_lines_for_auto_detect_without_confidence() -> None:
    app = _app()

    lines = App._asr_language_completion_lines(
        app,
        {"language": "en"},
        requested_language=None,
    )

    assert lines == ["Detected language: en"]


def test_auto_probe_with_selected_whispercpp_does_not_add_faster_whisper_fallback() -> None:
    app = App.__new__(App)
    candidates = App._build_asr_auto_probe_candidates(
        app,
        selected_model="large-v3",
        selected_device="vulkan",
        selected_compute_type="",
    )

    assert candidates
    assert all(candidate["engine"] == "whispercpp_vulkan" for candidate in candidates)
    assert {candidate["device"] for candidate in candidates} == {"vulkan"}
    assert {candidate["compute_type"] for candidate in candidates} == {""}


def test_whispercpp_json_full_parser_extracts_word_timestamps() -> None:
    payload = """
    {
      "transcription": [
        {
          "text": " Alpha beta.",
          "timestamps": {"from": "00:00:00,100", "to": "00:00:00,900"},
          "tokens": [
            {
              "text": " Alpha",
              "timestamps": {"from": "00:00:00,100", "to": "00:00:00,400"},
              "p": 0.91
            },
            {
              "text": " beta",
              "timestamps": {"from": "00:00:00,500", "to": "00:00:00,800"},
              "p": 0.88
            },
            {
              "text": ".",
              "timestamps": {"from": "00:00:00,800", "to": "00:00:00,900"},
              "p": 0.92
            }
          ]
        }
      ]
    }
    """

    segments, words = asr_whispercpp._parse_whispercpp_json(payload, "Speaker 1")

    assert len(segments) == 1
    assert segments[0].start == "00:00:00.100"
    assert segments[0].end == "00:00:00.900"
    assert [word["text"] for word in words] == ["Alpha", "beta."]
    assert words[0]["start"] == 0.1
    assert words[1]["end"] == 0.9


def test_whispercpp_token_reconstruction_joins_subword_names_and_contractions() -> None:
    tokens = [
        {"text": " Sh", "timestamps": {"from": "00:00:00,000", "to": "00:00:00,100"}},
        {"text": "ows", "timestamps": {"from": "00:00:00,100", "to": "00:00:00,200"}},
        {"text": "mith", "timestamps": {"from": "00:00:00,200", "to": "00:00:00,300"}},
        {"text": " I", "timestamps": {"from": "00:00:00,500", "to": "00:00:00,600"}},
        {"text": "'m", "timestamps": {"from": "00:00:00,600", "to": "00:00:00,700"}},
        {"text": " Cal", "timestamps": {"from": "00:00:01,000", "to": "00:00:01,100"}},
        {"text": "ther", "timestamps": {"from": "00:00:01,100", "to": "00:00:01,200"}},
        {"text": "is", "timestamps": {"from": "00:00:01,200", "to": "00:00:01,300"}},
    ]

    words = asr_whispercpp._reconstruct_words_from_whispercpp_tokens(tokens)

    assert [word["text"] for word in words] == ["Showsmith", "I'm", "Caltheris"]


def test_whispercpp_command_requests_json_full_structured_output() -> None:
    command = ["whisper-cli.exe", "-m", "model.bin"]

    asr_whispercpp._append_whispercpp_json_flags(command)
    asr_whispercpp._append_whispercpp_json_flags(command)

    assert command.count("-oj") == 1
    assert command.count("-ojf") == 1


def run_self_test() -> None:
    test_local_asr_whispercpp_selection_reaches_existing_dispatch_wrapper()
    test_local_asr_language_completion_lines_for_auto_detect_confidence()
    test_local_asr_language_completion_lines_for_auto_detect_without_confidence()
    test_auto_probe_with_selected_whispercpp_does_not_add_faster_whisper_fallback()
    test_whispercpp_json_full_parser_extracts_word_timestamps()
    test_whispercpp_token_reconstruction_joins_subword_names_and_contractions()
    test_whispercpp_command_requests_json_full_structured_output()


if __name__ == "__main__":
    run_self_test()
    print("local_asr_dispatch_test.py: OK")
