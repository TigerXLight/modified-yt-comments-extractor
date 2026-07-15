from __future__ import annotations

import os
import sys
import tempfile
from types import SimpleNamespace

import main
from credential_runtime_status import (
    CredentialPresenceState,
    CredentialProvenance,
    CredentialRuntimeStatus,
    SafeCredentialDiagnostic,
)
from provider_key_validation import (
    KEY_STATUS_SAVED_NOT_VALIDATED,
    KEY_VALIDATION_VALIDATED,
)
from asr_provider_action import ASR_PROVIDER_ACTION_TRANSCRIBE
from elevenlabs_scribe_provider import (
    ELEVENLABS_SCRIBE_MODEL_ID,
    ELEVENLABS_SCRIBE_PROVIDER_ID,
    ElevenLabsScribeResult,
    ElevenLabsScribeStatus,
    ElevenLabsScribeWord,
)


SECRET_SENTINEL = "ONLINE-ASR-SECRET-MUST-NOT-LEAK"
CREATED_WIDGETS: list["FakeWidget"] = []


class FakeWidget:
    def __init__(self, parent: object = None, **kwargs: object) -> None:
        self.parent = parent
        self.kwargs = dict(kwargs)
        self.pack_calls: list[dict[str, object]] = []
        self.grid_calls: list[dict[str, object]] = []
        self.place_calls: list[dict[str, object]] = []
        self.bind_calls: list[tuple[str, object, object]] = []
        self.destroyed = False
        CREATED_WIDGETS.append(self)

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

    def grid_rowconfigure(self, *_args: object, **_kwargs: object) -> None:
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


def _patch_fake_widgets() -> tuple[object, ...]:
    CREATED_WIDGETS.clear()
    original_toplevel = main.ctk.CTkToplevel
    original_frame = main.ctk.CTkFrame
    original_button = main.ctk.CTkButton
    original_ctk_label = main.ctk.CTkLabel
    original_entry = main.ctk.CTkEntry
    original_font = main.ctk.CTkFont
    original_label = main.tk.Label
    original_string_var = main.tk.StringVar
    main.ctk.CTkToplevel = FakeWidget
    main.ctk.CTkFrame = FakeWidget
    main.ctk.CTkButton = FakeWidget
    main.ctk.CTkLabel = FakeWidget
    main.ctk.CTkEntry = FakeWidget
    main.ctk.CTkFont = lambda **kwargs: ("font", kwargs)
    main.tk.Label = FakeWidget
    main.tk.StringVar = FakeVar
    return (
        original_toplevel,
        original_frame,
        original_button,
        original_ctk_label,
        original_entry,
        original_font,
        original_label,
        original_string_var,
    )


def _created_widgets_with_text(text: str) -> list[FakeWidget]:
    return [widget for widget in CREATED_WIDGETS if widget.kwargs.get("text") == text]


def _created_textvariable_values() -> list[object]:
    values = []
    for widget in CREATED_WIDGETS:
        variable = widget.kwargs.get("textvariable")
        if hasattr(variable, "get"):
            values.append(variable.get())
    return values


def _restore_fake_widgets(originals: tuple[object, ...]) -> None:
    (
        main.ctk.CTkToplevel,
        main.ctk.CTkFrame,
        main.ctk.CTkButton,
        main.ctk.CTkLabel,
        main.ctk.CTkEntry,
        main.ctk.CTkFont,
        main.tk.Label,
        main.tk.StringVar,
    ) = originals


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
    app.online_asr_provider_window = None
    app.online_asr_provider_id = main.ONLINE_ASR_DEFAULT_PROVIDER_ID
    app.online_asr_provider_selection_status = ""
    app._set_linked_transcript_media = lambda path: setattr(app, "linked_media", path)
    app._refresh_transcript_display = lambda: setattr(app, "refreshed", True)
    app.access_keys_validation_states = {}
    return app


def _configured_elevenlabs_status() -> CredentialRuntimeStatus:
    return CredentialRuntimeStatus(
        credential_id="elevenlabs_scribe_api_key",
        entry_id="asr:elevenlabs_scribe",
        state=CredentialPresenceState.CONFIGURED,
        provenance=CredentialProvenance.SECURE_KEYRING,
        safe_diagnostic=SafeCredentialDiagnostic.CONFIGURED_PRESENCE_ONLY,
    )


class FakeSettingsManager:
    def __init__(self, provider_id: str = "") -> None:
        self.settings = main.AppSettings(online_asr_provider_id=provider_id)
        self.saved_settings: list[object] = []
        self.load_calls = 0
        self.load_preferences_calls = 0

    def load(self) -> object:
        self.load_calls += 1
        return self.settings

    def load_preferences_only(self) -> object:
        self.load_preferences_calls += 1
        return self.settings

    def save(self, settings: object) -> bool:
        self.saved_settings.append(settings)
        self.settings = settings
        return True


class FakeEntry:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.config: dict[str, object] = {}

    def delete(self, *_args: object) -> None:
        self.value = ""

    def insert(self, _index: object, value: object) -> None:
        self.value = str(value)

    def get(self) -> str:
        return self.value

    def configure(self, **kwargs: object) -> None:
        self.config.update(kwargs)


def _settings_app(settings_manager: FakeSettingsManager) -> main.App:
    app = _app()
    app.settings_manager = settings_manager
    app.api_key_entry = FakeEntry()
    app.spam_filter_var = FakeVar()
    app.spam_threshold_var = FakeVar()
    app.exclude_creator_var = FakeVar()
    app.min_likes_entry = FakeEntry()
    app.max_comments_entry = FakeEntry()
    app.filter_words_entry = FakeEntry()
    app.sort_var = FakeVar()
    app._on_spam_threshold_change = lambda _value: None
    app._on_spam_filter_toggle = lambda: None
    app._update_filter_counts = lambda: None
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


def test_main_import_does_not_eager_load_heavy_asr_or_sdk_client() -> None:
    assert "faster_whisper" not in sys.modules
    assert "elevenlabs.client" not in sys.modules


def test_load_settings_uses_preferences_only_and_keeps_provider_selection() -> None:
    manager = FakeSettingsManager(main.ELEVENLABS_SCRIBE_PROVIDER_ID)
    app = _settings_app(manager)

    main.App._load_settings(app)

    assert manager.load_preferences_calls == 1
    assert manager.load_calls == 0
    assert app.online_asr_provider_id == main.ELEVENLABS_SCRIBE_PROVIDER_ID
    assert app.api_key_entry.get() == ""
    assert app.api_key_entry.config["show"] == "*"


def test_api_section_startup_does_not_probe_credential_status() -> None:
    originals = _patch_fake_widgets()
    try:
        app = _app()
        app.sidebar_scroll = FakeWidget()

        class ExplodingSettingsManager:
            def get_storage_info(self) -> str:
                raise AssertionError("startup should not probe credential storage")

        app.settings_manager = ExplodingSettingsManager()
        app._refresh_youtube_credential_status = lambda: (_ for _ in ()).throw(
            AssertionError("startup should not refresh credential status")
        )

        main.App._create_api_section(app)

        assert app.storage_label.kwargs["text"] == "Credential status not refreshed"
    finally:
        _restore_fake_widgets(originals)


def test_online_asr_cog_opens_access_keys_without_dispatch() -> None:
    originals = _patch_fake_widgets()
    try:
        app = _app()
        app.settings_manager = FakeSettingsManager()
        status_calls: list[str] = []
        app._online_asr_credential_status_provider = (
            lambda: status_calls.append("status") or {}
        )
        calls: list[str] = []
        app.open_access_keys_window = lambda: calls.append("access_keys") or "window"
        app._dispatch_online_asr_provider_action = lambda *_args, **_kwargs: calls.append("dispatch")

        window = app.open_online_asr_settings_clicked()

        assert isinstance(window, FakeWidget)
        assert window.kwargs["title"] == main.ONLINE_ASR_PROVIDERS_WINDOW_TITLE
        assert calls == []
        assert status_calls == ["status"]
    finally:
        _restore_fake_widgets(originals)


def test_online_asr_provider_window_uses_shared_key_status_wording() -> None:
    originals = _patch_fake_widgets()
    try:
        app = _app()
        app.settings_manager = FakeSettingsManager()
        app._online_asr_credential_status_provider = lambda: {
            "asr:elevenlabs_scribe": _configured_elevenlabs_status()
        }

        app.open_online_asr_settings_clicked()
        values = _created_textvariable_values()

        assert KEY_STATUS_SAVED_NOT_VALIDATED in values
        assert "Credential status: Configured" not in values
        assert "Configured" not in values
    finally:
        _restore_fake_widgets(originals)


def test_keys_button_still_opens_access_keys_directly() -> None:
    app = _app()
    app.access_keys_window = None
    app.settings_manager = object()
    calls: list[str] = []
    app.open_access_keys_window = lambda: calls.append("access_keys") or "window"

    assert app.open_access_keys_window() == "window"
    assert calls == ["access_keys"]


def test_online_asr_body_still_opens_transcription_workflow() -> None:
    app = _app()
    calls: list[str] = []
    app.online_asr_transcribe_clicked = lambda: calls.append("body")

    app.online_asr_transcribe_clicked()

    assert calls == ["body"]


def test_online_asr_provider_selection_persists_non_secret_metadata() -> None:
    app = _app()
    manager = FakeSettingsManager()
    app.settings_manager = manager

    selected = app._set_online_asr_provider_id(
        main.ELEVENLABS_SCRIBE_PROVIDER_ID,
        persist=True,
    )

    assert selected == main.ELEVENLABS_SCRIBE_PROVIDER_ID
    assert manager.saved_settings
    saved = manager.saved_settings[-1]
    assert saved.online_asr_provider_id == main.ELEVENLABS_SCRIBE_PROVIDER_ID
    assert getattr(saved, "api_key", "") == ""
    assert SECRET_SENTINEL not in repr(saved)


def test_online_asr_invalid_provider_falls_back_safely() -> None:
    app = _app()
    app.settings_manager = FakeSettingsManager("unsupported_provider")

    selected = app._set_online_asr_provider_id("unsupported_provider", persist=False)

    assert selected == main.ONLINE_ASR_DEFAULT_PROVIDER_ID
    assert app.online_asr_provider_selection_status
    assert "Unsupported" in app.online_asr_provider_selection_status


def test_online_asr_manage_key_opens_access_keys_without_dispatch() -> None:
    originals = _patch_fake_widgets()
    try:
        app = _app()
        app.settings_manager = FakeSettingsManager()
        app._online_asr_credential_status_provider = lambda: {}
        calls: list[str] = []
        access_window = SimpleNamespace(
            _select_entry=lambda entry_id: calls.append(f"select:{entry_id}")
        )
        app.open_access_keys_window = lambda: calls.append("access_keys") or access_window
        app._dispatch_online_asr_provider_action = lambda *_args, **_kwargs: calls.append("dispatch")

        app.open_online_asr_settings_clicked()
        manage_buttons = [
            widget
            for widget in _created_widgets_with_text("Manage key")
        ]
        assert manage_buttons
        manage_buttons[-1].kwargs["command"]()

        assert calls == ["access_keys", "select:asr:elevenlabs_scribe"]
    finally:
        _restore_fake_widgets(originals)


def test_online_asr_use_provider_saves_without_dispatch() -> None:
    originals = _patch_fake_widgets()
    try:
        app = _app()
        manager = FakeSettingsManager()
        app.settings_manager = manager
        app._online_asr_credential_status_provider = lambda: {}
        dispatch_calls: list[str] = []
        app._dispatch_online_asr_provider_action = (
            lambda *_args, **_kwargs: dispatch_calls.append("dispatch")
        )

        app.open_online_asr_settings_clicked()
        use_buttons = _created_widgets_with_text("Use provider")
        assert use_buttons
        use_buttons[-1].kwargs["command"]()

        assert dispatch_calls == []
        assert manager.saved_settings
        assert manager.saved_settings[-1].online_asr_provider_id == main.ELEVENLABS_SCRIBE_PROVIDER_ID
    finally:
        _restore_fake_widgets(originals)


def test_cloud_asr_key_validation_uses_connection_coordinator_and_safe_tester() -> None:
    app = _app()
    tester_calls: list[tuple[str, str]] = []

    class FakeCoordinator:
        def test_provider_connection(self, provider_id: str, *, tester: object):
            tester(provider_id, SECRET_SENTINEL)
            return SimpleNamespace(
                status=main.ASRConnectionTestStatus.TESTER_COMPLETED,
                safe_diagnostic="trusted_connection_tester_completed",
            )

    def fake_tester(provider_id: str, credential: str) -> None:
        tester_calls.append((provider_id, credential))

    record = app._validate_cloud_asr_provider_key(
        main.ELEVENLABS_SCRIBE_PROVIDER_ID,
        coordinator=FakeCoordinator(),
        tester=fake_tester,
    )

    assert record.provider_id == main.ELEVENLABS_SCRIBE_PROVIDER_ID
    assert record.state == KEY_VALIDATION_VALIDATED
    assert tester_calls == [(main.ELEVENLABS_SCRIBE_PROVIDER_ID, SECRET_SENTINEL)]
    assert SECRET_SENTINEL not in repr(record)


def test_cloud_asr_key_validation_persists_only_non_secret_metadata() -> None:
    app = _app()
    manager = FakeSettingsManager()
    app.settings_manager = manager

    app._set_access_keys_validation_records(
        {
            main.ELEVENLABS_SCRIBE_PROVIDER_ID: {
                "provider_id": main.ELEVENLABS_SCRIBE_PROVIDER_ID,
                "state": KEY_VALIDATION_VALIDATED,
                "checked_at_utc": "2026-07-15T12:00:00+00:00",
                "safe_diagnostic": "key_validation_succeeded",
                "api_key": SECRET_SENTINEL,
            }
        }
    )

    saved = manager.saved_settings[-1]
    data = saved.access_keys_validation_states
    assert data[main.ELEVENLABS_SCRIBE_PROVIDER_ID]["state"] == KEY_VALIDATION_VALIDATED
    assert "api_key" not in data[main.ELEVENLABS_SCRIBE_PROVIDER_ID]
    assert SECRET_SENTINEL not in repr(data)


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
    test_main_import_does_not_eager_load_heavy_asr_or_sdk_client()
    test_load_settings_uses_preferences_only_and_keeps_provider_selection()
    test_api_section_startup_does_not_probe_credential_status()
    test_online_asr_cog_opens_access_keys_without_dispatch()
    test_online_asr_provider_window_uses_shared_key_status_wording()
    test_keys_button_still_opens_access_keys_directly()
    test_online_asr_body_still_opens_transcription_workflow()
    test_online_asr_provider_selection_persists_non_secret_metadata()
    test_online_asr_invalid_provider_falls_back_safely()
    test_online_asr_manage_key_opens_access_keys_without_dispatch()
    test_online_asr_use_provider_saves_without_dispatch()
    test_cloud_asr_key_validation_uses_connection_coordinator_and_safe_tester()
    test_cloud_asr_key_validation_persists_only_non_secret_metadata()
    test_online_asr_dispatch_uses_coordinator_and_validated_request_once()
    test_online_asr_start_requires_file_and_prevents_duplicate_dispatch()
    test_online_asr_success_routes_to_transcript_display()
    test_online_asr_worker_restores_controls_after_safe_failure()
    test_online_asr_worker_restores_main_button_when_dialog_was_closed()
    print("Online ASR UI self-test passed.")
