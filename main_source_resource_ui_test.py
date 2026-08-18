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
    assert any(("Metadata probes may run" in message) or ("Network actions performed: none" in message) for message, _level in app.log_messages)


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
    assert 'text="▧"' in source
    assert 'text="▶"' in source
    assert 'text="×"' in source
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
    assert 'text="Save"' in create_source
    assert ('text="Load"' in create_source) or ('text="Unload"' in create_source)
    assert 'text="Import"' in create_source
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


def test_media_resource_window_has_v77f_preservation_scaffolding() -> None:
    source = inspect.getsource(App._open_source_resource_window)

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
    assert "No visible image previews match this source/filter" in source
    assert "hidden/no-preview candidates stay hidden unless Show hidden is enabled" in source
    assert "Select all" in source
    assert "window.after" in source
    assert "show_messages=False" in source
    app_source = inspect.getsource(App)
    assert "_start_webpage_image_source_row_prefetch" in app_source
    assert "_apply_prefetched_webpage_image_discovery" in app_source
    assert "Prefetched" in app_source
    assert "_start_webpage_video_source_row_prefetch" in app_source
    assert "_apply_prefetched_webpage_video_discovery" in app_source
    assert "Video & Audio can open from the cached candidate list" in app_source
    assert "discover_webpage_videos_for_row" in Path("main.py").read_text(encoding="utf-8")
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
    assert "video_hover_preview_frames_by_id" in source
    assert "_apply_cached_video_hover_preview" in source
    assert "A poster/thumbnail cache hit must not block animated hover-preview" in source
    assert "_start_webpage_video_hover_preview_prefetch_for_discovery" in inspect.getsource(App)
    assert "Prefetched {count} animated video hover preview" in inspect.getsource(App)
    assert "serious_review_markers" in source


def test_media_resource_window_download_labels_and_gallery() -> None:
    source = inspect.getsource(App._open_source_resource_window)

    assert 'text=("Download selected"' in source
    assert "Review selected" in source
    assert "preview_box" in source
    assert "thumbnail_images_by_id" in source
    assert "thumbnail_hidden_resource_ids" in source
    assert "show_hidden_images_var" in source
    assert "Show hidden" in source
    assert "_is_default_hidden_webpage_image_candidate" in source
    assert "hidden_candidate_count" in source
    assert "thumbnail_preview_status_by_id" in source
    assert "thumbnail_probe_thread_active" in source
    assert "webpage_image_preview_pil_cache_by_url" in source
    assert "webpage_image_discovery_cache_by_url" in source
    assert "_webpage_image_discovery_cache_key" in source
    assert "Using cached webpage image candidate list" in source
    assert "_prewarm_rendered_discovery_if_js_heavy" in source
    assert "prewarm_rendered_browser_discovery_worker" in inspect.getsource(App)
    assert "start_internal_browser_image_discovery_service" in inspect.getsource(App)
    assert "close_rendered_browser_discovery_worker" in inspect.getsource(App)
    assert "start_internal_browser_image_discovery_service" in inspect.getsource(App)
    assert "_start_internal_browser_image_discovery_service" in inspect.getsource(App)
    assert "YTCEInternalBrowserImageDiscoveryService" in inspect.getsource(App)
    assert 'self.__dict__.get("internal_browser_image_discovery_service_started", False)' in inspect.getsource(App)
    assert 'if "tk" not in self.__dict__:' in inspect.getsource(App)
    assert "Source-row prefetch is a real GUI/background-network path" in inspect.getsource(App)
    assert "Video prefetch may perform static HTML and rendered DOM/network probes" in inspect.getsource(App)
    assert "Refresh images forces a rescan" in source
    assert "Refresh videos forces a rescan" in source
    assert "candidate lists and previews are cached" in source
    assert "candidate lists and previews are cached/prefetched" in source
    assert "visible rendering is capped and diff-refreshed" in source
    assert "rendered_tile_refreshers_by_id" in source
    assert "display_resource_ids == rendered_tile_resource_ids" in source
    assert "refresh_rendered_tile" in source
    assert "cached_discovery_on_open" in source
    assert "_apply_cached_thumbnail_preview" in source
    assert "_start_thumbnail_preview_probe" in source
    assert "threading.Thread(target=_worker" in source
    assert "return thumbnail_images_by_id.get(item.resource_id)" in source
    assert "timeout=0.7" in source
    assert "response.read(384 * 1024)" in source
    assert "_schedule_thumbnail_probe_render(delay_ms: int = 650)" in source
    assert "Loading previewable image thumbnails" in source
    assert "default view shows only candidates that successfully preview" in source
    assert "Discovering image candidates in the background" in source
    assert "image_discovery_thread_active" in source
    assert "video_discovery_thread_active" in source
    assert "video_discovery_results_lock" in source
    assert "webpage_video_discovery_cache_by_url" in source
    assert "_apply_webpage_video_discovery_result" in source
    assert "visible rendering is capped and diff-refreshed for responsiveness" in source
    assert "discovery_method=" in source
    assert "refresh_images_button.configure(state=\"disabled\"" in source
    assert "refresh_images_button.configure(state=\"normal\", text=\"Refresh images\")" in source
    assert "default_image_render_limit = 32" in source
    assert "hidden_image_render_limit = 24" in source
    assert "ThreadPoolExecutor(max_workers=worker_count)" in source
    assert "source_badge" not in source
    assert "bind_image_detail_hover" in source
    assert "image_resource_detail_text" in source
    assert "show_image_detail_popup" in source
    assert "show_image_size_badge" in source
    assert "hide_image_size_badge" in source
    assert "bind_image_detail_hover(preview_box" not in source
    assert "bind_image_detail_hover(preview_label" not in source
    assert "checkbox.place_forget()" in source
    assert "checkbox = ctk.CTkLabel(" in source
    assert "checkbox = ctk.CTkCheckBox(" not in source
    checkbox_start = source.index("checkbox = ctk.CTkLabel(")
    checkbox_end = source.index("def toggle_item_from_checkbox", checkbox_start)
    checkbox_source = source[checkbox_start:checkbox_end]
    assert "ctk.CTkLabel(\n                    preview_box," in checkbox_source
    assert 'fg_color="transparent"' not in checkbox_source
    assert 'fg_color=COLORS["bg_input"]' in checkbox_source
    assert "cb.place(x=6, y=6)" in source
    assert "tile_checkbox_refreshers" in source
    assert "_refresh_all_tile_checkbox_visibility" in source
    assert "tile_checkbox_watchdog" in source
    assert "pointer_over_image = _pointer_is_over_tile_image_area(image_area)" in source
    assert "show_badge()" in source
    assert "hide_badge()" in source
    assert "def _run_tile_checkbox_watchdog" in source
    assert "checkbox_visibility_state" in source
    assert 'state.get("visible")' in source
    assert 'state.get("selected") == selected' in source
    assert 'window.bind("<Motion>", _refresh_all_tile_checkbox_visibility' not in source
    assert 'window.after(25, _run_tile_checkbox_watchdog)' not in source
    assert 'window.after(120, _run_tile_checkbox_watchdog)' in source
    assert "item_card.grid_rowconfigure(0, weight=1" in source
    assert 'preview_box.grid(row=0, column=0, sticky="nsew"' in source
    assert "placeholder_text = _media_placeholder_text_for_item(item)" in source
    assert "font=ctk.CTkFont(size=_media_placeholder_font_size(item), weight=\"bold\")" in source
    assert "def _media_placeholder_font_size" in source
    assert 'preview_box.bind("<Motion>", show_image_size_badge' in source
    assert "for hover_widget in (preview_box, preview_label, checkbox):" in source
    assert "for boundary_widget in (item_card, name_label):" in source
    assert 'hover_widget.bind("<Motion>", refresh_tile_checkbox_visibility' in source
    assert 'boundary_widget.bind("<Motion>", refresh_tile_checkbox_visibility' not in source
    assert "def _poll_tile_checkbox_boundary" not in source
    assert "checkbox_pointer_poll" not in source
    assert "start_tile_checkbox_hover" not in source
    assert "toggle_item_from_checkbox" in source
    assert 'item_var.trace_add("write"' in source
    assert "_pointer_is_over_tile_image_control" not in source
    assert "item_card.after(35, _poll_tile_checkbox_boundary)" not in source
    assert 'hover_widget.bind("<Motion>", show_tile_checkbox' not in source
    assert "for hover_widget in (item_card, preview_box, preview_label, name_label):" not in source
    assert "def _pointer_is_over_tile_image_area" in source
    assert "return _pointer_inside_widget(image_area)" in source
    assert "return _pointer_inside_widget(image_area) or _pointer_inside_widget(cb)" not in source
    assert "_pointer_inside_widget" in source
    assert "original_preview_width, original_preview_height" in source
    assert "Hover a file name for source details; hover an image square for dimensions" in source
    assert "Select all" in source
    assert "Downloaded webpage image FILES refresh" in source
    assert "_webpage_image_session_download_root" in source
    assert "_cached_webpage_image_session_paths" in source
    assert "Choose folder for selected webpage image downloads" not in source
    assert "use EXPORT to choose a final output folder" in source
    assert "_refresh_session_files_list()" in source
    assert "_refresh_export_entry_state()" in source
    assert "update_idletasks()" in source



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
    assert "Source site/method selector audit-required rows:" in fake_messagebox.infos[0][1]
    assert "Named-site source method pack count: 11" in fake_messagebox.infos[0][1]
    assert "MSN source method packs: 2" in fake_messagebox.infos[0][1]
    assert "X/Twitter source method packs: 2" in fake_messagebox.infos[0][1]
    assert "YouTube source method packs: 2" in fake_messagebox.infos[0][1]
    assert "Generic/archive source method packs: 5" in fake_messagebox.infos[0][1]
    assert "Database review workflow: source_database_review_workflow_" in fake_messagebox.infos[0][1]
    assert "Source record review workflow: source_record_review_workflow_" in fake_messagebox.infos[0][1]
    assert "Selector approval packets: source_selector_approval_packets_" in fake_messagebox.infos[0][1]
    assert "Manual live-site smoke: pending separate approval" in fake_messagebox.infos[0][1]
    assert app.last_operational_capture_status.startswith("Fixture/model-only")
    assert app.url_status.config["text"].startswith("Fixture/model-only")
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
        assert result.file_count == 38
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
    assert 'right_action_panel.grid(row=0, column=2, rowspan=4, sticky="e")' in source
    assert 'self.discussion_source_menu.grid(row=0, column=0, sticky="e"' in source


def test_visible_header_is_removed_to_recover_vertical_space() -> None:
    source = inspect.getsource(App._create_header)

    assert "height=0" in source
    assert "no visible header content" in source
    assert "APP_DESCRIPTION" not in source
    assert "by Creator Intelligence" not in source

def run_self_test() -> None:
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
