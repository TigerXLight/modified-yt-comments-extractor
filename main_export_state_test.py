import threading
from pathlib import Path

import main
from main import App, FetchState, is_export_allowed
from core.settings import AppSettings
from youtube_credential_migration import YouTubeCredentialActionStatus

STORED_KEY_SENTINEL = "AIza" + ("S" * 35)
DRAFT_KEY_SENTINEL = "AIza" + ("D" * 35)


class MessageBoxRecorder:
    def __init__(self) -> None:
        self.warnings = []
        self.errors = []

    def showwarning(self, title: str, message: str) -> None:
        self.warnings.append((title, message))

    def showerror(self, title: str, message: str) -> None:
        self.errors.append((title, message))


class DialogRecorder:
    def __init__(self) -> None:
        self.save_called = False

    def asksaveasfilename(self, **_kwargs: object) -> str:
        self.save_called = True
        raise AssertionError("Save dialog should not open while export is blocked")


class FakeApiKeyEntry:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self.options = {"show": "*"}

    def get(self) -> str:
        return self.value

    def delete(self, _start: object, _end: object) -> None:
        self.value = ""

    def insert(self, _index: object, value: object) -> None:
        self.value = str(value)

    def configure(self, **kwargs: object) -> None:
        self.options.update(kwargs)

    def cget(self, key: str) -> object:
        return self.options.get(key, "")


class FakeStorageLabel:
    def __init__(self) -> None:
        self.text = ""

    def configure(self, *, text: str) -> None:
        self.text = text


class FakeVar:
    def __init__(self, value: object = "") -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def set(self, value: object) -> None:
        self.value = value


class FakeWidget:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}
        self.packed = False

    def configure(self, **kwargs: object) -> None:
        self.config.update(kwargs)

    def pack(self, **_kwargs: object) -> None:
        self.packed = True

    def pack_forget(self) -> None:
        self.packed = False


class FakeProgress:
    def __init__(self) -> None:
        self.value = 0

    def set(self, value: object) -> None:
        self.value = value


class FakeTextBox:
    def __init__(self, text: str) -> None:
        self.text = text

    def get(self, *_args: object) -> str:
        return self.text


class FakeSettingsManager:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.load_calls = 0

    def load(self) -> AppSettings:
        self.load_calls += 1
        return self.settings


class FakeThread:
    created: list["FakeThread"] = []

    def __init__(self, *, target: object, args: tuple[object, ...], daemon: bool) -> None:
        self.target = target
        self.args = args
        self.daemon = daemon
        self.started = False
        FakeThread.created.append(self)

    def start(self) -> None:
        self.started = True


class FakeExtractor:
    api_keys: list[str] = []

    def __init__(self, api_key: str, **_kwargs: object) -> None:
        FakeExtractor.api_keys.append(api_key)


class FakeYouTubeService:
    def __init__(
        self,
        status: YouTubeCredentialActionStatus,
        storage_state: main.YouTubeCredentialStorageState = main.YouTubeCredentialStorageState.MISSING,
    ) -> None:
        self.status = status
        self.storage_state = storage_state
        self.saved_values: list[str] = []
        self.migrated = False
        self.cleared = False

    class _Storage:
        def __init__(self, state: main.YouTubeCredentialStorageState) -> None:
            self.state = state

    class _Result:
        def __init__(self, status: YouTubeCredentialActionStatus) -> None:
            self.status = status

    def storage_status(self) -> object:
        return self._Storage(self.storage_state)

    def save_secure(self, value: str) -> object:
        self.saved_values.append(value)
        return self._Result(self.status)

    def migrate_legacy_to_secure(self) -> object:
        self.migrated = True
        return self._Result(self.status)

    def clear_all(self) -> object:
        self.cleared = True
        return self._Result(self.status)


def _make_app(fetch_state: FetchState, comments: list[dict[str, object]]) -> App:
    app = App.__new__(App)
    app.fetch_state = fetch_state
    app._data_lock = threading.Lock()
    app.all_metadata = [{"video_id": "aB3_dE-9xYz"}] if comments else []
    app.all_comments = comments
    app.all_spam = []
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    return app


def _make_credential_app(service: FakeYouTubeService) -> App:
    app = App.__new__(App)
    app.api_key_entry = FakeApiKeyEntry("placeholder")
    app.storage_label = FakeStorageLabel()
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    app._youtube_credential_service = lambda: service
    return app


def _make_load_settings_app(settings: AppSettings) -> App:
    app = App.__new__(App)
    app.settings_manager = FakeSettingsManager(settings)
    app.api_key_entry = FakeApiKeyEntry()
    app.spam_filter_var = FakeVar()
    app.spam_threshold_var = FakeVar()
    app.exclude_creator_var = FakeVar()
    app.min_likes_entry = FakeApiKeyEntry()
    app.max_comments_entry = FakeApiKeyEntry()
    app.filter_words_entry = FakeApiKeyEntry()
    app.sort_var = FakeVar()
    app._on_spam_threshold_change = lambda _value: None
    app._on_spam_filter_toggle = lambda: None
    app._update_filter_counts = lambda: None
    return app


def _make_fetch_app(entry_value: str, stored_key: str = "") -> App:
    app = App.__new__(App)
    app.fetch_state = FetchState()
    app.api_key_entry = FakeApiKeyEntry(entry_value)
    app.settings_manager = FakeSettingsManager(AppSettings(api_key=stored_key))
    app.url_entry = FakeTextBox("https://www.youtube.com/watch?v=aB3_dE-9xYz")
    app._url_placeholder = ""
    app._get_date_range = lambda: (None, None, None)
    app._save_settings = lambda: True
    app.fetch_button = FakeWidget()
    app.cancel_button = FakeWidget()
    app.export_button = FakeWidget()
    app.export_excel_button = FakeWidget()
    app.export_txt_button = FakeWidget()
    app.evidence_button = FakeWidget()
    app.progress_bar = FakeProgress()
    app.status_label = FakeWidget()
    app.clear_log = lambda: None
    app._data_lock = threading.Lock()
    app.all_metadata = []
    app.all_comments = []
    app.all_spam = []
    app._update_stats = lambda: None
    app.spam_threshold_var = FakeVar(0.5)
    app._blacklist_patterns = ""
    app._whitelist_patterns = ""
    app._get_filter_words = lambda: []
    app._get_max_comments = lambda: None
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    app.extract_comments_var = FakeVar(True)
    app.extract_live_chat_var = FakeVar(False)
    app.spam_filter_var = FakeVar(False)
    app._get_min_likes = lambda: 0
    app.sort_var = FakeVar(main.SortOption.DATE_NEWEST.display_name)
    app.exclude_creator_var = FakeVar(False)
    app._fetch_thread_ref = None
    return app


def _assert_entry_empty_and_masked(entry: FakeApiKeyEntry) -> None:
    if entry.get() != "":
        raise AssertionError("YouTube credential entry was not empty")
    if entry.cget("show") != "*":
        raise AssertionError("YouTube credential entry was not masked")


def _assert_value_used(actual: str, expected: str) -> None:
    if actual != expected:
        raise AssertionError("unexpected credential source was used")


def test_export_allowed_helper() -> None:
    idle_with_data = FetchState(is_fetching=False)
    assert is_export_allowed(idle_with_data, 1)

    idle_without_data = FetchState(is_fetching=False)
    assert not is_export_allowed(idle_without_data, 0)

    fetching = FetchState(is_fetching=True)
    assert not is_export_allowed(fetching, 1)

    cancelling = FetchState(is_fetching=False)
    cancelling.request_cancel()
    assert not is_export_allowed(cancelling, 1)


def test_direct_export_blocks_save_dialog_while_fetching() -> None:
    messagebox = MessageBoxRecorder()
    filedialog = DialogRecorder()
    original_messagebox = main.messagebox
    original_filedialog = main.filedialog
    main.messagebox = messagebox
    main.filedialog = filedialog
    try:
        app = _make_app(
            FetchState(is_fetching=True),
            [{"id": "comment-1", "text": "Exportable comment"}],
        )

        app.export_csv()

        assert not filedialog.save_called
        assert messagebox.warnings
        assert messagebox.warnings[0][0] == "Fetch In Progress"
        assert app.log_messages[-1][1] == "warning"
    finally:
        main.messagebox = original_messagebox
        main.filedialog = original_filedialog


def test_direct_export_blocks_save_dialog_without_data() -> None:
    messagebox = MessageBoxRecorder()
    filedialog = DialogRecorder()
    original_messagebox = main.messagebox
    original_filedialog = main.filedialog
    main.messagebox = messagebox
    main.filedialog = filedialog
    try:
        app = _make_app(FetchState(is_fetching=False), [])

        app.export_txt()

        assert not filedialog.save_called
        assert messagebox.warnings
        assert messagebox.warnings[0][0] == "No Data"
    finally:
        main.messagebox = original_messagebox
        main.filedialog = original_filedialog


def test_youtube_credential_actions_keep_entry_masked() -> None:
    service = FakeYouTubeService(YouTubeCredentialActionStatus.SAVED)
    app = _make_credential_app(service)
    app.api_key_entry.value = "draft-value"

    App._save_youtube_api_key_secure(app)

    assert app.api_key_entry.get() == ""
    assert app.api_key_entry.cget("show") == "*"
    if service.saved_values != ["draft-value"]:
        raise AssertionError("draft value was not passed to secure save")
    assert app.log_messages[-1][1] == "success"

    migrate_service = FakeYouTubeService(YouTubeCredentialActionStatus.MIGRATED)
    app = _make_credential_app(migrate_service)
    App._migrate_youtube_api_key(app)
    _assert_entry_empty_and_masked(app.api_key_entry)
    assert migrate_service.migrated is True

    clear_service = FakeYouTubeService(YouTubeCredentialActionStatus.CLEARED)
    app = _make_credential_app(clear_service)
    App._clear_youtube_api_key(app)
    assert app.api_key_entry.get() == ""
    assert app.api_key_entry.cget("show") == "*"
    assert clear_service.cleared is True


def test_load_settings_never_preloads_youtube_credential() -> None:
    for storage_name in ("secure", "legacy", "both"):
        app = _make_load_settings_app(AppSettings(api_key=STORED_KEY_SENTINEL))

        App._load_settings(app)

        _assert_entry_empty_and_masked(app.api_key_entry)
        if app.settings_manager.load_calls != 1:
            raise AssertionError(f"settings load count mismatch for {storage_name}")


def test_status_refresh_does_not_populate_youtube_entry() -> None:
    service = FakeYouTubeService(
        YouTubeCredentialActionStatus.SAVED,
        main.YouTubeCredentialStorageState.SECURE_KEYRING_ONLY,
    )
    app = _make_credential_app(service)
    app.api_key_entry.value = ""

    App._refresh_youtube_credential_status(app)

    _assert_entry_empty_and_masked(app.api_key_entry)
    assert app.storage_label.text == "Secure storage configured"


def test_youtube_api_key_resolution_prefers_draft_without_ui_preload() -> None:
    app = _make_fetch_app(DRAFT_KEY_SENTINEL, STORED_KEY_SENTINEL)

    resolved = App._resolve_youtube_api_key_for_action(app)

    _assert_value_used(resolved, DRAFT_KEY_SENTINEL)
    if app.settings_manager.load_calls != 0:
        raise AssertionError("stored credential lookup was unexpectedly used")
    _assert_value_used(app.api_key_entry.get(), DRAFT_KEY_SENTINEL)


def test_youtube_api_key_resolution_uses_stored_key_without_ui_preload() -> None:
    app = _make_fetch_app("", STORED_KEY_SENTINEL)

    resolved = App._resolve_youtube_api_key_for_action(app)

    _assert_value_used(resolved, STORED_KEY_SENTINEL)
    _assert_entry_empty_and_masked(app.api_key_entry)


def test_start_fetching_uses_stored_key_with_empty_entry() -> None:
    app = _make_fetch_app("", STORED_KEY_SENTINEL)
    original_extractor = main.YouTubeCommentExtractor
    original_thread = main.threading.Thread
    FakeExtractor.api_keys = []
    FakeThread.created = []
    main.YouTubeCommentExtractor = FakeExtractor
    main.threading.Thread = FakeThread
    try:
        App.start_fetching(app)
    finally:
        main.YouTubeCommentExtractor = original_extractor
        main.threading.Thread = original_thread

    _assert_value_used(FakeExtractor.api_keys[-1], STORED_KEY_SENTINEL)
    _assert_entry_empty_and_masked(app.api_key_entry)
    assert FakeThread.created[-1].started is True


def test_start_fetching_prefers_typed_draft_key() -> None:
    app = _make_fetch_app(DRAFT_KEY_SENTINEL, STORED_KEY_SENTINEL)
    original_extractor = main.YouTubeCommentExtractor
    original_thread = main.threading.Thread
    FakeExtractor.api_keys = []
    FakeThread.created = []
    main.YouTubeCommentExtractor = FakeExtractor
    main.threading.Thread = FakeThread
    try:
        App.start_fetching(app)
    finally:
        main.YouTubeCommentExtractor = original_extractor
        main.threading.Thread = original_thread

    _assert_value_used(FakeExtractor.api_keys[-1], DRAFT_KEY_SENTINEL)


def test_start_fetching_without_any_key_remains_invalid() -> None:
    app = _make_fetch_app("", "")
    messagebox = MessageBoxRecorder()
    original_messagebox = main.messagebox
    original_extractor = main.YouTubeCommentExtractor
    main.messagebox = messagebox
    main.YouTubeCommentExtractor = FakeExtractor
    FakeExtractor.api_keys = []
    try:
        App.start_fetching(app)
    finally:
        main.messagebox = original_messagebox
        main.YouTubeCommentExtractor = original_extractor

    assert messagebox.errors
    assert messagebox.errors[0][0] == "Invalid API Key"
    assert not FakeExtractor.api_keys


def test_youtube_reveal_toggle_is_removed() -> None:
    main_source = Path("main.py").read_text(encoding="utf-8")
    assert "_toggle_api_key_visibility" not in main_source
    assert "api_key_visible" not in main_source
    assert "toggle_api_key_button" not in main_source
    assert 'show=""' not in main_source


def run_self_test() -> None:
    test_export_allowed_helper()
    test_direct_export_blocks_save_dialog_while_fetching()
    test_direct_export_blocks_save_dialog_without_data()
    test_youtube_credential_actions_keep_entry_masked()
    test_load_settings_never_preloads_youtube_credential()
    test_status_refresh_does_not_populate_youtube_entry()
    test_youtube_api_key_resolution_prefers_draft_without_ui_preload()
    test_youtube_api_key_resolution_uses_stored_key_without_ui_preload()
    test_start_fetching_uses_stored_key_with_empty_entry()
    test_start_fetching_prefers_typed_draft_key()
    test_start_fetching_without_any_key_remains_invalid()
    test_youtube_reveal_toggle_is_removed()


if __name__ == "__main__":
    run_self_test()
    print("Main export state self-test passed.")
