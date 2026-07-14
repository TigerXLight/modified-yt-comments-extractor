from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

import main
from asr_provider_action import ASR_PROVIDER_ACTION_TRANSCRIBE
from elevenlabs_scribe_provider import (
    ELEVENLABS_SCRIBE_MODEL_ID,
    ELEVENLABS_SCRIBE_PROVIDER_ID,
    ElevenLabsScribeResult,
    ElevenLabsScribeStatus,
    ElevenLabsScribeWord,
)


SECRET_SENTINEL = "ONLINE-ASR-SECRET-MUST-NOT-LEAK"


class FakeWidget:
    def __init__(self, parent: object = None, **kwargs: object) -> None:
        self.parent = parent
        self.kwargs = dict(kwargs)
        self.pack_calls: list[dict[str, object]] = []
        self.grid_calls: list[dict[str, object]] = []
        self.place_calls: list[dict[str, object]] = []
        self.bind_calls: list[tuple[str, object, object]] = []
        self.destroyed = False

    def configure(self, **kwargs: object) -> None:
        self.kwargs.update(kwargs)

    def cget(self, key: str) -> object:
        return self.kwargs.get(key, "")

    def pack(self, **kwargs: object) -> None:
        self.pack_calls.append(dict(kwargs))

    def grid(self, **kwargs: object) -> None:
        self.grid_calls.append(dict(kwargs))

    def place(self, **kwargs: object) -> None:
        self.place_calls.append(dict(kwargs))

    def pack_propagate(self, value: object) -> None:
        self.kwargs["pack_propagate"] = value

    def bind(self, event: str, callback: object, add: object = None) -> None:
        self.bind_calls.append((event, callback, add))

    def grid_columnconfigure(self, *_args: object, **_kwargs: object) -> None:
        return None

    def title(self, value: str) -> None:
        self.kwargs["title"] = value

    def geometry(self, value: str) -> None:
        self.kwargs["geometry"] = value

    def transient(self, parent: object) -> None:
        self.kwargs["transient"] = parent

    def protocol(self, name: str, callback: object) -> None:
        self.kwargs[f"protocol:{name}"] = callback

    def winfo_exists(self) -> bool:
        return not self.destroyed

    def focus(self) -> None:
        self.kwargs["focused"] = True

    def destroy(self) -> None:
        self.destroyed = True


class FakeVar:
    def __init__(self, value: object = "") -> None:
        self.value = value

    def set(self, value: object) -> None:
        self.value = value

    def get(self) -> object:
        return self.value


class FakeThread:
    created: list["FakeThread"] = []

    def __init__(self, *, target: object, daemon: bool) -> None:
        self.target = target
        self.daemon = daemon
        self.started = False
        FakeThread.created.append(self)

    def start(self) -> None:
        self.started = True


class ImmediateThread(FakeThread):
    def start(self) -> None:
        self.started = True
        self.target()


class FakeEvidenceButton:
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


def _patch_fake_widgets() -> tuple[object, object, object, object]:
    original_frame = main.ctk.CTkFrame
    original_button = main.ctk.CTkButton
    original_font = main.ctk.CTkFont
    original_label = main.tk.Label
    main.ctk.CTkFrame = FakeWidget
    main.ctk.CTkButton = FakeWidget
    main.ctk.CTkFont = lambda **kwargs: ("font", kwargs)
    main.tk.Label = FakeWidget
    return original_frame, original_button, original_font, original_label


def _restore_fake_widgets(originals: tuple[object, object, object, object]) -> None:
    main.ctk.CTkFrame, main.ctk.CTkButton, main.ctk.CTkFont, main.tk.Label = originals


def _app() -> main.App:
    app = main.App.__new__(main.App)
    app.after = lambda _delay, callback: callback()
    app.winfo_containing = lambda *_args: None
    app.winfo_pointerx = lambda: 0
    app.winfo_pointery = lambda: 0
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    app.evidence_button = FakeEvidenceButton()
    app.online_asr_busy = False
    app.transcript_online_asr_button = None
    app._set_linked_transcript_media = lambda path: setattr(app, "linked_media", path)
    app._refresh_transcript_display = lambda: setattr(app, "refreshed", True)
    return app


def test_online_asr_control_copies_local_asr_visual_spec() -> None:
    originals = _patch_fake_widgets()
    try:
        app = _app()
        app.asr_cog_icon_image = object()
        app.asr_cog_icon_hover_image = object()
        parent = FakeWidget()

        app._create_asr_action_control(
            parent,
            text=main.LOCAL_ASR_BUTTON_TEXT,
            command=lambda: None,
            settings_command=lambda: None,
            wrap_attr="local_wrap",
            button_attr="local_button",
            settings_attr="local_cog",
        )
        app._create_asr_action_control(
            parent,
            text=main.ONLINE_ASR_BUTTON_TEXT,
            command=lambda: None,
            settings_command=lambda: None,
            wrap_attr="online_wrap",
            button_attr="online_button",
            settings_attr="online_cog",
        )

        assert getattr(app, "online_button").kwargs["text"].endswith("Online ASR")
        assert "Online ASR" in getattr(app, "online_button").kwargs["text"]
        for local_attr, online_attr in (
            ("local_wrap", "online_wrap"),
            ("local_button", "online_button"),
            ("local_cog", "online_cog"),
        ):
            local_widget = getattr(app, local_attr)
            online_widget = getattr(app, online_attr)
            local_kwargs = {
                key: value
                for key, value in local_widget.kwargs.items()
                if key not in {"text", "command"}
            }
            online_kwargs = {
                key: value
                for key, value in online_widget.kwargs.items()
                if key not in {"text", "command"}
            }
            assert online_kwargs == local_kwargs
            assert online_widget.pack_calls == local_widget.pack_calls
            assert online_widget.place_calls == local_widget.place_calls
        assert getattr(app, "online_cog").kwargs["image"] is app.asr_cog_icon_image
        assert getattr(app, "online_cog").kwargs["bg"] == main.COLORS["accent"]
    finally:
        _restore_fake_widgets(originals)


def test_online_asr_cog_opens_access_keys_without_dispatch() -> None:
    app = _app()
    calls: list[str] = []
    app.open_access_keys_window = lambda: calls.append("access_keys") or "window"

    assert app.open_online_asr_settings_clicked() == "window"
    assert calls == ["access_keys"]


def test_online_asr_dispatch_uses_coordinator_and_validated_request_once() -> None:
    app = _app()
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"tiny")
        media_file = handle.name

    executor_calls: list[tuple[str, str, str, dict[str, object]]] = []

    def fake_executor_factory(request: object):
        parameters = request.to_transport_parameters()
        assert parameters["model_id"] == ELEVENLABS_SCRIBE_MODEL_ID
        assert parameters["tag_audio_events"] is False
        assert "timestamps_granularity" not in parameters
        assert "keyterms" not in parameters

        def execute(provider_id: str, action_kind: str, credential: str) -> ElevenLabsScribeResult:
            executor_calls.append((provider_id, action_kind, credential, parameters))
            return ElevenLabsScribeResult(
                provider_id=provider_id,
                model_id=ELEVENLABS_SCRIBE_MODEL_ID,
                status=ElevenLabsScribeStatus.SUCCEEDED,
                safe_diagnostic="ok",
                text="hello",
            )

        return execute

    class FakeCoordinator:
        def __init__(self, *, executors: dict[tuple[str, str], object]) -> None:
            self.executors = executors

        def dispatch_provider_action(self, provider_id: str, *, action_kind: str):
            executor = self.executors[(provider_id, action_kind)]
            executor(provider_id, action_kind, SECRET_SENTINEL)
            return SimpleNamespace(
                status=SimpleNamespace(value="action_succeeded"),
                safe_diagnostic="provider_action_completed",
                action_succeeded=True,
            )

    try:
        action_result, provider_result = app._dispatch_online_asr_provider_action(
            media_file,
            coordinator_factory=FakeCoordinator,
            executor_factory=fake_executor_factory,
        )
    finally:
        os.unlink(media_file)

    assert action_result.action_succeeded is True
    assert provider_result is not None
    assert len(executor_calls) == 1
    assert executor_calls[0][0] == ELEVENLABS_SCRIBE_PROVIDER_ID
    assert executor_calls[0][1] == ASR_PROVIDER_ACTION_TRANSCRIBE
    assert executor_calls[0][2] == SECRET_SENTINEL


def test_online_asr_start_requires_file_and_prevents_duplicate_dispatch(monkeypatch=None) -> None:
    original_thread = main.threading.Thread
    FakeThread.created = []
    main.threading.Thread = FakeThread
    try:
        app = _app()
        status = FakeVar()
        assert app._start_online_asr_transcription("", status_var=status) is False
        assert status.value == "Choose a local media file before transcribing."
        assert FakeThread.created == []

        with tempfile.NamedTemporaryFile(delete=False) as handle:
            media_file = handle.name
        try:
            assert app._start_online_asr_transcription(media_file, status_var=status) is True
            assert app.online_asr_busy is True
            assert len(FakeThread.created) == 1
            assert app._start_online_asr_transcription(media_file, status_var=status) is False
            assert len(FakeThread.created) == 1
        finally:
            os.unlink(media_file)
    finally:
        main.threading.Thread = original_thread


def test_online_asr_success_routes_to_transcript_display() -> None:
    original_messagebox = main.messagebox
    main.messagebox = FakeMessageBox
    FakeMessageBox.infos = []
    FakeMessageBox.errors = []
    try:
        app = _app()
        result = ElevenLabsScribeResult(
            provider_id=ELEVENLABS_SCRIBE_PROVIDER_ID,
            model_id=ELEVENLABS_SCRIBE_MODEL_ID,
            status=ElevenLabsScribeStatus.SUCCEEDED,
            safe_diagnostic="ok",
            text="hello world",
            language_code="eng",
            language_probability=0.9,
            words=(
                ElevenLabsScribeWord(text="hello", start=0.0, end=0.4, word_type="word"),
                ElevenLabsScribeWord(text="noise", start=0.5, end=0.7, word_type="audio_event"),
                ElevenLabsScribeWord(text="world", start=0.8, end=1.0, word_type="word"),
            ),
        )

        app._apply_online_asr_success("C:/tmp/sample.wav", result)

        assert [segment.text for segment in app.transcript_segments] == ["hello", "world"]
        assert app.last_youtube_video_info is None
        assert app.last_asr_metadata["engine"] == "online_asr"
        assert app.last_asr_metadata["audio_event_item_count"] == 1
        assert app.last_transcript_source == "Online ASR transcript from sample.wav using ElevenLabs Scribe v2"
        assert app.evidence_button.config["state"] == "normal"
        assert app.refreshed is True
        assert FakeMessageBox.infos
        assert not FakeMessageBox.errors
    finally:
        main.messagebox = original_messagebox


def test_online_asr_worker_restores_controls_after_safe_failure() -> None:
    original_thread = main.threading.Thread
    original_messagebox = main.messagebox
    main.threading.Thread = ImmediateThread
    main.messagebox = FakeMessageBox
    FakeMessageBox.infos = []
    FakeMessageBox.errors = []
    try:
        app = _app()
        status = FakeVar()
        start_button = FakeWidget()

        def fake_dispatch(_media_file: str):
            return (
                SimpleNamespace(
                    status=SimpleNamespace(value="credential_unavailable"),
                    safe_diagnostic="cloud_asr_credential_missing",
                    action_succeeded=False,
                ),
                None,
            )

        app._dispatch_online_asr_provider_action = fake_dispatch

        with tempfile.NamedTemporaryFile(delete=False) as handle:
            media_file = handle.name
        try:
            assert app._start_online_asr_transcription(
                media_file,
                status_var=status,
                start_button=start_button,
            ) is True
        finally:
            os.unlink(media_file)

        assert app.online_asr_busy is False
        assert start_button.kwargs["state"] == "normal"
        assert "credential_unavailable" in status.value
        assert "credential_unavailable" in FakeMessageBox.errors[0][1]
    finally:
        main.threading.Thread = original_thread
        main.messagebox = original_messagebox


def test_online_asr_worker_restores_main_button_when_dialog_was_closed() -> None:
    original_thread = main.threading.Thread
    main.threading.Thread = ImmediateThread
    try:
        app = _app()
        dialog = FakeWidget()
        dialog.destroy()
        start_button = FakeWidget()
        app.transcript_online_asr_button = FakeWidget()

        def fake_dispatch(_media_file: str):
            return (
                SimpleNamespace(
                    status=SimpleNamespace(value="credential_unavailable"),
                    safe_diagnostic="cloud_asr_credential_missing",
                    action_succeeded=False,
                ),
                None,
            )

        app._dispatch_online_asr_provider_action = fake_dispatch

        with tempfile.NamedTemporaryFile(delete=False) as handle:
            media_file = handle.name
        try:
            assert app._start_online_asr_transcription(
                media_file,
                start_button=start_button,
                dialog=dialog,
            ) is True
        finally:
            os.unlink(media_file)

        assert app.online_asr_busy is False
        assert app.transcript_online_asr_button.kwargs["state"] == "normal"
        assert start_button.kwargs["state"] == "normal"
    finally:
        main.threading.Thread = original_thread


if __name__ == "__main__":
    test_online_asr_control_copies_local_asr_visual_spec()
    test_online_asr_cog_opens_access_keys_without_dispatch()
    test_online_asr_dispatch_uses_coordinator_and_validated_request_once()
    test_online_asr_start_requires_file_and_prevents_duplicate_dispatch()
    test_online_asr_success_routes_to_transcript_display()
    test_online_asr_worker_restores_controls_after_safe_failure()
    test_online_asr_worker_restores_main_button_when_dialog_was_closed()
    print("Online ASR UI self-test passed.")
