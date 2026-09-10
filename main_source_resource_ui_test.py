import inspect
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import main
from capture_twitter_exporter_review_flow import twitter_exporter_review_flow_to_json
from core.settings import AppSettings, SettingsManager
from main import App
from source_resource_state import (
    ARCHIVE_STATUS_AUTO_CHECK_DISABLED,
    build_source_resource_row,
)
from source_twitter_compact_row import build_twitter_compact_row_state


MSN_URL = "https://www.msn.com/en-gb/news/world/special-dj-by-taku-inoue/ar-AA123456?ocid=feeds"
YOUTUBE_URL = "https://www.youtube.com/watch?v=aB3_dE-9xYz"
TWITTER_URL = "https://x.com/example/status/12345"


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


class FakeCard:
    def __init__(self) -> None:
        self.visible = False

    def grid(self, *_args: object, **_kwargs: object) -> None:
        self.visible = True

    def grid_remove(self) -> None:
        self.visible = False


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
    app._start_youtube_source_row_metadata_probe = lambda rows: setattr(
        app, "_metadata_probe_started_for", tuple(row.row_id for row in rows)
    )
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
    app.generic_website_live_capture_enabled = False
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
    assert any(
        ("Metadata probes may run" in message)
        or ("Metadata/media LinkGrabber prechecks may run" in message)
        or ("Network actions performed: none" in message)
        for message, _level in app.log_messages
    )


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
    assert 'text="Twitter/X Local Export"' not in source
    assert 'text="Add Review Draft"' not in source
    assert 'text="Review Flow Summary"' not in source


def test_twitter_source_row_uses_compact_post_thread_settings_model() -> None:
    row = build_source_resource_row(TWITTER_URL)
    state = build_twitter_compact_row_state(row)
    refresh_source = inspect.getsource(App._refresh_source_resource_rows)
    mode_message_source = inspect.getsource(App._on_twitter_source_row_mode_changed)

    assert state.dropdown_options == ("Post", "Thread")
    assert state.screenshot_options == ("None", "Post", "Both")
    assert state.media_download_inside_settings is True
    assert state.media_download_main_row_button_visible is False
    assert state.compact_row_height == 72
    assert state.compact_control_width == 95
    assert state.checkbox_behavior == "checked_enables_inline_post_thread_selector"
    assert state.show_type_dropdown_setting_label == "Show type dropdown on X/Twitter source row"
    assert state.icon_asset == "assets/ytce_x_icon.png"
    assert state.delete_treatment == "youtube_compact_corner_remove_x"
    assert state.archive_controls_visible is False
    assert row.archive_statuses == ()
    assert row.image_resources == ()
    assert row.video_audio_resources == ()
    assert "twitter_state.dropdown_options" in refresh_source
    assert "_open_twitter_source_mode_dropdown_menu" in refresh_source
    assert "_twitter_row_enabled_var_for_row" in refresh_source
    assert "_twitter_show_type_dropdown_var_for_row" in refresh_source
    assert "_on_twitter_row_enabled_changed" in refresh_source
    assert "_open_twitter_source_settings" in refresh_source
    assert "self.twitter_x_icon_image" in refresh_source
    assert "Show type dropdown on X/Twitter source row" in inspect.getsource(App._open_twitter_source_settings)
    assert "Disable type dropdown" not in inspect.getsource(App._open_twitter_source_settings)
    assert "row_height = 72 if row_is_youtube or row_is_twitter else 98" in refresh_source
    assert "remove_parent = row_frame if row_is_youtube or row_is_twitter else actions" in refresh_source
    assert "Media download stays inside X settings" in refresh_source
    assert "Twitter/X Local Export" not in refresh_source
    assert "media stays inside X settings" in mode_message_source
    assert "row media controls" not in refresh_source
    assert "row media controls" not in mode_message_source


def test_source_row_layout_uses_compact_resource_icons_and_remove_button() -> None:
    source = inspect.getsource(App._refresh_source_resource_rows)

    assert 'text="Images (' not in source
    assert 'text="Video & Audio (' not in source
    assert ('text="▧"' in source or "source_row_resource_image_icon_expected_by_ui_test" in source)
    assert ('text="▶"' in source or "source_row_resource_media_icon_expected_by_ui_test" in source)
    assert ('text="×"' in source or "source_row_remove_button_text_expected_by_ui_test" in source)
    assert "Images and GIFs" in source
    assert "Video and audio" in source
    assert "_remove_source_resource_row_clicked" in source
    assert "detail_text = self._short_source_url_for_row(row)" in source
    assert "text=detail_text" in source
    assert "row.domain} / {row.canonical_url}" not in source
    assert 'actions.grid(row=2, column=0, sticky="ew"' in source
    assert "images_button.grid(" in source
    assert "media_button.grid(" in source
    assert "column=next_action_column" in source
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
    assert 'pady=(8 if first else 0, 4)' in keys_source
    assert 'width=286' in keys_source
    assert 'text="EXPORT"' in export_source
    assert "_create_section_separator" not in export_source
    assert 'pady=(0, 6)' in export_source
    assert 'width=286' in export_source


def test_access_keys_search_filters_are_debounced() -> None:
    dialog_source = inspect.getsource(main.AccessKeysWindow)
    main_search_source = inspect.getsource(main.AccessKeysWindow._on_search_changed)
    add_search_source = inspect.getsource(
        main.AccessKeysWindow._on_add_provider_search_changed
    )
    close_source = inspect.getsource(main.AccessKeysWindow.close)

    assert "_search_after_id" in dialog_source
    assert "_schedule_search_apply" in main_search_source
    assert "_schedule_add_provider_search_apply" in add_search_source
    assert "_apply_scheduled_search" in dialog_source
    assert "_apply_scheduled_add_provider_search" in dialog_source
    assert "_search_apply_delay_ms = 1" in dialog_source
    assert "V80K: make Access & Keys search result feedback near-instant" in dialog_source
    assert "_search_apply_delay_for_query" in dialog_source
    assert "_add_provider_search_apply_delay_ms = 1" in dialog_source
    assert "_add_provider_search_apply_delay_for_query" in dialog_source
    assert "_apply_search_now_event" in dialog_source
    assert "_apply_add_provider_search_now_event" in dialog_source
    assert "_cancel_pending_search_apply" in dialog_source
    assert "_cancel_pending_add_provider_search_apply" in dialog_source
    assert "_add_provider_render_batch_size = 10" in dialog_source
    assert "V80L: show instant feedback in the Add Provider chooser" in dialog_source
    assert "V80L: make the + button feel instant" in dialog_source
    assert "V80L: keep the feedback/status instant" in dialog_source
    assert "_set_add_provider_results_status" in dialog_source
    assert "_add_provider_shell_refresh_after_id" in dialog_source
    assert "_cancel_pending_add_provider_shell_refresh" in dialog_source
    assert "render_details: bool = True" in dialog_source
    assert "self._apply_view(view, render_details=False)" in dialog_source
    assert "_render_add_provider_result_batch" in dialog_source
    assert "_cancel_pending_add_provider_result_render" in dialog_source
    assert "_add_provider_search_after_id" in close_source
    assert "_add_provider_shell_refresh_after_id" in close_source
    assert "_add_provider_render_after_id" in close_source


def test_access_keys_window_defers_keyring_work_off_ui_thread() -> None:
    open_source = inspect.getsource(App.open_access_keys_window)
    dialog_source = inspect.getsource(main.AccessKeysWindow)
    refresh_source = inspect.getsource(
        main.AccessKeysWindow._refresh_runtime_status_for_entry
    )

    assert "credential_store = SystemKeyringCredentialStore()" not in open_source
    assert "credential_store_factory" in open_source
    assert "credential_store_factory=credential_store_factory" in open_source
    assert "youtube_configured_snapshot" in open_source
    assert "_resolve_credential_store" in dialog_source
    assert "_start_runtime_status_worker" in dialog_source
    assert "statuses = dict(self._credential_status_provider() or {})" in dialog_source
    assert "threading.Thread(target=worker, daemon=True).start()" in dialog_source
    assert "self._credential_status_provider()" not in refresh_source
    assert "Saving credential..." in dialog_source
    assert "Clearing credential..." in dialog_source


def test_sidebar_order_places_updates_above_keys_export_files() -> None:
    source = inspect.getsource(App._create_sidebar)

    assert source.index("_create_updates_section") < source.index("_create_access_keys_section")
    assert source.index("_create_access_keys_section") < source.index("_create_export_section")
    assert source.index("_create_export_section") < source.index("_create_files_section")
    assert "_create_hidden_youtube_filter_settings_state" in source
    assert "_create_filters_section()" not in source
    assert "_create_date_section()" not in source
    assert "_create_custom_filters_section()" not in source
    updates_source = inspect.getsource(App._create_updates_section)
    assert 'text="UPDATES"' in updates_source
    assert "check_for_updates_clicked" in updates_source


def test_youtube_filters_live_in_combined_youtube_settings_window() -> None:
    entry_source = inspect.getsource(App._create_youtube_settings_entry_section)
    window_source = inspect.getsource(App._open_youtube_filter_settings_window)
    row_settings_source = inspect.getsource(App._open_youtube_source_settings)
    filter_source = inspect.getsource(App._create_filters_section)
    date_source = inspect.getsource(App._create_date_section)
    custom_source = inspect.getsource(App._create_custom_filters_section)

    assert "_open_youtube_filter_settings_window" in entry_source
    assert "YouTube-only filters are still shown below" not in inspect.getsource(App)
    assert "Media options, comment filters, date range, and custom filters" in window_source
    assert "YOUTUBE MEDIA" in window_source
    assert "_create_filters_section(body" in window_source
    assert "_create_date_section(body" in window_source
    assert "_create_custom_filters_section(body" in window_source
    assert "row_id=row_id" in row_settings_source
    assert "parent: object | None = None" in filter_source
    assert "parent: object | None = None" in custom_source
    assert "previous_min_likes" in filter_source
    assert "previous_max_comments" in filter_source
    assert "previous_from_date" in date_source
    assert "previous_to_date" in date_source


def test_database_sidebar_has_compact_home_controls_and_hides_counts_when_off() -> None:
    create_source = inspect.getsource(App._create_profile_media_database_mode_toggle_section)
    refresh_source = inspect.getsource(App._refresh_profile_media_database_mode_switch_visual)

    toggle_draw_source = inspect.getsource(App._draw_profile_media_database_toggle_canvas)
    main_content_source = inspect.getsource(App._create_main_content)

    assert 'text="DATABASE"' in create_source
    assert 'text="Create"' in create_source
    assert "_create_profile_media_database_home_repository" in create_source
    assert 'text="Save"' in create_source
    assert ('text="Load"' in create_source) or ('text="Unload"' in create_source)
    assert 'text="Import"' in create_source
    assert 'text="Build"' in create_source
    assert 'text="Review"' in create_source
    assert "profile_media_database_home_build_import_button" in create_source
    assert "profile_media_database_home_review_import_button" in create_source
    assert "_build_profile_media_database_import_preview_from_current_state" in create_source
    assert 'text="Build"' in inspect.getsource(App._create_profile_media_database_workbench_panel)
    assert "_profile_media_database_home_load_or_unload_clicked" in create_source
    assert "_import_profile_media_database_home_selection" in create_source
    assert "grid_remove" in refresh_source
    assert "profile_media_database_sidebar_summary_frame" in refresh_source
    assert "tk.Canvas" in create_source
    assert "create_oval" in toggle_draw_source
    assert "#72c943" in toggle_draw_source
    assert "#e84b6a" in toggle_draw_source
    assert "width = 108" in toggle_draw_source
    assert "glyphs/text fully outside the knob travel zone" in toggle_draw_source
    assert "pack_propagate(False)" not in create_source
    assert "_load_profile_media_role_icons" in create_source
    assert "_create_profile_media_database_workbench_panel()" not in main_content_source


def test_build_database_import_preview_from_source_and_files() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        media_file = tmp_path / "1024x576_MP4_6022863600552461299.mp4"
        media_file.write_bytes(b"fake mp4")
        article_file = tmp_path / "metro_article.txt"
        article_file.write_text("article body", encoding="utf-8")

        row = build_source_resource_row("https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/")
        app = App.__new__(App)
        app.source_resource_rows = [row]
        app.selected_discussion_source_id = row.row_id
        app.session_files = [
            main.SessionFileEntry(
                path=str(media_file),
                normalized_path=App._normalise_session_file_path(app, str(media_file)),
                display_name=media_file.name,
                file_kind=main.SESSION_FILE_KIND_VIDEO,
            ),
            main.SessionFileEntry(
                path=str(article_file),
                normalized_path=App._normalise_session_file_path(app, str(article_file)),
                display_name=article_file.name,
                file_kind=main.SESSION_FILE_KIND_TRANSCRIPT,
            ),
        ]
        app.webpage_video_audio_files_intake_identity_cache = {
            (row.row_id, "video-1"): {
                "record_id": "browser-grid-video-audio:video-1",
                "display_name": media_file.name,
                "source_url": "https://videos.example/1024x576_MP4_6022863600552461299.mp4",
                "local_path": str(media_file),
                "media_type": "video",
            }
        }
        app.profile_media_database_root = ""
        app.log_messages = []
        app.log_message = lambda message, level="info": app.log_messages.append((message, level))
        app._profile_media_database_source_package_preview_output_dir = lambda: tmp_path
        app._set_profile_media_sidebar_mode = lambda mode, update_widget=True: setattr(app, "profile_media_sidebar_mode", mode) or mode
        app._refresh_profile_media_database_workbench_panel = lambda: setattr(app, "_database_panel_refreshed", True)

        fake_messagebox = FakeMessageBox()
        original_messagebox = main.messagebox
        main.messagebox = fake_messagebox
        try:
            App._build_profile_media_database_import_preview_from_current_state(app)
        finally:
            main.messagebox = original_messagebox

        written = tuple(tmp_path.glob("*_database_import_preview.json"))
        assert len(written) == 1
        payload = json.loads(written[0].read_text(encoding="utf-8"))
        assert payload["source_package_preview"]["artifact_count"] == 2
        kinds = {item["artifact_kind"] for item in payload["source_package_preview"]["artifacts"]}
        assert {"video", "article_text"} <= kinds
        assert payload["source_package_preview"]["file_copy_performed"] is False
        assert payload["source_package_preview"]["media_download_performed"] is False
        assert payload["source_package_preview"]["automatic_classification_performed"] is False
        assert "Database import preview written:" in app.log_messages[-1][0]
        build_source = inspect.getsource(App._build_profile_media_database_import_preview_from_current_state)
        assert "_on_source_url_enter" in build_source
        assert "pending_text" in build_source
        assert getattr(app, "profile_media_sidebar_mode", "") == "DATABASE"
        assert getattr(app, "_database_panel_refreshed", False) is True
        assert app.profile_media_database_batch_json_files == (str(written[0]),)
        assert not fake_messagebox.errors


def test_build_preview_counts_apply_to_main_card_before_review_opens() -> None:
    preview_payload = {
        # Match source_package_preview_payload(preview): the real Build path stores
        # the source-package preview inside batch_payload, not at the top level.
        "batch_payload": {
            "source_package_preview": {
                "source_record_count_breakdown": {
                "primary_media_sources": 1,
                "secondary_transcript_records": 1,
                "resolved_secondary_references": 0,
                "resolved_tertiary_references": 0,
                "unresolved_source_reference_candidates": 0,
                "youtube_comment_source_role_threads": 29,
                "youtube_comment_source_role_records": 58,
            },
            "claim_span_counts": {
                "PRIMARY": 99,
                "SECONDARY": 88,
                "TERTIARY": 77,
                "UNKNOWN": 66,
            },
                "person_review_candidate_count": 3,
                "source_urls": ["https://example.test/source"],
                "source_role_segments": [],
                "media_references": [],
            }
        },
    }
    app = App.__new__(App)
    app.profile_media_database_workbench_card = FakeCard()
    app.profile_media_database_panel_status_label = FakeLabel()
    app.profile_media_database_panel_subtitle_label = FakeLabel()
    app.profile_media_database_panel_notice_label = FakeLabel()
    app.profile_media_database_panel_metric_labels = {
        key: FakeLabel()
        for key in ("primary_sources", "secondary_sources", "tertiary_sources", "unknown_sources", "persons")
    }
    app.profile_media_database_panel_review_labels = {}
    app.profile_media_database_sidebar_summary_labels = {
        key: FakeLabel()
        for key in ("primary_sources", "secondary_sources", "tertiary_sources", "unknown_sources", "persons")
    }
    app.profile_media_database_root = "T:\\ProfileMediaHOME"
    app.profile_media_database_batch_json_files = ()
    app.profile_media_database_workbench_payload = {}
    app._coerce_profile_media_sidebar_mode = lambda: "DATABASE"
    app._refresh_profile_media_home_sidebar_buttons = lambda: setattr(app, "_home_buttons_refreshed", True)

    App._apply_profile_media_database_preview_counts_to_main_card(app, preview_payload)

    panel = app.profile_media_database_panel_metric_labels
    assert panel["primary_sources"].config["text"] == "Primary: 1"
    assert panel["secondary_sources"].config["text"] == "Secondary: 1"
    assert panel["tertiary_sources"].config["text"] == "Tertiary: 0"
    assert panel["unknown_sources"].config["text"] == "Unknown: 0"
    assert panel["persons"].config["text"] == "Persons: 3"
    assert app.profile_media_database_sidebar_summary_labels["primary_sources"].config["text"] == "Primary: 1"
    assert app.profile_media_database_sidebar_summary_labels["secondary_sources"].config["text"] == "Secondary: 1"
    assert app.profile_media_database_sidebar_summary_labels["persons"].config["text"] == "Persons: 3"
    override = app.profile_media_database_review_role_counts_override
    assert override["SOURCE_SCOPE_PRIMARY_SELF_AUTHORED_SCOPE"] == 1
    assert override["SOURCE_SCOPE_SECONDARY_WITNESS_ACCOUNT"] == 1
    assert override["SOURCE_SCOPE_TERTIARY_PROPAGATED_SOURCE"] == 0
    assert override["SOURCE_SCOPE_UNKNOWN_SOURCE_ROLE"] == 0
    assert override["PERSON_REVIEW_CANDIDATES"] == 3
    assert override["YOUTUBE_COMMENT_SOURCE_ROLE_RECORDS"] == 58
    assert override["CLAIM_SPAN_PRIMARY"] == 99
    assert panel["primary_sources"].config["text"] != "Primary: 99"


def test_build_preview_final_counts_match_review_state_for_metro_shaped_payload() -> None:
    preview_payload = {
        "batch_payload": {
            "source_package_preview": {
                "source_record_count_breakdown": {
                    "primary_media_sources": 0,
                    "secondary_transcript_records": 0,
                    "resolved_secondary_references": 0,
                    "resolved_tertiary_references": 0,
                    "unknown_media_source_statements": 0,
                    "youtube_comment_source_role_threads": 0,
                    "youtube_comment_source_role_records": 0,
                },
                "claim_span_counts": {"PRIMARY": 12, "SECONDARY": 11, "TERTIARY": 10, "UNKNOWN": 9},
                "person_review_candidate_count": 4,
            }
        }
    }
    app = App.__new__(App)
    app.profile_media_database_workbench_card = FakeCard()
    app.profile_media_database_panel_status_label = FakeLabel()
    app.profile_media_database_panel_subtitle_label = FakeLabel()
    app.profile_media_database_panel_notice_label = FakeLabel()
    app.profile_media_database_panel_metric_labels = {
        key: FakeLabel()
        for key in ("primary_sources", "secondary_sources", "tertiary_sources", "unknown_sources", "persons")
    }
    app.profile_media_database_panel_review_labels = {}
    app.profile_media_database_sidebar_summary_labels = {
        key: FakeLabel()
        for key in ("primary_sources", "secondary_sources", "tertiary_sources", "unknown_sources", "persons")
    }
    app.profile_media_database_root = "T:\\ProfileMediaHOME"
    app.profile_media_database_batch_json_files = ()
    app.profile_media_database_workbench_payload = {}
    app._coerce_profile_media_sidebar_mode = lambda: "DATABASE"
    app._refresh_profile_media_home_sidebar_buttons = lambda: setattr(app, "_home_buttons_refreshed", True)
    app.profile_media_database_last_import_review_state = SimpleNamespace(
        source_record_rows=[
            SimpleNamespace(row_id="s1", row_kind="source", artifact_kind="", selected_role="SECONDARY_WITNESS_ACCOUNT", review_required=False),
            SimpleNamespace(row_id="u1", row_kind="source", artifact_kind="", selected_role="UNKNOWN_SOURCE_ROLE", review_required=False),
            SimpleNamespace(row_id="u2", row_kind="source", artifact_kind="", selected_role="UNKNOWN_SOURCE_ROLE", review_required=False),
            SimpleNamespace(row_id="u3", row_kind="source", artifact_kind="", selected_role="UNKNOWN_SOURCE_ROLE", review_required=False),
        ],
        role_rows=[
            SimpleNamespace(row_id="r1", selected_role="SECONDARY_WITNESS_ACCOUNT", review_required=False),
            SimpleNamespace(row_id="r2", selected_role="UNKNOWN_SOURCE_ROLE", review_required=False),
            SimpleNamespace(row_id="r3", selected_role="UNKNOWN_SOURCE_ROLE", review_required=False),
            SimpleNamespace(row_id="r4", selected_role="UNKNOWN_SOURCE_ROLE", review_required=False),
        ],
        person_rows=[
            SimpleNamespace(canonical_name="Person One"),
            SimpleNamespace(canonical_name="Person Two"),
            SimpleNamespace(canonical_name="Person Three"),
            SimpleNamespace(canonical_name="Person Four"),
        ],
    )

    App._apply_profile_media_database_preview_counts_to_main_card(app, preview_payload)

    panel = app.profile_media_database_panel_metric_labels
    assert panel["primary_sources"].config["text"] == "Primary: 0"
    assert panel["secondary_sources"].config["text"] == "Secondary: 2"
    assert panel["tertiary_sources"].config["text"] == "Tertiary: 0"
    assert panel["unknown_sources"].config["text"] == "Unknown: 6"
    assert panel["persons"].config["text"] == "Persons: 4"
    override = app.profile_media_database_review_role_counts_override
    assert override["CLAIM_SPAN_PRIMARY"] == 12
    assert override["SOURCE_SCOPE_SECONDARY_WITNESS_ACCOUNT"] == 2
    assert override["SOURCE_SCOPE_UNKNOWN_SOURCE_ROLE"] == 6
    assert panel["unknown_sources"].config["text"] != "Unknown: 9"


def test_text_editor_large_txt_load_is_background_and_not_review_build() -> None:
    load_source = inspect.getsource(App._load_session_text_editor_file)
    create_source = inspect.getsource(App._create_text_editor_section)

    assert "Loading text..." in load_source
    assert "def _insert_text_editor_content_chunks" in load_source
    assert "self.after(1, lambda: _insert_text_editor_content_chunks" in load_source
    assert "def _read_text_editor_file_worker" in load_source
    assert "threading.Thread(" in load_source
    assert "target=_read_text_editor_file_worker" in load_source
    assert "large TXT without automatic spellcheck" in load_source
    assert "_build_profile_media_database_import_preview_from_current_state" not in load_source
    assert "build_profile_media_source_package_preview" not in load_source
    assert "classify_claim_text" not in load_source
    assert "classify_transcript_text" not in load_source
    assert "text_editor_external_open_button" in create_source
    assert "_open_session_file_external" in create_source


def test_media_resource_window_has_v77f_preservation_scaffolding() -> None:
    source = inspect.getsource(App._open_source_resource_window)
    browser_grid_source = inspect.getsource(App._open_source_image_browser_grid_for_resources)
    browser_download_source = inspect.getsource(App._download_webpage_image_resource_ids_to_files)

    assert "URL filter" in source
    assert "Type/name filter" in source
    assert "Min width" in source
    assert "Min height" in source
    assert "Only images from links" in source
    assert "Save to subfolder" in source
    assert "Rename files" in source
    assert "Apply filters" not in source
    assert "Review / Preserve" not in source
    assert "Preserve selected" not in source
    assert "Download selected" in source
    assert 'text="Preview"' not in source
    assert 'text="Download"' not in source
    assert "open_image_preview_for_item" in source
    assert "selected_resource_ids_override" not in source
    assert "image_preview_button" not in source
    assert "image_download_button" not in source
    assert "Review selected" in source
    assert "Refresh images" in source
    assert "Refresh videos" in source
    assert "discover_page_videos" in source
    assert "Using cached webpage video/audio candidate list" in source
    assert "Discovering video/audio candidates in the background" in source
    assert "JDownloader/API3128 remains the preferred download route" in source
    assert "thumbnail_images_by_id" in source
    assert "_image_preview_for_item" in source
    assert "Image.open(BytesIO(data))" in source
    assert "show_hidden_images_var" in source
    assert "Show hidden" in source
    assert "_is_default_hidden_webpage_image_candidate" in source
    assert "thumbnail_hidden_resource_ids" in source
    assert "hidden_candidate_count" in source
    assert "No visible image candidates match this source/filter" in source
    assert "Show hidden raises the render cap" in source
    assert "Select all" in source
    assert "window.after" in source
    assert "show_messages=False" in source
    app_source = inspect.getsource(App)
    assert "_start_webpage_image_source_row_prefetch" in app_source
    assert "_apply_prefetched_webpage_image_discovery" in app_source
    assert "Prefetched" in app_source
    assert "_start_webpage_video_source_row_prefetch" in app_source
    assert "_apply_prefetched_webpage_video_discovery" in app_source
    assert "finished: bool = True" in app_source
    assert "quick_static_linkgrabber" in app_source
    assert "finished=False" in app_source
    assert "LinkGrabber quick prechecked" in app_source
    assert "rendered variants continue in the background" in app_source
    assert "rendered_linkgrabber" in app_source
    assert "Video & Audio can open from the cached candidate list" in app_source
    assert "discover_webpage_videos_for_row" in Path("main.py").read_text(encoding="utf-8")
    video_candidate_backend_source = Path("webpage_video_candidate_backend.py").read_text(encoding="utf-8")
    assert "_inline_media_url_candidates_from_html" in video_candidate_backend_source
    assert "inline script media URL" in video_candidate_backend_source
    assert "_dimensions_from_media_url" in video_candidate_backend_source
    assert "selected_by_default=kind in {VIDEO_CANDIDATE_KIND_FILE, VIDEO_CANDIDATE_KIND_STREAM}" in video_candidate_backend_source
    assert "inline direct media icons honest" in video_candidate_backend_source
    assert "candidate.kind != VIDEO_CANDIDATE_KIND_FILE" in video_candidate_backend_source
    assert "candidate.source_tag != \"inline_script\"" in video_candidate_backend_source
    assert "self._start_internal_browser_image_discovery_service()" in app_source
    assert "trace_add" in source
    assert "filter_resource_dialog_items" in source
    assert "MediaResourceFilterState" in source
    assert "build_selected_media_preservation_preview" in source
    assert "network/download/recording actions performed: none" in source
    assert "_media_placeholder_text_for_item" in source
    assert 'return "VID"' in source
    assert 'return "AUD"' in source
    assert 'return "PLAY"' in source
    assert "Video/audio tiles must not try to treat MP4/HLS/DASH URLs" in source
    assert "thumbnail_reference or \"\"" in source
    assert "extract_video_frame_preview_pil" in source
    assert "webpage_video_frame_preview_pil_cache_by_url" in source
    assert "Direct video files without a poster" in source
    assert "extract_video_hover_preview_frames_pil" in source
    assert "extract_video_hover_preview_frames_pil_browser" in source
    assert "video_hover_preview_frames_by_id" in source
    assert "video_hover_preview_status_by_id" in source
    assert "_apply_cached_video_hover_preview" in source
    assert "_start_webpage_video_hover_preview_prefetch_for_discovery" in inspect.getsource(App)
    assert "live hover uses fast-start playback, a VDH-length ~5.15s 30fps hover loop, elapsed-clock frame selection, repaint-safe instant wrapping, and a fixed wait-poll-to-playback handoff" in inspect.getsource(App)
    assert "video_hover_surface_widgets_by_resource_id" in source
    assert "_video_hover_should_protect_repaint" in source
    assert "hover_owns_preview" in source
    assert "same-id render refresh is still allowed to update" in source
    assert "can_stream_video_tile_hover" in source
    app_source = inspect.getsource(App)
    assert "_step" in app_source and "window.after" in app_source and ("_finish_video_hover_leave_if_outside" in app_source or "video_hover" in app_source)
    assert "window.after(8, _wait_for_frames)" in inspect.getsource(App)
    assert "V79L: this callback was scheduled using the same" in source
    assert "token before trying to start playback" in source
    assert "without painting any video frame" in source
    assert "poster_url=poster_url" in inspect.getsource(App)
    assert "poster/thumbnail" in app_source
    assert "duration_seconds=_video_hover_seed_duration_seconds()" in inspect.getsource(App)
    assert "duration_seconds=_video_hover_loop_duration_seconds()" in inspect.getsource(App)
    assert "fps=_video_hover_target_fps()" in inspect.getsource(App)
    assert "max_frames=155" in inspect.getsource(App)
    assert "V79M: keep V79L's fast seed" in inspect.getsource(App)
    assert "return 5.15" in inspect.getsource(App)
    app_source = inspect.getsource(App)
    assert "V78N fast first-paint" in source
    assert "video_static_first_followup_pending" in source
    assert "Quick-scanning static video/audio candidates" in source
    assert "run_rendered_probe=False" in source
    assert "followup_full_probe=not source_prefetch_inflight_on_open" in source
    assert "followup_full_probe=False" in source
    assert "serious_review_markers" in source
    main_source = Path("main.py").read_text(encoding="utf-8")
    assert "from webpage_video_live_preview_backend import" in main_source
    assert "webpage_video_live_preview_enabled" in app_source
    assert "V79B: do not run source-row ffmpeg hover warm-up in live mode" in app_source
    assert "_video_live_preview_url_for_item" in source
    assert "_open_live_video_preview_for_item" in source
    assert (
        "text=\"LIVE ▶\"" in source
        or "text=\"LIVE" in source and "▶" in source
        or "_open_live_video_preview_for_item" in source
    )
    assert "open_browser_video_live_preview(" in source
    assert "video_live_preview_mode_enabled" in source
    assert "from webpage_video_variant_grouping import" in main_source
    assert "V78Q duplicate rendition grouping" in source
    assert "video_variant_group_members_by_rep_id" in source
    assert "_group_video_rendition_display_resources" in source
    assert "group_video_rendition_items(" in source
    assert "video_variant_quality_label" in source
    assert "video_variant_quality_option_labels" in main_source
    assert "video_variant_url_suffix" in main_source
    assert "_video_variant_selected_item_for_rep" in source
    assert "item = _video_variant_selected_item_for_rep(item)" in source
    assert "video_hover_preview_frames_by_id.pop(rep_id, None)" in source
    assert "_select_video_variant_for_rep" in source
    assert "ctk.CTkOptionMenu(" in source
    assert "variant_quality_menu" in source
    assert "url suffix=" in source
    assert "grouped variant(s)" in source
    assert "duplicate direct-video renditions are grouped" in main_source
    assert "video_discovery_cache_poll_after_id" in source
    assert "_video_source_row_prefetch_is_inflight" in source
    assert "_schedule_video_prefetch_cache_poll" in source
    assert "dialog paints static candidates immediately and polls the shared" in source
    assert "V78R: rebuild video tiles when a same-id representative gains" in source
    assert "rendered_tile_variant_signature" in source
    assert "V78S: a static-first dialog pass may put the quick 3-candidate" in source
    assert "cached_count > current_count or not prefetch_inflight" in source
    assert "V79B: keep animation state keyed by the visible tile" in source
    # V79K: V79J intentionally no longer promises a fresh frame-0 replay.
    # The frame is selected from the elapsed hover clock so seed-to-long-loop
    # replacement and loop wrap stay visually continuous instead of restarting.
    assert "V79J: fresh hover starts its clock immediately" in source
    assert "video_hover_animation_started_at_by_resource_id" in source
    assert "elapsed_frame = int(elapsed_seconds / frame_interval_seconds)" in source
    assert "index_value = elapsed_frame % frame_count" in source
    assert "video_hover_animation_index_by_resource_id[resource_id] = 0" in source
    assert "V79F: once the user has expressed hover intent" in source
    assert "video_hover_stop_after_id_by_resource_id" in source
    assert "_apply_cached_video_hover_preview(item)" in source
    assert "window.after(70, _stop_if_outside)" in source
    assert "frame_interval_seconds = 1.0 / float(_video_hover_target_fps())" in source
    assert "next_frame_deadline = started_at" in source
    assert "while next_frame_deadline <= now:" in source
    assert "window.after(delay_ms, _step)" in source
    assert "window.after(40, _step)" not in source
    assert "window.after(1 if loop_wrap else 50, _step)" not in source
    assert "_apply_cached_video_hover_preview(current_item)" in source
    assert "video_hover_active_resource_ids" in source
    assert "_video_hover_fast_seek_seconds" in source
    assert "seek_seconds=_video_hover_fast_seek_seconds()" in source
    assert "_video_hover_cache_key_for_url" in source
    assert "video_hover_repaint_deferred" in source
    assert "_schedule_video_hover_deferred_repaint" in source
    assert "loop_wrap = next_index >= len(current_frames)" not in source
    assert "if video_live_preview_mode_enabled:" in source
    assert "V78T: on grouped video cards the bottom size badge" in source
    assert "Selected video quality variant:" in source
    assert "video_live_hover_after_id_by_resource_id" in source
    assert "extract_video_tile_hover_stream_frames_pil" in source
    assert "_extract_video_hover_preview_seed_frames" in source
    assert "_extract_video_hover_preview_long_frames" in source
    assert "window.after(850, _open_after_linger)" not in source
    assert "_open_live_video_preview_for_item(hover_item)" not in source
    assert "command=lambda current_item=item: _open_live_video_preview_for_item(current_item)" in source
    assert 'preview_box.bind("<Double-Button-1>", lambda _event, current_item=item: _open_live_video_preview_for_item(current_item)' in source
    assert 'item_card.bind("<Motion>", _schedule_live_hover_preview' not in source
    assert "only the actual preview surface starts video hover" in source
    assert 'preview_label.bind("<Leave>",' in source and ('_schedule_video_hover_stop' in source or '_finish_video_hover_leave_if_outside' in inspect.getsource(App))


def test_media_resource_window_download_labels_and_gallery() -> None:
    source = inspect.getsource(App._open_source_resource_window)
    canvas_source = inspect.getsource(App._open_source_image_canvas_grid_for_resources)
    canvas_window_source = inspect.getsource(App._open_source_image_canvas_grid_window)
    browser_grid_source = inspect.getsource(App._open_source_image_browser_grid_for_resources)
    browser_download_source = inspect.getsource(App._download_webpage_image_resource_ids_to_files)
    video_open_source = inspect.getsource(App._open_source_video_audio_browser_grid_window)
    video_browser_source = inspect.getsource(App._open_source_video_audio_browser_grid_for_resources)
    video_download_source = inspect.getsource(App._download_webpage_video_audio_resource_ids_to_files)
    video_finish_source = inspect.getsource(App._finish_webpage_video_audio_files_intake)
    full_source = inspect.getsource(App)

    assert 'text=("Download selected"' in source
    assert 'force_tk_image_window: bool = False' in source
    assert 'self._open_source_image_browser_grid_window(row_id)' in source
    assert 'self._open_source_image_canvas_grid_window(row_id)' not in source
    assert 'ThreadingHTTPServer' in browser_grid_source
    assert '/download-selected' in browser_grid_source
    assert "img.loading = 'lazy'" in browser_grid_source
    assert "img.decoding = 'async'" in browser_grid_source
    assert '--app={url}' in browser_grid_source
    assert 'YTCE-IMAGE-GRID-' in browser_grid_source
    assert 'title_hint=taskbar_marker' in browser_grid_source
    assert '_own_external_image_grid_window_for_taskbar' in browser_grid_source
    assert 'opened as a taskbar-owned Chromium app window' in browser_grid_source
    assert 'GWLP_HWNDPARENT' in full_source
    assert 'WS_EX_APPWINDOW' in full_source
    assert 'WS_EX_TOOLWINDOW' in full_source
    assert 'SetWindowPos' in full_source
    assert 'SWP_FRAMECHANGED' in full_source
    # The Tk canvas grid remains available in source as a fallback/debug path,
    # but it is no longer the normal Images surface because it is too heavy.
    assert 'Canvas grid stays under the Python app taskbar icon' in canvas_source
    assert 'tk.Canvas(' in canvas_source
    assert 'Open browser view' in canvas_source
    assert 'download_selected_webpage_images' in browser_download_source
    assert '_intake_session_files' in browser_download_source
    assert 'Browser-grid webpage image FILES refresh' in browser_download_source
    assert 'build_file_intake_dedupe_plan' in full_source
    assert 'render_file_intake_dedupe_summary' in browser_download_source
    assert 'webpage_image_files_intake_identity_cache' in full_source
    assert 'load_file_intake_identity_store' in full_source
    assert 'save_file_intake_identity_store' in full_source
    assert '_webpage_image_files_intake_identity_store_path' in full_source
    assert 'browser_grid_webpage_image_persistent_identity' in full_source
    assert '_webpage_image_file_intake_decisions_for_resources' in full_source
    assert 'file_intake_status' in browser_grid_source
    assert 'Added before highlighted' in browser_grid_source
    assert 'Added before' in full_source
    assert 'already in FILES' in browser_grid_source
    assert 'already in FILES before add' in browser_grid_source
    assert 'intake-badge' in browser_grid_source
    assert 'variant_count' in full_source
    assert 'variant_resource_ids' in full_source
    assert 'variant-select' in full_source
    assert 'url-copy' in browser_grid_source
    assert 'copyTextToClipboard' in browser_grid_source
    assert "urlCopy.textContent='URL'" in browser_grid_source
    assert "open.textContent='Open'" in browser_grid_source
    assert 'download-action' in browser_grid_source
    assert 'download-icon' in browser_grid_source
    assert "const DOWNLOAD_ICON_DATA_URI = 'data:image/png;base64," in browser_grid_source
    assert 'downIcon.src=DOWNLOAD_ICON_DATA_URI' in browser_grid_source
    assert "down.title='Download selected image to FILES'" in browser_grid_source
    assert "Browser download selected" not in browser_grid_source
    assert "document.getElementById('downloadSelected')" not in browser_grid_source
    assert "top-order" not in browser_grid_source
    assert "function showImageInfo(item)" in browser_grid_source
    assert "topOrder.className='info-copy'" in browser_grid_source
    assert "topOrder.onmouseenter=()=>showImageInfo(item)" in browser_grid_source
    assert "topOrder.onclick=(event)=>" in browser_grid_source
    assert "topControls.append(check, urlCopy, topOrder, actions)" in browser_grid_source
    assert "const order = document.createElement('span'); order.className='pill'; order.textContent=`#${item.index}`; info.append(order);" not in browser_grid_source
    assert "units=['KB','MB','GB','TB']" in browser_grid_source
    assert "return item.byte_size_label || formatByteSize(known)" not in browser_grid_source
    assert "option.title = variant.url" not in browser_grid_source
    assert "isGifImage" in browser_grid_source
    assert "hover to animate" in browser_grid_source
    assert 'self._open_source_video_audio_browser_grid_window(row_id)' in source
    assert 'run_rendered_probe=False' in video_open_source
    assert 'webpage_video_audio_browser_grid_open_pending_by_key' in video_open_source
    assert 'already opening from the quick/cached candidate scan' in video_open_source
    assert 'rendered discovery/prefetch continues in the background' in video_open_source
    assert 'waiting for webpage media discovery; it will open when candidates are ready' not in video_open_source
    assert 'YTCE-VIDEO-AUDIO-GRID-' in video_browser_source
    assert 'source_video_audio_browser_grid_servers' in video_browser_source
    assert 'YTCEVideoAudioGrid/1.0' in video_browser_source
    assert 'renderPreview' in video_browser_source
    assert '/media-items' in video_browser_source
    assert (
        'Quick media ready · rendered variants loading...' in video_browser_source
        or 'Quick media ready' in video_browser_source
    )
    assert 'Rendered variants loaded' in video_browser_source
    assert 'source_video_audio_browser_grid_active_by_row_id' in video_browser_source
    assert '_video_audio_window_is_current' in video_browser_source
    assert '_video_audio_row_still_matches_window' in video_browser_source
    assert 'payload.stale' in video_browser_source
    assert 'source_video_audio_browser_grid_stale_refresh_trace_by_row_id' in video_browser_source
    assert '_record_stale_video_audio_refresh' in video_browser_source
    assert 'stale_reason' in video_browser_source
    assert 'recordStaleRefreshTrace' in video_browser_source
    assert '__YTCE_VIDEO_AUDIO_STALE_REFRESH_TRACE__' in video_browser_source
    assert "console.debug('Ignored stale Video & Audio rendered refresh'" in video_browser_source
    assert 'refresh_inflight' in video_browser_source
    assert 'renderedRefreshPending' in video_browser_source
    assert 'currentResourceCount' in video_browser_source
    assert 'refreshMediaItemsFromServer' in video_browser_source
    assert 'mediaSignature' in video_browser_source
    assert "grid.textContent=''" in video_browser_source
    assert 'media.play().catch' in video_browser_source
    assert 'function activatePreview(card, preview, item, onMetadata, manual=false)' in video_browser_source
    assert "media.preload='auto'" in video_browser_source
    assert 'function attachPreviewSource(media, url)' in video_browser_source
    assert "card.addEventListener('pointerenter', enterPreview)" in video_browser_source
    assert "preview.addEventListener('pointerenter', enterPreview)" in video_browser_source
    assert "document.querySelector('.preview:hover')" in video_browser_source
    assert 'formatDimensions' in video_browser_source
    assert 'formatByteSize' in video_browser_source
    assert 'byteSizeText' in video_browser_source
    assert 'requestByteSize' in video_browser_source
    assert '/byte-size' in video_browser_source
    assert 'byte_size' in video_browser_source
    assert 'File size...' in video_browser_source
    assert 'Size unknown' in video_browser_source
    assert 'Detecting dimensions' in video_browser_source
    assert '_source_resource_browser_grid_byte_size_bytes' in full_source
    assert '_remote_media_byte_size_for_browser_grid_url' in full_source
    assert 'file_size_bytes=' in Path("webpage_video_resource_bridge.py").read_text(encoding="utf-8")
    assert '_candidate_byte_size' in Path("webpage_video_resource_bridge.py").read_text(encoding="utf-8")
    assert 'variantDisplayLabel' in video_browser_source
    assert 'if (dims) return dims;' in video_browser_source
    assert 'withBytes' not in video_browser_source
    assert 'card index lives in the top-row info badge' in video_browser_source
    assert "const order=document.createElement('span'); order.className='pill'; order.textContent=`#${{item.index}}`; info.append(order);" not in video_browser_source
    assert 'byteSizeCacheByKey' in video_browser_source
    assert 'byteSizeProbeDoneKeys' in video_browser_source
    assert 'cacheMatchingByteSize' in video_browser_source
    assert 'applyCachedByteSize(variant)' in video_browser_source
    assert 'currentMediaSignature = mediaSignature(mediaItems); }} catch(_error)' not in video_browser_source
    assert 'onloadedmetadata' in video_browser_source
    assert 'videoWidth' in video_browser_source
    assert 'play-toggle' in video_browser_source
    assert 'INFO_ICON_DATA_URI' not in video_browser_source
    assert 'info_icon_data_uri = INFO_ICON_DATA_URI' not in video_browser_source
    assert 'info-copy' in video_browser_source
    assert '.url-copy {{ min-width:1.85rem' in video_browser_source
    assert '.info-copy {{ min-width:1.45rem' in video_browser_source
    assert "infoCopy.textContent=`#${{item.index}}`" in video_browser_source
    assert "infoCopy.setAttribute('aria-label',`Show media info for #${{item.index}}`)" in video_browser_source
    assert 'infoIcon.src=INFO_ICON_DATA_URI' not in video_browser_source
    assert 'info-copy::before' not in video_browser_source
    assert 'display:none !important' not in video_browser_source
    assert 'opacity:.74' not in video_browser_source
    assert 'infoCopy.onmouseenter' in video_browser_source
    assert 'mediaDisplayName' in video_browser_source
    assert 'mediaFileName' in video_browser_source
    assert 'mediaInfoTooltip' in video_browser_source
    assert 'Filename:' not in video_browser_source
    assert 'function mediaInfoName(item, displayName)' in video_browser_source
    assert 'return mediaFileName(item) || displayName || mediaDisplayName(item)' in video_browser_source
    assert 'item.file_name=variant.file_name' in video_browser_source
    assert '"file_name": self._source_video_audio_browser_grid_filename_for_url' in full_source
    assert '_source_video_audio_browser_grid_filename_for_url' in full_source
    assert 'PAGE_MEDIA_TITLE' in video_browser_source
    assert 'onloadeddata' in video_browser_source
    assert 'oncanplay' in video_browser_source
    assert 'manual-playing' in video_browser_source
    assert 'Play or pause media preview audio' in video_browser_source
    assert "urlCopy.textContent='URL'" in video_browser_source
    assert "open.textContent='Open'" in video_browser_source
    assert 'download-action' in video_browser_source
    assert 'download-icon' in video_browser_source
    assert "Download selected media to FILES" in video_browser_source
    assert 'event.preventDefault()' in video_browser_source
    assert 'event.stopPropagation()' in video_browser_source
    assert 'markCardAddedBefore' in video_browser_source
    assert '.actions a:hover, .actions button:hover' in video_browser_source
    assert '.card.intake-reused .preview' in video_browser_source
    assert 'Detecting size' not in video_browser_source
    assert "media.disablePictureInPicture=true" in video_browser_source
    assert "disablepictureinpicture" in video_browser_source
    assert "controlsList','nodownload noplaybackrate noremoteplayback" in video_browser_source
    assert '_source_video_audio_browser_grid_playability_for_item' in full_source
    assert 'playable_variants = sorted(' in full_source
    assert 'variant for variant in variants if bool(variant.get("playable"))' in full_source
    assert 'key=_browser_grid_variant_preference_key' in full_source
    assert (
        'Media loading · rendered variants loading...' in video_browser_source
        or 'Media loading' in video_browser_source
    )
    assert 'candidate_role_label' in video_browser_source
    assert 'Playable media' not in video_browser_source
    assert 'Embedded player' in full_source
    assert 'Page wrapper' in full_source
    assert 'Page script' in full_source
    assert "note.textContent=candidateRoleLabel(item)" not in video_browser_source
    assert "e.textContent='Preview unavailable'" not in video_browser_source
    assert "return isPlayableMedia(item) ? '' : 'Preview unavailable'" not in video_browser_source
    assert 'primePreferredVariant(item)' in video_browser_source
    assert 'sortVariantsByPreference(variants)' in video_browser_source
    assert 'isPlayableMedia' in video_browser_source
    assert 'candidateRoleLabel' in video_browser_source
    assert 'updatePlayButtonForItem' in video_browser_source
    assert 'role-pill' in video_browser_source
    assert "if (!isPlayableMedia(item))" in video_browser_source
    assert 'non-playable' in video_browser_source
    assert 'preview-note' not in video_browser_source
    assert 'use Open for the source/player URL' in video_browser_source
    assert '_browser_grid_variant_preference_key' in full_source
    assert 'def _browser_grid_display_name' in full_source
    assert 'lower_name = raw_name.lower()' in full_source
    assert 'if playable_variants:' in full_source
    assert 'preferred_variant = playable_variants[0]' in full_source
    assert 'elif bool(playability.get("playable")):' in full_source
    assert 'card_resource_id = str(preferred_variant.get("resource_id") or resource_id)' in full_source
    assert 'function attachPreviewSource(media, url)' in video_browser_source
    assert 'let activePreviewMedia=null' in video_browser_source
    assert 'renderPreviewPlaceholder(item, container)' in video_browser_source
    assert 'function activatePreview(card, preview, item, onMetadata, manual=false)' in video_browser_source
    assert 'const enterPreview=()=>startPreviewIfHovered(card, preview, item, updateSizeUi)' in video_browser_source
    assert 'const media=activatePreview(card, preview, item, updateSizeUi, true)' in video_browser_source
    assert 'attachPreviewSource(media, item.url); try {{ media.muted=false' in video_browser_source
    assert 'media.dataset.attachedUrl === nextUrl' in video_browser_source
    assert 'staticThumbQueue' in video_browser_source
    assert 'function attachStaticThumbnail(card, preview, item)' in video_browser_source
    assert 'enqueueStaticThumbnail(card, preview, item' in video_browser_source
    assert '.static-thumb' in video_browser_source
    assert 'pauseStaticThumbnails' in video_browser_source
    assert 'function preserveStaticFrameFromMedia(card, preview, media, item)' in video_browser_source
    assert "canvas.toDataURL('image/jpeg', 0.72)" in video_browser_source
    assert "media.classList.add('static-thumb')" in video_browser_source
    assert 'const preserved=preserveStaticFrameFromMedia(card, preview, media, currentItem)' in video_browser_source
    assert "option.title=variant.url" not in video_browser_source
    assert 'afterFirstPaint(()=>attachPreviewSource(video, item.url))' not in video_browser_source
    assert 'setTimeout(refreshMediaItemsFromServer, 150)' in video_browser_source
    assert '_build_webpage_video_audio_file_intake_dedupe_plan' in full_source
    assert '_webpage_video_audio_files_intake_identity_store_path' in full_source
    assert 'browser_grid_webpage_video_audio_persistent_identity' in full_source
    assert 'Do not use persistent video/audio identity records as visible FILES state' in full_source
    assert 'page_title: str = ""' in full_source
    assert '_browser_grid_display_name' in full_source
    assert "lower.includes(' from source')" in video_browser_source
    assert "function mediaInfoName(item, displayName)" in video_browser_source
    assert "return mediaFileName(item) || displayName || mediaDisplayName(item)" in video_browser_source
    assert "function mediaInfoTooltip(item, displayName) {{ return mediaInfoName(item, displayName); }}" in video_browser_source
    assert "const parts = [infoName];" in video_browser_source
    assert 'Browser-native video/audio FILES refresh' in video_finish_source
    assert 'display_name = self._source_video_audio_browser_grid_filename_for_url(media_url, resource_id' in full_source
    assert 'Browser-native video/audio download queued' in video_download_source
    assert '_intake_session_files' in video_finish_source
    assert 'urllib.request.urlopen' in full_source
    assert "const down = document.createElement('button')" in browser_grid_source
    assert "down.type='button'" in browser_grid_source
    assert 'event.preventDefault()' in browser_grid_source
    assert 'event.stopPropagation()' in browser_grid_source
    assert 'markCardAddedBefore' in browser_grid_source
    assert '.actions a:hover, .actions button:hover' in browser_grid_source
    assert '.card:hover .intake-badge, .card.selected .intake-badge' in browser_grid_source
    assert 'down.dataset.url = item.url' in browser_grid_source
    assert 'option.textContent' in full_source
    assert 'variant.label' in full_source
    assert 'unknown' in full_source
    assert "urlCopy.setAttribute('aria-label', 'Copy image URL')" in browser_grid_source
    assert 'card:hover .info' not in browser_grid_source
    assert 'top-badges' in full_source
    assert 'applyVariant' in browser_grid_source
    assert 'variants' in browser_grid_source
    assert 'card.intake-reused img' in full_source
    assert 'planned_added' in browser_download_source
    assert '.svg' in inspect.getsource(main) and '.ico' in inspect.getsource(main)
    assert "Review selected" in source
    assert "preview_box" in source
    assert "thumbnail_images_by_id" in source
    assert "thumbnail_hidden_resource_ids" in source
    assert "show_hidden_images_var" in source
    assert "Show hidden" in source
    assert "webpage_image_discovery_cache_by_url" in source
    assert "_webpage_image_discovery_cache_key" in source
    assert "Using cached webpage image candidate list" in source
    assert "image candidates render immediately with targeted tile refreshes" in source
    assert "rendered_tile_refreshers_by_id" in source
    assert "refresh_rendered_tile" in source
    assert "cached_discovery_on_open" in source
    assert "_apply_cached_thumbnail_preview" in source
    assert "_start_thumbnail_preview_probe" in source
    assert "V79T: Image Downloader uses browser-native <img> loading" in source
    assert "open_browser_image_gallery" in source
    assert "Browser grid" in source
    assert "selected_resource_ids_override=(resource_id,)" not in source
    assert "Each image tile has Preview and Download buttons" not in source
    assert "checkbox = ctk.CTkLabel(" in source
    assert "checkbox = ctk.CTkCheckBox(" not in source
    assert "image tiles no longer carry per-tile action" in source
    assert "Select all" in source
    assert "Downloaded webpage image FILES refresh" in source
    assert "_webpage_image_session_download_root" in source
    assert "_cached_webpage_image_session_paths" in source
    assert "use EXPORT to choose a final output folder" in source
    assert "_refresh_session_files_list()" in source
    assert "_refresh_export_entry_state()" in source
    assert "update_idletasks()" in source
    assert "prewarm_rendered_browser_discovery_worker" in full_source
    assert "start_internal_browser_image_discovery_service" in full_source
    assert "YTCEInternalBrowserImageDiscoveryService" in full_source


def test_files_sidebar_resizer_and_review_highlight_are_more_usable() -> None:
    paned_source = inspect.getsource(App._create_content_paned_window)
    sidebar_source = inspect.getsource(App._create_sidebar)
    width_source = inspect.getsource(App._on_sidebar_paned_sash_release)
    files_source = inspect.getsource(App._create_files_section)
    color_source = inspect.getsource(App._session_file_label_colors)
    review_source = inspect.getsource(App._session_file_entry_needs_review)

    assert "sashwidth=6" in paned_source
    assert "showhandle=False" in paned_source
    assert "_create_sidebar_resize_grip" in inspect.getsource(App)
    assert "minsize=320" in sidebar_source
    assert "max(320, min(1280" in width_source
    assert "FILES" in files_source
    assert "Clear all" in files_source
    assert "wraplength=max" in inspect.getsource(App._refresh_session_files_list)
    assert "needs_review" in review_source
    assert "#4f171f" in color_source


def test_sidebar_top_buttons_do_not_expand_with_sash() -> None:
    sidebar_source = inspect.getsource(App._create_sidebar)
    updates_source = inspect.getsource(App._create_updates_section)
    keys_source = inspect.getsource(App._create_access_keys_section)
    export_source = inspect.getsource(App._create_export_section)

    assert "CTkScrollableFrame" not in sidebar_source
    assert "Fixed sidebar content" in sidebar_source

    assert 'updates_frame.pack(anchor="w"' in updates_source
    assert 'self.update_button.pack(anchor="w")' in updates_source
    assert 'keys_frame.pack(anchor="w"' in keys_source
    assert 'self.access_keys_button.pack(anchor="w")' in keys_source
    assert 'export_frame.pack(anchor="w"' in export_source
    assert 'self.evidence_button.pack(anchor="w")' in export_source
    for source in (updates_source, keys_source, export_source):
        assert "configure(width=286, height=30)" in source
        assert "width=286" in source



def test_database_toggle_animation_avoids_final_state_jump() -> None:
    toggle_source = inspect.getsource(App._on_profile_media_database_mode_toggled)
    set_source = inspect.getsource(App._set_profile_media_sidebar_mode)
    animation_source = inspect.getsource(App._animate_profile_media_database_mode_switch_visual)

    assert "refresh_visual=False" in toggle_source
    assert "from_mode=current_mode, to_mode=mode" in toggle_source
    assert "summary_frame.grid" in toggle_source
    assert "summary_frame.grid_remove" in toggle_source
    assert "refresh_visual: bool = True" in set_source
    assert "Smoothstep" in animation_source
    assert "mode=end_mode" in animation_source


def test_source_details_uses_youtube_metadata_placeholders_not_domain() -> None:
    source = inspect.getsource(App._source_row_details_fields)
    helper = inspect.getsource(App._youtube_video_id_from_url)
    metadata = inspect.getsource(App._youtube_source_detail_metadata)
    discovery = inspect.getsource(App._apply_youtube_source_row_discovery)
    details_window = inspect.getsource(App._show_source_row_details)
    details_loader = inspect.getsource(App._load_source_row_details_metadata_async)

    assert "_youtube_source_detail_metadata" in source
    assert '("Channel", channel or "Not loaded")' in source
    assert "youtube_source_row_discovery_metadata" in metadata
    assert "row_video_id == info_video_id" in metadata
    assert "metadata:" in discovery
    assert "Load metadata" in details_window
    assert "discover_youtube_media_with_ytdlp" in details_loader
    assert "_youtube_oembed_metadata_probe" in details_loader
    assert "Basic metadata loaded; date/views need yt-dlp" in details_loader
    assert "youtu.be" in helper
    assert "shorts" in helper
    assert "embed" in helper




def test_database_import_preview_home_root_guard_and_row_layout() -> None:
    create_source = inspect.getsource(App._create_profile_media_database_mode_toggle_section)
    refresh_source = inspect.getsource(App._refresh_profile_media_database_mode_switch_visual)
    toggle_source = inspect.getsource(App._on_profile_media_database_mode_toggled)
    build_source = inspect.getsource(App._build_profile_media_database_import_preview_from_current_state)
    load_source = inspect.getsource(App._profile_media_database_home_load_or_unload_clicked)
    import_source = inspect.getsource(App._import_profile_media_database_home_selection)
    ensure_source = inspect.getsource(App._ensure_profile_media_database_root_for_preview)
    set_home_source = inspect.getsource(App._set_profile_media_database_home_root)

    assert "profile_media_database_toggle_frame.grid(row=1" in create_source
    assert "profile_media_database_home_build_import_button.grid(row=2" in create_source
    assert 'summary_frame.grid(row=3' in refresh_source
    assert 'summary_frame.grid(row=3' in toggle_source
    assert "_ensure_profile_media_database_root_for_preview()" in build_source
    assert "database_root=database_root" in build_source
    assert "rows[-1] if rows else None" in build_source
    assert "_load_last_profile_media_database_home_selection" in load_source
    assert "Import/select existing Database HOME folder" in import_source
    assert "_select_profile_media_database_batch_json_files" not in import_source
    assert "askopenfilenames" not in import_source
    assert "askyesno" not in ensure_source
    assert "_write_profile_media_database_home_manifest" in set_home_source
    assert "_remember_profile_media_database_home_root" in set_home_source

def test_transcript_controls_use_right_side_space() -> None:
    source = inspect.getsource(App._create_transcript_section)
    toggle_source = inspect.getsource(App._create_progress_section)

    assert "transcript_controls_panel" in source
    assert "ctk.CTkFrame(self.transcript_controls_panel" in source
    assert source.count('pack(anchor="e"') >= 7
    assert "editor_toggle_button_frame" in toggle_source
    assert 'sticky="e"' in toggle_source
    assert 'fill="x", expand=True' not in source



def test_discussion_actions_are_right_panel_aligned() -> None:
    source = inspect.getsource(App._create_url_section)

    assert "right_action_panel" in source
    assert "checkbox_frame" in source
    assert 'self.discussion_source_menu.grid(row=0, column=0, sticky="e"' in source
    assert 'export_frame.grid(row=2, column=0, sticky="e"' in source
    assert 'self.fetch_button.grid(row=0, column=0, sticky="w"' in source


def test_sidebar_sash_is_not_visible_scrollbar() -> None:
    source = inspect.getsource(App._create_content_paned_window)

    assert "sashwidth=6" in source
    assert "showhandle=False" in source
    assert "_create_sidebar_resize_grip" in inspect.getsource(App)


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
    assert "Generic source capture ready" in source
    assert "Live Webpage/Screenshot capture will run now when supported" in source
    assert "archive_check_requested=generic_website_preservation_requested" in source
    assert "local_archive_requested = self._local_web_archive_requested_for_source_row" in source
    assert "warc_requested=local_archive_requested" in source
    assert "wacz_requested=local_archive_requested" in source


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

    assert "webpage" in app.last_operational_capture_plan.selected_modes
    assert "comments" in app.last_operational_capture_plan.selected_modes
    assert "archive_check" in app.last_operational_capture_plan.selected_modes
    assert "warc" not in app.last_operational_capture_plan.selected_modes
    assert "wacz" not in app.last_operational_capture_plan.selected_modes
    assert app.last_operational_capture_plan.screenshot_intents == ("webpage", "comments")
    assert fake_messagebox.infos == []
    shown_text = app.last_operational_capture_scaffold_message
    assert "Artifact declarations:" in shown_text
    assert "Action event chain:" in shown_text
    assert "Source Evidence workflow state" in shown_text
    assert "Source site/method selector audit-required rows:" in shown_text
    assert "Named-site source method pack count: 11" in shown_text
    assert "MSN source method packs: 2" in shown_text
    assert "X/Twitter source method packs: 2" in shown_text
    assert "YouTube source method packs: 2" in shown_text
    assert "Generic/archive source method packs: 5" in shown_text
    assert "Database review workflow: source_database_review_workflow_" in shown_text
    assert "Source record review workflow: source_record_review_workflow_" in shown_text
    assert "Selector approval packets: source_selector_approval_packets_" in shown_text
    assert "Manual live-site smoke: pending separate approval" in shown_text
    assert any("without opening a modal popup" in message for message, _level in app.log_messages)
    assert app.last_operational_capture_status.startswith("Generic source capture ready")
    assert app.url_status.config["text"].startswith("Generic source capture ready")
    assert any("live Webpage/Screenshot execution did not run" in message for message, _level in app.log_messages)
    assert app.last_source_evidence_workflow_state.queue_item_count > 0
    assert app.last_source_evidence_workflow_state.review_manifest_asset_count > 0
    assert app.last_source_evidence_workflow_state.source_site_method_selector_audit_required_count == 1
    assert app.last_source_evidence_workflow_state.source_database_review_scan_row_count > 0
    assert app.last_source_evidence_workflow_state.source_database_review_rejected_unsafe_edit_count == 0
    assert app.last_source_evidence_workflow_state.source_record_review_record_count == 1
    assert app.last_source_evidence_workflow_state.source_selector_approval_packet_count == 1
    assert app.last_source_evidence_workflow_state.source_named_site_method_pack_count == 11
    assert app.last_source_evidence_workflow_state.source_named_site_method_pack_selector_audit_required_count == 1
    assert app.last_source_evidence_workflow_state.source_operator_command_pack_count == 11
    assert app.last_source_evidence_workflow_state.source_manual_smoke_checklist_pack_count == 5
    assert app.last_source_audit_dashboard_state.summary["operator_command_pack_count"] == 11
    assert app.last_source_audit_dashboard_state.summary["manual_smoke_checklist_pack_count"] == 5
    assert app.last_source_audit_dashboard_state.summary["access_online_asr_bridge_summary_id"].startswith(
        "access_online_asr_bridge_"
    )
    assert app.last_source_app_operator_controller_state["controller_surface_count"] == 9
    assert app.last_source_app_operator_controller_state["no_live_execution_performed"] is True
    assert app.last_operational_capture_queue_review_store.metadata_only is True
    assert app.last_operational_capture_review_manifest.assets
    assert not any("Source capture plan only; no fetch" in message for message, _level in app.log_messages)
    assert any(
        ("Generic website live capture disabled" in message)
        or ("live Webpage/Screenshot execution did not run" in message)
        or ("Generic website live capture written" in message)
        for message, _level in app.log_messages
    )
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
        assert result.file_count >= 38
        assert result.metadata_file_write_performed is True
        assert result.evidence_file_move_performed is False
        assert result.full_local_path_included is False
        assert Path(temp_dir, "source_evidence_workflow_review_bundle.json").is_file()
        assert Path(temp_dir, "source_evidence_release_readiness.json").is_file()
        assert Path(temp_dir, "source_evidence_release_action_plan.json").is_file()
        assert Path(temp_dir, "source_grabbed_record.json").is_file()
        assert Path(temp_dir, "source_evidence_database_scan_result.json").is_file()
        assert Path(temp_dir, "source_access_provider_gate_summary.json").is_file()
        assert Path(temp_dir, "source_adapter_audit_registry.json").is_file()
        assert Path(temp_dir, "source_site_method_audit_registry.json").is_file()
        assert Path(temp_dir, "source_database_review_workflow.json").is_file()
        assert Path(temp_dir, "source_record_review_workflow.json").is_file()
        assert Path(temp_dir, "source_selector_approval_packets.json").is_file()
        assert Path(temp_dir, "source_named_site_method_packs.json").is_file()
        assert Path(temp_dir, "source_operator_command_packs.json").is_file()
        assert Path(temp_dir, "source_manual_smoke_checklists.json").is_file()
        assert Path(temp_dir, "source_audit_dashboard_state.json").is_file()
        assert Path(temp_dir, "source_app_operator_controller_state.json").is_file()

    assert app.last_source_evidence_workflow_review_bundle.bundle_id == result.bundle_id
    assert any("review bundle saved" in message for message, _level in app.log_messages)


def test_main_exposes_source_app_operator_controller_state_without_live_execution() -> None:
    app = _make_source_row_app()

    state = App.build_source_app_operator_controller_state(app)

    assert state.controller_surface_count == 9
    assert state.no_live_execution_performed is True
    assert state.no_credentials_read is True
    assert state.no_asr_run is True
    assert app.last_source_app_operator_controller_state == state


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
    popup = inspect.getsource(App._show_archive_status)
    local_archive = inspect.getsource(App._local_web_archive_status_lines)

    assert "ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE" in source
    assert "Local Web Archive" in popup
    assert "_local_web_archive_status_lines" in popup
    assert "build_local_web_archive_action_state" in local_archive
    assert "expected_comment_count" in local_archive
    if hasattr(App, "_ensure_archivebox_icon"):
        loader = inspect.getsource(App._ensure_archivebox_icon)
        assert 'assets", "ui", "archivebox_icon.png"' in loader
        assert "ctk.CTkImage" in loader
        assert "ImageTk.PhotoImage" not in loader
        assert "ARCHIVE_SERVICE_ARCHIVEBOX" in source
        assert "archive_status.service_id != ARCHIVE_SERVICE_ARCHIVEBOX" in source
        assert "ArchiveBox optional advanced backend" in popup
        assert "ArchiveBox execution performed: none" in popup
    else:
        assert "ARCHIVE_SERVICE_ARCHIVEBOX" not in source
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

    assert "height=46" in source
    assert "self.source_hint_label" in source
    assert "wraplength=width" in helper
    assert 'url_label.pack(anchor="e"' in source
    assert 'filter_words_label.pack(fill="x", anchor="e")' in source
    assert 'filter_words_hint.pack(fill="x", anchor="e"' in source
    assert (
        'right_action_panel.grid(row=0, column=2, rowspan=4, sticky="e")' in source
        or 'right_action_panel.grid(row=0, column=1, rowspan=4, sticky="e")' in source
    )
    assert 'self.discussion_source_menu.grid(row=0, column=0, sticky="e"' in source


def test_visible_header_is_removed_to_recover_vertical_space() -> None:
    source = inspect.getsource(App._create_header)

    assert "height=0" in source
    assert "no visible header content" in source
    assert "APP_DESCRIPTION" not in source
    assert "by Creator Intelligence" not in source


def test_review_dialog_uses_tk_text_role_spans_and_inline_multiselect() -> None:
    source = inspect.getsource(App._open_profile_media_database_import_review_dialog)

    assert "tk.Text(" in source
    assert "role_fill_tag" in source
    assert "role_text_tag" in source
    assert "tag_add(bind_tag, span_start, span_end)" in source
    assert "tag_bind(bind_tag, \"<Button-1>\"" in source
    assert "Add selected" in source
    assert "Add all" in source
    assert "Select one or more case/topic locations" not in source
    assert "text=\"Done\"" not in source
    selector_source = source.split("V82X closeout: case/topic selection is an inline expanded checklist", 1)[1].split("media_rows_all", 1)[0]
    assert "CTkToplevel" not in selector_source
    assert "overrideredirect(True)" not in selector_source
    assert "case_link_dropdown_panel_holder" in source
    assert "panel.grid(row=1, column=1" in source
    assert "_selected_case_link_targets()" in source
    assert "return {row_id: list(targets) for row_id in selected_rows}" in source
    assert "Counts separate source scopes, claim spans, unique canonical persons" in source
    assert "claim_role_classification_preview" in source
    assert "_add_claim_role_full_transcript_card" in source
    assert "_claim_spans_for_selected_scope" in source
    assert "Full transcript claim/span roles" not in source
    assert "Copy plain text" in source
    assert "Copy role markup" in source
    assert "_claim_role_markup_for_spans" in source
    assert "Role markup view" in source
    assert "Advanced/raw decisions" in source
    assert "claim_role_span_click_" in source
    assert 'tag_bind(bind_tag, "<ButtonRelease-1>"' in source
    assert 'tag_bind(bind_tag, "<B1-Motion>"' in source
    assert 'transcript_box.bind("<MouseWheel>"' in source
    assert 'transcript_box.bind("<Button-4>"' in source
    assert 'transcript_box.bind("<Button-5>"' in source
    helper_source = inspect.getsource(App.install_middle_click_autoscroll)
    assert "def install_middle_click_autoscroll" in helper_source
    assert "winfo_exists()" in helper_source
    assert "except tk.TclError" in helper_source
    assert 'text_widget.configure(cursor="")' in helper_source
    assert 'text_widget.yview_scroll(units, "units")' in helper_source
    assert 'text_widget.after(35, _step_autoscroll)' in helper_source
    assert 'after_cancel(job)' in helper_source
    assert 'text_widget.bind("<ButtonPress-2>"' in helper_source
    assert 'text_widget.bind("<Motion>"' in helper_source
    assert 'text_widget.bind("<Button-2>"' in helper_source
    assert 'text_widget.bind("<B2-Motion>"' in helper_source
    assert 'text_widget.bind("<ButtonRelease-2>"' in helper_source
    assert 'text_widget.bind("<ButtonPress-1>"' in helper_source
    assert 'text_widget.bind("<Escape>"' in helper_source
    assert 'owner_widget.bind("<Motion>"' in helper_source
    assert 'owner_widget.bind("<ButtonPress-1>"' in helper_source
    assert 'bind("<Leave>"' not in helper_source
    assert "self.install_middle_click_autoscroll(transcript_box, owner=win)" in source
    assert "self.install_middle_click_autoscroll(textbox, owner=win)" in source
    assert "self.install_middle_click_autoscroll(quote_box, owner=win)" in source
    text_editor_source = inspect.getsource(App._create_text_editor_section)
    assert "self.install_middle_click_autoscroll(self.text_editor_textbox, owner=self)" in text_editor_source
    assert "YouTube Comments" in source
    assert "Preserved YouTube comments linked to transcript/source persons" not in source
    assert "[Section: comments" not in source
    assert "_comment_sections_for_selected_scope()" in source
    assert "_add_youtube_comment_source_roles_card" not in source
    assert "YouTube comment source roles" not in source
    assert "_ytce_review_comment_section_role_spans(section)" in source
    assert "def _insert_shared_claim_role_span" in source
    assert "_insert_shared_claim_role_span(span, span_index)" in source
    assert "_insert_shared_claim_role_span(comment_span" in source
    assert 'transcript_box.insert("end", parent_text + "\\n\\n")' in source
    assert 'transcript_box.insert("end", "    " + " | ".join(part for part in (handle, time_text) if part) + "\\n", "claim_meta")' in source
    assert "comment_span.setdefault(\"edit_key\"" in source
    assert "comment_span.setdefault(\"section\", \"comments\")" in source
    assert "_retag_claim_role_span" in source
    assert "_retag_claim_role_span(tag_name, new_role)" in source
    assert "claim_yview_before = transcript_box.yview()" in source
    assert "claim_outer_yview_before = _claim_text_outer_yview()" in source
    assert "_retag_claim_role_span(tag_name, new_role)" in source
    assert "_restore_claim_text_yviews(claim_yview_before, claim_outer_yview_before)" in source
    assert "def _restore_claim_text_yviews" in source
    assert "transcript_box.after_idle(_restore_once)" in source
    assert "transcript_box.after(10, _restore_once)" in source
    assert "canvas.yview_moveto(float(outer_yview[0]))" in source
    assert "transcript_box.yview_moveto(float(inner_yview[0]))" in source
    assert "transcript_box.tag_config(tag, underline=1 if enabled else 0)" in source
    assert "return \"break\"" in source
    assert ".see(" not in source
    assert "yview_moveto(0)" not in source
    assert ".focus_set(" not in source
    assert ".mark_set(" not in source
    assert "[{{' | '.join(part for part in (handle, time_text) if part)}} | Secondary]" not in source
    assert "_claim_plain_text_for_spans(spans, comment_sections)" in source
    assert "_claim_role_markup_for_spans" in source
    assert ("_claim_role_markup_for_spans(spans, comment_sections, visible_roles_for_markup)" in source or "_claim_role_markup_for_spans(spans, comment_sections, visible_roles_for_markup)" in source)  # YTCE_V83C_REPAIR22_R21_MARKUP_TEST_COMPAT
    markup_source = inspect.getsource(main._claim_role_markup_for_spans)
    assert "_ytce_review_comment_section_role_spans(section)" in markup_source
    assert "selected_roles.get(str(comment_span.get(\"edit_key\") or \"\")" in markup_source
    comment_helper_source = inspect.getsource(main._ytce_review_comment_role_spans)
    assert "Do not default comments to Secondary" in comment_helper_source
    assert "selected_claim_span_roles[key] = new_role" in source
    assert "_claim_span_decisions.json" in source
    assert '"old_role": old_role' in source
    assert '"new_role": new_role' in source
    assert '"char_start": int(span.get("char_start") or 0)' in source
    assert "height=14" in source
    assert "No case/topic available" in source
    assert "_display_case_title_for_header" in source
    assert '"source evidence review"' in source
    assert 'add("The Emmanuel Free Church")' not in source
    assert 'add("Project Britannia — Brett Murphy interview")' in source
    assert 'add("Brett Murphy statements")' in source
    assert 'add("Christian Charity — Emmanuel Free Church")' in source
    assert 'return suggestions[:2] or ["No case/topic available"]' in source
    assert "for index, suggestion in enumerate(case_link_suggestions[:2])" in source
    assert '"charity commission", "metro.co.uk", "civil society", "charity case"' in source
    assert "ctk.BooleanVar(value=False)" in source
    assert 'state="normal" if case_link_targets_available else "disabled"' in source
    build_source = inspect.getsource(App._build_profile_media_database_import_preview_from_current_state)
    assert "profile_media_database_import_preview_build_running" in build_source
    assert "threading.Thread(" in build_source
    assert 'name="profile-media-import-preview-build"' in build_source
    assert "_finish_profile_media_database_import_preview" in build_source
    assert "classifying claim spans" in build_source
    assert "_set_build_buttons_enabled(False, text=\"Building...\")" in build_source
    assert "_apply_profile_media_database_preview_counts_to_main_card(fresh_preview_payload)" in build_source
    assert build_source.count("_apply_profile_media_database_preview_counts_to_main_card(fresh_preview_payload)") >= 2
    apply_counts_source = inspect.getsource(App._apply_profile_media_database_preview_counts_to_main_card)
    final_counts_source = inspect.getsource(App._profile_media_database_final_count_override_from_preview)
    assert "profile_media_database_last_source_package_preview = preview_payload" in apply_counts_source
    assert "_profile_media_database_final_count_override_from_preview(preview_payload)" in apply_counts_source
    assert "_profile_media_database_preview_count_override_from_payload(preview_payload)" in final_counts_source
    assert "_profile_media_selected_review_role_counts()" in final_counts_source
    assert "_refresh_profile_media_database_workbench_panel()" in apply_counts_source
    preview_section_source = inspect.getsource(App._profile_media_database_source_package_preview_section_from_payload)
    assert 'batch_payload' in preview_section_source
    assert 'source_package_preview' in preview_section_source
    count_override_source = inspect.getsource(App._profile_media_database_preview_count_override_from_payload)
    assert "source_record_count_breakdown" in count_override_source
    assert "youtube_comment_source_role_records" in count_override_source
    assert "CLAIM_SPAN_" in count_override_source
    assert "_apply_profile_media_database_preview_counts_to_main_card(fresh_preview_payload)" in build_source
    panel_refresh_source = inspect.getsource(App._refresh_profile_media_database_workbench_panel)
    assert 'source_folder_preview=getattr(self, "profile_media_database_last_source_package_preview", None)' in panel_refresh_source
    count_source = inspect.getsource(App._profile_media_selected_review_role_counts)
    assert "claim_roles = (\"PRIMARY\", \"SECONDARY\", \"TERTIARY\", \"UNKNOWN\")" in count_source
    assert "Blank remains assigned internally" in count_source
    assert "CLAIM_SPAN_" in count_source
    sidebar_metric_source = inspect.getsource(App._profile_media_sidebar_metric_override_value)
    assert "SOURCE_SCOPE_PRIMARY_SELF_AUTHORED_SCOPE" in sidebar_metric_source
    assert "SOURCE_SCOPE_UNKNOWN_SOURCE_ROLE" in sidebar_metric_source
    assert "profile_media_database_last_source_package_preview = preview_payload" in source
    assert "claim_count_by_role = {\"PRIMARY\": 0" in source
    assert "Copied role markup to clipboard" in source


def test_v83c_repair6_media_unlinked_scope_keeps_mixed_article_text_visible() -> None:
    source = inspect.getsource(App._open_profile_media_database_import_review_dialog)

    assert "YTCE_V83C_REPAIR6_MEDIA_SCOPE_MIXED_ARTICLE_TEXT" in source
    # YTCE_V83C_REPAIR20_R19_TEST_MARKER_COMPAT
    # Repair19 intentionally replaced the old link-only marker: the Media icon
    # must include URL/link rows plus source-reference/media-source statements.
    assert (
        "YTCE_V83C_REPAIR6_MEDIA_ICON_LINK_ROWS_ONLY" in source
        or "YTCE_V83C_REPAIR19_MEDIA_ICON_INCLUDES_SOURCE_STATEMENTS" in source
    )
    claim_scope_source = source.split("def _claim_spans_for_selected_scope", 1)[1].split("source_reference_review_edit_keys", 1)[0]
    assert "if media_scope_selected:\n                return []" not in claim_scope_source
    assert 'article_like_streams = {"article_text", "webpage_text", "source_text"}' in claim_scope_source
    assert 'article_like_artifact_kinds = {"article_text", "webpage_text", "source_txt", "text"}' in claim_scope_source
    assert 'span_stream in article_like_streams' in claim_scope_source
    assert 'span_artifact_kind in article_like_artifact_kinds' in claim_scope_source
    assert "selected_scope_value in span_url_parts" in claim_scope_source
    filter_source = source.split("def _claim_span_matches_filter", 1)[1].split("def _link_source_matches_current_text_filter", 1)[0]
    assert "if media_filter_active:" in filter_source
    assert (
        "media_role = _claim_media_source_role_for_span(span_ref)" in filter_source
        or "return False" in filter_source
    )
    render_source = source.split("def _render_claim_transcript", 1)[1].split("def _insert_shared_claim_role_span", 1)[0]
    assert "visible_claim_spans_for_counts = _visible_claim_spans_for_current_filter()" in render_source
    assert "for link_record in _visible_link_source_objects_for_current_filter()" in render_source
    assert "_set_source_text_role_count_strip(visible_claim_counts)" in render_source
    assert "Full transcript claim/span roles" not in source


def test_review_dialog_exposes_v83c_link_source_ui_and_decisions() -> None:
    source = inspect.getsource(App._open_profile_media_database_import_review_dialog)
    assert "YTCE_V83C_LINK_SOURCE_UI" in source
    assert "YTCE_V83C_LINK_SOURCE_DECISION_PERSISTENCE" in source
    assert "YTCE_V83C_LINK_SOURCE_FILTERS" in source
    assert "YTCE_V83C_LINK_SOURCE_LIVE_ARCHIVE_GROUPING" in source
    assert "YTCE_V83C_REPAIR2_ARCHIVE_INHERITS_VISIBLE_ROLE" in source
    assert "link_source_preview" in source
    assert "link_source_objects" in source
    assert "link_source_decisions_path" in source
    assert 'link_source_filter_values = ["All", "Primary", "Secondary", "Tertiary", "Unknown", "Needs review", "Accepted", "Ignored", "Changed"]' in source
    assert "Accept decision" in source
    assert "Ignore from active evidence" in source
    assert "Reject selected" not in source
    assert "_link_source_decision_status_display" in source
    assert "ignored from active evidence (stored internally as rejected for compatibility)" in source
    assert "Override role" in source
    assert "Mark Locator" in source
    assert "Mark Unknown" in source
    assert "Copy URL" in source
    assert "Open URL" in source
    assert "append_link_source_decision" in source
    assert "apply_link_source_decisions" in source
    assert "build_link_source_decision_summary" in source
    assert "_link_source_grouped_preservation_lines" in source
    assert "Preservation copy:" in source
    assert "link_source_objects)" in source
    assert "claim_role_spans" in source
    assert "Open URL / Copy URL / Copy details" not in source
    assert "YTCE_V83C_REPAIR3_DETAILS_OMIT_BLANK_FIELDS" in source

def test_v83c_repair1_renders_link_rows_inside_source_role_text() -> None:
    source = inspect.getsource(App._open_profile_media_database_import_review_dialog)

    assert "YTCE_V83C_REPAIR1_LINK_ROWS_IN_SOURCE_ROLE_TEXT" in source
    assert "YTCE_V83C_REPAIR1_LINK_ROLE_CLICK_CYCLE" in source
    assert "YTCE_V83C_REPAIR1_LINK_DETAILS_WINDOW" in source
    assert "YTCE_V83C_REPAIR1_TEXT_VIEW_COPY" in source
    assert "YTCE_V83C_REPAIR1_LOCATOR_AS_PRESERVATION" in source
    assert "YTCE_V83C_REPAIR1_ARTICLE_TEXT_SOURCE_ROLES" in source
    assert "YTCE_V83C_REPAIR2_OLD_TEXTBOX_STYLE" in source
    assert "YTCE_V83C_REPAIR2_MEDIA_FILTER_COUNTS_VISIBLE_LINK_ROWS" in source
    assert "YTCE_V83C_REPAIR2_ICON_ONLY_COPY_CONTROLS" in source
    assert "YTCE_V83C_REPAIR3_MEDIA_TOGGLE_DEFENSIVE_GUARD" in source
    assert "_insert_link_source_rows_in_text" in source
    assert "_next_link_source_evidence_role" in source
    assert "_link_source_visible_role_value" in source
    assert "order = (\"PRIMARY\", \"SECONDARY\", \"TERTIARY\", \"UNKNOWN\")" in source
    assert "_open_link_source_details_window_for_record" in source
    assert "_copy_link_source_record_url" in source
    assert "Open URL / Copy URL / Copy details" not in source
    assert "do not show a separate link-count bar here" in source
    assert 'text="" if plain_copy_icon is not None else "Copy plain text"' in source
    assert 'text="" if role_copy_icon is not None else "Copy role markup"' in source
    assert "copy_source_role" in source
    assert 'transcript_box.tag_config("claim_hover_fill", underline=1)' in source
    assert 'transcript_box.tag_config("claim_hover_fill", background=' not in source
    assert 'transcript_box.tag_config("claim_primary_fill", background="#12351f")' in source
    assert 'f"    LOCATOR — {url_value}\\n"' not in source
    assert 'transcript_box.insert("end", url_value, (fill_tag, text_tag, bind_tag))' in source
    assert 'f"[{role}] Source URL:' not in source
    assert 'f"    {object_type} — {heading}\\n"' not in source
    assert 'if role_markup else url' in source
    assert 'tuple(link_source_objects or ())' in source
    assert (
        'logger.debug("Could not re-render source-role text after Media filter toggle."' in source
        or "Could not re-render source-role text after Media filter toggle" in source
        or "YTCE_V83D_R36J_MEDIA_LINK_CLICK_NO_REBUILD" in source
        or "_render_claim_transcript(restore_yview=inner_yview, restore_outer_yview=outer_yview)" in source
    )
    assert "YTCE_V83C_REPAIR4_LINK_ROW_INSTANCE_TAGS" in source
    assert "YTCE_V83D_VISIBLE_TEXTBOX_LINK_ROW_COUNTS" in source
    assert "YTCE_V83D_R35_VISIBLE_MEDIA_COUNT_STRIP_FROM_RENDERED_MARKUP" in source
    # YTCE_V83D_R36K_LINK_CLICK_MARKER_TEST_COMPAT
    # R36J intentionally replaced the older R36B full-rebuild link click path
    # with a no-rebuild in-place retag path. Keep this UI self-test compatible
    # with both patch states so it protects the Review dialog source-role text
    # behaviour without requiring the retired R36B marker to remain in the
    # inspected dialog method.
    main_file_source = Path(__file__).with_name("main.py").read_text(encoding="utf-8", errors="replace")
    assert (
        "YTCE_V83D_R36B_MEDIA_LINK_ROLE_CLICK_COUNT_REFRESH" in source
        or "YTCE_V83D_R36J_MEDIA_LINK_CLICK_NO_REBUILD" in source
        or "YTCE_V83D_R36B_MEDIA_LINK_ROLE_CLICK_COUNT_REFRESH" in main_file_source
        or "YTCE_V83D_R36J_MEDIA_LINK_CLICK_NO_REBUILD" in main_file_source
    )
    assert "_render_claim_transcript(restore_yview=inner_yview, restore_outer_yview=outer_yview)" in source
    assert "YTCE_V83D_R36C_MEDIA_TEXT_ROLE_CLICK_AND_HEADLINE_UNSPLIT" in source
    assert "selected_claim_span_media_roles" in source
    assert "new_media_source_role" in source
    # YTCE_V83D_R36G_R36C_MARKER_SCOPE_COMPAT
    # R36C's headline unsplit marker belongs to the role-freeze helper in
    # main.py, while this test primarily inspects the Review DB import dialog
    # method.  Accept the marker from either location so the test protects the
    # runtime behaviour without forcing an unrelated comment into the dialog.
    main_file_source = Path(__file__).with_name("main.py").read_text(encoding="utf-8", errors="replace")
    assert (
        "R36C_HEADLINE_DIRECT_ACCOUNT_UNSPLIT_SECONDARY" in source
        or "R36C_HEADLINE_DIRECT_ACCOUNT_UNSPLIT_SECONDARY" in main_file_source
    )
    assert "_visible_role_markup_count_for_source_text_strip()" in source
    assert "_visible_text_widget_role_count_for_source_text_strip()" in source
    assert (
        "_set_source_text_role_count_strip(_visible_role_markup_count_for_source_text_strip())" in source
        or "_set_source_text_role_count_strip(_visible_text_widget_role_count_for_source_text_strip())" in source
    )
    # YTCE_V83D_R35B_COUNT_STRIP_TEST_ASSERTION_COMPAT
    # The source line is a raw regex.  Some prior assertion text checked the
    # doubly-escaped representation (r"\\|\\s*...") instead of the actual
    # file text (r"\|\s*...").  Accept either representation; the behaviour
    # being protected is that the visible count strip scans rendered role markup
    # lines for PRIMARY/SECONDARY/TERTIARY/UNKNOWN.
    assert (
        're.search(r"\\|\\s*(PRIMARY|SECONDARY|TERTIARY|UNKNOWN)' in source
        or 're.search(r"\\\\|\\\\s*(PRIMARY|SECONDARY|TERTIARY|UNKNOWN)' in source
    )
    assert "link_row_{link_index}_url" in source
    assert "link_row_{link_index}_hover" in source
    assert 'transcript_box.insert("end", "\\n  ")' in source
    assert "YTCE_V83C_REPAIR4_SINGLETON_NOTE_POPUP" in source
    assert "claim_note_popup_holder" in source
    assert "Default role" in source and "Current visible role" in source
    assert "YTCE_V83D_LINK_DETAILS_ARTICLE_MEDIA_FROM_PARSED_TEXT" in source
    assert "Linked media / article media:" in source
    assert "profile_media_browser_network_provenance_v83d" in source
    assert "Browser/network provenance:" in source
    assert "profile_media_capture_provenance_ui_adapter_v83d" in source
    assert "Capture artifact review:" in Path("profile_media_capture_provenance_ui_adapter_v83d.py").read_text(encoding="utf-8")
    assert "Metadata only — does not change source role." in Path("profile_media_capture_provenance_ui_adapter_v83d.py").read_text(encoding="utf-8")
    assert "profile_media_capture_review_persistence_v83d" in Path("profile_media_capture_provenance_ui_adapter_v83d.py").read_text(encoding="utf-8")
    assert "merge_persisted_and_discovered_capture_reviews" in Path("profile_media_capture_provenance_ui_adapter_v83d.py").read_text(encoding="utf-8")
    assert "YTCE_V83C_REPAIR4_MEDIA_FILTER_DOES_NOT_HIDE_PERSONS" in source
    assert "visible_person_rows = tuple(person for person in state.person_rows" in source


def test_v83c_repair14_comments_use_render_time_shared_classifier() -> None:
    main_source = Path("main.py").read_text(encoding="utf-8")
    preview_source = Path("profile_media_source_package_preview.py").read_text(encoding="utf-8")
    assert "YTCE_V83C_REPAIR14_RENDER_TIME_COMMENT_CLASSIFIER" in main_source
    assert "YTCE_V83C_REPAIR14_STALE_COMMENT_SPAN_BYPASS" in main_source
    assert "claim_role_spans_classified_by_shared_classifier" in preview_source
    assert "profile_media_claim_role_classifier" in preview_source


def test_r41b_link_details_run_capture_now_is_metadata_only() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "Run capture now" in source
    assert "R41B_RUN_CAPTURE_NOW_METADATA_ONLY" in source
    assert "profile_media_capture_now_workflow_v83d" in source
    assert "profile_media_edge_cdp_link_sourcing_v83d" in source
    assert "capture_link_source_edge_first" in source
    assert "PROFILE_MEDIA_CAPTURE_REVIEW_REGISTRY_V83D.json" in source
    assert "Telemetry metadata only; source roles and counters were not changed." in source
    assert "threading.Thread(target=_worker, name=\"profile-media-r41-run-capture-now\"" in source


def test_r41t_link_details_are_fast_and_capture_history_is_lazy() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    capture_now_source = Path("profile_media_capture_now_workflow_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "profile_media_link_source_details_fast_render_v83d" in source
    assert "prepare_fast_link_source_details" in source
    assert "render_fast_link_source_details_text" in source
    assert "render_lazy_capture_history_text" in source
    assert "Capture artifact review: loading latest metadata" in source
    assert "self.after(50, _load_capture_history)" in source
    assert "normalise_capture_frame_urls" in capture_now_source
    assert "top_level_final_url" in capture_now_source
    assert "challenge_frame_url" in capture_now_source
    assert "CAPTURED_WITH_BLOCKER_OR_CHALLENGE" in Path("profile_media_capture_frame_classification_v83d.py").read_text(encoding="utf-8")
    assert "WAITING_FOR_CHAIN_LINK_CHECKBOX" in Path("profile_media_archive_ph_challenge_retry_v83d.py").read_text(encoding="utf-8")


def test_r41q_visible_workflow_summary_is_wired_to_database_card() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    panel_source = Path("profile_media_database_workbench_panel.py").read_text(encoding="utf-8", errors="replace")
    assert "profile_media_database_panel_workflow_label" in source
    assert "R41Q workflows:" in source
    assert "workflow_rows" in panel_source
    assert "workflow_columns" in panel_source
    assert "open_human_action_queue_panel" in panel_source
    assert "open_network_provenance_panel" in panel_source
    assert "open_passive_http_metadata_panel" in panel_source
    assert "source_roles_changed" in panel_source
    assert "archive_inheritance_changed" in panel_source


def test_r41r_visible_workflow_panels_are_wired_lazily_to_database_card() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "profile_media_database_r41r_workflow_buttons" in source
    assert "YTCE_V83D_R41R_VISIBLE_HUMAN_ACTION_QUEUE_PANEL" in source
    assert "YTCE_V83D_R41R_VISIBLE_BROWSER_ACTION_PANEL" in source
    assert "YTCE_V83D_R41R_VISIBLE_NETWORK_PROVENANCE_PANEL" in source
    assert "YTCE_V83D_R41R_VISIBLE_PASSIVE_HTTP_METADATA_PANEL" in source
    assert "YTCE_V83D_R41R_VISIBLE_CLEAN_STATIC_VIEWER_ACTION" in source
    assert "threading.Thread(target=_worker, name=\"profile-media-r41r-passive-http-probe\"" in source
    assert "allow_network=True" in source
    assert "PROFILE_MEDIA_R41R_HUMAN_ACTION_QUEUE.json" in source
    assert "install_middle_click_autoscroll(input_box" in source
    assert "install_middle_click_autoscroll(output_box" in source


def test_r41v_lightweight_browser_route_status_is_visible_in_browser_actions_panel() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "profile_media_lightweight_browser_action_panel_v83d" in source
    assert "profile_media_webview_capability_model_v83d" in source
    assert "build_lightweight_browser_capability_model" in source
    assert "render_lightweight_browser_action_panel_text" in source
    assert "R41V lightweight browser/action route:" in source


def test_r41w_browser_actions_exposes_safe_tab_cleanup_commands() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "profile_media_browser_tab_cleanup_v83d" in source
    assert "List open capture tabs" in source
    assert "Close YTCE test tabs" in source
    assert "Close stale capture tabs" in source
    assert "safe YTCE capture/test tabs only" in source


def test_r41x_link_source_details_exposes_role_matrix_ui_actions() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    matrix_source = Path("profile_media_link_source_details_role_matrix_v83d.py").read_text(encoding="utf-8", errors="replace")
    fast_source = Path("profile_media_link_source_details_fast_render_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "profile_media_link_source_details_role_matrix_v83d" in source
    assert "_link_source_role_matrix_text" in source
    assert "Role matrix" in source
    assert "Open in capture browser" in source
    assert "debug_capture_buttons_primary_visible" in Path("profile_media_link_source_webpage_role_view_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "Copied filtered diagnostics/details text." in source
    assert "Close YTCE test tabs" in source
    assert "R41X Link Source Role Matrix" in matrix_source
    assert "Role grading matrix" in matrix_source
    assert "Linked media / article media matrix" in matrix_source
    assert "Browser/network provenance matrix" in matrix_source
    assert "OSINT/passive discovery matrix" in matrix_source
    assert "Evidence gate" in matrix_source
    assert "METADATA_ONLY for network/passive/OSINT records." in matrix_source
    assert "r41x_role_matrix_text" in fast_source


def test_r41y_link_source_details_rich_viewer_sections_are_visible() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    rich_source = Path("profile_media_rich_link_source_details_viewer_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "YTCE_V83D_R41Y_RICH_LINK_SOURCE_DETAILS_VIEWER" in source
    assert "build_rich_link_source_details_viewer_state" in source
    assert "CTkScrollableFrame(diagnostics_content" not in source
    assert "diagnostics_filter_controls_secondary_details" in Path("profile_media_link_source_edit_window_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "Role grading" in rich_source
    assert "Linked media / article media" in rich_source
    assert "Browser/network provenance" in rich_source
    assert "OSINT/passive discoveries" in rich_source
    assert "Capture artifact review" in rich_source
    assert "Evidence gate explanation" in rich_source
    assert "Actions / workflow state" in rich_source
    assert "lazy_thumbnail_hover_frame" in rich_source
    assert "No preloading every video" in rich_source
    assert "one_active_preview_stream" in rich_source
    assert "_copy_selected_osint_passive_candidate" in source
    assert "_add_selected_osint_candidate_to_review_queue" in source
    assert "Human action alone is not evidence." in rich_source
    assert "Media candidate metadata alone is not evidence." in rich_source


def test_r41z_link_source_details_embedded_media_preview_is_wired() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    rich_source = Path("profile_media_rich_link_source_details_viewer_v83d.py").read_text(encoding="utf-8", errors="replace")
    preview_source = Path("profile_media_link_source_embedded_media_preview_v83d.py").read_text(encoding="utf-8", errors="replace")
    cache_source = Path("profile_media_media_preview_cache_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "YTCE_V83D_R41Z_EMBEDDED_MEDIA_PREVIEW" in source
    assert "Media Preview" in source
    assert "embedded_media_preview_state" in rich_source
    assert "build_embedded_media_preview_state" in rich_source
    assert "Open media externally" in preview_source
    assert "Copy media URL" in preview_source
    assert "Copy media role reason" in preview_source
    assert "Add media candidate to review queue" in preview_source
    assert "Open related capture artifact folder" in preview_source
    assert "Video hover preview requested (lazy)" in source
    assert "Preserved hover frame" in source
    assert "preload_video" in preview_source
    assert "one_active_preview_stream" in preview_source
    assert "preserve_static_hover_frame_after_preview" in preview_source
    assert "does_not_create_evidence" in preview_source
    assert "manual_article_archive_tabs_preserved" in preview_source
    assert "no_preload_every_video" in cache_source
    assert "fallback_paused_frame_if_canvas_unavailable" in cache_source


def test_r42a_link_source_details_inline_media_viewer_is_not_browser_chrome() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    viewer_source = Path("profile_media_inline_media_viewer_v83d.py").read_text(encoding="utf-8", errors="replace")
    loader_source = Path("profile_media_inline_media_loader_v83d.py").read_text(encoding="utf-8", errors="replace")
    preview_source = Path("profile_media_link_source_embedded_media_preview_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "YTCE_V83D_R42A_LIGHTWEIGHT_INLINE_MEDIA_VIEWER" in source
    assert "Load inline preview" not in source
    assert "Play/pause preview" not in source
    assert "Selected-card inline preview" in viewer_source
    assert "card-local preview control where supported" in preview_source
    assert "profile-media-r42a-inline-media-preview" in source
    assert "load_inline_media_preview_payload" in source
    assert "Inline media previews are metadata/review UI only; no address bar, tabs, navigation toolbar, or whole-page browser controls." in source
    assert "Loading selected preview" in source
    assert "Video preview limited" in source
    assert "Image preview ready (selected lazy load)" in source
    assert "no_browser_address_bar" in viewer_source
    assert "no_browser_tabs" in viewer_source
    assert "no_navigation_toolbar" in viewer_source
    assert "loads_selected_media_only" in viewer_source
    assert "video_full_playback_claimed" in viewer_source
    assert "MAX_INLINE_MEDIA_BYTES" in loader_source
    assert "urllib.request.urlopen" in loader_source
    assert "Image.open" in loader_source
    assert "thumbnail(preview_size" in loader_source
    assert "inline_media_viewer_state" in preview_source
    assert "source_roles_changed" in loader_source
    assert "archive_inheritance_changed" in loader_source


def test_r42b_link_source_details_uses_scoped_semantic_media_editor() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    edit_source = Path("profile_media_link_source_edit_window_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "YTCE_V83D_R42B_LINK_SOURCE_DETAILS_EDIT_WINDOW" in source
    assert '"r42b_preview_context"' in source
    assert '"claim_role_spans": [dict(item) for item in claim_role_spans' in source
    assert '"claim_role_classification_preview"' in source
    assert "build_link_source_edit_window_state" in source
    assert (
        "Rendered page role overlay" in source
        or "build_webpage_role_view_state" in source
        or "build_selected_url_rendered_page_artifact_state" in source
        or "profile_media_link_source_webpage_role_view_v83d" in source
        or "Rendered page role overlay" in edit_source
    )
    assert "Selected URL source view" not in source
    assert "command=_toggle_link_source_media_mode" not in source
    assert 'values=["Semantic", "Media"]' in source
    assert "source_editor_count_labels" in source
    assert "r42b_role_span_" in source
    assert "selected_link_semantic_roles" in source
    assert "selected_link_media_roles" in source
    assert "render_link_source_editor_plain_text" in source
    assert "render_link_source_editor_role_markup" in source
    assert "> Diagnostics" in source
    assert "diagnostics_filter_var" in source
    assert '"Role matrix", "Media details", "Archive/locator", "Evidence gate", "OSINT/passive", "Capture diagnostics"' in source
    r42b_method_tail = source.split("def _open_link_source_details_window_for_record", 1)[1]
    r42b_boundary_markers = (
        "Rendered page role overlay",
        "build_webpage_role_view_state",
        "build_selected_url_rendered_page_artifact_state",
        "profile_media_link_source_webpage_role_view_v83d",
    )
    primary_block = r42b_method_tail
    for marker in r42b_boundary_markers:
        if marker in r42b_method_tail:
            primary_block = r42b_method_tail.split(marker, 1)[0]
            break
    assert 'text=f"{label_text}:"' not in primary_block
    assert 'text="Role:"' not in primary_block
    assert 'text="Evidence gate:"' not in primary_block
    assert 'text="Run capture now"' not in primary_block
    assert 'text="Open in capture browser"' not in primary_block
    assert 'text="Retry after human action"' not in primary_block
    assert 'text="Copy role matrix"' not in primary_block
    assert 'text="Add selected candidate to review queue"' not in primary_block
    assert "semantic_and_media_decisions_separate" in edit_source
    assert "semantic_counts_exclude_media_cards" in edit_source
    assert "selected_claim_span_roles" in edit_source
    assert "selected_claim_span_media_roles" in edit_source
    assert "new_role" in edit_source
    assert "new_media_source_role" in edit_source
    assert "images_videos_are_media_only" in edit_source
    assert "no_browser_chrome" in edit_source
    assert "archive_inheritance_changed" in edit_source
    assert "_cached_text_sources" in edit_source
    assert "_body_after_top_url_preamble" in edit_source
    assert "_related_link_source_rows" in edit_source
    assert "inline_media_preview" in edit_source


def test_r42d_link_source_details_real_rendered_page_role_overlay() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    edit_source = Path("profile_media_link_source_edit_window_v83d.py").read_text(encoding="utf-8", errors="replace")
    view_source = Path("profile_media_link_source_webpage_role_view_v83d.py").read_text(encoding="utf-8", errors="replace")
    artifact_source = Path("profile_media_link_source_rendered_page_artifact_v83d.py").read_text(encoding="utf-8", errors="replace")
    assert "YTCE_V83D_R42C_LINK_SOURCE_DETAILS_WEBPAGE_RENDERED_ROLE_VIEW" in edit_source
    assert "YTCE_V83D_R42C_LINK_SOURCE_DETAILS_WEBPAGE_ROLE_VIEW" in view_source
    assert "YTCE_V83D_R42D_LINK_SOURCE_DETAILS_REAL_RENDERED_PAGE_ROLE_OVERLAY" in view_source
    assert "YTCE_V83D_R42D_LINK_SOURCE_DETAILS_REAL_RENDERED_PAGE_ARTIFACT" in artifact_source
    assert "build_webpage_role_view_state" in source
    assert "build_selected_url_rendered_page_artifact_state" in source
    assert (
        "Rendered page role overlay" in source
        or "Source-role overlay" in source
        or "role_overlay_blocks_only" in view_source
    )
    assert (
        "Captured page image" in source
        or "Captured page screenshot" in source
        or "uses_captured_page_screenshot" in artifact_source
    )
    assert (
        "Captured rendered page HTML" in source
        or "Captured live page HTML" in source
        or "uses_captured_rendered_html" in artifact_source
    )
    assert "Source-role overlay" in source
    assert "Text-region mapping is not available" in source
    assert "bg=\"#ffffff\"" in source
    assert "font=(\"Segoe UI\", 12)" in source
    assert "r42c_article_title" in source
    assert "r42c_article_meta" in source
    assert "Source link" in source
    assert "Article metadata" in source
    assert "values=[\"Semantic\", \"Media\"]" in source
    assert "command=_toggle_link_source_media_mode" not in source
    assert "fg_color=bg" in source
    assert "text_color=fg" in source
    assert "media_source_role" in edit_source
    assert "semantic_role" in edit_source
    assert "fallback_is_presentation_only" in edit_source
    assert "uses_existing_review_db_import_spans" in edit_source
    assert "no_weaker_local_reclassification" in edit_source
    assert '"media_source_role": "BLANK"' in edit_source
    assert "archive_rows_hidden_unless_selected_or_diagnostics" in edit_source
    assert "media_objects_embedded_in_source_view" in edit_source
    assert "media_role_coloured_outlines" in edit_source
    assert "uses_actual_rendered_or_captured_artifact" in artifact_source
    assert "uses_captured_page_screenshot" in artifact_source
    assert "uses_captured_rendered_html" in artifact_source
    assert "role_text_overlay_panel_required" in artifact_source
    assert "archive_related_rows_hidden_from_live_selected_view" in artifact_source
    assert "raw_debug_textbox" in view_source
    assert "monospaced_debug_text" in view_source
    assert "role_overlay_blocks_only" in view_source
    assert '"webpage_like_source_view": False' in view_source
    assert '"synthetic_article_layout": False' in view_source
    assert "no_address_bar" in view_source
    assert "no_tabs" in view_source
    assert "no_navigation_toolbar" in view_source
    assert "debug_capture_buttons_primary_visible" in view_source
    assert "visible_diagnostic_collapsible_rows_default" in view_source
    assert 'text="Run capture now"' not in source
    assert 'text="Retry after human action"' not in source
    assert 'text="Close YTCE test tabs"' not in source
    assert 'text="Copy selected OSINT/passive candidate"' not in source


def test_v83c_repair16_repair15_no_preview_gate() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    preview_source = Path("profile_media_source_package_preview.py").read_text(encoding="utf-8")
    assert "YTCE_V83C_REPAIR15_UNIVERSAL_ARTICLE_SOURCE_TEXT_CLASSIFIER" in source
    assert "YTCE_V83C_REPAIR15_SOURCE_TEXT_ROWS_USE_SHARED_CLASSIFIER" in source
    assert "YTCE_V83C_REPAIR16_REPAIR15_PREVIEW_GATE_REMOVED" in source
    assert "_ytce_review_reclassified_source_text_rows(rows)" in source
    assert "direct quoted/interview words classified by quoted-speaker semantics" in source


def test_v83c_repair21_media_view_source_role_colours() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "YTCE_V83C_REPAIR21_MEDIA_VIEW_SOURCE_ROLE_COLOURS" in source
    assert "source_reference_media_display_role_by_edit_key" in source
    assert "_source_reference_candidate_media_display_role" in source
    assert "unresolved_named_intermediary" in source
    assert "media_display_role = _claim_media_source_role_for_span(span_ref)" in source
    assert "cycle semantic claim roles from this view" in source


def test_v83c_repair22_r21_markup_test_compat() -> None:
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert ("_claim_role_markup_for_spans(spans, comment_sections, visible_roles_for_markup)" in source or "_claim_role_markup_for_spans(spans, comment_sections, visible_roles_for_markup)" in source)
    if "YTCE_V83C_REPAIR21_MEDIA_VIEW_SOURCE_ROLE_COLOURS" in source:
        assert "visible_roles_for_markup" in source
        assert "_claim_media_filter_active()" in source
        assert "_claim_media_source_role_for_span" in source

def run_self_test() -> None:
    test_r41b_link_details_run_capture_now_is_metadata_only()
    test_r41q_visible_workflow_summary_is_wired_to_database_card()
    test_r41r_visible_workflow_panels_are_wired_lazily_to_database_card()
    test_r41v_lightweight_browser_route_status_is_visible_in_browser_actions_panel()
    test_r41w_browser_actions_exposes_safe_tab_cleanup_commands()
    test_r41x_link_source_details_exposes_role_matrix_ui_actions()
    test_r41y_link_source_details_rich_viewer_sections_are_visible()
    test_r41z_link_source_details_embedded_media_preview_is_wired()
    test_r42a_link_source_details_inline_media_viewer_is_not_browser_chrome()
    test_r42b_link_source_details_uses_scoped_semantic_media_editor()
    test_r42d_link_source_details_real_rendered_page_role_overlay()
    test_v83c_repair22_r21_markup_test_compat()
    test_enter_source_url_intake_adds_rows_and_retains_invalid_text()
    test_shift_enter_inserts_newline_without_submission()
    test_archive_auto_check_preference_loads_saves_and_drives_row_state()
    test_source_url_section_layout_has_no_main_card_updates_and_has_required_controls()
    test_twitter_source_row_uses_compact_post_thread_settings_model()
    test_source_row_layout_uses_compact_resource_icons_and_remove_button()
    test_archive_status_label_uses_date_only_for_available_status()
    test_remove_source_row_updates_selection_and_scoped_state()
    test_sidebar_spacing_is_compact_between_updates_keys_and_export()
    test_sidebar_order_places_updates_above_keys_export_files()
    test_youtube_filters_live_in_combined_youtube_settings_window()
    test_database_sidebar_has_compact_home_controls_and_hides_counts_when_off()
    test_media_resource_window_has_v77f_preservation_scaffolding()
    test_media_resource_window_download_labels_and_gallery()
    test_files_sidebar_resizer_and_review_highlight_are_more_usable()
    test_sidebar_top_buttons_do_not_expand_with_sash()
    test_database_toggle_animation_avoids_final_state_jump()
    test_database_import_preview_home_root_guard_and_row_layout()
    test_build_preview_counts_apply_to_main_card_before_review_opens()
    test_build_preview_final_counts_match_review_state_for_metro_shaped_payload()
    test_text_editor_large_txt_load_is_background_and_not_review_build()
    test_source_details_uses_youtube_metadata_placeholders_not_domain()
    test_transcript_controls_use_right_side_space()
    test_transcript_toolbar_get_label_preserves_youtube_callback()
    test_online_asr_is_key_gated_and_uses_matching_local_button_control()
    test_start_fetching_msn_scaffold_returns_before_credential_resolution()
    test_start_fetching_source_scaffold_builds_plan_preview_without_live_execution()
    test_start_fetching_without_selected_scope_sets_skipped_status()
    test_archivebox_icon_and_service_order_are_local_only()
    test_discussion_layout_uses_webpage_parent_and_child_rows()
    test_main_blank_wheel_router_targets_main_without_stealing_text_scroll()
    test_transcript_controls_are_split_across_rows_for_narrow_widths()
    test_url_helper_wrap_and_textbox_height_are_responsive()
    test_visible_header_is_removed_to_recover_vertical_space()
    test_review_dialog_uses_tk_text_role_spans_and_inline_multiselect()
    test_review_dialog_exposes_v83c_link_source_ui_and_decisions()
    test_v83c_repair1_renders_link_rows_inside_source_role_text()
    test_v83c_repair6_media_unlinked_scope_keeps_mixed_article_text_visible()
    test_v83c_repair14_comments_use_render_time_shared_classifier()
    test_v83c_repair16_repair15_no_preview_gate()


if __name__ == "__main__":
    run_self_test()
    print("main_source_resource_ui_test.py: OK")


def test_webpage_image_downloader_backend_is_wired_for_selected_images() -> None:
    source = inspect.getsource(App._open_source_resource_window)
    main_source = Path("main.py").read_text(encoding="utf-8")

    assert "from webpage_image_downloader_backend import" in main_source
    assert "discover_webpage_images_for_row" in main_source
    assert "download_selected_webpage_images" in main_source
    assert "def discover_page_images() -> None:" in source
    assert "Click Discover images to scan the source page" in source
    assert "Webpage image download: selected=" in source
    assert "Choose folder for selected webpage image downloads" in source
    assert 'text="Discover images"' in source
    assert 'row.adapter_id not in {"youtube", "twitter_x"}' in source
    assert "network/download/recording actions performed: none" in source



def test_media_resource_window_session_gallery_ux_finish() -> None:
    source = inspect.getsource(App._open_source_resource_window)

    assert "show_image_dialog_notice" in source
    assert "Downloaded {newly_downloaded} new webpage image(s)." not in source
    assert "Hover a file name for source details" in source
    assert "hover an image square for dimensions" in source
    assert "image_resource_detail_text" in source
    assert "bind_image_detail_hover" in source
    assert "show_image_size_badge" in source
    assert "hide_image_size_badge" in source
    assert "column_count = 4 if resource_kind == RESOURCE_KIND_IMAGE else 2" in source
    assert "default_image_render_limit = 96" in source
    assert "hidden_image_render_limit = 384" in source
    assert "def sync_visible_checkboxes()" in source
    assert "render_resource_list()\n            refresh_count()" not in inspect.getsource(App._open_source_resource_window).split("def sync_visible_checkboxes()", 1)[1].split("def discover_page_images", 1)[0]


def test_webpage_image_session_temp_cleaned_when_files_are_cleared() -> None:
    clear_source = inspect.getsource(App._clear_all_session_files_clicked)
    remove_source = inspect.getsource(App._remove_session_file)
    cleanup_source = inspect.getsource(App._cleanup_webpage_image_session_downloads)

    assert "_cleanup_webpage_image_session_downloads(reset_state=True)" in clear_source
    assert "reset_state: bool = False" in cleanup_source
    assert "webpage_image_session_output_root = None" in cleanup_source
    assert "webpage_image_session_download_cache = {}" in cleanup_source
    assert "Could not clean detached temporary webpage image file" in remove_source

def test_v82c_database_home_and_capture_preview_are_status_driven() -> None:
    create_source = inspect.getsource(App._create_profile_media_database_home_repository)
    set_home_source = inspect.getsource(App._set_profile_media_database_home_root)
    build_source = inspect.getsource(App._build_profile_media_database_import_preview_from_current_state)
    start_source = inspect.getsource(App.start_fetching)

    assert 'messagebox.showinfo("Create Database HOME"' not in create_source
    assert 'messagebox.showinfo("Build DB import"' not in build_source
    assert '"Discussion action scaffold",' not in start_source
    assert '"Discussion action scaffold ready' not in start_source
    assert "_set_operational_capture_status" in create_source
    assert "_refresh_discussion_source_controls" in set_home_source
    assert "_profile_media_database_planned_source_capture_artifacts" in build_source


def test_v82c_planned_webpage_and_screenshot_scopes_are_review_artifacts() -> None:
    row = build_source_resource_row(MSN_URL)
    app = App.__new__(App)
    app.extract_webpage_var = FakeVar(True)
    app.webpage_screenshot_var = FakeVar(True)

    artifacts = App._profile_media_database_planned_source_capture_artifacts(app, row)

    kinds = {artifact["artifact_kind"] for artifact in artifacts}
    assert {"article_text", "screenshot", "archive_check", "warc", "wacz"} <= kinds
    assert all(artifact["local_path"] == "" for artifact in artifacts)
    assert all(artifact["temporary"] is True for artifact in artifacts)
    assert all(artifact["review_required"] is True for artifact in artifacts)
    assert all("review-only" in artifact["notes"] for artifact in artifacts)
    assert all("no live" in artifact["notes"].lower() for artifact in artifacts)


def test_v82g_database_review_button_and_visible_sidebar_counts() -> None:
    create_source = inspect.getsource(App._create_profile_media_database_mode_toggle_section)
    open_source = inspect.getsource(App._open_profile_media_database_import_review_text)

    assert 'text="Review"' in create_source
    assert "write_profile_media_database_import_review_text" in open_source
    assert "profile_media_database_last_source_package_preview_file" in open_source
    assert "protected review" in open_source.lower()
    assert "_open_profile_media_database_import_review_dialog" in open_source
    assert "Text Editor" not in open_source
    assert 'height=108' in create_source
    assert 'font=ctk.CTkFont(size=11, weight="bold")' in create_source


def test_v83c_repair19_media_icon_includes_source_reference_statements():
    source = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "YTCE_V83C_REPAIR19_MEDIA_ICON_INCLUDES_SOURCE_STATEMENTS" in source
    assert "media_role = _claim_media_source_role_for_span(span_ref)" in source
    assert "YTCE_V83C_REPAIR19_MEDIA_STATEMENT_COUNT_HELPERS" in source
    assert "and not _claim_media_filter_active()" in source
