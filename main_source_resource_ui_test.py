import inspect
import json
import tempfile
from pathlib import Path

import main
from capture_twitter_exporter_review_flow import twitter_exporter_review_flow_to_json
from core.settings import AppSettings, SettingsManager
from main import App
from source_resource_state import (
    ARCHIVE_STATUS_AUTO_CHECK_DISABLED,
    build_source_resource_row,
)


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456?ocid=feeds"
YOUTUBE_URL = "https://www.youtube.com/watch?v=aB3_dE-9xYz"


class FakeTextBox:
    def __init__(self, text: str) -> None:
        self.text = text
        self.config: dict[str, object] = {}

    def get(self, *_args: object) -> str:
        return self.text

    def delete(self, *_args: object) -> None:
        self.text = ""

    def insert(self, _index: object, value: object) -> None:
        self.text = str(value) + self.text

    def configure(self, **kwargs: object) -> None:
        self.config.update(kwargs)


class FakeLabel:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}

    def configure(self, **kwargs: object) -> None:
        self.config.update(kwargs)


class FakeSettingsManager:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.saved_settings: list[AppSettings] = []

    def load_preferences_only(self) -> AppSettings:
        return self.settings

    def load(self) -> AppSettings:
        return self.settings

    def save(self, settings: AppSettings) -> bool:
        self.saved_settings.append(settings)
        self.settings = settings
        return True


class FakeVar:
    def __init__(self, value: object = "") -> None:
        self.value = value

    def get(self) -> object:
        return self.value

    def set(self, value: object) -> None:
        self.value = value


class FakeEntry(FakeTextBox):
    pass


class FakeFetchState:
    def __init__(self) -> None:
        self.is_fetching = False


class FakeMessageBox:
    def __init__(self) -> None:
        self.infos: list[tuple[str, str]] = []
        self.errors: list[tuple[str, str]] = []

    def showinfo(self, title: str, message: str) -> None:
        self.infos.append((title, message))

    def showerror(self, title: str, message: str) -> None:
        self.errors.append((title, message))


def _make_intake_app(text: str) -> App:
    app = App.__new__(App)
    app._url_placeholder = "placeholder"
    app.url_entry = FakeTextBox(text)
    app.url_status = FakeLabel()
    app.source_archive_auto_check_enabled = True
    app.source_resource_rows = []
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    app._refresh_source_resource_rows = lambda: setattr(app, "_rows_refreshed", True)
    app._refresh_discussion_source_controls = lambda: setattr(app, "_discussion_refreshed", True)
    return app


def _make_source_row_app() -> App:
    app = App.__new__(App)
    app.source_resource_rows = [
        build_source_resource_row(MSN_URL),
        build_source_resource_row(YOUTUBE_URL),
    ]
    app.selected_discussion_source_id = app.source_resource_rows[0].row_id
    app.source_resource_selections = {
        app.source_resource_rows[0].row_id: ("fixture-resource",),
        app.source_resource_rows[1].row_id: ("youtube-resource",),
    }
    app.source_screenshot_preferences = {
        app.source_resource_rows[0].row_id: {"webpage_screenshot": True},
        app.source_resource_rows[1].row_id: {"comments_screenshot": True},
    }
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    app.fetch_state = FakeFetchState()
    app.url_status = FakeLabel()
    app.extract_webpage_var = FakeVar(False)
    app.extract_comments_var = FakeVar(True)
    app.extract_live_chat_var = FakeVar(False)
    app.webpage_screenshot_var = FakeVar(False)
    app.comments_screenshot_var = FakeVar(False)
    app.livechat_screenshot_var = FakeVar(False)
    app._refresh_source_resource_rows = lambda: setattr(app, "_rows_refreshed", True)
    app._refresh_discussion_source_controls = lambda: setattr(app, "_discussion_refreshed", True)
    return app


def _make_settings_app(settings: AppSettings) -> App:
    app = App.__new__(App)
    app.settings_manager = FakeSettingsManager(settings)
    app.api_key_entry = FakeEntry("")
    app.spam_filter_var = FakeVar()
    app.spam_threshold_var = FakeVar()
    app.exclude_creator_var = FakeVar()
    app.min_likes_entry = FakeEntry("")
    app.max_comments_entry = FakeEntry("")
    app.filter_words_entry = FakeEntry("")
    app.sort_var = FakeVar()
    app._on_spam_threshold_change = lambda _value: None
    app._on_spam_filter_toggle = lambda: None
    app._update_filter_counts = lambda: None
    app._set_online_asr_provider_id = lambda _value, persist=False: None
    app._get_online_asr_provider_id = lambda: "elevenlabs_scribe"
    app._get_access_keys_added_provider_ids = lambda: ()
    app._get_min_likes = lambda: 0
    app._get_max_comments = lambda: None
    app._blacklist_patterns = ""
    app._whitelist_patterns = ""
    app.access_keys_validation_states = {}
    app.source_resource_rows = []
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    return app


def _make_twitter_import_app() -> App:
    app = App.__new__(App)
    app.url_status = FakeLabel()
    app.log_messages = []
    app.log_message = lambda message, level="info": app.log_messages.append((message, level))
    return app


def test_enter_source_url_intake_adds_rows_and_retains_invalid_text() -> None:
    app = _make_intake_app(f"bad words {MSN_URL}, {YOUTUBE_URL}")

    result = App._on_source_url_enter(app)

    assert result == "break"
    assert [row.adapter_id for row in app.source_resource_rows] == ["msn", "youtube"]
    assert "bad words" in app.url_entry.text
    assert app.url_status.config["text"].endswith("retained")
    assert app._rows_refreshed is True
    assert app._discussion_refreshed is True
    assert any("Network actions performed: none" in message for message, _level in app.log_messages)


def test_shift_enter_inserts_newline_without_submission() -> None:
    app = _make_intake_app("one")

    result = App._on_source_url_shift_enter(app)

    assert result == "break"
    assert app.url_entry.text.startswith("\n")
    assert app.source_resource_rows == []


def test_archive_auto_check_preference_loads_saves_and_drives_row_state() -> None:
    app = _make_settings_app(AppSettings(source_archive_auto_check_enabled=False))

    App._load_settings(app)
    assert app.source_archive_auto_check_enabled is False

    App._save_settings(app)
    assert app.settings_manager.saved_settings[-1].source_archive_auto_check_enabled is False

    intake = main.parse_source_url_intake(
        MSN_URL,
        archive_auto_check_enabled=app.source_archive_auto_check_enabled,
    )
    assert intake.rows[0].archive_statuses[0].status == ARCHIVE_STATUS_AUTO_CHECK_DISABLED


def test_source_url_section_layout_has_no_main_card_updates_and_has_required_controls() -> None:
    source = inspect.getsource(App._create_url_section)

    assert "Discussion source:" not in source
    assert "No discussion source" not in source
    assert 'values=[""]' in source
    assert source.index('text="Comments"') < source.index('text="Livechat"')
    assert source.index('text="Webpage"') < source.index('text="Comments"')
    assert source.count('text="Screenshot"') == 3
    assert "self.extract_webpage_var" in source
    assert "self.webpage_screenshot_var" in source
    assert "self.comments_screenshot_var" in source
    assert "self.livechat_screenshot_var" in source
    assert "self.update_button" not in source
    assert "_on_source_url_enter" in source
    assert "Source URLs" in source
    assert "Submit" not in source
    assert 'text="Twitter/X Local Export"' in source
    assert 'text="Add Review Draft"' in source
    assert 'text="Review Flow Summary"' in source
    assert "import_twitter_exporter_local_export_clicked" in source
    assert "queue_twitter_exporter_review_draft_clicked" in source
    assert "review_twitter_exporter_flow_summary_clicked" in source


def test_source_row_layout_uses_compact_resource_icons_and_remove_button() -> None:
    source = inspect.getsource(App._refresh_source_resource_rows)

    assert 'text="Images (' not in source
    assert 'text="Video & Audio (' not in source
    assert 'text="▧"' in source
    assert 'text="▶"' in source
    assert 'text="×"' in source
    assert "Images and GIFs" in source
    assert "Video and audio" in source
    assert "ARCHIVE_SERVICE_ARCHIVEBOX" in source
    assert "image=archivebox_icon" not in source  # CTkImage is supplied through kwargs
    assert 'button_kwargs["image"] = archivebox_icon' in source
    assert "_remove_source_resource_row_clicked" in source
    assert "text=row.domain" in source
    assert "row.domain} / {row.canonical_url}" not in source
    assert 'actions.grid(row=2, column=0, sticky="ew"' in source
    assert 'images_button.grid(row=0, column=1' in source
    assert 'media_button.grid(row=0, column=2' in source
    assert 'status_label.grid(' in source
    assert 'row=1,' in source
    assert 'remove_button.grid(' in source


def test_archive_status_label_uses_date_only_for_available_status() -> None:
    helper_source = inspect.getsource(App._archive_status_label_text)
    row_source = inspect.getsource(App._refresh_source_resource_rows)
    popup_source = inspect.getsource(App._show_archive_status)

    assert 'archive_status.status == "available"' in helper_source
    assert "archive_status.saved_date" in helper_source
    assert '"Saved"' not in helper_source
    assert 'text_color=COLORS["text_primary"]' in row_source
    assert "archive_status.tooltip" not in popup_source
    assert "status_text = self._archive_status_label_text" in popup_source


def test_remove_source_row_updates_selection_and_scoped_state() -> None:
    app = _make_source_row_app()
    removed_id = app.source_resource_rows[0].row_id
    remaining_id = app.source_resource_rows[1].row_id

    App._remove_source_resource_row_clicked(app, removed_id)

    assert [row.row_id for row in app.source_resource_rows] == [remaining_id]
    assert app.selected_discussion_source_id == remaining_id
    assert removed_id not in app.source_resource_selections
    assert removed_id not in app.source_screenshot_preferences
    assert app._rows_refreshed is True
    assert app._discussion_refreshed is True

    App._remove_source_resource_row_clicked(app, remaining_id)

    assert app.source_resource_rows == []
    assert app.selected_discussion_source_id == ""
    assert app.source_resource_selections == {}
    assert app.source_screenshot_preferences == {}


def test_sidebar_spacing_is_compact_between_updates_keys_and_export() -> None:
    keys_source = inspect.getsource(App._create_access_keys_section)
    export_source = inspect.getsource(App._create_export_section)

    assert 'text="KEYS/ACCOUNTS"' in keys_source
    assert "_create_section_separator" not in keys_source
    assert 'pady=(15 if first else 0, 6)' in keys_source
    assert 'text="EXPORT"' in export_source
    assert "_create_section_separator" not in export_source
    assert 'pady=(0, 10)' in export_source


def test_sidebar_order_places_updates_above_keys_export_files() -> None:
    source = inspect.getsource(App._create_sidebar)

    assert source.index("_create_updates_section") < source.index("_create_access_keys_section")
    assert source.index("_create_access_keys_section") < source.index("_create_export_section")
    assert source.index("_create_export_section") < source.index("_create_files_section")
    updates_source = inspect.getsource(App._create_updates_section)
    assert 'text="UPDATES"' in updates_source
    assert "check_for_updates_clicked" in updates_source


def test_evidence_database_review_has_no_visible_main_hook() -> None:
    source = inspect.getsource(App)

    assert "Evidence Database" not in source
    assert "evidence_database_review" not in source
    assert "build_synthetic_demo_review_window_controller" not in source
    assert "create_evidence_database_review_window" not in source


def test_transcript_toolbar_get_label_preserves_youtube_callback() -> None:
    source = inspect.getsource(App._create_transcript_section)
    reset_source = inspect.getsource(App.download_youtube_transcript_clicked)

    assert 'text="Get"' in source
    assert "command=self.download_youtube_transcript_clicked" in source
    assert "transcript_get_tooltip_text" in source
    assert "Current runtime support remains limited" in source
    assert 'text="⬇ YouTube"' not in source
    assert 'text="Get"' in reset_source


def test_online_asr_is_key_gated_and_uses_matching_local_button_control() -> None:
    transcript_source = inspect.getsource(App._create_transcript_section)
    action_control_source = inspect.getsource(App._create_asr_action_control)
    start_source = inspect.getsource(App._start_online_asr_transcription)
    gate_source = inspect.getsource(App._record_online_asr_provider_call_gate)

    assert "ONLINE_ASR_BUTTON_TEXT" in transcript_source
    assert 'wrap_attr="transcript_online_asr_button_wrap"' in transcript_source
    assert 'button_attr="transcript_online_asr_button"' in transcript_source
    assert 'settings_attr="transcript_online_asr_settings_button"' in transcript_source
    assert "ASR_ACTION_BUTTON_SPEC" in action_control_source
    assert "button_width" in action_control_source
    assert "button_height" in action_control_source
    assert "cog_x" in action_control_source
    assert "_record_online_asr_provider_call_gate" in start_source
    assert "credential_configured" in start_source
    assert "KEYS/ACCOUNTS" in start_source
    assert "open_online_asr_settings_clicked" in start_source
    assert "_dispatch_online_asr_provider_action" in start_source
    main_source = Path("main.py").read_text(encoding="utf-8")
    assert "build_online_asr_execution_gate_plan" in gate_source or "build_online_asr_execution_gate_plan" in main_source
    assert "last_online_asr_execution_gate_plan" in gate_source or "last_online_asr_execution_gate_plan" in main_source
    assert "last_online_asr_execution_gate_summary" in gate_source or "last_online_asr_execution_gate_summary" in main_source
    assert "render_online_asr_execution_gate_summary_text" in gate_source or "render_online_asr_execution_gate_summary_text" in main_source


def test_start_fetching_msn_scaffold_returns_before_credential_resolution() -> None:
    source = inspect.getsource(App.start_fetching)

    assert 'selected_discussion_row.adapter_id != "youtube"' in source
    assert "webpage_screenshot_requested=self.webpage_screenshot_var.get()" in source
    assert "build_operational_capture_plan" in source
    assert "format_operational_capture_plan_message" in source
    assert "last_operational_capture_plan" in source
    assert source.index('selected_discussion_row.adapter_id != "youtube"') < source.index(
        "_resolve_youtube_api_key_for_action"
    )
    assert "_set_operational_capture_status" in source
    assert "_record_operational_capture_review_metadata" in source
    review_metadata_source = inspect.getsource(
        main.App._record_operational_capture_review_metadata
    )
    assert "build_source_evidence_workflow_state" in review_metadata_source
    assert "last_source_evidence_workflow_state" in review_metadata_source
    assert "Fixture/model-only capture plan ready" in source


def test_start_fetching_source_scaffold_builds_plan_preview_without_live_execution() -> None:
    app = _make_source_row_app()
    app.extract_webpage_var.set(True)
    app.webpage_screenshot_var.set(True)
    app.comments_screenshot_var.set(True)
    fake_messagebox = FakeMessageBox()
    original_messagebox = main.messagebox
    main.messagebox = fake_messagebox
    try:
        App.start_fetching(app)
    finally:
        main.messagebox = original_messagebox

    assert app.last_operational_capture_plan.selected_modes == ("webpage", "comments")
    assert app.last_operational_capture_plan.screenshot_intents == ("webpage", "comments")
    assert fake_messagebox.infos[0][0] == "Discussion action scaffold"
    assert "Artifact declarations:" in fake_messagebox.infos[0][1]
    assert "Action event chain:" in fake_messagebox.infos[0][1]
    assert "Source Evidence workflow state" in fake_messagebox.infos[0][1]
    assert "Manual live-site smoke: pending separate approval" in fake_messagebox.infos[0][1]
    assert app.last_operational_capture_status.startswith("Fixture/model-only")
    assert app.url_status.config["text"].startswith("Fixture/model-only")
    assert app.last_source_evidence_workflow_state.queue_item_count > 0
    assert app.last_source_evidence_workflow_state.review_manifest_asset_count > 0
    assert app.last_operational_capture_queue_review_store.metadata_only is True
    assert app.last_operational_capture_review_manifest.assets
    assert any("no fetch" in message for message, _level in app.log_messages)
    assert any("WARC/WACZ" in message for message, _level in app.log_messages)
    assert any("Source evidence review metadata ready" in message for message, _level in app.log_messages)




def test_source_evidence_workflow_state_can_save_review_bundle() -> None:
    app = _make_source_row_app()
    app.extract_webpage_var.set(True)
    app.webpage_screenshot_var.set(True)
    fake_messagebox = FakeMessageBox()
    original_messagebox = main.messagebox
    main.messagebox = fake_messagebox
    try:
        App.start_fetching(app)
    finally:
        main.messagebox = original_messagebox

    with tempfile.TemporaryDirectory() as temp_dir:
        result = App.save_last_source_evidence_workflow_review_bundle(app, temp_dir)
        assert result.file_count == 8
        assert result.metadata_file_write_performed is True
        assert result.evidence_file_move_performed is False
        assert result.full_local_path_included is False
        assert Path(temp_dir, "source_evidence_workflow_review_bundle.json").is_file()
        assert Path(temp_dir, "source_evidence_release_readiness.json").is_file()
        assert Path(temp_dir, "source_evidence_release_action_plan.json").is_file()
        assert Path(temp_dir, "source_grabbed_record.json").is_file()
        assert Path(temp_dir, "source_evidence_database_scan_result.json").is_file()
        assert Path(temp_dir, "source_access_provider_gate_summary.json").is_file()

    assert app.last_source_evidence_workflow_review_bundle.bundle_id == result.bundle_id
    assert any("review bundle saved" in message for message, _level in app.log_messages)


def test_start_fetching_without_selected_scope_sets_skipped_status() -> None:
    app = _make_source_row_app()
    app.extract_webpage_var.set(False)
    app.extract_comments_var.set(False)
    app.extract_live_chat_var.set(False)
    fake_messagebox = FakeMessageBox()
    original_messagebox = main.messagebox
    main.messagebox = fake_messagebox
    try:
        App.start_fetching(app)
    finally:
        main.messagebox = original_messagebox

    assert fake_messagebox.errors[0][0] == "Selection Required"
    assert app.last_operational_capture_status == "Skipped: no selected source scopes."
    assert app.url_status.config["text"] == "Skipped: no selected source scopes."
    assert "last_operational_capture_plan" not in app.__dict__


def test_twitter_exporter_import_review_action_is_summary_only_and_local() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "tweet.json"
        source.write_text(
            json.dumps([{"id": "909", "text": "DO NOT SHOW THIS TWEET BODY"}]),
            encoding="utf-8",
        )
        app = _make_twitter_import_app()
        fake_messagebox = FakeMessageBox()
        original_messagebox = main.messagebox
        main.messagebox = fake_messagebox
        try:
            state = App._run_twitter_exporter_local_import_review_action(
                app,
                (str(source),),
            )
        finally:
            main.messagebox = original_messagebox

    assert state.review_status == "USER_REVIEW_REQUIRED"
    assert state.provenance_status == "USER_SUPPLIED_LOCAL_EXPORT"
    assert state.queue_metadata_available is False
    assert app.last_twitter_exporter_import_review_state == state
    assert app.url_status.config["text"].startswith("Twitter/X local export review:")
    assert "1 parsed" in app.url_status.config["text"]
    shown_text = fake_messagebox.infos[0][1]
    combined_log = "\n".join(message for message, _level in app.log_messages)
    assert "tweet.json" in shown_text
    assert "USER_REVIEW_REQUIRED" in shown_text
    assert "USER_SUPPLIED_LOCAL_EXPORT" in shown_text
    assert "Network actions performed: none" in shown_text
    assert "DO NOT SHOW THIS TWEET BODY" not in shown_text
    assert "DO NOT SHOW THIS TWEET BODY" not in combined_log
    assert "Source files were not moved" in combined_log


def test_twitter_exporter_import_review_action_reports_invalid_files_safely() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        unsupported = root / "bad.exe"
        unsupported.write_text("not supported", encoding="utf-8")
        missing = root / "missing.txt"
        app = _make_twitter_import_app()
        fake_messagebox = FakeMessageBox()
        original_messagebox = main.messagebox
        main.messagebox = fake_messagebox
        try:
            state = App._run_twitter_exporter_local_import_review_action(
                app,
                (str(unsupported), str(missing)),
            )
        finally:
            main.messagebox = original_messagebox

    shown_text = fake_messagebox.infos[0][1]
    assert state.total_error_count == 2
    assert "bad.exe" in shown_text
    assert "missing.txt" in shown_text
    assert "Unsupported Twitter exporter import file type" in shown_text
    assert "does not exist" in shown_text
    assert str(root) not in shown_text
    assert app.url_status.config["text_color"] == main.COLORS["warning"]
    assert "Network actions performed: none" in shown_text


def test_twitter_exporter_queue_review_draft_action_uses_last_summary_only_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "tweet.json"
        source.write_text(
            json.dumps([{"id": "1001", "text": "DO NOT QUEUE THIS TWEET BODY"}]),
            encoding="utf-8",
        )
        app = _make_twitter_import_app()
        fake_messagebox = FakeMessageBox()
        original_messagebox = main.messagebox
        main.messagebox = fake_messagebox
        try:
            App._run_twitter_exporter_local_import_review_action(app, (str(source),))
            draft = App._run_twitter_exporter_queue_review_draft_action(app)
        finally:
            main.messagebox = original_messagebox

    assert draft is app.last_twitter_exporter_queue_review_draft
    assert draft.review_status == "USER_REVIEW_REQUIRED"
    assert draft.provenance_status == "USER_SUPPLIED_LOCAL_EXPORT"
    assert draft.eligible_input_count == 1
    assert draft.queue_items[0]["item_status"] == "NEEDS_REVIEW"
    assert draft.queue_items[0]["local_path"] == ""
    assert app.url_status.config["text"].startswith("Twitter/X queue review draft:")
    shown_text = fake_messagebox.infos[-1][1]
    combined_log = "\n".join(message for message, _level in app.log_messages)
    combined_draft = json.dumps(draft.to_dict(), sort_keys=True)
    assert "DO NOT QUEUE THIS TWEET BODY" not in shown_text
    assert "DO NOT QUEUE THIS TWEET BODY" not in combined_log
    assert "DO NOT QUEUE THIS TWEET BODY" not in combined_draft
    assert "Metadata/counts only" in combined_log
    assert "evidence-completion claims: none" in shown_text


def test_twitter_exporter_queue_review_draft_action_handles_missing_prior_import() -> None:
    app = _make_twitter_import_app()
    fake_messagebox = FakeMessageBox()
    original_messagebox = main.messagebox
    main.messagebox = fake_messagebox
    try:
        draft = App._run_twitter_exporter_queue_review_draft_action(app)
    finally:
        main.messagebox = original_messagebox

    assert draft is None
    assert "import a local export first" in app.url_status.config["text"]
    assert "import a local export first" in fake_messagebox.infos[0][1]
    assert "last_twitter_exporter_queue_review_draft" not in app.__dict__


def test_twitter_exporter_review_flow_summary_action_is_counts_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = root / "tweet.json"
        second = root / "tweet 2.jsonl"
        first.write_text(
            json.dumps([{"id": "2001", "text": "DO NOT DISPLAY FIRST BODY"}]),
            encoding="utf-8",
        )
        second.write_text(
            json.dumps({"id": "2002", "text": "DO NOT DISPLAY SECOND BODY"}) + "\n",
            encoding="utf-8",
        )
        app = _make_twitter_import_app()
        fake_messagebox = FakeMessageBox()
        original_messagebox = main.messagebox
        main.messagebox = fake_messagebox
        try:
            flow = App._run_twitter_exporter_review_flow_summary_action(
                app,
                (str(first), str(second)),
            )
        finally:
            main.messagebox = original_messagebox

    assert flow is app.last_twitter_exporter_review_flow
    assert app.last_twitter_exporter_import_review_state is flow.source_review_state
    assert app.last_twitter_exporter_queue_review_draft is flow.queue_draft
    assert flow.review_status == "USER_REVIEW_REQUIRED"
    assert flow.provenance_status == "USER_SUPPLIED_LOCAL_EXPORT"
    assert flow.source_review_state.input_count == 2
    assert flow.queue_draft.eligible_input_count == 2
    assert len(flow.manifest_report.entries) == 2
    assert len(flow.action_receipt.file_entries) == 2
    assert app.url_status.config["text"].startswith("Twitter/X review flow summary:")
    assert "USER_REVIEW_REQUIRED / USER_SUPPLIED_LOCAL_EXPORT" in app.url_status.config["text"]
    shown_text = fake_messagebox.infos[0][1]
    combined_log = "\n".join(message for message, _level in app.log_messages)
    combined_state = twitter_exporter_review_flow_to_json(flow)
    for safe_text in (shown_text, combined_state):
        assert "tweet.json" in safe_text
        assert "tweet 2.jsonl" in safe_text
        assert "USER_REVIEW_REQUIRED" in safe_text
        assert "USER_SUPPLIED_LOCAL_EXPORT" in safe_text
        assert "DO NOT DISPLAY FIRST BODY" not in safe_text
        assert "DO NOT DISPLAY SECOND BODY" not in safe_text
        assert str(root) not in safe_text
    assert "DO NOT DISPLAY FIRST BODY" not in combined_log
    assert "DO NOT DISPLAY SECOND BODY" not in combined_log
    assert str(root) not in combined_log
    assert "Summary/counts only" in shown_text
    assert "completed-evidence claims: none" in shown_text
    for claim in (
        "api_capture_claimed",
        "archive_claimed",
        "automatic_classification_claimed",
        "browser_automation_claimed",
        "completed_evidence_claimed",
        "downloaded_media_claimed",
        "live_verification_claimed",
        "screenshot_ocr_claimed",
        "warc_wacz_claimed",
    ):
        assert f'"{claim}": false' in combined_state


def test_twitter_exporter_review_flow_summary_action_is_deterministic_for_batches() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = root / "one.csv"
        second = root / "two.tsv"
        first.write_text("id,text\n3001,DO NOT DISPLAY CSV BODY\n", encoding="utf-8")
        second.write_text("id\ttext\n3002\tDO NOT DISPLAY TSV BODY\n", encoding="utf-8")
        app = _make_twitter_import_app()
        fake_messagebox = FakeMessageBox()
        original_messagebox = main.messagebox
        main.messagebox = fake_messagebox
        try:
            first_flow = App._run_twitter_exporter_review_flow_summary_action(
                app,
                (str(first), str(second)),
            )
            second_flow = App._run_twitter_exporter_review_flow_summary_action(
                app,
                (str(first), str(second)),
            )
        finally:
            main.messagebox = original_messagebox

    first_json = twitter_exporter_review_flow_to_json(first_flow)
    second_json = twitter_exporter_review_flow_to_json(second_flow)
    assert first_json == second_json
    assert "DO NOT DISPLAY CSV BODY" not in first_json
    assert "DO NOT DISPLAY TSV BODY" not in first_json
    assert str(root) not in first_json
    assert first_flow.file_summaries[0].input_file_name == "one.csv"
    assert first_flow.file_summaries[1].input_file_name == "two.tsv"


def test_twitter_exporter_review_flow_summary_action_handles_no_selection() -> None:
    app = _make_twitter_import_app()
    fake_messagebox = FakeMessageBox()
    original_messagebox = main.messagebox
    main.messagebox = fake_messagebox
    try:
        flow = App._run_twitter_exporter_review_flow_summary_action(app, ())
    finally:
        main.messagebox = original_messagebox

    assert flow is None
    assert "no local export files selected" in app.url_status.config["text"]
    assert "no local export files selected" in fake_messagebox.infos[0][1]
    assert "Network actions performed: none" in app.log_messages[0][0]
    assert "last_twitter_exporter_review_flow" not in app.__dict__
    assert "last_twitter_exporter_queue_review_draft" not in app.__dict__


def test_twitter_exporter_review_flow_summary_action_reports_invalid_files_safely() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        unsupported = root / "raw.bin"
        unsupported.write_bytes(b"\x00\x01")
        missing = root / "missing.json"
        app = _make_twitter_import_app()
        fake_messagebox = FakeMessageBox()
        original_messagebox = main.messagebox
        main.messagebox = fake_messagebox
        try:
            flow = App._run_twitter_exporter_review_flow_summary_action(
                app,
                (str(unsupported), str(missing)),
            )
        finally:
            main.messagebox = original_messagebox

    shown_text = fake_messagebox.infos[0][1]
    combined_log = "\n".join(message for message, _level in app.log_messages)
    combined_state = twitter_exporter_review_flow_to_json(flow)
    assert flow.status == "REVIEW_ERROR"
    assert flow.source_review_state.total_error_count == 2
    assert "raw.bin" in shown_text
    assert "missing.json" in shown_text
    assert "Unsupported Twitter exporter import file type" in shown_text
    assert "does not exist" in shown_text
    assert str(root) not in shown_text
    assert str(root) not in combined_log
    assert str(root) not in combined_state
    assert "completed-evidence claims: none" in shown_text
    assert app.url_status.config["text_color"] == main.COLORS["warning"]


def test_archivebox_icon_and_service_order_are_local_only() -> None:
    source = inspect.getsource(App._refresh_source_resource_rows)
    loader = inspect.getsource(App._ensure_archivebox_icon)
    popup = inspect.getsource(App._show_archive_status)

    assert 'assets", "ui", "archivebox_icon.png"' in loader
    assert "ctk.CTkImage" in loader
    assert "ImageTk.PhotoImage" not in loader
    assert "ARCHIVE_SERVICE_ARCHIVEBOX" in source
    assert "archive_status.service_id != ARCHIVE_SERVICE_ARCHIVEBOX" in source
    assert "ArchiveBox local webpage archive scaffold" in popup
    assert "ArchiveBox execution performed: none" in popup
    assert source.index("for archive_status in row.archive_statuses") < source.index('text="×"')


def test_discussion_layout_uses_webpage_parent_and_child_rows() -> None:
    source = inspect.getsource(App._create_url_section)
    refresh_source = inspect.getsource(App._refresh_discussion_source_controls)

    assert 'text="Webpage"' in source
    assert source.count('text="Screenshot"') == 3
    assert "self.extract_webpage_var" in source
    assert "webpage_active" in refresh_source
    assert "self.webpage_checkbox.configure" in refresh_source


def test_main_blank_wheel_router_targets_main_without_stealing_text_scroll() -> None:
    source = inspect.getsource(App._route_main_pointer_wheel)
    scroll_source = inspect.getsource(App._scroll_main_frame_with_mousewheel)

    assert "winfo_containing" in source
    assert "sidebar_scroll" in source
    assert "main_frame" in source
    assert '"CTkTextbox"' in source
    assert "_scroll_main_frame_with_mousewheel" in source
    assert "lines_per_notch = 5" in scroll_source
    assert "high-resolution wheel/touchpad input" in scroll_source


def test_transcript_controls_are_split_across_rows_for_narrow_widths() -> None:
    source = inspect.getsource(App._create_transcript_section)

    assert "asr_button_row" in source
    assert "transcript_merge_row" in source
    assert source.index("asr_button_row") < source.index("transcript_media_status_label")


def test_url_helper_wrap_and_textbox_height_are_responsive() -> None:
    source = inspect.getsource(App._create_url_section)
    helper = inspect.getsource(App._on_url_card_configure)

    assert "height=112" in source
    assert "self.source_hint_label" in source
    assert "wraplength=width" in helper
    assert 'row=3, column=0, columnspan=5' in source


def run_self_test() -> None:
    test_enter_source_url_intake_adds_rows_and_retains_invalid_text()
    test_shift_enter_inserts_newline_without_submission()
    test_archive_auto_check_preference_loads_saves_and_drives_row_state()
    test_source_url_section_layout_has_no_main_card_updates_and_has_required_controls()
    test_source_row_layout_uses_compact_resource_icons_and_remove_button()
    test_archive_status_label_uses_date_only_for_available_status()
    test_remove_source_row_updates_selection_and_scoped_state()
    test_sidebar_spacing_is_compact_between_updates_keys_and_export()
    test_sidebar_order_places_updates_above_keys_export_files()
    test_transcript_toolbar_get_label_preserves_youtube_callback()
    test_online_asr_is_key_gated_and_uses_matching_local_button_control()
    test_start_fetching_msn_scaffold_returns_before_credential_resolution()
    test_start_fetching_source_scaffold_builds_plan_preview_without_live_execution()
    test_start_fetching_without_selected_scope_sets_skipped_status()
    test_twitter_exporter_import_review_action_is_summary_only_and_local()
    test_twitter_exporter_import_review_action_reports_invalid_files_safely()
    test_twitter_exporter_queue_review_draft_action_uses_last_summary_only_state()
    test_twitter_exporter_queue_review_draft_action_handles_missing_prior_import()
    test_twitter_exporter_review_flow_summary_action_is_counts_only()
    test_twitter_exporter_review_flow_summary_action_is_deterministic_for_batches()
    test_twitter_exporter_review_flow_summary_action_handles_no_selection()
    test_twitter_exporter_review_flow_summary_action_reports_invalid_files_safely()
    test_archivebox_icon_and_service_order_are_local_only()
    test_discussion_layout_uses_webpage_parent_and_child_rows()
    test_main_blank_wheel_router_targets_main_without_stealing_text_scroll()
    test_transcript_controls_are_split_across_rows_for_narrow_widths()
    test_url_helper_wrap_and_textbox_height_are_responsive()


if __name__ == "__main__":
    run_self_test()
    print("main_source_resource_ui_test.py: OK")
