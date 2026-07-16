import inspect

import main
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
    test_start_fetching_msn_scaffold_returns_before_credential_resolution()
    test_archivebox_icon_and_service_order_are_local_only()
    test_discussion_layout_uses_webpage_parent_and_child_rows()
    test_main_blank_wheel_router_targets_main_without_stealing_text_scroll()
    test_transcript_controls_are_split_across_rows_for_narrow_widths()
    test_url_helper_wrap_and_textbox_height_are_responsive()


if __name__ == "__main__":
    run_self_test()
    print("main_source_resource_ui_test.py: OK")
