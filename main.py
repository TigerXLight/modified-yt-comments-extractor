"""
YouTube Comment Extractor - Desktop Application.

A modern GUI application for extracting, filtering, and analyzing
YouTube comments with advanced spam detection.
"""

from __future__ import annotations

import logging
import html
import os
import re
import sys
import tempfile
import array
import csv
import concurrent.futures
import json
import subprocess
import random
import shutil
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, replace
from pathlib import Path
from io import BytesIO
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Dict, List, Optional, Sequence, Tuple

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw

from core.constants import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    COLORS,
    LOG_COLORS,
    LOG_ICONS,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    DIALOG_WIDTH,
    DIALOG_HEIGHT,
    API_DELAY_BETWEEN_VIDEOS_MIN,
    API_DELAY_BETWEEN_VIDEOS_MAX,
    SortOption,
)
from core.settings import SettingsManager, AppSettings
from core.validators import (
    URLValidator,
    DateValidator,
    APIKeyValidator,
    MinLikesValidator,
    MaxCommentsValidator,
    WordsFilterValidator,
)
from extractor import (
    YouTubeCommentExtractor,
    CommentsDisabledError,
    VideoNotFoundError,
    QuotaExceededError,
)

from updater import check_for_updates
from evidence_exporter import create_evidence_package
from transcript_tools import (
    TranscriptSegment,
    import_transcript,
    export_transcript_txt,
    export_transcript_csv,
    export_transcript_srt,
    export_transcript_vtt,
)
from speech_interval_vad import detect_speech_intervals_for_media_file

from youtube_transcript_downloader import (
    download_youtube_transcript,
    merge_transcript_segments,
)
from youtube_video_metadata import fetch_youtube_video_metadata
from asr_provider_action import (
    ASRProviderActionCoordinator,
    ASR_PROVIDER_ACTION_TRANSCRIBE,
)
from asr_connection_test import (
    ASRConnectionTestCoordinator,
    ASRConnectionTestStatus,
)
from elevenlabs_scribe_provider import (
    ELEVENLABS_SCRIBE_CREDENTIAL_ID,
    ELEVENLABS_SCRIBE_MODEL_ID,
    ELEVENLABS_SCRIBE_PROVIDER_ID,
    ElevenLabsScribeRequest,
    ElevenLabsScribeResult,
    ElevenLabsScribeValidationError,
)
from elevenlabs_scribe_transport import create_elevenlabs_scribe_sdk_provider_executor
from elevenlabs_key_validation import (
    ELEVENLABS_KEY_VALIDATION_AUTH_FAILED,
    ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE,
    ElevenLabsKeyValidationError,
    ElevenLabsModelsListKeyValidator,
)
from access_keys_dialog import (
    ACCESS_KEYS_BUTTON_TEXT,
    AccessKeysWindow,
    open_or_focus_access_keys_window,
)
from provider_key_validation import (
    KEY_VALIDATION_COULD_NOT_COMPLETE,
    KEY_VALIDATION_FAILED,
    KEY_VALIDATION_NOT_CONFIGURED,
    KEY_VALIDATION_VALIDATED,
    KEY_STATUS_NO_KEY_CONFIGURED,
    ProviderKeyValidationRecord,
    current_utc_timestamp,
    normalize_validation_records,
    validation_record_for_cleared_key,
    validation_records_to_settings_dict,
    validation_status_text_for_state,
)
from credential_runtime_status import (
    CredentialPresenceState,
    CredentialRuntimeStatus,
    build_runtime_credential_statuses,
)
from credential_store import SystemKeyringCredentialStore
from youtube_credential_migration import (
    YouTubeCredentialActionStatus,
    YouTubeCredentialMigrationService,
    YouTubeCredentialStorageState,
)
from local_asr_capabilities import (
    ASR_ENGINE_WHISPERCPP_VULKAN,
    resolve_local_asr_selection,
)
from capture_controller import (
    build_operational_capture_plan,
    format_operational_capture_plan_message,
)
from source_evidence_workflow_state import build_source_evidence_workflow_state
from source_app_operator_controller import build_app_operator_controller_state
from source_local_web_archive_actions import (
    build_local_web_archive_action_state,
    local_web_archive_status_lines,
)
from source_resource_state import (
    ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE,
    RESOURCE_KIND_IMAGE,
    RESOURCE_KIND_VIDEO_AUDIO,
    SourceResourceRowState,
    build_discussion_capture_options,
    build_discussion_selection_state,
    build_selected_media_preservation_preview,
    filter_resource_dialog_items,
    MediaResourceFilterState,
    parse_source_url_intake,
    remove_source_resource_row,
    resource_dialog_state_for_row,
    select_all_resources,
    clear_resource_selection,
)
from source_media_gui_bridge import (
    MEDIA_GUI_DOWNLOAD_STATUS_READY,
    run_source_media_gui_download,
)
from webpage_image_downloader_backend import (
    close_rendered_browser_discovery_worker,
    discover_webpage_images_for_row,
    download_selected_webpage_images,
    prewarm_rendered_browser_discovery_worker,
    start_internal_browser_image_discovery_service,
)
from webpage_video_resource_bridge import discover_webpage_videos_for_row, discover_fast_rendered_webpage_videos_for_row
from webpage_video_preview_backend import (
    can_generate_video_frame_preview,
    can_generate_video_hover_preview,
    extract_video_frame_preview_pil,
    extract_video_hover_preview_frames_pil,
    extract_video_hover_preview_frames_pil_browser,
    video_frame_preview_cache_key,
    video_hover_preview_cache_key,
)
from webpage_video_hover_stream_backend import (
    can_stream_video_tile_hover,
    extract_video_tile_hover_stream_frames_pil,
    video_tile_hover_stream_cache_key,
)
from webpage_video_live_preview_backend import (
    can_open_browser_video_live_preview,
    open_browser_video_live_preview,
)
from webpage_video_variant_grouping import (
    group_video_rendition_items,
    video_variant_quality_label,
    video_variant_quality_option_labels,
    video_variant_url_suffix,
)
from source_twitter_compact_row import (
    TWITTER_COMPACT_MODES,
    TWITTER_SCREENSHOT_MODES,
    TWITTER_SCREENSHOT_MODE_VALUES,
    build_twitter_compact_row_state,
)
from youtube_gui_media_queue import (
    YOUTUBE_GUI_MEDIA_QUEUE_STATUS_READY,
    YOUTUBE_GUI_QUALITY_PRESETS,
    YouTubeGuiMediaPreferences,
    default_youtube_gui_media_preferences,
    normalized_youtube_quality_labels,
    queue_youtube_gui_source_row_selection,
    youtube_available_quality_labels_from_discovery,
    youtube_title_from_discovery,
)
from youtube_media_download_backend import discover_youtube_media_with_ytdlp


SESSION_FILE_KIND_TRANSCRIPT = "transcript"
SESSION_FILE_KIND_AUDIO = "audio"
SESSION_FILE_KIND_VIDEO = "video"
SESSION_FILE_KIND_MEDIA = "media"
SESSION_FILE_KIND_OTHER = "other"

TRANSCRIPT_FILE_EXTENSIONS = {".srt", ".vtt", ".txt"}
AUDIO_FILE_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
VIDEO_FILE_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm"}
IMAGE_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


@dataclass(frozen=True)
class SessionFileEntry:
    """A local file added to the current GUI session only."""

    path: str
    normalized_path: str
    display_name: str
    file_kind: str


@dataclass(frozen=True)
class SessionFileIntakeResult:
    """Summary of a local FILES intake operation."""

    added_paths: Tuple[str, ...] = ()
    duplicate_paths: Tuple[str, ...] = ()
    unsupported_paths: Tuple[str, ...] = ()
    rejected_paths: Tuple[str, ...] = ()
    selected_path: str = ""


class TranscriptPositionScrubber(tk.Canvas):
    """Lightweight absolute-position scrubber for smooth playback updates."""

    def __init__(self, master, *, command=None, height: int = 16, **kwargs) -> None:
        super().__init__(
            master,
            height=height,
            bg=kwargs.pop("bg", COLORS["bg_input"]),
            highlightthickness=0,
            bd=0,
            takefocus=True,
            **kwargs,
        )
        self._command = command
        self._value = 0.0
        self._render_x: Optional[float] = None
        self._dragging = False
        self._track_id = None
        self._fill_id = None
        self._knob_id = None
        self.bind("<Configure>", lambda _event: self._redraw(immediate=True), add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<B1-Motion>", self._on_drag, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<Left>", lambda _event: self._keyboard_step(-1.0), add="+")
        self.bind("<Right>", lambda _event: self._keyboard_step(1.0), add="+")

    def get(self) -> float:
        return self._value

    def set(self, value: object) -> None:
        try:
            self._value = max(0.0, min(100.0, float(value)))
        except Exception:
            self._value = 0.0
        self._redraw(immediate=False)

    def set_immediate(self, value: object) -> None:
        try:
            self._value = max(0.0, min(100.0, float(value)))
        except Exception:
            self._value = 0.0
        self._redraw(immediate=True)

    def _track_bounds(self) -> Tuple[float, float, float]:
        width = max(1.0, float(self.winfo_width() or 1))
        y = max(8.0, float(self.winfo_height() or 16) / 2.0)
        return 8.0, max(8.0, width - 8.0), y

    def _desired_x(self) -> float:
        left, right, _y = self._track_bounds()
        return left + (right - left) * (self._value / 100.0)

    def _redraw(self, *, immediate: bool) -> None:
        left, right, y = self._track_bounds()
        desired_x = self._desired_x()
        if self._render_x is None or immediate or self._dragging:
            render_x = desired_x
        else:
            delta = desired_x - self._render_x
            render_x = (
                self._render_x + (1.0 if delta > 0 else -1.0)
                if abs(delta) > 1.0
                else desired_x
            )
        self._render_x = render_x
        if self._track_id is None:
            self._track_id = self.create_line(
                left,
                y,
                right,
                y,
                fill=COLORS["border"],
                width=4,
                capstyle="round",
            )
            self._fill_id = self.create_line(
                left,
                y,
                render_x,
                y,
                fill=COLORS["accent"],
                width=4,
                capstyle="round",
            )
            self._knob_id = self.create_oval(
                render_x - 6,
                y - 6,
                render_x + 6,
                y + 6,
                fill=COLORS["accent"],
                outline=COLORS["text_primary"],
                width=1,
            )
        else:
            self.coords(self._track_id, left, y, right, y)
            self.coords(self._fill_id, left, y, render_x, y)
            self.coords(self._knob_id, render_x - 6, y - 6, render_x + 6, y + 6)

    def _set_from_x(self, x: object, *, notify: bool = True) -> None:
        left, right, _y = self._track_bounds()
        try:
            x_value = max(left, min(right, float(x)))
        except Exception:
            x_value = left
        span = max(1.0, right - left)
        self._value = (x_value - left) / span * 100.0
        self._redraw(immediate=True)
        if notify and callable(self._command):
            self._command(self._value)

    def _on_press(self, event) -> None:
        self._dragging = True
        self.focus_set()
        self._set_from_x(getattr(event, "x", 0), notify=False)

    def _on_drag(self, event) -> None:
        self._set_from_x(getattr(event, "x", 0))

    def _on_release(self, event) -> None:
        self._set_from_x(getattr(event, "x", 0))
        self._dragging = False

    def _keyboard_step(self, delta: float) -> str:
        self.set_immediate(self._value + float(delta))
        if callable(self._command):
            self._command(self._value)
        return "break"


class _NoOpSidebarControl:
    """Compatibility proxy for removed persistent sidebar controls."""

    def configure(self, **_kwargs: object) -> None:
        return

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress Google API client cache warning
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def transcribe_media_file(*args: Any, **kwargs: Any) -> Any:
    from asr_tools import transcribe_media_file as _transcribe_media_file

    return _transcribe_media_file(*args, **kwargs)


def build_whispercpp_prompt(*args: Any, **kwargs: Any) -> Any:
    from asr_whispercpp import build_whispercpp_prompt as _build_whispercpp_prompt

    return _build_whispercpp_prompt(*args, **kwargs)


def is_whispercpp_vulkan_available(*args: Any, **kwargs: Any) -> Any:
    from asr_whispercpp import (
        is_whispercpp_vulkan_available as _is_whispercpp_vulkan_available,
    )

    return _is_whispercpp_vulkan_available(*args, **kwargs)


def ensure_asr_calibration_sample(*args: Any, **kwargs: Any) -> Any:
    from asr_calibration import ensure_asr_calibration_sample as _ensure_sample

    return _ensure_sample(*args, **kwargs)


def get_asr_calibration_reference_segments(*args: Any, **kwargs: Any) -> Any:
    from asr_calibration import (
        get_asr_calibration_reference_segments as _get_reference_segments,
    )

    return _get_reference_segments(*args, **kwargs)


def load_asr_defaults(*args: Any, **kwargs: Any) -> Any:
    from asr_defaults import load_asr_defaults as _load_asr_defaults

    return _load_asr_defaults(*args, **kwargs)


def save_asr_defaults(*args: Any, **kwargs: Any) -> Any:
    from asr_defaults import save_asr_defaults as _save_asr_defaults

    return _save_asr_defaults(*args, **kwargs)


def ask_asr_settings(*args: Any, **kwargs: Any) -> Any:
    from asr_settings_dialog import ask_asr_settings as _ask_asr_settings

    return _ask_asr_settings(*args, **kwargs)


def resolve_asr_topic_glossary(*args: Any, **kwargs: Any) -> Any:
    from asr_topic_resolver import (
        resolve_asr_topic_glossary as _resolve_asr_topic_glossary,
    )

    return _resolve_asr_topic_glossary(*args, **kwargs)


ASR_ACTION_BUTTON_SPEC: Dict[str, Any] = {
    "wrap_width": 150,
    "wrap_height": 36,
    "wrap_pack_padx": 3,
    "wrap_pack_pady": 3,
    "button_width": 150,
    "button_height": 32,
    "button_font_size": 11,
    "button_font_weight": "bold",
    "button_corner_radius": 8,
    "button_anchor": "w",
    "button_fg_color_key": "accent",
    "button_hover_color_key": "accent_hover",
    "button_text_color_key": "text_primary",
    "cog_x": 121,
    "cog_y": 4,
    "cog_width": 24,
    "cog_height": 24,
    "cog_normal_asset": "asr_cog_normal.png",
    "cog_hover_asset": "asr_cog_hover.png",
    "fallback_cog_text": "⚙",
    "fallback_cog_font": ("Segoe UI Symbol", 13, "bold"),
    "fallback_cog_normal_fg": "#5f5f5f",
    "fallback_cog_hover_fg": "#2f2f2f",
}

ONLINE_ASR_BUTTON_TEXT = "🎙 Online ASR"
LOCAL_ASR_BUTTON_TEXT = "🎙 Local ASR"
ONLINE_ASR_PROVIDERS_WINDOW_TITLE = "Online ASR Providers"
ONLINE_ASR_DEFAULT_PROVIDER_ID = ELEVENLABS_SCRIBE_PROVIDER_ID


@dataclass(frozen=True)
class OnlineASRProviderOption:
    provider_id: str
    display_name: str
    model_id: str
    credential_id: str
    credential_entry_id: str


from online_asr_execution_gate import (
    build_online_asr_execution_gate_plan,
    render_online_asr_execution_gate_summary_text,
)

ONLINE_ASR_PROVIDER_OPTIONS: Tuple[OnlineASRProviderOption, ...] = (
    OnlineASRProviderOption(
        provider_id=ELEVENLABS_SCRIBE_PROVIDER_ID,
        display_name="ElevenLabs Scribe v2",
        model_id=ELEVENLABS_SCRIBE_MODEL_ID,
        credential_id=ELEVENLABS_SCRIBE_CREDENTIAL_ID,
        credential_entry_id="asr:elevenlabs_scribe",
    ),
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FetchState:
    """State for the fetch operation."""
    is_fetching: bool = False
    cancel_event: Optional[threading.Event] = None

    def __post_init__(self):
        if self.cancel_event is None:
            self.cancel_event = threading.Event()

    def start(self) -> None:
        """Start a new fetch operation."""
        self.is_fetching = True
        self.cancel_event.clear()

    def stop(self) -> None:
        """Stop the fetch operation."""
        self.is_fetching = False
        self.cancel_event.clear()

    def request_cancel(self) -> None:
        """Request cancellation of the fetch operation."""
        self.cancel_event.set()

    @property
    def cancel_requested(self) -> bool:
        """Check if cancellation was requested."""
        return self.cancel_event.is_set()


def is_export_allowed(fetch_state: FetchState, exportable_count: int) -> bool:
    """Return whether an export can start for the current fetch/data state."""
    if fetch_state.is_fetching or fetch_state.cancel_requested:
        return False
    return exportable_count > 0


# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class App(ctk.CTk):
    """Main application window."""

    SIDEBAR_WIDTH = 360

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title(APP_NAME)
        self.geometry(f"{WINDOW_DEFAULT_WIDTH}x{WINDOW_DEFAULT_HEIGHT}")
        self.minsize(max(WINDOW_MIN_WIDTH, 1120), max(WINDOW_MIN_HEIGHT, 760))
        self.configure(fg_color=COLORS["bg_dark"])

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Grid configuration - header on top, sidebar + main content below
        self.grid_columnconfigure(0, weight=0)  # Sidebar - fixed width
        self.grid_columnconfigure(1, weight=1)  # Main content - expandable
        self.grid_rowconfigure(0, weight=0)  # Header - fixed height
        self.grid_rowconfigure(1, weight=1)  # Content area - expandable

        # State
        self.settings_manager = SettingsManager()
        self.extractor: Optional[YouTubeCommentExtractor] = None
        self.fetch_state = FetchState()

        # Data storage (protected by lock for thread safety)
        self._data_lock = threading.Lock()
        self.all_metadata: List[Dict[str, Any]] = []
        self.all_comments: List[Dict[str, Any]] = []
        self.all_spam: List[Dict[str, Any]] = []
        self.attached_screenshots: List[str] = []
        self.transcript_segments: List[TranscriptSegment] = []
        self.transcript_undo_stack: List[List[TranscriptSegment]] = []
        self.transcript_redo_stack: List[List[TranscriptSegment]] = []
        self.transcript_history_limit: int = 75
        self.transcript_has_unsaved_edits: bool = False
        self.transcript_text_edit_phase_segment_index: Optional[int] = None
        self.transcript_glossary_terms: List[str] = [
            "Kingman",
            "ZoneX",
            "Shadowsmith",
            "Nicolas Cage",
            "Freckelston",
            "Caltheris",
            "Nyxara",
        ]
        self.transcript_qa_known_confusions: List[Tuple[str, str]] = [
            ("Calpheon", "Caltheris"),
            ("Cal Ferris", "Caltheris"),
            ("Calferis", "Caltheris"),
            ("Calfaris", "Caltheris"),
            ("Calfare", "Caltheris"),
            ("Kalfirisk", "Caltheris"),
            ("Shousemith", "Shadowsmith"),
            ("Shadomsmith", "Shadowsmith"),
            ("Shadow Smith", "Shadowsmith"),
            ("Nicholas Cage", "Nicolas Cage"),
        ]
        self.transcript_qa_issues: List[Dict[str, Any]] = []
        self.transcript_qa_after_id = None
        self.last_transcript_source: Optional[str] = None
        self.last_youtube_video_info: Optional[Dict[str, Any]] = None
        self.last_asr_metadata: Optional[Dict[str, Any]] = None
        self.linked_transcript_media_path: Optional[str] = None
        self.session_files: List[SessionFileEntry] = []
        self.selected_session_file_path: str = ""
        self.active_media_file_path: str = ""
        self.active_transcript_file_path: str = ""
        self.file_drag_drop_ready: bool = False
        self.file_drag_drop_status: str = "not_initialized"
        self.transcript_waveform_peaks: List[float] = []
        self.transcript_waveform_source_path: Optional[str] = None
        self.last_package_dir: Optional[str] = None
        self.last_asr_topic_glossary: Optional[Dict[str, Any]] = None
        self.access_keys_window: Optional[AccessKeysWindow] = None
        self.online_asr_provider_window = None
        self.online_asr_provider_id: str = ONLINE_ASR_DEFAULT_PROVIDER_ID
        self.online_asr_provider_selection_status: str = ""
        self.access_keys_added_provider_ids: tuple[str, ...] = ()
        self.access_keys_validation_states: dict[str, dict[str, str]] = {}
        self.source_resource_rows: List[SourceResourceRowState] = []
        self.selected_discussion_source_id: str = ""
        self.source_archive_auto_check_enabled: bool = True
        self.source_screenshot_preferences: dict[str, dict[str, bool]] = {}
        self._main_pointer_wheel_bound: bool = False
        self.source_resource_selections: dict[str, tuple[str, ...]] = {}
        self.webpage_image_session_output_root: Optional[Path] = None
        self.webpage_image_session_download_cache: dict[tuple[str, str], str] = {}
        self.internal_browser_image_discovery_service_started: bool = False
        self.youtube_source_row_quality_vars: dict[str, ctk.StringVar] = {}
        self.youtube_source_row_quality_enabled_vars: dict[str, ctk.BooleanVar] = {}
        self.youtube_source_row_preferences: dict[str, YouTubeGuiMediaPreferences] = {}
        self.youtube_source_row_available_quality_labels: dict[str, tuple[str, ...]] = {}
        self.youtube_source_row_discovery_status: dict[str, str] = {}
        self.youtube_source_row_discovery_metadata: dict[str, dict[str, str]] = {}
        self.profile_media_runtime_state_path: Optional[Path] = None
        self.profile_media_sidebar_mode: str = self._load_profile_media_sidebar_mode_for_startup()
        self.profile_media_database_mode_var = None
        self.profile_media_database_panel_state = None
        self.profile_media_database_root = ""
        self.profile_media_database_batch_json_files: tuple[str, ...] = ()
        self.profile_media_database_workbench_payload: dict[str, object] | None = None
        self.profile_media_database_batch_import_result: dict[str, object] | None = None
        self.profile_media_database_materialize_result: dict[str, object] | None = None
        self.profile_media_database_panel_metric_labels: dict[str, object] = {}
        self.profile_media_database_panel_review_labels: dict[str, object] = {}
        self.profile_media_database_gui_state_path = None
        self.profile_media_database_gui_state_payload: dict[str, object] | None = None

        self.transcript_show_speakers_var = ctk.BooleanVar(value=True)
        self.transcript_show_timestamps_var = ctk.BooleanVar(value=True)

        # Custom filter patterns
        self._blacklist_patterns: str = ""
        self._whitelist_patterns: str = ""

        # Thread reference for clean shutdown
        self._fetch_thread_ref: Optional[threading.Thread] = None

        # Build UI
        self._initialize_file_drag_drop()
        self._create_header()
        self._create_content_paned_window()
        self._load_profile_media_database_saved_gui_state_for_startup()
        self._create_sidebar()
        self._create_main_content()
        self._bind_main_pointer_wheel_router()
        self._bind_final_file_drop_targets()
        self._log_file_drag_drop_startup_state()
        self._start_internal_browser_image_discovery_service()

        # Bind keyboard shortcuts
        self.bind("<Control-Return>", lambda e: self.start_fetching())
        self.bind("<Control-s>", lambda e: self.export_csv())
        self.bind("<Control-e>", lambda e: self.export_excel())
        self.bind("<Control-t>", lambda e: self.export_txt())
        self.bind_all("<Control-z>", self.undo_transcript_edit)
        self.bind_all("<Control-Z>", self.undo_transcript_edit)
        self.bind_all("<Control-y>", self.redo_transcript_edit)
        self.bind_all("<Control-Y>", self.redo_transcript_edit)
        self.bind_all("[", self._on_visual_sync_minus_shortcut)
        self.bind_all("]", self._on_visual_sync_plus_shortcut)
        self.bind_all("<Control-0>", self._on_visual_sync_reset_shortcut)
        self._bind_window_size_shortcuts()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Load settings
        self._load_settings()

    # =========================================================================
    # HEADER CREATION
    # =========================================================================

    @staticmethod
    def _create_play_icon() -> ctk.CTkImage:
        """Create a comment-bubble icon with a play triangle inside."""
        s = 120
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        body_top, body_bottom = 6, 88
        draw.rounded_rectangle(
            [6, body_top, s - 6, body_bottom],
            radius=20, outline="white", width=5,
        )

        tail = [(24, body_bottom - 2), (44, body_bottom - 2), (16, 110)]
        draw.polygon(tail, fill=(42, 42, 42, 255))
        draw.line([tail[0], tail[2]], fill="white", width=5)
        draw.line([tail[2], tail[1]], fill="white", width=5)

        cx, cy = s // 2, (body_top + body_bottom) // 2
        tri_h = 18
        tri_w = 16
        draw.polygon(
            [(cx - tri_w + 3, cy - tri_h), (cx - tri_w + 3, cy + tri_h), (cx + tri_w, cy)],
            fill="white",
        )

        return ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))

    def _create_header(self) -> None:
        """Create a zero-height header shell so the workspace uses the top area."""
        # The visible title/tagline consumed useful vertical space in normal
        # non-fullscreen use. Keep a shell for layout compatibility, but render
        # no visible header content. The native window title still carries the
        # app name.
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_dark"],
            corner_radius=0,
            height=0,
        )
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header_frame.grid_propagate(False)

    # =========================================================================
    # SIDEBAR CREATION
    # =========================================================================

    def _create_sidebar(self) -> None:
        """Create the left sidebar with all settings."""
        initial_sidebar_width = self._get_sidebar_width_preference()
        parent = getattr(self, "content_paned_window", self)
        self.sidebar = ctk.CTkFrame(
            parent,
            width=initial_sidebar_width,
            fg_color=COLORS["bg_card"],
            corner_radius=0
        )
        if parent is self:
            try:
                self.grid_columnconfigure(0, minsize=initial_sidebar_width)
            except Exception:
                pass
            self.sidebar.grid(row=1, column=0, sticky="nsew")
        else:
            parent.add(
                self.sidebar,
                minsize=320,
                width=initial_sidebar_width,
                stretch="never",
            )
        self.sidebar.grid_propagate(False)

        # Fixed sidebar content. Do not use a left-side scrollable wrapper: the
        # separate scrollbar consumed width and blocked the FILES pane from using
        # the dragged sidebar space. The main workspace keeps its own scrolling.
        self.sidebar_scroll = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent",
        )
        self.sidebar_scroll.pack(fill="both", expand=True, padx=0, pady=0)
        self._create_sidebar_resize_grip()

        # Global actions stay pinned in the sidebar above FILES.
        self._create_updates_section(first=True)

        # Access & Keys section owns credential management.
        self._create_access_keys_section()

        # Export/package entry point
        self._create_export_section()

        # Profile/media Database mode toggle sits directly above FILES.
        self._create_profile_media_database_mode_toggle_section()

        # Session files section
        self._create_files_section()

        # YouTube filters stay functional, but visible controls live in each
        # YouTube source row settings dialog, not in the main sidebar.
        self._create_hidden_youtube_filter_settings_state()

        # Custom filters now live inside the combined YouTube settings window.

        # Version at bottom
        self._create_sidebar_footer()

    def _create_content_paned_window(self) -> None:
        """Create the native resizable sidebar/workspace container."""
        self.content_paned_window = tk.PanedWindow(
            self,
            orient=tk.HORIZONTAL,
            sashwidth=6,
            bd=0,
            showhandle=False,
            bg=COLORS["bg_dark"],
            opaqueresize=False,
        )
        self.content_paned_window.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.content_paned_window.bind(
            "<ButtonRelease-1>",
            self._on_sidebar_paned_sash_release,
            add="+",
        )

    def _create_sidebar_resize_grip(self) -> None:
        try:
            self.sidebar_resize_grip = tk.Frame(
                self.sidebar,
                width=18,
                cursor="sb_h_double_arrow",
                bg=COLORS["bg_card"],
                bd=0,
                highlightthickness=0,
            )
            self.sidebar_resize_grip.place(relx=1.0, x=-18, y=0, relheight=1.0, width=18)
            self.sidebar_resize_grip.bind("<ButtonPress-1>", self._on_sidebar_resize_grip_press, add="+")
            self.sidebar_resize_grip.bind("<B1-Motion>", self._on_sidebar_resize_grip_drag, add="+")
            self.sidebar_resize_grip.bind("<ButtonRelease-1>", self._on_sidebar_resize_grip_release, add="+")
        except Exception:
            logger.debug("Could not create sidebar resize grip.", exc_info=True)

    def _on_sidebar_resize_grip_press(self, event: object) -> None:
        try:
            self._sidebar_resize_drag_start_x = int(event.x_root)
            self._sidebar_resize_drag_start_width = int(getattr(self, "sidebar_width", self.SIDEBAR_WIDTH))
        except Exception:
            self._sidebar_resize_drag_start_x = 0
            self._sidebar_resize_drag_start_width = int(getattr(self, "sidebar_width", self.SIDEBAR_WIDTH))

    def _on_sidebar_resize_grip_drag(self, event: object) -> None:
        try:
            start_x = int(getattr(self, "_sidebar_resize_drag_start_x", event.x_root))
            start_width = int(getattr(self, "_sidebar_resize_drag_start_width", self.SIDEBAR_WIDTH))
            delta = int(event.x_root) - start_x
            width = max(320, min(1280, start_width + delta))
            self.sidebar_width = width
            try:
                self.content_paned_window.paneconfigure(self.sidebar, width=width)
            except Exception:
                pass
            try:
                self.content_paned_window.sash_place(0, width, 0)
            except Exception:
                pass
            try:
                self.sidebar.configure(width=width)
            except Exception:
                pass
            self._refresh_session_files_list()
        except Exception:
            logger.debug("Could not drag sidebar resize grip.", exc_info=True)

    def _on_sidebar_resize_grip_release(self, event: object | None = None) -> None:
        self._on_sidebar_paned_sash_release(event)

    def _on_sidebar_paned_sash_release(self, _event=None) -> None:
        try:
            width = int(self.sidebar.winfo_width())
        except Exception:
            width = int(getattr(self, "sidebar_width", self.SIDEBAR_WIDTH))
        # Let FILES use the available fullscreen width, while the right pane
        # keeps a minimum usable workspace from the PanedWindow child minsize.
        self.sidebar_width = max(320, min(1280, width))
        self._persist_sidebar_width_preference(self.sidebar_width)

    def _get_sidebar_width_preference(self) -> int:
        width = getattr(self, "sidebar_width", self.SIDEBAR_WIDTH)
        try:
            settings = self.settings_manager.load_preferences_only()
            width = getattr(settings, "sidebar_width", width)
        except Exception:
            pass
        try:
            width = int(width)
        except Exception:
            width = self.SIDEBAR_WIDTH
        return max(320, min(1280, width))

    def _persist_sidebar_width_preference(self, width: int) -> None:
        try:
            settings = self.settings_manager.load_preferences_only()
            settings.api_key = ""
            settings.sidebar_width = max(320, min(1280, int(width)))
            self.settings_manager.save(settings)
            self.sidebar_width = settings.sidebar_width
        except Exception:
            logger.error("Failed to persist sidebar width safely.")

    def _create_section_label(self, parent: ctk.CTkFrame, text: str, first: bool = False) -> None:
        """Create a section label with divider."""
        if not first:
            divider = ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1)
            divider.pack(fill="x", padx=16, pady=(8, 6))

        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        label.pack(anchor="w", padx=20, pady=(15 if first else 0, 10))

    def _initialize_file_drag_drop(self) -> bool:
        """Initialize TkDND against the existing CustomTkinter root exactly once."""
        if getattr(self, "file_drag_drop_status", "") not in {"", "not_initialized"}:
            return bool(getattr(self, "file_drag_drop_ready", False))
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
            TkinterDnD.require(self)
            self._file_drag_drop_type = DND_FILES
            self.file_drag_drop_ready = True
            self.file_drag_drop_status = "ready"
        except Exception as error:
            self._file_drag_drop_type = ""
            self.file_drag_drop_ready = False
            self.file_drag_drop_status = f"unavailable: {error}"
        return self.file_drag_drop_ready

    def _log_file_drag_drop_startup_state(self) -> None:
        if getattr(self, "file_drag_drop_ready", False):
            self.log_message("File drag-and-drop: Ready", "success")
            return
        reason = getattr(self, "file_drag_drop_status", "unavailable")
        self.log_message(f"File drag-and-drop: {reason}", "warning")

    def _create_api_section(self) -> None:
        """Create API key input section in sidebar."""
        self._create_section_label(self.sidebar_scroll, "API KEY", first=True)

        api_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        api_frame.pack(fill="x", padx=20)

        # API key entry. It remains masked; migration/clear actions are explicit.
        entry_frame = ctk.CTkFrame(api_frame, fg_color="transparent")
        entry_frame.pack(fill="x")
        entry_frame.grid_columnconfigure(0, weight=1)

        self.api_key_entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="Enter API key",
            height=36,
            font=ctk.CTkFont(family="Cascadia Mono", size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6,
            show="*"
        )
        self.api_key_entry.grid(row=0, column=0, sticky="ew")

        # Storage info is refreshed explicitly after user credential actions
        # or when Access & Keys opens. Startup avoids probing keyring merely
        # to draw the sidebar.
        info_text = "Credential status not refreshed"
        self.storage_label = ctk.CTkLabel(
            api_frame,
            text=info_text,
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        self.storage_label.pack(anchor="w", pady=(4, 0))

        api_actions = ctk.CTkFrame(api_frame, fg_color="transparent")
        api_actions.pack(fill="x", pady=(8, 0))
        api_actions.grid_columnconfigure((0, 1), weight=1)

        self.save_api_key_button = ctk.CTkButton(
            api_actions,
            text="Save secure",
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._save_youtube_api_key_secure,
        )
        self.save_api_key_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.clear_api_key_button = ctk.CTkButton(
            api_actions,
            text="Clear credential",
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._clear_youtube_api_key,
        )
        self.clear_api_key_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.migrate_api_key_button = ctk.CTkButton(
            api_frame,
            text="Migrate legacy key to secure storage",
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self._migrate_youtube_api_key,
        )
        self.migrate_api_key_button.pack(fill="x", pady=(6, 0))
        self.access_keys_button = ctk.CTkButton(
            api_frame,
            text=ACCESS_KEYS_BUTTON_TEXT,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self.open_access_keys_window,
        )
        self.access_keys_button.pack(fill="x", pady=(10, 0))

    def _create_access_keys_section(self, first: bool = False) -> None:
        """Create the Access & Keys entry point without duplicating API-key fields."""
        keys_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        keys_frame.configure(width=286, height=30)
        keys_frame.pack(anchor="w", padx=14, pady=(8 if first else 0, 4))
        keys_frame.pack_propagate(False)
        self.access_keys_button = ctk.CTkButton(
            keys_frame,
            text="KEYS/ACCOUNTS",
            width=286,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            command=self.open_access_keys_window,
        )
        self.access_keys_button.pack(anchor="w")

    def _create_updates_section(self, first: bool = False) -> None:
        """Create the Updates sidebar entry point."""
        if not first:
            separator = ctk.CTkFrame(self.sidebar_scroll, height=1, fg_color=COLORS["border"])
            separator.pack(fill="x", padx=20, pady=(15, 8))
        updates_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        updates_frame.configure(width=286, height=30)
        updates_frame.pack(anchor="w", padx=14, pady=(8 if first else 0, 4))
        updates_frame.pack_propagate(False)
        self.update_button = ctk.CTkButton(
            updates_frame,
            text="UPDATES",
            command=self.check_for_updates_clicked,
            width=286,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.update_button.pack(anchor="w")

    def _create_export_section(self) -> None:
        """Create the consolidated export/package sidebar entry point."""
        export_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        export_frame.configure(width=286, height=30)
        export_frame.pack(anchor="w", padx=14, pady=(0, 6))
        export_frame.pack_propagate(False)

        self.evidence_button = ctk.CTkButton(
            export_frame,
            text="EXPORT",
            command=self.open_files_export_dialog,
            width=286,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6,
            state="disabled",
        )
        self.evidence_button.pack(anchor="w")
        self.sidebar_evidence_button = self.evidence_button
        self.sidebar_open_last_package_button = _NoOpSidebarControl()
        self.sidebar_screenshot_button = _NoOpSidebarControl()
        self.sidebar_clear_screenshots_button = _NoOpSidebarControl()

    def open_access_keys_window(self) -> AccessKeysWindow:
        """Open or focus the read-only Access & Keys status window."""
        existing = getattr(self, "access_keys_window", None)
        credential_store = SystemKeyringCredentialStore()

        def credential_status_provider():
            return build_runtime_credential_statuses(
                settings_manager=self.settings_manager,
                youtube_configured=bool(
                    getattr(getattr(self, "api_key_entry", None), "get", lambda: "")().strip()
                ),
                credential_store=credential_store,
            )

        self.access_keys_window = open_or_focus_access_keys_window(
            existing,
            lambda: AccessKeysWindow(
                self,
                credential_store=credential_store,
                credential_status_provider=credential_status_provider,
                validation_records=self._get_access_keys_validation_records(),
                on_validation_records_change=self._set_access_keys_validation_records,
                validate_provider_key=self._validate_cloud_asr_provider_key,
                youtube_migration_action=self._migrate_youtube_api_key,
                browser_opener=webbrowser.open,
                added_entry_ids=self._get_access_keys_added_provider_ids(),
                on_added_entry_ids_change=self._set_access_keys_added_provider_ids,
                on_close=self._on_access_keys_window_closed,
            ),
        )
        return self.access_keys_window

    def _on_access_keys_window_closed(self) -> None:
        """Release the closed Access & Keys window reference."""
        self.access_keys_window = None

    def _load_profile_media_sidebar_mode_for_startup(self) -> str:
        """Load the persisted FILES/DATABASE sidebar mode without running Database work."""
        try:
            from profile_media_database_runtime import (
                default_profile_media_runtime_state_path,
                load_profile_media_runtime_state,
            )

            self.profile_media_runtime_state_path = default_profile_media_runtime_state_path()
            return load_profile_media_runtime_state(self.profile_media_runtime_state_path).sidebar_mode
        except Exception:
            logger.debug("Could not load profile/media Database runtime mode; defaulting to FILES.", exc_info=True)
            return "FILES"

    def _save_profile_media_sidebar_mode_for_runtime(self, mode: object) -> None:
        """Persist the mode-only Database toggle without scanning or moving case folders."""
        try:
            from profile_media_database_runtime import (
                build_profile_media_runtime_state,
                default_profile_media_runtime_state_path,
                save_profile_media_runtime_state,
            )

            state_path = getattr(self, "profile_media_runtime_state_path", None)
            if state_path is None:
                state_path = default_profile_media_runtime_state_path()
                self.profile_media_runtime_state_path = state_path
            save_profile_media_runtime_state(build_profile_media_runtime_state(mode), state_path)
        except Exception:
            logger.debug("Could not save profile/media Database runtime mode.", exc_info=True)

    def _coerce_profile_media_sidebar_mode(self, value: object | None = None) -> str:
        """Return the FILES/DATABASE sidebar mode using the V75H view-model enum."""
        from profile_media_database_view_model import coerce_profile_media_view_mode

        raw_value = getattr(self, "profile_media_sidebar_mode", "FILES") if value is None else value
        return coerce_profile_media_view_mode(raw_value).value

    def _set_profile_media_sidebar_mode(self, mode: object, *, update_widget: bool = True, refresh_visual: bool = True) -> str:
        """Set the sidebar mode without scanning, creating, moving, or renaming folders."""
        coerced = self._coerce_profile_media_sidebar_mode(mode)
        self.profile_media_sidebar_mode = coerced
        if update_widget:
            mode_var = getattr(self, "profile_media_database_mode_var", None)
            if mode_var is not None:
                try:
                    mode_var.set(coerced == "DATABASE")
                except Exception:
                    logger.debug("Could not update profile/media Database toggle variable.", exc_info=True)
        if refresh_visual:
            self._refresh_profile_media_database_mode_switch_visual()
        self._save_profile_media_sidebar_mode_for_runtime(coerced)
        self._refresh_profile_media_database_workbench_panel()
        return coerced

    def _profile_media_database_toggle_text(self, mode: object | None = None) -> str:
        """Fallback text for non-canvas tests and environments."""
        if self._coerce_profile_media_sidebar_mode(mode) == "DATABASE":
            return "ON"
        return "OFF"

    def _draw_profile_media_database_toggle_canvas(
        self,
        canvas: object,
        *,
        mode: object | None = None,
        knob_progress: float | None = None,
    ) -> None:
        """Draw the requested red/green animated pill switch on a plain Canvas."""
        try:
            canvas.delete("all")
        except Exception:
            return
        resolved_mode = self._coerce_profile_media_sidebar_mode(mode)
        is_database = resolved_mode == "DATABASE"
        width = 108
        height = 20
        pad = 2
        knob = 14
        radius = (height - pad * 2) / 2
        track = "#72c943" if is_database else "#e84b6a"
        border = "#4d9b29" if is_database else "#b92d4d"
        knob_fill = "#eef2ef"
        progress = 1.0 if is_database else 0.0
        if knob_progress is not None:
            progress = max(0.0, min(1.0, float(knob_progress)))
        left_center = pad + knob / 2
        right_center = width - pad - knob / 2
        center_y = height / 2
        knob_center = left_center + (right_center - left_center) * progress
        x1, y1, x2, y2 = pad, pad, width - pad, height - pad
        # Rounded track from rectangles + end ovals keeps this dependency-free.
        canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=track, outline=border, width=2)
        canvas.create_oval(x1, y1, x1 + radius * 2, y2, fill=track, outline=border, width=2)
        canvas.create_oval(x2 - radius * 2, y1, x2, y2, fill=track, outline=border, width=2)
        # Keep glyphs/text fully outside the knob travel zone: ON text lives
        # on the left while the ON knob is on the right; OFF text lives on the
        # right while the OFF knob is on the left.
        if is_database:
            canvas.create_text(15, center_y, text="✓", fill="#ffffff", font=("Segoe UI", 8, "bold"))
            canvas.create_text(42, center_y, text="ON", fill="#ffffff", font=("Segoe UI", 8, "bold"))
        else:
            canvas.create_text(60, center_y, text="OFF", fill="#ffffff", font=("Segoe UI", 8, "bold"))
            canvas.create_text(90, center_y, text="✕", fill="#ffffff", font=("Segoe UI", 8, "bold"))
        canvas.create_oval(
            knob_center - knob / 2,
            center_y - knob / 2,
            knob_center + knob / 2,
            center_y + knob / 2,
            fill=knob_fill,
            outline="#cfd6cf",
            width=2,
        )

    def _refresh_profile_media_database_mode_switch_visual(self) -> None:
        """Refresh the red/green animated Database pill and sidebar counters."""
        switch = getattr(self, "profile_media_database_mode_switch", None)
        mode = self._coerce_profile_media_sidebar_mode()
        is_database = mode == "DATABASE"
        if switch is not None:
            if isinstance(switch, tk.Canvas):
                self._draw_profile_media_database_toggle_canvas(switch, mode=mode)
            else:
                try:
                    switch.configure(
                        text=self._profile_media_database_toggle_text(mode),
                        fg_color="#7ac943" if is_database else "#e84b6a",
                        hover_color="#8ed957" if is_database else "#f05d7a",
                        border_color="#4d9b29" if is_database else "#b92d4d",
                        text_color="#ffffff",
                    )
                except Exception:
                    logger.debug("Could not refresh profile/media Database toggle visual.", exc_info=True)
        self._refresh_profile_media_home_sidebar_buttons()
        summary_frame = getattr(self, "profile_media_database_sidebar_summary_frame", None)
        if summary_frame is not None:
            try:
                if is_database:
                    summary_frame.grid(row=2, column=0, sticky="w", pady=(5, 0))
                else:
                    summary_frame.grid_remove()
            except Exception:
                logger.debug("Could not refresh Database role counter visibility.", exc_info=True)

    def _animate_profile_media_database_mode_switch_visual(
        self,
        *,
        from_mode: object | None = None,
        to_mode: object | None = None,
    ) -> None:
        """Animate the Database toggle knob without the final-state jump."""
        switch = getattr(self, "profile_media_database_mode_switch", None)
        if not isinstance(switch, tk.Canvas):
            self._refresh_profile_media_database_mode_switch_visual()
            return
        start_mode = self._coerce_profile_media_sidebar_mode(from_mode)
        end_mode = self._coerce_profile_media_sidebar_mode(to_mode)
        start_progress = 1.0 if start_mode == "DATABASE" else 0.0
        end_progress = 1.0 if end_mode == "DATABASE" else 0.0
        if start_progress == end_progress:
            self._refresh_profile_media_database_mode_switch_visual()
            return

        frame_count = 18

        def eased_step(index: int) -> float:
            t = max(0.0, min(1.0, index / frame_count))
            # Smoothstep avoids the visible snap/jump at the start and end.
            eased = t * t * (3.0 - 2.0 * t)
            return start_progress + (end_progress - start_progress) * eased

        def draw_step(index: int = 1) -> None:
            if index > frame_count:
                self._refresh_profile_media_database_mode_switch_visual()
                return
            self._draw_profile_media_database_toggle_canvas(
                switch,
                mode=end_mode,
                knob_progress=eased_step(index),
            )
            try:
                self.after(10, lambda: draw_step(index + 1))
            except Exception:
                self._refresh_profile_media_database_mode_switch_visual()

        draw_step()

    def _on_profile_media_database_mode_toggled(self) -> None:
        """Handle the left-sidebar Database On/Off toggle above FILES."""
        current_mode = self._coerce_profile_media_sidebar_mode()
        requested_mode = "FILES" if current_mode == "DATABASE" else "DATABASE"
        mode = self._set_profile_media_sidebar_mode(requested_mode, update_widget=True, refresh_visual=False)
        summary_frame = getattr(self, "profile_media_database_sidebar_summary_frame", None)
        if summary_frame is not None:
            try:
                if mode == "DATABASE":
                    summary_frame.grid(row=2, column=0, sticky="w", pady=(5, 0))
                else:
                    summary_frame.grid_remove()
            except Exception:
                logger.debug("Could not update Database summary visibility before animation.", exc_info=True)
        self._animate_profile_media_database_mode_switch_visual(from_mode=current_mode, to_mode=mode)
        try:
            state_text = "on" if mode == "DATABASE" else "off"
            self.log_message(
                f"Profile/media Database mode: {state_text}. No folder scan, move, rename, or classification was performed.",
                "info",
            )
        except Exception:
            logger.debug("Could not log profile/media Database mode toggle.", exc_info=True)

    def _profile_media_home_loaded(self) -> bool:
        """Return whether a HOME/import selection is currently loaded."""
        return bool(
            getattr(self, "profile_media_database_root", "")
            or getattr(self, "profile_media_database_batch_json_files", ())
            or getattr(self, "profile_media_database_workbench_payload", None)
        )

    def _refresh_profile_media_home_sidebar_buttons(self) -> None:
        """Keep sidebar HOME buttons honest: show Load until a HOME selection exists."""
        loaded = self._profile_media_home_loaded()
        unload_button = getattr(self, "profile_media_database_home_unload_button", None)
        if unload_button is not None:
            try:
                unload_button.configure(text="Unload" if loaded else "Load")
            except Exception:
                logger.debug("Could not refresh HOME Load/Unload button text.", exc_info=True)

    def _profile_media_database_home_load_or_unload_clicked(self) -> None:
        """Load HOME/import state when empty; unload only after something is loaded."""
        if self._profile_media_home_loaded():
            self._unload_profile_media_database_home_selection()
        else:
            self._import_profile_media_database_home_selection()

    def _load_profile_media_role_icons(self) -> dict[str, object]:
        """Load local Profile/Media role icons without external fonts or web assets."""
        cached = getattr(self, "profile_media_role_icon_images", None)
        if isinstance(cached, dict):
            return cached
        self.profile_media_role_icon_images = {}
        asset_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "profile_media", "source_roles")
        filenames = {
            "primary_sources": "icons8-writer-male-32.png",
            "secondary_sources": "icons8-user-account-32.png",
            "tertiary_sources": "icons8-people-32.png",
            "persons": "icons8-contacts-32.png",
        }
        for key, filename in filenames.items():
            path = os.path.join(asset_base, filename)
            if not os.path.exists(path):
                continue
            try:
                image = Image.open(path).convert("RGBA")
                self.profile_media_role_icon_images[key] = ctk.CTkImage(
                    light_image=image,
                    dark_image=image,
                    size=(16, 16),
                )
            except Exception:
                logger.debug("Could not load Profile/Media role icon %s.", filename, exc_info=True)
        return self.profile_media_role_icon_images

    def _profile_media_sidebar_metric_text(self, key: str, label: str, value: object = 0) -> str:
        if key == "review_items":
            return f"Review: {value}"
        return f"{label}: {value}"

    def _create_profile_media_database_mode_toggle_section(self) -> None:
        """Create the square mode-only Database On/Off toggle directly above the FILES section."""
        initial_mode = self._coerce_profile_media_sidebar_mode()
        self.profile_media_database_mode_var = ctk.BooleanVar(value=initial_mode == "DATABASE")

        self.profile_media_mode_frame = ctk.CTkFrame(
            self.sidebar_scroll,
            fg_color="transparent",
        )
        self.profile_media_mode_frame.configure(width=286)
        self.profile_media_mode_frame.pack(anchor="w", padx=14, pady=(0, 6))
        self.profile_media_mode_frame.grid_columnconfigure(0, weight=0, minsize=286)

        database_header = ctk.CTkFrame(self.profile_media_mode_frame, fg_color="transparent")
        database_header.configure(width=286, height=24)
        database_header.grid(row=0, column=0, sticky="w")
        database_header.grid_propagate(False)
        database_header.grid_columnconfigure(0, weight=1, minsize=108)

        database_label = ctk.CTkLabel(
            database_header,
            text="DATABASE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        database_label.grid(row=0, column=0, sticky="w")

        self.profile_media_database_home_save_button = ctk.CTkButton(
            database_header,
            text="Save",
            command=self._save_profile_media_database_to_home_repository,
            width=42,
            height=22,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.profile_media_database_home_save_button.grid(row=0, column=1, sticky="e", padx=(4, 0))

        self.profile_media_database_home_unload_button = ctk.CTkButton(
            database_header,
            text="Load",
            command=self._profile_media_database_home_load_or_unload_clicked,
            width=48,
            height=22,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.profile_media_database_home_unload_button.grid(row=0, column=2, sticky="e", padx=(4, 0))

        self.profile_media_database_home_import_button = ctk.CTkButton(
            database_header,
            text="Import",
            command=self._import_profile_media_database_home_selection,
            width=50,
            height=22,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.profile_media_database_home_import_button.grid(row=0, column=3, sticky="e", padx=(4, 0))

        self.profile_media_database_toggle_frame = ctk.CTkFrame(
            self.profile_media_mode_frame,
            fg_color="transparent",
            width=110,
            height=22,
        )
        self.profile_media_database_toggle_frame.grid(row=1, column=0, sticky="w", pady=(4, 2))
        self.profile_media_database_toggle_frame.grid_propagate(False)
        self.profile_media_database_mode_switch = tk.Canvas(
            self.profile_media_database_toggle_frame,
            width=108,
            height=20,
            highlightthickness=0,
            bd=0,
            bg=COLORS["bg_card"],
            cursor="hand2",
        )
        self.profile_media_database_mode_switch.grid(row=0, column=0, sticky="w")
        self.profile_media_database_mode_switch.bind(
            "<Button-1>",
            lambda _event: self._on_profile_media_database_mode_toggled(),
            add="+",
        )

        self.profile_media_database_sidebar_summary_frame = ctk.CTkFrame(
            self.profile_media_mode_frame,
            fg_color=COLORS["bg_input"],
            corner_radius=7,
        )
        self.profile_media_database_sidebar_summary_frame.configure(width=286, height=96)
        self.profile_media_database_sidebar_summary_frame.grid(row=2, column=0, sticky="w", pady=(5, 0))
        self.profile_media_database_sidebar_summary_frame.grid_propagate(False)
        # Keep the two metric columns fixed near the left; they should not
        # drift apart when the sidebar sash is dragged wider.
        self.profile_media_database_sidebar_summary_frame.grid_columnconfigure((0, 1), weight=0)
        self.profile_media_database_sidebar_summary_labels = {}
        role_icons = self._load_profile_media_role_icons()
        summary_items = (
            ("primary_sources", "Primary"),
            ("secondary_sources", "Secondary"),
            ("tertiary_sources", "Tertiary"),
            ("persons", "Persons"),
            ("review_items", "Review"),
        )
        for index, (key, label_text) in enumerate(summary_items):
            label_kwargs = {}
            if key in role_icons:
                label_kwargs.update({"image": role_icons[key], "compound": "left"})
            summary_label = ctk.CTkLabel(
                self.profile_media_database_sidebar_summary_frame,
                text=self._profile_media_sidebar_metric_text(key, label_text, 0),
                font=ctk.CTkFont(size=10, weight="bold" if key == "persons" else "normal"),
                text_color="#ff7a8a" if key == "review_items" else COLORS["text_secondary"],
                anchor="w",
                **label_kwargs,
            )
            summary_label.grid(row=index // 2, column=index % 2, sticky="w", padx=(6, 18 if index % 2 == 0 else 6), pady=(4 if index < 2 else 2, 4))
            self.profile_media_database_sidebar_summary_labels[key] = summary_label
        self._refresh_profile_media_database_mode_switch_visual()

    def _create_files_section(self) -> None:
        """Create the session-only local files section in the sidebar."""
        divider = ctk.CTkFrame(self.sidebar_scroll, fg_color=COLORS["border"], height=1)
        divider.pack(fill="x", padx=16, pady=(8, 6))

        self.files_header_frame = ctk.CTkFrame(
            self.sidebar_scroll,
            fg_color="transparent",
        )
        self.files_header_frame.pack(fill="x", padx=14, pady=(0, 6))
        self.files_header_frame.grid_columnconfigure(0, weight=1, minsize=54)

        files_label = ctk.CTkLabel(
            self.files_header_frame,
            text="FILES",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        )
        files_label.grid(row=0, column=0, sticky="w")

        self.files_clear_all_button = ctk.CTkButton(
            self.files_header_frame,
            text="Clear all",
            width=68,
            height=24,
            command=self._clear_all_session_files_clicked,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.files_clear_all_button.grid(row=0, column=1, sticky="e", padx=(0, 3))

        self.files_add_button_tooltip_text = "Add files"
        self.files_add_button = ctk.CTkButton(
            self.files_header_frame,
            text="+",
            width=28,
            height=24,
            command=self._add_session_files_clicked,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.files_expand_all_button = ctk.CTkButton(
            self.files_header_frame,
            text="Expand all",
            width=64,
            height=24,
            command=lambda: self._set_all_session_folders_collapsed(False),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.files_expand_all_button.grid(row=0, column=2, sticky="e", padx=(0, 3))

        self.files_collapse_all_button = ctk.CTkButton(
            self.files_header_frame,
            text="Collapse all",
            width=70,
            height=24,
            command=lambda: self._set_all_session_folders_collapsed(True),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
        )
        self.files_collapse_all_button.grid(row=0, column=3, sticky="e", padx=(0, 3))

        self.files_add_button.grid(row=0, column=4, sticky="e")

        self.files_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        self.files_frame.pack(fill="x", padx=8)

        self.files_list_frame = ctk.CTkScrollableFrame(
            self.files_frame,
            height=330,
            fg_color=COLORS["bg_input"],
            corner_radius=6,
        )
        self.files_list_frame.pack(fill="x")
        self.files_list_frame.grid_columnconfigure(0, weight=1)

        self.files_empty_label = ctk.CTkLabel(
            self.files_list_frame,
            text="No session files yet",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.files_empty_label.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        self.files_drop_status_label = ctk.CTkLabel(
            self.files_frame,
            text="Drop files here",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.files_drop_status_label.pack(fill="x", pady=(4, 0))
        self.session_file_row_widgets: dict[str, object] = {}
        self._bind_files_drop_targets()

    def _session_file_picker_filetypes(self) -> List[Tuple[str, str]]:
        return [
            (
                "Supported session files",
                "*.srt *.vtt *.txt *.mp3 *.wav *.m4a *.aac *.flac *.ogg *.mp4 *.mkv *.mov *.avi *.webm *.jpg *.jpeg *.png *.webp *.gif *.bmp *.tif *.tiff",
            ),
            ("Transcript files", "*.srt *.vtt *.txt"),
            ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
            ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm"),
            ("Image files", "*.jpg *.jpeg *.png *.webp *.gif *.bmp *.tif *.tiff"),
            ("All files", "*.*"),
        ]

    def _add_session_files_clicked(self) -> None:
        files = filedialog.askopenfilenames(
            title="Add Session Files",
            filetypes=self._session_file_picker_filetypes(),
        )
        if not files:
            return
        self._intake_session_files(files, select_first=True, source_label="selected")

    def _bind_files_drop_targets(self) -> bool:
        """Bind TkDND file drops when initialization succeeded."""
        bound = False
        if not vars(self).get("file_drag_drop_ready", False):
            self.files_drag_drop_available = False
            return False
        drop_type = vars(self).get("_file_drag_drop_type", "")
        if not drop_type:
            self.files_drag_drop_available = False
            return False
        for widget in (
            getattr(self, "files_header_frame", None),
            getattr(self, "files_frame", None),
            getattr(self, "files_list_frame", None),
            getattr(self, "files_empty_label", None),
            getattr(self, "files_drop_status_label", None),
        ):
            if widget is None:
                continue
            drop_register = getattr(widget, "drop_target_register", None)
            dnd_bind = getattr(widget, "dnd_bind", None)
            if not callable(drop_register) or not callable(dnd_bind):
                continue
            try:
                drop_register(drop_type)
                dnd_bind("<<Drop>>", self._handle_files_drop_event)
                dnd_bind("<<DragEnter>>", self._handle_files_drag_enter)
                dnd_bind("<<DragLeave>>", self._handle_files_drag_leave)
                bound = True
            except Exception:
                logger.debug("FILES drag/drop binding unavailable.", exc_info=True)
        self.files_drag_drop_available = bound
        return bound

    def _bind_final_file_drop_targets(self) -> bool:
        """Register drag/drop on the final live FILES and Transcript widgets."""
        files_bound = self._bind_files_drop_targets()
        transcript_bound = self._bind_transcript_drop_targets()
        bound = bool(files_bound or transcript_bound)
        if bound:
            self.file_drag_drop_ready = True
            self.file_drag_drop_status = "ready"
        elif getattr(self, "_file_drag_drop_type", ""):
            self.file_drag_drop_ready = False
            self.file_drag_drop_status = "unavailable: no live drop targets"
        return bound

    def _set_files_drop_highlight(self, active: bool) -> None:
        if hasattr(self, "files_list_frame"):
            try:
                self.files_list_frame.configure(
                    border_width=1 if active else 0,
                    border_color="#8a63d2" if active else COLORS["border"],
                )
            except Exception:
                pass
        if hasattr(self, "files_drop_status_label"):
            self.files_drop_status_label.configure(
                text="Release to add files" if active else "Drop files here",
                text_color="#c5a6ff" if active else COLORS["text_muted"],
            )

    def _handle_files_drag_enter(self, _event: object) -> str:
        self._set_files_drop_highlight(True)
        return "copy"

    def _handle_files_drag_leave(self, _event: object) -> str:
        self._set_files_drop_highlight(False)
        return "break"

    def _handle_files_drop_event(self, event: object) -> str:
        self._set_files_drop_highlight(False)
        try:
            paths = self._session_file_paths_from_drop_data(getattr(event, "data", ""))
        except Exception:
            paths = ()
        self._intake_session_files(paths, select_first=True, source_label="dropped")
        return "break"

    def _bind_transcript_drop_targets(self) -> bool:
        """Bind transcript-specific drops without changing the FILES drop target."""
        bound = False
        if not getattr(self, "file_drag_drop_ready", False):
            self.transcript_drag_drop_available = False
            return False
        drop_type = getattr(self, "_file_drag_drop_type", "")
        if not drop_type:
            self.transcript_drag_drop_available = False
            return False
        transcript_text_widget = None
        try:
            transcript_text_widget = self._get_transcript_text_widget()
        except Exception:
            transcript_text_widget = None
        for widget in (
            getattr(self, "transcript_card", None),
            getattr(self, "transcript_textbox", None),
            transcript_text_widget,
            getattr(self, "transcript_timeline_canvas", None),
        ):
            if widget is None:
                continue
            drop_register = getattr(widget, "drop_target_register", None)
            dnd_bind = getattr(widget, "dnd_bind", None)
            if not callable(drop_register) or not callable(dnd_bind):
                continue
            try:
                drop_register(drop_type)
                dnd_bind("<<Drop>>", self._handle_transcript_drop_event)
                dnd_bind("<<DragEnter>>", self._handle_transcript_drag_enter)
                dnd_bind("<<DragLeave>>", self._handle_transcript_drag_leave)
                bound = True
            except Exception:
                logger.debug("Transcript drag/drop binding unavailable.", exc_info=True)
        self.transcript_drag_drop_available = bound
        return bound

    def _set_transcript_drop_highlight(self, active: bool, text: str = "") -> None:
        if hasattr(self, "transcript_card"):
            try:
                self.transcript_card.configure(
                    border_width=2 if active else 1,
                    border_color="#8a63d2" if active else COLORS["border"],
                )
            except Exception:
                pass
        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=text or (
                    "Release to load transcript here"
                    if active
                    else self._transcript_empty_state_text()
                    if not getattr(self, "transcript_segments", [])
                    else "Click inside the transcript to select a segment."
                ),
                text_color="#c5a6ff" if active else COLORS["text_primary"],
            )

    def _handle_transcript_drag_enter(self, _event: object) -> str:
        self._set_transcript_drop_highlight(True)
        return "copy"

    def _handle_transcript_drag_leave(self, _event: object) -> str:
        self._set_transcript_drop_highlight(False)
        return "break"

    def _handle_transcript_drop_event(self, event: object) -> str:
        self._set_transcript_drop_highlight(False)
        try:
            paths = self._session_file_paths_from_drop_data(getattr(event, "data", ""))
        except Exception:
            paths = ()
        self._handle_transcript_drop_paths(paths)
        return "break"

    def _handle_transcript_drop_paths(self, paths: object) -> SessionFileIntakeResult:
        """Add transcript-section drops and load the first transcript deterministically."""
        if isinstance(paths, (str, bytes, os.PathLike)):
            incoming = [os.fspath(paths)]
        else:
            try:
                incoming = [os.fspath(path) for path in paths]  # type: ignore[arg-type]
            except TypeError:
                incoming = []

        transcript_paths: List[str] = []
        media_paths: List[str] = []
        other_paths: List[str] = []
        for path in incoming:
            kind = self._session_file_kind_for_path(path)
            if kind == SESSION_FILE_KIND_TRANSCRIPT:
                transcript_paths.append(path)
            elif self._is_session_media_kind(kind):
                media_paths.append(path)
            else:
                other_paths.append(path)

        combined_paths = transcript_paths + media_paths + other_paths
        result = self._intake_session_files(
            combined_paths,
            select_first=False,
            source_label="transcript drop",
        )

        loaded = False
        for path in transcript_paths:
            entry = self._find_session_file_by_normalized_path(path)
            if entry is not None and self._load_session_transcript_file(entry):
                loaded = True
                break

        if media_paths:
            self.log_message(
                "Media dropped on Transcript was added to FILES. Select it there to make it active media.",
                "info",
            )
        if transcript_paths and not loaded:
            self.log_message("No dropped transcript was loaded.", "warning")
        return result

    def _session_file_paths_from_drop_data(self, data: object) -> Tuple[str, ...]:
        text = str(data or "").strip()
        if not text:
            return ()

        splitlist = getattr(vars(self).get("tk"), "splitlist", None)
        if not callable(splitlist):
            raise RuntimeError("Tk drop payload parser is unavailable.")
        parts = tuple(str(part) for part in splitlist(text))
        return tuple(part.strip() for part in parts if str(part or "").strip())

    def _intake_session_files(
        self,
        paths: object,
        *,
        select_first: bool = True,
        source_label: str = "selected",
    ) -> SessionFileIntakeResult:
        """Add supported local files through one picker/drop intake path."""
        if isinstance(paths, (str, bytes, os.PathLike)):
            incoming = [os.fspath(paths)]
        else:
            try:
                incoming = [os.fspath(path) for path in paths]  # type: ignore[arg-type]
            except TypeError:
                incoming = []

        self._ensure_session_files_state()
        added: List[str] = []
        duplicates: List[str] = []
        unsupported: List[str] = []
        rejected: List[str] = []
        candidates: List[SessionFileEntry] = []
        seen_in_batch: set[str] = set()

        for raw_path in incoming:
            path = os.path.abspath(os.path.expanduser(str(raw_path or "").strip()))
            if not path:
                continue
            try:
                normalized = self._normalise_session_file_path(path)
            except Exception:
                rejected.append(path)
                continue
            if normalized in seen_in_batch:
                duplicates.append(path)
                continue
            seen_in_batch.add(normalized)
            if os.path.isdir(path):
                rejected.append(path)
                continue
            if not os.path.isfile(path):
                rejected.append(path)
                continue
            file_kind = self._session_file_kind_for_path(path)
            if file_kind == SESSION_FILE_KIND_OTHER:
                unsupported.append(path)
                continue

            before_count = len(self.session_files)
            entry = self._add_session_file(path, file_kind)
            if entry is None:
                rejected.append(path)
                continue
            if len(self.session_files) == before_count:
                duplicates.append(path)
            else:
                added.append(path)
            candidates.append(entry)

        # Adding files to FILES must not auto-open Transcript/Text Editor/media panels.
        # The user opens those explicitly with CC/TXT/ASR/open actions.
        selected_path = ""

        result = SessionFileIntakeResult(
            added_paths=tuple(added),
            duplicate_paths=tuple(duplicates),
            unsupported_paths=tuple(unsupported),
            rejected_paths=tuple(rejected),
            selected_path=selected_path,
        )
        self._report_session_file_intake_result(result, source_label=source_label)
        if result.added_paths:
            self._reset_editor_panels_after_file_intake()
        return result

    def _report_session_file_intake_result(
        self,
        result: SessionFileIntakeResult,
        *,
        source_label: str,
    ) -> None:
        if result.added_paths:
            noun = "file" if len(result.added_paths) == 1 else "files"
            self.log_message(
                f"Added {len(result.added_paths)} {source_label} session {noun}.",
                "success",
            )

        skipped = result.unsupported_paths + result.rejected_paths
        if not skipped:
            return

        names = ", ".join(os.path.basename(path) or "unnamed" for path in skipped[:5])
        if len(skipped) > 5:
            names += f", +{len(skipped) - 5} more"
        message = f"Some files were not added: {names}"
        self.log_message(message, "warning")
        try:
            messagebox.showwarning("Some Files Were Not Added", message)
        except Exception:
            logger.debug("Could not show FILES intake warning.", exc_info=True)

    def _ensure_session_files_state(self) -> None:
        state = getattr(self, "__dict__", {})
        if "session_files" not in state:
            self.session_files = []
        if "selected_session_file_path" not in state:
            self.selected_session_file_path = ""
        if "active_media_file_path" not in state:
            self.active_media_file_path = ""
        if "active_transcript_file_path" not in state:
            self.active_transcript_file_path = ""
        if "session_file_folders" not in state:
            self.session_file_folders = {}
        if "session_file_folder_names" not in state:
            self.session_file_folder_names = []
        if "session_file_folder_collapsed" not in state:
            self.session_file_folder_collapsed = {}
        if "session_file_folder_editing" not in state:
            self.session_file_folder_editing = ""
        if "session_file_drag_source_path" not in state:
            self.session_file_drag_source_path = ""
        if "session_file_drag_hover_path" not in state:
            self.session_file_drag_hover_path = ""
        if "last_session_file_click_path" not in state:
            self.last_session_file_click_path = ""
        if "last_session_file_click_time" not in state:
            self.last_session_file_click_time = 0.0
        if "session_file_label_widgets" not in state:
            self.session_file_label_widgets = {}

    def _has_exportable_session_content(self) -> bool:
        """Return whether the sidebar EXPORT entry should be enabled."""
        self._ensure_session_files_state()
        return bool(
            getattr(self, "session_files", [])
            or getattr(self, "transcript_segments", [])
            or getattr(self, "all_comments", [])
        )

    def _refresh_export_entry_state(self) -> None:
        """Keep the sidebar EXPORT button enabled for FILES/transcript/comment content."""
        if "evidence_button" not in getattr(self, "__dict__", {}):
            return
        fetch_state = getattr(self, "fetch_state", None)
        fetching = False
        if fetch_state is not None:
            try:
                fetching = bool(fetch_state.is_fetching or fetch_state.cancel_requested)
            except Exception:
                fetching = bool(getattr(fetch_state, "is_fetching", False))
        state = "normal" if self._has_exportable_session_content() and not fetching else "disabled"
        try:
            self.evidence_button.configure(state=state)
        except Exception:
            logger.debug("Could not refresh EXPORT button state.", exc_info=True)

    def _normalise_session_file_path(self, path: str) -> str:
        return os.path.normcase(os.path.abspath(os.path.expanduser(path or "")))

    def _session_file_kind_for_path(self, path: str) -> str:
        suffix = os.path.splitext(path or "")[1].lower()
        if suffix in TRANSCRIPT_FILE_EXTENSIONS:
            return SESSION_FILE_KIND_TRANSCRIPT
        if suffix in AUDIO_FILE_EXTENSIONS:
            return SESSION_FILE_KIND_AUDIO
        if suffix in VIDEO_FILE_EXTENSIONS:
            return SESSION_FILE_KIND_VIDEO
        if suffix in IMAGE_FILE_EXTENSIONS:
            return SESSION_FILE_KIND_MEDIA
        return SESSION_FILE_KIND_OTHER

    def _session_file_icon_for_kind(self, file_kind: str) -> str:
        if file_kind == SESSION_FILE_KIND_TRANSCRIPT:
            return "TXT"
        if file_kind == SESSION_FILE_KIND_AUDIO:
            return "AUD"
        if file_kind == SESSION_FILE_KIND_VIDEO:
            return "VID"
        if file_kind == SESSION_FILE_KIND_MEDIA:
            return "IMG"
        return "FILE"

    def _is_session_media_kind(self, file_kind: str) -> bool:
        return file_kind in {
            SESSION_FILE_KIND_AUDIO,
            SESSION_FILE_KIND_VIDEO,
            SESSION_FILE_KIND_MEDIA,
        }

    def _is_session_asr_source_kind(self, file_kind: str) -> bool:
        """Only audio/video files should expose Local ASR / Online ASR actions."""
        return file_kind in {
            SESSION_FILE_KIND_AUDIO,
            SESSION_FILE_KIND_VIDEO,
        }

    def _is_session_caption_candidate_entry(self, entry: SessionFileEntry) -> bool:
        """Text/subtitle rows that can be explicitly imported as Transcript via CC."""
        suffix = os.path.splitext(entry.path or "")[1].lower()
        return suffix in {".txt", ".srt", ".vtt"}

    def _is_session_plain_text_entry(self, entry: SessionFileEntry) -> bool:
        """Plain .txt rows that should expose the Text Editor action."""
        return os.path.splitext(entry.path or "")[1].lower() == ".txt"

    def _ensure_session_file_action_icons(self) -> None:
        if hasattr(self, "session_text_file_icon_image") and hasattr(self, "session_caption_icon_image"):
            return
        self.session_text_file_icon_image = None
        self.session_caption_icon_image = None
        asset_base_dir = os.path.dirname(os.path.abspath(__file__))

        def _load_icon(filename: str) -> Optional[ctk.CTkImage]:
            icon_path = os.path.join(asset_base_dir, "assets", filename)
            if not os.path.exists(icon_path):
                return None
            icon_image = Image.open(icon_path).convert("RGBA")
            return ctk.CTkImage(light_image=icon_image, dark_image=icon_image, size=(18, 18))

        try:
            self.session_text_file_icon_image = _load_icon("ytce_file_text_icon.png")
            self.session_caption_icon_image = _load_icon("ytce_file_cc_icon.png")
        except Exception as icon_error:
            logger.warning(f"Could not load FILES action icons: {icon_error}")
            self.session_text_file_icon_image = None
            self.session_caption_icon_image = None

    def _open_session_text_file_action(self, normalized_path: str) -> None:
        """Open a .txt file in the in-app Text Editor panel."""
        self._load_session_text_editor_file(normalized_path)

    def _reset_editor_panels_after_file_intake(self) -> None:
        """Adding files to FILES should not force Transcript/Text Editor open."""
        self.active_text_editor_file_path = ""
        if hasattr(self, "text_editor_status_label"):
            self.text_editor_status_label.configure(text="No text file loaded")
        if hasattr(self, "text_editor_textbox"):
            self.text_editor_textbox.configure(state="normal")
            self.text_editor_textbox.delete("1.0", "end")
            self.text_editor_textbox.insert("1.0", "Open a .txt file from FILES with the TXT icon.")
            self.text_editor_textbox.configure(state="disabled")
        if hasattr(self, "text_editor_save_button"):
            self.text_editor_save_button.configure(state="disabled")
        if hasattr(self, "text_editor_external_open_button"):
            self.text_editor_external_open_button.configure(state="disabled")
        self._hide_text_editor_panel()
        self._hide_transcript_panel()

    def _session_media_entries(self) -> List[SessionFileEntry]:
        self._ensure_session_files_state()
        return [
            entry
            for entry in self.session_files
            if self._is_session_media_kind(entry.file_kind)
        ]

    def _find_session_file_by_normalized_path(
        self,
        normalized_path: str,
    ) -> Optional[SessionFileEntry]:
        self._ensure_session_files_state()
        normalized_path = self._normalise_session_file_path(normalized_path)
        return next(
            (
                candidate
                for candidate in self.session_files
                if candidate.normalized_path == normalized_path
            ),
            None,
        )

    def _normalise_session_file_folder_state(self) -> None:
        self._ensure_session_files_state()
        names = list(getattr(self, "session_file_folder_names", []) or [])
        folders = getattr(self, "session_file_folders", {}) or {}
        for folder_name in folders.values():
            if folder_name and folder_name not in names:
                names.append(folder_name)
        self.session_file_folder_names = names
        collapsed = dict(getattr(self, "session_file_folder_collapsed", {}) or {})
        for folder_name in names:
            collapsed.setdefault(folder_name, True)
        self.session_file_folder_collapsed = {
            folder_name: bool(collapsed.get(folder_name, True))
            for folder_name in names
        }

    def _clear_all_session_files_clicked(self) -> None:
        """Detach all FILES entries from this session without deleting source files."""
        self._ensure_session_files_state()
        count = len(getattr(self, "session_files", []) or [])
        if not count and not getattr(self, "session_file_folder_names", []):
            return
        self.session_files = []
        self.session_file_folders = {}
        self.session_file_folder_names = []
        self.session_file_folder_collapsed = {}
        self.session_file_folder_editing = ""
        self._cleanup_webpage_image_session_downloads(reset_state=True)
        self.selected_session_file_path = ""
        self.active_media_file_path = ""
        self.active_transcript_file_path = ""
        self._set_linked_transcript_media(None)
        self._refresh_session_files_list()
        self.log_message(f"Cleared {count} FILES entr{'y' if count == 1 else 'ies'} from the session. Local files were not deleted.", "muted")

    def _set_all_session_folders_collapsed(self, collapsed: bool) -> None:
        self._normalise_session_file_folder_state()
        self.session_file_folder_collapsed = {
            folder_name: bool(collapsed)
            for folder_name in getattr(self, "session_file_folder_names", [])
        }
        self._refresh_session_files_list()

    def _toggle_session_file_folder_collapsed(self, folder_name: str) -> None:
        self._normalise_session_file_folder_state()
        folder_name = str(folder_name or "")
        if not folder_name:
            return
        current = bool(getattr(self, "session_file_folder_collapsed", {}).get(folder_name, True))
        self.session_file_folder_collapsed[folder_name] = not current
        self._refresh_session_files_list()

    def _remove_session_file_folder(self, folder_name: str) -> None:
        """Remove a FILES folder object and move any children back to root."""
        self._normalise_session_file_folder_state()
        folder_name = str(folder_name or "")
        if not folder_name:
            return
        moved_count = sum(
            1
            for folder in getattr(self, "session_file_folders", {}).values()
            if folder == folder_name
        )
        self.session_file_folders = {
            path: folder
            for path, folder in getattr(self, "session_file_folders", {}).items()
            if folder != folder_name
        }
        self.session_file_folder_names = [
            name for name in getattr(self, "session_file_folder_names", []) if name != folder_name
        ]
        self.session_file_folder_collapsed.pop(folder_name, None)
        if getattr(self, "session_file_folder_editing", "") == folder_name:
            self.session_file_folder_editing = ""
        if moved_count:
            self.log_message(f"Removed FILES folder '{folder_name}' and moved {moved_count} item(s) to root.", "success")
        else:
            self.log_message(f"Removed empty FILES folder '{folder_name}'.", "success")
        self._refresh_session_files_list()

    def _move_session_file_out_of_folder(self, normalized_path: str) -> None:
        self._ensure_session_files_state()
        normalized_path = self._normalise_session_file_path(normalized_path)
        if normalized_path in getattr(self, "session_file_folders", {}):
            self.session_file_folders.pop(normalized_path, None)
            self._refresh_session_files_list()

    def _open_session_file_external(self, normalized_path: str) -> None:
        self._ensure_session_files_state()
        entry = self._find_session_file_by_normalized_path(normalized_path)
        if entry is None:
            return
        try:
            os.startfile(entry.path)  # type: ignore[attr-defined]
        except Exception as error:
            self.log_message(f"Could not open file externally: {error}", "error")
            try:
                messagebox.showerror("Open File", str(error), parent=self)
            except Exception:
                logger.debug("Could not show external open error.", exc_info=True)

    def _session_file_folder_for_entry(self, entry: SessionFileEntry) -> str:
        self._ensure_session_files_state()
        return str(getattr(self, "session_file_folders", {}).get(entry.normalized_path, "") or "")

    def _session_file_export_display_name(self, entry: SessionFileEntry) -> str:
        folder = self._session_file_folder_for_entry(entry)
        return f"{folder} / {entry.display_name}" if folder else entry.display_name

    def _safe_session_folder_name(self, value: str) -> str:
        cleaned = "".join(ch if ch not in '<>:"/\\|?*' else "_" for ch in str(value or "").strip())
        cleaned = cleaned.strip(" .")
        return cleaned or "New folder"

    def _unique_session_file_folder_name(self, preferred: str, *, excluding: str = "") -> str:
        self._ensure_session_files_state()
        base = self._safe_session_folder_name(preferred)
        existing = {
            str(name)
            for name in [
                *list(getattr(self, "session_file_folder_names", []) or []),
                *list(getattr(self, "session_file_folders", {}).values()),
            ]
            if str(name) and str(name) != excluding
        }
        if base not in existing:
            return base
        index = 2
        while f"{base} {index}" in existing:
            index += 1
        return f"{base} {index}"

    def _suggest_session_folder_name(self, first: SessionFileEntry, second: SessionFileEntry) -> str:
        first_stem = os.path.splitext(first.display_name)[0].strip()
        second_stem = os.path.splitext(second.display_name)[0].strip()
        prefix = os.path.commonprefix([first_stem, second_stem]).strip(" -_()[]{}.")
        if len(prefix) >= 3:
            return prefix
        return "New folder"

    def _rename_session_file_folder(self, old_name: str, new_name: str) -> None:
        self._ensure_session_files_state()
        old_name = str(old_name or "")
        if not old_name:
            return
        new_name = self._unique_session_file_folder_name(new_name or old_name, excluding=old_name)
        if new_name != old_name:
            self.session_file_folders = {
                path: (new_name if folder == old_name else folder)
                for path, folder in getattr(self, "session_file_folders", {}).items()
            }
            self.session_file_folder_names = [
                (new_name if folder == old_name else folder)
                for folder in getattr(self, "session_file_folder_names", [])
            ]
            collapsed_value = bool(getattr(self, "session_file_folder_collapsed", {}).pop(old_name, True))
            self.session_file_folder_collapsed[new_name] = collapsed_value
        if getattr(self, "session_file_folder_editing", "") == old_name:
            self.session_file_folder_editing = ""
        self._refresh_session_files_list()

    def _session_file_label_text(self, entry: SessionFileEntry, *, drag_hover: bool = False) -> str:
        text = f"{self._session_file_icon_for_kind(entry.file_kind)}  {entry.display_name}"
        return f"Drop here → {text}" if drag_hover else text

    def _session_file_entry_needs_review(self, entry: SessionFileEntry) -> bool:
        marker_text = f"{entry.display_name} {entry.path}".lower()
        return any(marker in marker_text for marker in ("needs_review", "needs-review", "review_required", "review-required", "manual_review", "manual-review"))

    def _session_file_label_colors(self, entry: SessionFileEntry, *, drag_hover: bool = False) -> tuple[str, str]:
        selected = entry.normalized_path == self.selected_session_file_path
        active_media = (
            self._is_session_media_kind(entry.file_kind)
            and entry.normalized_path == getattr(self, "active_media_file_path", "")
        )
        if drag_hover:
            return COLORS["accent"], COLORS["bg_dark"]
        if active_media:
            return "#4b2d73", "#f4ecff"
        if selected:
            return COLORS["accent_secondary"], COLORS["text_primary"]
        if self._session_file_entry_needs_review(entry):
            return "#4f171f", "#ffb3c0"
        return "transparent", COLORS["text_primary"]

    def _set_session_file_label_visual(self, normalized_path: str, *, drag_hover: bool = False) -> None:
        normalized_path = self._normalise_session_file_path(normalized_path)
        entry = self._find_session_file_by_normalized_path(normalized_path)
        label = getattr(self, "session_file_label_widgets", {}).get(normalized_path)
        if entry is None or label is None:
            return
        row_color, text_color = self._session_file_label_colors(entry, drag_hover=drag_hover)
        try:
            label.configure(
                text=self._session_file_label_text(entry, drag_hover=drag_hover),
                fg_color=row_color,
                text_color=text_color,
            )
        except Exception:
            logger.debug("Could not update FILES drag-hover visual.", exc_info=True)

    def _cancel_session_file_global_drag_bindings(self) -> None:
        try:
            self.unbind_all("<B1-Motion>")
            self.unbind_all("<ButtonRelease-1>")
        except Exception:
            logger.debug("Could not unbind global FILES drag handlers.", exc_info=True)

    def _handle_session_file_label_press(self, normalized_path: str, _event: Any = None) -> str | None:
        """Start filename-label drag, or open externally on a quick second click.

        Tk/CustomTkinter double-click delivery can be inconsistent when the same
        label is also draggable. This press-time fallback makes quick repeated
        clicks open the file without needing three or more clicks.
        """
        self._ensure_session_files_state()
        normalized_path = self._normalise_session_file_path(normalized_path)
        now = time.monotonic()
        if (
            normalized_path == getattr(self, "last_session_file_click_path", "")
            and now - float(getattr(self, "last_session_file_click_time", 0.0) or 0.0) <= 0.55
        ):
            self.last_session_file_click_path = ""
            self.last_session_file_click_time = 0.0
            self._handle_session_file_external_open(normalized_path, _event)
            return "break"
        self.last_session_file_click_path = normalized_path
        self.last_session_file_click_time = now
        self._begin_session_file_drag(normalized_path)
        return None

    def _handle_session_file_external_open(self, normalized_path: str, _event: Any = None) -> str:
        self._cancel_session_file_global_drag_bindings()
        self.session_file_drag_source_path = ""
        self.session_file_drag_hover_path = ""
        self._open_session_file_external(normalized_path)
        return "break"

    def _begin_session_file_drag(self, normalized_path: str) -> None:
        self._ensure_session_files_state()
        self.session_file_drag_source_path = self._normalise_session_file_path(normalized_path)
        self.session_file_drag_hover_path = ""

    def _session_file_path_for_widget(self, widget: Any) -> str:
        row_widgets = getattr(self, "session_file_row_widgets", {}) or {}
        current = widget
        while current is not None:
            for path, row_widget in row_widgets.items():
                if current == row_widget:
                    return path
            current = getattr(current, "master", None)
        return ""

    def _update_session_file_drag_hover(self, event: Any) -> None:
        if not getattr(self, "session_file_drag_source_path", ""):
            return
        target_widget = None
        try:
            target_widget = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            target_widget = None
        target_path = self._session_file_path_for_widget(target_widget) if target_widget is not None else ""
        target_path = self._normalise_session_file_path(target_path) if target_path else ""
        if target_path == getattr(self, "session_file_drag_source_path", ""):
            target_path = ""
        previous_path = getattr(self, "session_file_drag_hover_path", "") or ""
        if target_path != previous_path:
            if previous_path:
                self._set_session_file_label_visual(previous_path, drag_hover=False)
            self.session_file_drag_hover_path = target_path
            if target_path:
                self._set_session_file_label_visual(target_path, drag_hover=True)

    def _finish_session_file_drag(self, normalized_path: str, event: Any) -> None:
        self._ensure_session_files_state()
        source_path = self._normalise_session_file_path(
            getattr(self, "session_file_drag_source_path", "") or normalized_path
        )
        target_path = getattr(self, "session_file_drag_hover_path", "") or ""
        if not target_path:
            target_widget = None
            try:
                target_widget = self.winfo_containing(event.x_root, event.y_root)
            except Exception:
                target_widget = None
            target_path = self._session_file_path_for_widget(target_widget) if target_widget is not None else ""
        self.session_file_drag_source_path = ""
        self.session_file_drag_hover_path = ""
        self._cancel_session_file_global_drag_bindings()
        if target_path and self._normalise_session_file_path(target_path) != source_path:
            self._create_session_file_folder_from_drop(source_path, target_path)
        else:
            self._refresh_session_files_list()

    def _bind_session_file_drag_handlers(self, widget: Any, normalized_path: str) -> None:
        """Bind FILES filename label: drag by label, double-click to open externally."""
        try:
            widget.bind("<ButtonPress-1>", lambda event, path=normalized_path: self._handle_session_file_label_press(path, event), add="+")
            widget.bind("<B1-Motion>", self._update_session_file_drag_hover, add="+")
            widget.bind("<ButtonRelease-1>", lambda event, path=normalized_path: self._finish_session_file_drag(path, event), add="+")
            widget.bind("<Double-Button-1>", lambda event, path=normalized_path: self._handle_session_file_external_open(path, event), add="+")
        except Exception:
            logger.debug("Could not bind FILES row label handlers.", exc_info=True)

    def _create_session_file_folder_from_drop(self, source_path: str, target_path: str) -> None:
        self._ensure_session_files_state()
        source_path = self._normalise_session_file_path(source_path)
        target_path = self._normalise_session_file_path(target_path)
        if source_path == target_path:
            return
        source = self._find_session_file_by_normalized_path(source_path)
        target = self._find_session_file_by_normalized_path(target_path)
        if source is None or target is None:
            return
        folders = getattr(self, "session_file_folders", {})
        folder_name = folders.get(target_path) or folders.get(source_path)
        created_new_folder = False
        if not folder_name:
            folder_name = self._unique_session_file_folder_name(
                self._suggest_session_folder_name(source, target)
            )
            created_new_folder = True
        if folder_name not in getattr(self, "session_file_folder_names", []):
            self.session_file_folder_names.append(folder_name)
            created_new_folder = True
        self.session_file_folders[source_path] = folder_name
        self.session_file_folders[target_path] = folder_name
        self.session_file_folder_collapsed[folder_name] = True
        if created_new_folder:
            self.session_file_folder_editing = folder_name
        self.log_message(
            f"{'Created' if created_new_folder else 'Updated'} FILES folder '{folder_name}' with {source.display_name} and {target.display_name}.",
            "success",
        )
        self._refresh_session_files_list()

    def _default_session_media_path(self) -> str:
        self._ensure_session_files_state()
        for value in (
            getattr(self, "active_media_file_path", ""),
            getattr(self, "linked_transcript_media_path", "") or "",
            getattr(self, "selected_session_file_path", ""),
        ):
            if not value:
                continue
            entry = self._find_session_file_by_normalized_path(value)
            if entry is not None and self._is_session_media_kind(entry.file_kind):
                return entry.path
        media_entries = self._session_media_entries()
        if len(media_entries) == 1:
            return media_entries[0].path
        return ""

    def _session_media_options(self) -> Tuple[Tuple[str, str], ...]:
        result: List[Tuple[str, str]] = []
        for index, entry in enumerate(self._session_media_entries(), start=1):
            result.append((f"{index}. {entry.display_name}", entry.path))
        return tuple(result)

    def _add_session_file(
        self,
        path: str,
        file_kind: str = "",
        *,
        select: bool = False,
    ) -> Optional[SessionFileEntry]:
        """Add a local file to the current session list without persistence."""
        self._ensure_session_files_state()
        if not path:
            return None
        normalized = self._normalise_session_file_path(path)
        absolute_path = os.path.abspath(os.path.expanduser(path))
        for entry in self.session_files:
            if entry.normalized_path == normalized:
                if select:
                    self.selected_session_file_path = normalized
                    if self._is_session_media_kind(entry.file_kind):
                        self.active_media_file_path = normalized
                    elif entry.file_kind == SESSION_FILE_KIND_TRANSCRIPT:
                        self.active_transcript_file_path = normalized
                    self._refresh_session_files_list()
                return entry
        entry = SessionFileEntry(
            path=absolute_path,
            normalized_path=normalized,
            display_name=os.path.basename(absolute_path),
            file_kind=file_kind or self._session_file_kind_for_path(absolute_path),
        )
        self.session_files.append(entry)
        if select:
            self.selected_session_file_path = normalized
            if self._is_session_media_kind(entry.file_kind):
                self.active_media_file_path = normalized
            elif entry.file_kind == SESSION_FILE_KIND_TRANSCRIPT:
                self.active_transcript_file_path = normalized
        self._refresh_session_files_list()
        return entry

    def _remove_session_file(self, normalized_path: str) -> None:
        """Detach a file from this session list without deleting it from disk."""
        self._ensure_session_files_state()
        normalized_path = self._normalise_session_file_path(normalized_path)
        self.session_files = [
            entry
            for entry in self.session_files
            if entry.normalized_path != normalized_path
        ]
        if hasattr(self, "session_file_folders"):
            self.session_file_folders.pop(normalized_path, None)
        if self.selected_session_file_path == normalized_path:
            self.selected_session_file_path = ""
        if self.active_media_file_path == normalized_path:
            self.active_media_file_path = ""
            self._set_linked_transcript_media(None)
        if self.active_transcript_file_path == normalized_path:
            self.active_transcript_file_path = ""
        try:
            root = getattr(self, "webpage_image_session_output_root", None)
            if root:
                root_path = Path(root).resolve()
                target_path = Path(normalized_path).resolve()
                if target_path.is_relative_to(root_path):
                    Path(normalized_path).unlink(missing_ok=True)
                    cache = getattr(self, "webpage_image_session_download_cache", {}) or {}
                    self.webpage_image_session_download_cache = {
                        key: value
                        for key, value in cache.items()
                        if self._normalise_session_file_path(value) != normalized_path
                    }
        except Exception:
            logger.debug("Could not clean detached temporary webpage image file.", exc_info=True)
        self._refresh_session_files_list()

    def _refresh_session_files_list(self) -> None:
        if "files_list_frame" not in getattr(self, "__dict__", {}):
            return
        for widget in getattr(self, "session_file_row_widgets", {}).values():
            try:
                widget.destroy()
            except Exception:
                pass
        self.session_file_row_widgets = {}
        self.session_file_label_widgets = {}

        self._normalise_session_file_folder_state()
        folder_map = getattr(self, "session_file_folders", {}) or {}
        folder_names = list(getattr(self, "session_file_folder_names", []) or [])
        has_files = bool(getattr(self, "session_files", []))
        if not has_files and not folder_names:
            self.files_empty_label.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
            self._refresh_export_entry_state()
            return
        self.files_empty_label.grid_remove()

        render_row = 0

        def render_folder_header(folder_name: str) -> None:
            nonlocal render_row
            collapsed = bool(getattr(self, "session_file_folder_collapsed", {}).get(folder_name, True))
            header = ctk.CTkFrame(self.files_list_frame, fg_color="transparent")
            header.grid(row=render_row, column=0, sticky="ew", padx=4, pady=(8, 2))
            header.grid_columnconfigure(1, weight=1)
            toggle_button = ctk.CTkButton(
                header,
                text="▸" if collapsed else "▾",
                width=22,
                height=24,
                fg_color="transparent",
                hover_color=COLORS["border"],
                text_color=COLORS["text_secondary"],
                command=lambda name=folder_name: self._toggle_session_file_folder_collapsed(name),
            )
            toggle_button.grid(row=0, column=0, sticky="w", padx=(0, 2))
            if folder_name == getattr(self, "session_file_folder_editing", ""):
                entry = ctk.CTkEntry(
                    header,
                    height=26,
                    fg_color=COLORS["bg_input"],
                    text_color=COLORS["text_primary"],
                    border_color=COLORS["accent"],
                    border_width=1,
                )
                entry.insert(0, folder_name)
                entry.grid(row=0, column=1, sticky="ew")
                entry.focus_set()
                entry.select_range(0, "end")
                entry.bind("<Return>", lambda _event, old=folder_name, widget=entry: self._rename_session_file_folder(old, widget.get()))
                entry.bind("<FocusOut>", lambda _event, old=folder_name, widget=entry: self._rename_session_file_folder(old, widget.get()))
                remove_folder_button = ctk.CTkButton(
                    header,
                    text="×",
                    width=24,
                    height=24,
                    fg_color="transparent",
                    hover_color=COLORS["border"],
                    text_color=COLORS["text_muted"],
                    command=lambda name=folder_name: self._remove_session_file_folder(name),
                )
                remove_folder_button.bind(
                    "<ButtonPress-1>",
                    lambda _event, name=folder_name: (self._remove_session_file_folder(name), "break")[-1],
                    add="+",
                )
                remove_folder_button.grid(row=0, column=2, sticky="e", padx=(4, 0))
            else:
                folder_title = ctk.CTkLabel(
                    header,
                    text=f"📁 {folder_name}",
                    anchor="w",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color=COLORS["text_secondary"],
                    cursor="hand2",
                )
                folder_title.grid(row=0, column=1, sticky="ew")
                folder_title.bind(
                    "<Button-1>",
                    lambda _event, name=folder_name: self._toggle_session_file_folder_collapsed(name),
                    add="+",
                )
                edit_button = ctk.CTkButton(
                    header,
                    text="Rename",
                    width=58,
                    height=24,
                    fg_color="transparent",
                    hover_color=COLORS["border"],
                    text_color=COLORS["text_muted"],
                    command=lambda name=folder_name: (
                        setattr(self, "session_file_folder_editing", name),
                        self._refresh_session_files_list(),
                    ),
                )
                edit_button.grid(row=0, column=2, sticky="e", padx=(4, 0))
                remove_folder_button = ctk.CTkButton(
                    header,
                    text="×",
                    width=24,
                    height=24,
                    fg_color="transparent",
                    hover_color=COLORS["border"],
                    text_color=COLORS["text_muted"],
                    command=lambda name=folder_name: self._remove_session_file_folder(name),
                )
                remove_folder_button.bind(
                    "<ButtonPress-1>",
                    lambda _event, name=folder_name: (self._remove_session_file_folder(name), "break")[-1],
                    add="+",
                )
                remove_folder_button.grid(row=0, column=3, sticky="e", padx=(4, 0))
            render_row += 1

        def render_file_row(entry: SessionFileEntry, *, nested: bool = False) -> None:
            nonlocal render_row
            self._ensure_session_file_action_icons()
            row_frame = ctk.CTkFrame(self.files_list_frame, fg_color="transparent")
            row_frame.grid(row=render_row, column=0, sticky="ew", padx=(18 if nested else 4, 4), pady=2)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=0)
            row_frame.grid_columnconfigure(2, weight=0)
            drag_hover = entry.normalized_path == getattr(self, "session_file_drag_hover_path", "")
            row_color, text_color = self._session_file_label_colors(entry, drag_hover=drag_hover)
            label = ctk.CTkLabel(
                row_frame,
                text=self._session_file_label_text(entry, drag_hover=drag_hover),
                anchor="w",
                height=34,
                fg_color=row_color,
                text_color=text_color,
                corner_radius=6,
                justify="left",
                wraplength=max(340, min(600, int(getattr(self, "sidebar_width", self.SIDEBAR_WIDTH)) - 92)),
            )
            label.grid(row=0, column=0, sticky="ew")
            self._bind_session_file_drag_handlers(label, entry.normalized_path)
            self.session_file_row_widgets[entry.normalized_path] = row_frame
            self.session_file_label_widgets[entry.normalized_path] = label
            action_column = 1

            if nested:
                out_button = ctk.CTkButton(
                    row_frame,
                    text="Out",
                    width=36,
                    height=26,
                    fg_color="transparent",
                    hover_color=COLORS["border"],
                    text_color=COLORS["text_muted"],
                    command=lambda path=entry.normalized_path: self._move_session_file_out_of_folder(path),
                )
                out_button.grid(row=0, column=action_column, sticky="e", padx=(4, 0))
                action_column += 1

            if self._is_session_asr_source_kind(entry.file_kind):
                local_button = ctk.CTkButton(
                    row_frame,
                    text="⌂",
                    width=26,
                    height=26,
                    fg_color="transparent",
                    hover_color=COLORS["border"],
                    text_color=COLORS["text_primary"],
                    command=lambda path=entry.normalized_path: self._start_local_asr_full_for_session_file(path),
                )
                local_button.grid(row=0, column=action_column, sticky="e", padx=(4, 0))
                action_column += 1
                online_button = ctk.CTkButton(
                    row_frame,
                    text="◉",
                    width=26,
                    height=26,
                    fg_color="transparent",
                    hover_color=COLORS["border"],
                    text_color=COLORS["text_primary"],
                    command=lambda path=entry.normalized_path: self._start_online_asr_full_for_session_file(path),
                )
                online_button.grid(row=0, column=action_column, sticky="e", padx=(4, 0))
                action_column += 1

            if self._is_session_caption_candidate_entry(entry):
                cc_button_kwargs = {
                    "text": "" if self.session_caption_icon_image is not None else "CC",
                    "width": 30,
                    "height": 26,
                    "fg_color": "transparent",
                    "hover_color": COLORS["border"],
                    "text_color": COLORS["text_primary"],
                    "command": lambda item=entry: self._load_session_transcript_file(item),
                }
                if self.session_caption_icon_image is not None:
                    cc_button_kwargs["image"] = self.session_caption_icon_image
                cc_button = ctk.CTkButton(row_frame, **cc_button_kwargs)
                cc_button.grid(row=0, column=action_column, sticky="e", padx=(4, 0))
                action_column += 1

            if self._is_session_plain_text_entry(entry):
                text_button_kwargs = {
                    "text": "" if self.session_text_file_icon_image is not None else "TXT",
                    "width": 30,
                    "height": 26,
                    "fg_color": "transparent",
                    "hover_color": COLORS["border"],
                    "text_color": COLORS["text_primary"],
                    "command": lambda path=entry.normalized_path: self._open_session_text_file_action(path),
                }
                if self.session_text_file_icon_image is not None:
                    text_button_kwargs["image"] = self.session_text_file_icon_image
                text_button = ctk.CTkButton(row_frame, **text_button_kwargs)
                text_button.grid(row=0, column=action_column, sticky="e", padx=(4, 0))
                action_column += 1

            remove_button = ctk.CTkButton(
                row_frame,
                text="×",
                width=26,
                height=26,
                fg_color="transparent",
                hover_color=COLORS["border"],
                text_color=COLORS["text_muted"],
                command=lambda path=entry.normalized_path: self._remove_session_file(path),
            )
            remove_button.grid(row=0, column=action_column, sticky="e", padx=(4, 0))
            render_row += 1

        rendered_in_folders: set[str] = set()
        for folder_name in folder_names:
            render_folder_header(folder_name)
            if not bool(getattr(self, "session_file_folder_collapsed", {}).get(folder_name, True)):
                for nested_entry in self.session_files:
                    if str(folder_map.get(nested_entry.normalized_path, "") or "") == folder_name:
                        rendered_in_folders.add(nested_entry.normalized_path)
                        render_file_row(nested_entry, nested=True)
            else:
                for nested_entry in self.session_files:
                    if str(folder_map.get(nested_entry.normalized_path, "") or "") == folder_name:
                        rendered_in_folders.add(nested_entry.normalized_path)

        for entry in self.session_files:
            if entry.normalized_path in rendered_in_folders:
                continue
            if str(folder_map.get(entry.normalized_path, "") or ""):
                continue
            render_file_row(entry, nested=False)
        self._refresh_export_entry_state()

    def _save_transcript_before_session_switch(self) -> bool:
        if not self.transcript_segments:
            self.transcript_has_unsaved_edits = False
            return True
        filename = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT subtitle files", "*.srt")],
            title="Save Transcript Before Switching",
        )
        if not filename:
            return False
        try:
            export_transcript_srt(self.transcript_segments, filename)
            self.transcript_has_unsaved_edits = False
            self._refresh_session_files_list()
            self.log_message(
                f"Saved transcript before switching: {os.path.basename(filename)}",
                "success",
            )
            return True
        except Exception as error:
            logger.error("Transcript save before switch failed.")
            messagebox.showerror("Transcript Save Error", str(error))
            return False

    def _confirm_transcript_switch_allowed(self) -> bool:
        if not getattr(self, "transcript_has_unsaved_edits", False):
            return True
        answer = messagebox.askyesnocancel(
            "Unsaved Transcript Changes",
            "Save current transcript edits before switching files?\n\n"
            "Yes = Save\nNo = Discard\nCancel = stay on the current transcript.",
        )
        if answer is None:
            return False
        if answer is True:
            return self._save_transcript_before_session_switch()
        self.transcript_has_unsaved_edits = False
        self._refresh_session_files_list()
        return True

    def _select_session_file(self, normalized_path: str) -> None:
        self._ensure_session_files_state()
        normalized_path = self._normalise_session_file_path(normalized_path)
        now = time.monotonic()
        if (
            normalized_path == getattr(self, "last_session_file_click_path", "")
            and now - float(getattr(self, "last_session_file_click_time", 0.0) or 0.0) <= 0.55
        ):
            self.last_session_file_click_path = ""
            self.last_session_file_click_time = 0.0
            self._open_session_file_external(normalized_path)
            return
        self.last_session_file_click_path = normalized_path
        self.last_session_file_click_time = now
        entry = next(
            (
                candidate
                for candidate in self.session_files
                if candidate.normalized_path == normalized_path
            ),
            None,
        )
        if entry is None:
            return
        if entry.file_kind == SESSION_FILE_KIND_TRANSCRIPT:
            self._load_session_transcript_file(entry)
            return
        self._select_session_media_file(entry)

    def _load_session_transcript_file(self, entry: SessionFileEntry) -> bool:
        if not self._confirm_transcript_switch_allowed():
            return False
        try:
            segments = import_transcript(entry.path)
            if not segments:
                messagebox.showwarning(
                    "No Transcript Segments",
                    "No transcript segments could be imported from this file.",
                )
                return False
        except Exception as error:
            logger.error("Transcript session-file import error.")
            self.log_message(f"Transcript import failed: {error}", "error")
            messagebox.showerror("Transcript Import Error", str(error))
            return False

        if not self._confirm_transcript_media_duration_link(segments):
            return False

        self._show_transcript_panel()
        self.transcript_segments = segments
        self.last_transcript_source = f"Imported file: {entry.display_name}"
        self.transcript_has_unsaved_edits = False
        self.transcript_undo_stack = []
        self.transcript_redo_stack = []
        self.selected_session_file_path = entry.normalized_path
        self.active_transcript_file_path = entry.normalized_path
        self._refresh_transcript_display()
        if "evidence_button" in getattr(self, "__dict__", {}):
            self.evidence_button.configure(state="normal")
        self._refresh_session_files_list()
        return True

    def _confirm_transcript_media_duration_link(
        self,
        segments: List[TranscriptSegment],
    ) -> bool:
        media_duration = self._get_linked_media_duration_seconds()
        if not isinstance(media_duration, (int, float)) or media_duration <= 0:
            return True
        transcript_times = [
            seconds
            for segment in segments
            for seconds in (
                self._transcript_time_to_seconds(segment.start),
                self._transcript_time_to_seconds(segment.end),
            )
            if seconds is not None
        ]
        if not transcript_times:
            return True
        transcript_duration = max(transcript_times)
        difference = abs(float(transcript_duration) - float(media_duration))
        if difference < 5.0 or difference / max(1.0, float(media_duration)) < 0.08:
            return True
        if "tk" not in vars(self):
            return True
        choice = self._ask_transcript_media_mismatch_choice(
            media_duration=float(media_duration),
            transcript_duration=float(transcript_duration),
            media_name=os.path.basename(getattr(self, "linked_transcript_media_path", "") or "Media"),
            transcript_name=os.path.basename(
                getattr(self, "active_transcript_file_path", "") or "Transcript"
            ),
        )
        if choice == "cancel":
            return False
        if choice == "unlink":
            self._set_linked_transcript_media(None)
        return True

    def _ask_transcript_media_mismatch_choice(
        self,
        *,
        media_duration: float,
        transcript_duration: float,
        media_name: str = "Media",
        transcript_name: str = "Transcript",
    ) -> str:
        """Ask how to handle a transcript/media duration mismatch."""
        override = vars(self).get("_transcript_media_mismatch_choice_override")
        if override:
            return str(override)

        dialog = ctk.CTkToplevel(self)
        dialog.title("Transcript/Media Duration Mismatch")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        result = {"choice": "cancel"}
        frame = ctk.CTkFrame(dialog, fg_color=COLORS["bg_card"])
        frame.pack(fill="both", expand=True, padx=18, pady=18)
        ctk.CTkLabel(
            frame,
            text="Transcript and media durations differ",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            frame,
            text=(
                "The transcript duration differs materially from the active media duration.\n\n"
                f"Media:\n{media_name} - {self._format_timeline_time(media_duration)}\n\n"
                f"Transcript:\n{transcript_name} - {self._format_timeline_time(transcript_duration)}"
            ),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(8, 14))

        button_row = ctk.CTkFrame(frame, fg_color="transparent")
        button_row.pack(fill="x")

        def choose(value: str) -> None:
            result["choice"] = value
            dialog.destroy()

        for text, value, color in (
            ("Link anyway", "link", COLORS["accent"]),
            ("Keep transcript unlinked", "unlink", COLORS["accent_secondary"]),
            ("Cancel", "cancel", COLORS["border"]),
        ):
            ctk.CTkButton(
                button_row,
                text=text,
                command=lambda value=value: choose(value),
                fg_color=color,
                hover_color=COLORS["accent_hover"] if value == "link" else COLORS["border"],
                text_color="#000000" if value == "link" else COLORS["text_primary"],
                height=30,
                corner_radius=6,
            ).pack(side="left", padx=(0, 8))

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        try:
            dialog.wait_window()
        except Exception:
            return "cancel"
        return str(result["choice"])

    def _select_session_media_file(self, entry: SessionFileEntry) -> bool:
        if not os.path.exists(entry.path):
            messagebox.showerror(
                "Media Not Found",
                "The selected media file does not exist.",
            )
            return False
        self.selected_session_file_path = entry.normalized_path
        self.active_media_file_path = entry.normalized_path
        self._set_linked_transcript_media(entry.path, log=True)
        self._refresh_session_files_list()
        if "transcript_cursor_status_label" in getattr(self, "__dict__", {}):
            self.transcript_cursor_status_label.configure(
                text=f"Linked media: {entry.display_name}",
                text_color=COLORS["text_primary"],
            )
        return True

    def _start_local_asr_full_for_session_file(self, normalized_path: str) -> bool:
        entry = self._find_session_file_by_normalized_path(normalized_path)
        if entry is None or not self._is_session_media_kind(entry.file_kind):
            return False
        if not self._select_session_media_file(entry):
            return False
        self.local_asr_transcribe_clicked(media_file=entry.path, force_full=True)
        return True

    def _start_online_asr_full_for_session_file(self, normalized_path: str) -> bool:
        entry = self._find_session_file_by_normalized_path(normalized_path)
        if entry is None or not self._is_session_media_kind(entry.file_kind):
            return False
        if not self._select_session_media_file(entry):
            return False

        option = self._online_asr_provider_option(self._get_online_asr_provider_id())
        status = self._online_asr_provider_credential_status(option)
        if status is None or status.state is not CredentialPresenceState.CONFIGURED:
            self.open_online_asr_settings_clicked()
            return False

        return bool(self._start_online_asr_transcription(entry.path))

    def _get_access_keys_added_provider_ids(self) -> tuple[str, ...]:
        result: list[str] = []
        seen: set[str] = set()
        for value in getattr(self, "access_keys_added_provider_ids", ()):
            entry_id = " ".join(str(value or "").split())
            if not entry_id or entry_id in seen:
                continue
            seen.add(entry_id)
            result.append(entry_id)
        self.access_keys_added_provider_ids = tuple(result)
        return self.access_keys_added_provider_ids

    def _set_access_keys_added_provider_ids(self, entry_ids: tuple[str, ...]) -> None:
        self.access_keys_added_provider_ids = tuple(entry_ids)
        self._persist_access_keys_added_provider_ids()

    def _persist_access_keys_added_provider_ids(self) -> bool:
        try:
            load_preferences = getattr(
                self.settings_manager,
                "load_preferences_only",
                self.settings_manager.load,
            )
            settings = load_preferences()
            settings.api_key = ""
            settings.access_keys_added_provider_ids = (
                self._get_access_keys_added_provider_ids()
            )
            return self.settings_manager.save(settings)
        except Exception:
            logger.error("Failed to persist Access & Keys provider list safely.")
            return False

    def _get_access_keys_validation_records(self) -> dict[str, dict[str, str]]:
        records = normalize_validation_records(
            getattr(self, "access_keys_validation_states", {}) or {}
        )
        self.access_keys_validation_states = validation_records_to_settings_dict(
            records
        )
        return dict(self.access_keys_validation_states)

    def _set_access_keys_validation_records(
        self,
        records: dict[str, dict[str, str]],
    ) -> None:
        normalized = normalize_validation_records(records)
        self.access_keys_validation_states = validation_records_to_settings_dict(
            normalized
        )
        self._persist_access_keys_validation_records()

    def _persist_access_keys_validation_records(self) -> bool:
        try:
            load_preferences = getattr(
                self.settings_manager,
                "load_preferences_only",
                self.settings_manager.load,
            )
            settings = load_preferences()
            settings.api_key = ""
            settings.access_keys_validation_states = (
                self._get_access_keys_validation_records()
            )
            return self.settings_manager.save(settings)
        except Exception:
            logger.error("Failed to persist Access & Keys validation state safely.")
            return False

    def _validate_cloud_asr_provider_key(
        self,
        provider_id: str,
        *,
        coordinator: ASRConnectionTestCoordinator | None = None,
        tester: object | None = None,
    ) -> ProviderKeyValidationRecord:
        normalized = (provider_id or "").strip()
        test_coordinator = coordinator or ASRConnectionTestCoordinator()
        trusted_tester = tester
        if trusted_tester is None and normalized == ELEVENLABS_SCRIBE_PROVIDER_ID:
            trusted_tester = ElevenLabsModelsListKeyValidator()
        failure_category = ""

        def safe_tester(provider: str, credential: str) -> object:
            nonlocal failure_category
            try:
                return trusted_tester(provider, credential)  # type: ignore[misc]
            except ElevenLabsKeyValidationError as exc:
                failure_category = exc.category
                raise

        result = test_coordinator.test_provider_connection(
            normalized,
            tester=safe_tester if trusted_tester is not None else None,
        )
        if result.status is ASRConnectionTestStatus.TESTER_COMPLETED:
            state = KEY_VALIDATION_VALIDATED
            diagnostic = "key_validation_succeeded"
        elif (
            result.status is ASRConnectionTestStatus.TESTER_FAILED
            and failure_category == ELEVENLABS_KEY_VALIDATION_AUTH_FAILED
        ):
            state = KEY_VALIDATION_FAILED
            diagnostic = ELEVENLABS_KEY_VALIDATION_AUTH_FAILED
        elif result.status is ASRConnectionTestStatus.CREDENTIAL_UNAVAILABLE:
            state = KEY_VALIDATION_NOT_CONFIGURED
            diagnostic = result.safe_diagnostic or "credential_unavailable"
        else:
            state = KEY_VALIDATION_COULD_NOT_COMPLETE
            diagnostic = (
                failure_category
                or
                result.safe_diagnostic
                or ELEVENLABS_KEY_VALIDATION_COULD_NOT_COMPLETE
            )
        return ProviderKeyValidationRecord(
            provider_id=normalized,
            state=state,
            checked_at_utc=current_utc_timestamp(),
            safe_diagnostic=diagnostic,
        )

    def _ensure_asr_cog_icons(self) -> None:
        """Load shared Local/Online ASR cog icons once."""
        if hasattr(self, "asr_cog_icon_image") and hasattr(self, "asr_cog_icon_hover_image"):
            return

        try:
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                asset_base_dir = sys._MEIPASS
            else:
                asset_base_dir = os.path.dirname(os.path.abspath(__file__))

            def _load_asr_cog_variant(filename: str):
                icon_path = os.path.join(asset_base_dir, "assets", filename)
                icon_image = Image.open(icon_path).convert("RGBA")
                icon_image = icon_image.resize(
                    (ASR_ACTION_BUTTON_SPEC["cog_width"], ASR_ACTION_BUTTON_SPEC["cog_height"]),
                    Image.LANCZOS,
                )
                return ImageTk.PhotoImage(icon_image)

            self.asr_cog_icon_image = _load_asr_cog_variant(
                ASR_ACTION_BUTTON_SPEC["cog_normal_asset"]
            )
            self.asr_cog_icon_hover_image = _load_asr_cog_variant(
                ASR_ACTION_BUTTON_SPEC["cog_hover_asset"]
            )

        except Exception as icon_error:
            logger.warning(f"Could not load ASR cog icons: {icon_error}")
            self.asr_cog_icon_image = None
            self.asr_cog_icon_hover_image = None

    def _create_asr_action_control(
        self,
        parent: object,
        *,
        text: str,
        command: object,
        settings_command: object,
        wrap_attr: str,
        button_attr: str,
        settings_attr: str,
    ) -> None:
        """Create a Local-ASR-style action button with matching cog behavior."""
        spec = ASR_ACTION_BUTTON_SPEC
        self._ensure_asr_cog_icons()

        button_wrap = ctk.CTkFrame(
            parent,
            fg_color="transparent",
            width=spec["wrap_width"],
            height=spec["wrap_height"],
        )
        button_wrap.pack(
            side="left",
            padx=spec["wrap_pack_padx"],
            pady=spec["wrap_pack_pady"],
        )
        button_wrap.pack_propagate(False)

        action_button = ctk.CTkButton(
            button_wrap,
            text=text,
            command=command,
            width=spec["button_width"],
            height=spec["button_height"],
            font=ctk.CTkFont(
                size=spec["button_font_size"],
                weight=spec["button_font_weight"],
            ),
            fg_color=COLORS[spec["button_fg_color_key"]],
            hover_color=COLORS[spec["button_hover_color_key"]],
            text_color=COLORS[spec["button_text_color_key"]],
            corner_radius=spec["button_corner_radius"],
            anchor=spec["button_anchor"],
        )
        action_button.place(x=0, y=0)

        if self.asr_cog_icon_image is not None:
            settings_button = tk.Label(
                button_wrap,
                image=self.asr_cog_icon_image,
                bg=COLORS["accent"],
                activebackground=COLORS["accent"],
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=0,
                pady=0,
                cursor="hand2",
            )
        else:
            settings_button = tk.Label(
                button_wrap,
                text=spec["fallback_cog_text"],
                bg=COLORS["accent"],
                fg=spec["fallback_cog_normal_fg"],
                activebackground=COLORS["accent"],
                activeforeground=spec["fallback_cog_hover_fg"],
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=0,
                pady=0,
                font=spec["fallback_cog_font"],
                cursor="hand2",
            )

        settings_button.place(
            x=spec["cog_x"],
            y=spec["cog_y"],
            width=spec["cog_width"],
            height=spec["cog_height"],
        )

        def _set_button_normal() -> None:
            try:
                action_button.configure(
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"],
                )
            except Exception:
                pass

            try:
                button_wrap.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                settings_button.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                if self.asr_cog_icon_image is not None:
                    settings_button.configure(image=self.asr_cog_icon_image)
                else:
                    settings_button.configure(fg=spec["fallback_cog_normal_fg"])
            except Exception:
                pass

        def _set_button_hover() -> None:
            try:
                action_button.configure(
                    fg_color=COLORS["accent_hover"],
                    hover_color=COLORS["accent_hover"],
                )
            except Exception:
                pass

            try:
                button_wrap.configure(bg=COLORS["accent_hover"])
            except Exception:
                pass

            try:
                settings_button.configure(bg=COLORS["accent_hover"])
            except Exception:
                pass

            try:
                if self.asr_cog_icon_image is not None:
                    settings_button.configure(image=self.asr_cog_icon_image)
                else:
                    settings_button.configure(fg=spec["fallback_cog_normal_fg"])
            except Exception:
                pass

        def _set_cog_icon_hover() -> None:
            try:
                action_button.configure(
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"],
                )
            except Exception:
                pass

            try:
                button_wrap.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                settings_button.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                if self.asr_cog_icon_hover_image is not None:
                    settings_button.configure(image=self.asr_cog_icon_hover_image)
                else:
                    settings_button.configure(fg=spec["fallback_cog_hover_fg"])
            except Exception:
                pass

        def _sync_hover_from_pointer() -> None:
            try:
                pointer_widget = self.winfo_containing(
                    self.winfo_pointerx(),
                    self.winfo_pointery(),
                )
            except Exception:
                pointer_widget = None

            if pointer_widget is settings_button:
                _set_cog_icon_hover()
                return

            if pointer_widget is action_button:
                _set_button_hover()
                return

            _set_button_normal()

        def _button_enter(_event=None):
            _set_button_hover()
            return None

        def _button_leave(_event=None):
            self.after(40, _sync_hover_from_pointer)
            return None

        def _cog_enter(_event=None):
            _set_cog_icon_hover()
            return "break"

        def _cog_leave(_event=None):
            self.after(40, _sync_hover_from_pointer)
            return "break"

        action_button.bind("<Enter>", _button_enter, add="+")
        action_button.bind("<Leave>", _button_leave, add="+")
        settings_button.bind("<Enter>", _cog_enter)
        settings_button.bind("<Leave>", _cog_leave)
        settings_button.bind("<Button-1>", lambda _event: settings_command())

        setattr(self, wrap_attr, button_wrap)
        setattr(self, button_attr, action_button)
        setattr(self, settings_attr, settings_button)

    def _create_youtube_settings_entry_section(self) -> None:
        """Create a compact entry for moving YouTube-only filters into settings."""
        self.youtube_settings_entry_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        self.youtube_settings_entry_frame.pack(fill="x", padx=20, pady=(12, 8))
        self.youtube_settings_entry_button = ctk.CTkButton(
            self.youtube_settings_entry_frame,
            text="YouTube settings",
            command=self._open_youtube_filter_settings_window,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=7,
        )
        self.youtube_settings_entry_button.pack(fill="x")

    def _create_hidden_youtube_filter_settings_state(self) -> None:
        """Create hidden controls so preferences load before the settings window opens."""
        self.youtube_filter_hidden_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        self._create_filters_section(self.youtube_filter_hidden_frame, show_label=False)
        self._create_date_section(self.youtube_filter_hidden_frame, show_label=False)

    def _open_youtube_filter_settings_window(self, row_id: str | None = None) -> None:
        """Open the combined YouTube settings window for media, comment/date filters, and custom filters."""
        row = self._source_row_by_id(row_id) if row_id else None
        prefs = self._youtube_preferences_for_row(row.row_id) if row is not None else None
        window = ctk.CTkToplevel(self)
        window.title("YouTube settings")
        window.geometry("560x700")
        window.transient(self)
        window.grab_set()

        header_text = "YouTube settings"
        if row is not None:
            header_text = f"YouTube settings\n{row.title}\n{row.domain}"
        header = ctk.CTkLabel(
            window,
            text=header_text,
            font=ctk.CTkFont(size=16 if row is None else 14, weight="bold"),
            text_color=COLORS["text_primary"],
            justify="left",
        )
        header.pack(anchor="w", padx=18, pady=(16, 4))
        subheader = ctk.CTkLabel(
            window,
            text="Media options, comment filters, date range, and custom filters for YouTube sources.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            justify="left",
        )
        subheader.pack(anchor="w", padx=18, pady=(0, 10))

        body = ctk.CTkScrollableFrame(window, fg_color=COLORS["bg_input"])
        body.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        if row is not None and prefs is not None:
            ctk.CTkLabel(
                body,
                text="YOUTUBE MEDIA",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_secondary"],
            ).pack(anchor="w", padx=8, pady=(10, 6))
            video_var = ctk.BooleanVar(value=prefs.video_enabled)
            audio_var = ctk.BooleanVar(value=prefs.separate_audio_enabled)
            thumbnail_var = ctk.BooleanVar(value=prefs.thumbnail_enabled)
            subtitles_var = ctk.BooleanVar(value=prefs.subtitles_enabled)
            auto_subs_var = ctk.BooleanVar(value=prefs.auto_subtitles_enabled)
            show_dropdown_var = ctk.BooleanVar(value=prefs.show_quality_dropdown)
            quality_enabled_vars: dict[str, Any] = {}
            quality_labels = tuple(label for label, _height in YOUTUBE_GUI_QUALITY_PRESETS)
            default_label = prefs.default_quality_label if prefs.default_quality_label in set(quality_labels) else "1080"
            default_var = ctk.StringVar(value=default_label)

            def apply_preferences() -> YouTubeGuiMediaPreferences:
                enabled_labels = tuple(
                    label
                    for label, _height in YOUTUBE_GUI_QUALITY_PRESETS
                    if quality_enabled_vars.get(label) is not None
                    and bool(quality_enabled_vars[label].get())
                )
                if not enabled_labels:
                    enabled_labels = (default_var.get() or "1080",)
                default_choice = default_var.get() or enabled_labels[0]
                saved_default = default_choice if default_choice in enabled_labels else enabled_labels[0]
                saved = YouTubeGuiMediaPreferences(
                    video_enabled=bool(video_var.get()),
                    separate_audio_enabled=bool(audio_var.get()),
                    thumbnail_enabled=bool(thumbnail_var.get()),
                    subtitles_enabled=bool(subtitles_var.get()),
                    auto_subtitles_enabled=bool(auto_subs_var.get()),
                    show_quality_dropdown=bool(show_dropdown_var.get()),
                    enabled_quality_labels=enabled_labels,
                    default_quality_label=saved_default,
                )
                self.youtube_source_row_preferences[row.row_id] = saved
                self._youtube_quality_var_for_row(row.row_id).set(saved.default_quality_label)
                self._refresh_source_resource_rows()
                if hasattr(self, "url_status"):
                    self.url_status.configure(
                        text="YouTube settings applied.",
                        text_color=COLORS["text_secondary"],
                    )
                return saved

            for text_value, var in (
                ("Muxed video + best audio (mp4)", video_var),
                ("Separate audio file (m4a)", audio_var),
                ("Thumbnail / image", thumbnail_var),
                ("Manual subtitle files", subtitles_var),
                ("Auto / ASR subtitle files", auto_subs_var),
                ("Show quality dropdown on YouTube source row", show_dropdown_var),
            ):
                ctk.CTkCheckBox(
                    body,
                    text=text_value,
                    variable=var,
                    command=apply_preferences,
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_primary"],
                ).pack(anchor="w", padx=8, pady=5)

            ctk.CTkLabel(
                body,
                text="Enabled quality options",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_primary"],
            ).pack(anchor="w", padx=8, pady=(12, 4))
            enabled = set(prefs.enabled_quality_labels)
            for label, _height in YOUTUBE_GUI_QUALITY_PRESETS:
                var = ctk.BooleanVar(value=label in enabled)
                quality_enabled_vars[label] = var
                ctk.CTkCheckBox(
                    body,
                    text=label,
                    variable=var,
                    command=apply_preferences,
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_primary"],
                ).pack(anchor="w", padx=24, pady=3)

            ctk.CTkLabel(
                body,
                text="Default quality",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_primary"],
            ).pack(anchor="w", padx=8, pady=(12, 4))
            ctk.CTkOptionMenu(
                body,
                variable=default_var,
                values=list(quality_labels),
                command=lambda _choice: apply_preferences(),
                width=140,
                fg_color=COLORS["bg_card"],
                button_color=COLORS["accent_secondary"],
                button_hover_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                dropdown_fg_color=COLORS["bg_card"],
                dropdown_hover_color=COLORS["accent_secondary"],
                dropdown_text_color=COLORS["text_primary"],
            ).pack(anchor="w", padx=8, pady=(0, 8))
        else:
            ctk.CTkLabel(
                body,
                text="YOUTUBE MEDIA\nOpen the cog on a YouTube source row to edit row-specific media and quality options.",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_secondary"],
                justify="left",
            ).pack(anchor="w", padx=8, pady=(10, 12))

        self._create_filters_section(body, show_label=True)
        self._create_date_section(body, show_label=True)
        self._create_custom_filters_section(body, show_label=True)
        self._update_filter_counts()

        button_row = ctk.CTkFrame(window, fg_color="transparent")
        button_row.pack(fill="x", padx=18, pady=(0, 16))
        ctk.CTkButton(
            button_row,
            text="Close",
            command=window.destroy,
            width=92,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        ).pack(side="right")

    def _create_filters_section(self, parent: object | None = None, *, show_label: bool = True) -> None:
        """Create filters section in sidebar."""
        parent = parent or self.sidebar_scroll
        if show_label:
            self._create_section_label(parent, "YOUTUBE FILTERS")

        filters_frame = ctk.CTkFrame(parent, fg_color="transparent")
        filters_frame.pack(fill="x", padx=20 if show_label else 0)

        # Spam filter toggle
        spam_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        spam_row.pack(fill="x", pady=(0, 8))

        if not hasattr(self, "spam_filter_var"):
            self.spam_filter_var = ctk.BooleanVar(value=False)
        self.spam_filter_checkbox = ctk.CTkSwitch(
            spam_row,
            text="Separate flagged spam",
            variable=self.spam_filter_var,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            button_hover_color=COLORS["text_secondary"],
            command=self._on_spam_filter_toggle
        )
        self.spam_filter_checkbox.pack(side="left")

        # Spam threshold
        threshold_frame = ctk.CTkFrame(filters_frame, fg_color="transparent")
        threshold_frame.pack(fill="x", pady=(0, 12))

        threshold_label_row = ctk.CTkFrame(threshold_frame, fg_color="transparent")
        threshold_label_row.pack(fill="x")

        self.spam_threshold_label = ctk.CTkLabel(
            threshold_label_row,
            text="Sensitivity",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.spam_threshold_label.pack(side="left")

        self.spam_threshold_value_label = ctk.CTkLabel(
            threshold_label_row,
            text="Moderate",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["accent"]
        )
        self.spam_threshold_value_label.pack(side="right")

        if not hasattr(self, "spam_threshold_var"):
            self.spam_threshold_var = ctk.DoubleVar(value=0.5)
        self.spam_threshold_slider = ctk.CTkSlider(
            threshold_frame,
            from_=0.2,
            to=0.8,
            number_of_steps=12,
            variable=self.spam_threshold_var,
            height=14,
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            button_hover_color=COLORS["accent_hover"],
            fg_color=COLORS["bg_input"],
            command=self._on_spam_threshold_change
        )
        self.spam_threshold_slider.pack(fill="x", pady=(4, 0))

        # Exclude creator toggle
        if not hasattr(self, "exclude_creator_var"):
            self.exclude_creator_var = ctk.BooleanVar(value=False)
        self.exclude_creator_checkbox = ctk.CTkSwitch(
            filters_frame,
            text="Exclude Creator",
            variable=self.exclude_creator_var,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            button_hover_color=COLORS["text_secondary"]
        )
        self.exclude_creator_checkbox.pack(anchor="w", pady=(0, 12))

        # Min likes
        min_likes_frame = ctk.CTkFrame(filters_frame, fg_color="transparent")
        min_likes_frame.pack(fill="x", pady=(0, 12))

        min_likes_label = ctk.CTkLabel(
            min_likes_frame,
            text="Min Likes",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"]
        )
        min_likes_label.pack(side="left")

        previous_min_likes = ""
        if hasattr(self, "min_likes_entry"):
            try:
                previous_min_likes = self.min_likes_entry.get()
            except Exception:
                previous_min_likes = ""
        self.min_likes_entry = ctk.CTkEntry(
            min_likes_frame,
            width=70,
            height=32,
            placeholder_text="0",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6,
            justify="center"
        )
        self.min_likes_entry.pack(side="right")
        self.min_likes_entry.insert(0, previous_min_likes or "0")

        # Max comments
        max_comments_frame = ctk.CTkFrame(filters_frame, fg_color="transparent")
        max_comments_frame.pack(fill="x", pady=(0, 12))

        max_comments_label = ctk.CTkLabel(
            max_comments_frame,
            text="Max Comments",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"]
        )
        max_comments_label.pack(side="left")

        previous_max_comments = ""
        if hasattr(self, "max_comments_entry"):
            try:
                previous_max_comments = self.max_comments_entry.get()
            except Exception:
                previous_max_comments = ""
        self.max_comments_entry = ctk.CTkEntry(
            max_comments_frame,
            width=70,
            height=32,
            placeholder_text="All",
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6,
            justify="center"
        )
        self.max_comments_entry.pack(side="right")
        if previous_max_comments:
            self.max_comments_entry.insert(0, previous_max_comments)

        max_comments_hint = ctk.CTkLabel(
            filters_frame,
            text="Leave empty for all; limits count comments + replies",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        max_comments_hint.pack(anchor="w", pady=(0, 12))

        # Sort by
        sort_frame = ctk.CTkFrame(filters_frame, fg_color="transparent")
        sort_frame.pack(fill="x", pady=(0, 12))

        sort_label = ctk.CTkLabel(
            sort_frame,
            text="Sort By",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"]
        )
        sort_label.pack(side="left")

        if not hasattr(self, "sort_var"):
            self.sort_var = ctk.StringVar(value="Date (Newest)")
        self.sort_dropdown = ctk.CTkOptionMenu(
            sort_frame,
            values=["Likes", "Date (Newest)", "Date (Oldest)"],
            variable=self.sort_var,
            width=120,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_secondary"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_secondary"],
            corner_radius=6
        )
        self.sort_dropdown.pack(side="right")

    def _create_date_section(self, parent: object | None = None, *, show_label: bool = True) -> None:
        """Create date range section in sidebar."""
        parent = parent or self.sidebar_scroll
        if show_label:
            self._create_section_label(parent, "DATE RANGE")

        date_frame = ctk.CTkFrame(parent, fg_color="transparent")
        date_frame.pack(fill="x", padx=20 if show_label else 0)

        # From date
        from_frame = ctk.CTkFrame(date_frame, fg_color="transparent")
        from_frame.pack(fill="x", pady=(0, 8))

        from_label = ctk.CTkLabel(
            from_frame,
            text="From",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            width=50,
            anchor="w"
        )
        from_label.pack(side="left")

        previous_from_date = ""
        if hasattr(self, "from_date_entry"):
            try:
                previous_from_date = self.from_date_entry.get()
            except Exception:
                previous_from_date = ""
        self.from_date_entry = ctk.CTkEntry(
            from_frame,
            placeholder_text="YYYY-MM-DD",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6
        )
        self.from_date_entry.pack(side="right", fill="x", expand=True)
        if previous_from_date:
            self.from_date_entry.insert(0, previous_from_date)

        # To date
        to_frame = ctk.CTkFrame(date_frame, fg_color="transparent")
        to_frame.pack(fill="x")

        to_label = ctk.CTkLabel(
            to_frame,
            text="To",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            width=50,
            anchor="w"
        )
        to_label.pack(side="left")

        previous_to_date = ""
        if hasattr(self, "to_date_entry"):
            try:
                previous_to_date = self.to_date_entry.get()
            except Exception:
                previous_to_date = ""
        self.to_date_entry = ctk.CTkEntry(
            to_frame,
            placeholder_text="YYYY-MM-DD",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6
        )
        self.to_date_entry.pack(side="right", fill="x", expand=True)
        if previous_to_date:
            self.to_date_entry.insert(0, previous_to_date)

        # Hint
        hint_label = ctk.CTkLabel(
            date_frame,
            text="Leave empty for no limit",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        hint_label.pack(anchor="w", pady=(6, 0))

    def _create_custom_filters_section(self, parent: object | None = None, *, show_label: bool = True) -> None:
        """Create custom blacklist/whitelist controls inside YouTube settings."""
        parent = parent or self.sidebar_scroll
        if show_label:
            self._create_section_label(parent, "CUSTOM FILTERS")

        custom_frame = ctk.CTkFrame(parent, fg_color="transparent")
        custom_frame.pack(fill="x", padx=20 if show_label else 0)

        # Blacklist button
        self.blacklist_button = ctk.CTkButton(
            custom_frame,
            text="🚫 Blacklist Patterns",
            command=self._open_blacklist_dialog,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            anchor="w"
        )
        self.blacklist_button.pack(fill="x", pady=(0, 8))

        # Whitelist button
        self.whitelist_button = ctk.CTkButton(
            custom_frame,
            text="✓ Whitelist Patterns",
            command=self._open_whitelist_dialog,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=6,
            anchor="w"
        )
        self.whitelist_button.pack(fill="x")

        # Pattern count label
        self.pattern_count_label = ctk.CTkLabel(
            custom_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        self.pattern_count_label.pack(anchor="w", pady=(6, 0))

    def _create_sidebar_footer(self) -> None:
        """Create sidebar footer with version."""
        footer_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", padx=20, pady=15)

        version_label = ctk.CTkLabel(
            footer_frame,
            text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        version_label.pack(side="left")

        shortcuts_label = ctk.CTkLabel(
            footer_frame,
            text="Ctrl+Enter: Fetch",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        shortcuts_label.pack(side="right")

        window_size_label = ctk.CTkLabel(
            footer_frame,
            text="  Ctrl+1/2/3: Size  F11: Max",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        window_size_label.pack(side="right", padx=(8, 0))

    # =========================================================================
    # MAIN CONTENT CREATION
    # =========================================================================

    def _create_main_content(self) -> None:
        """Create the scrollable main content area."""
        parent = getattr(self, "content_paned_window", self)
        if parent is self:
            main_parent = self
            row = 1
            column = 1
        else:
            self.main_workspace = ctk.CTkFrame(
                parent,
                fg_color="transparent",
            )
            self.main_workspace.grid_columnconfigure(0, weight=1)
            self.main_workspace.grid_rowconfigure(0, weight=1)
            parent.add(
                self.main_workspace,
                minsize=420,
                stretch="always",
            )
            main_parent = self.main_workspace
            row = 0
            column = 0
        self.main_frame = ctk.CTkScrollableFrame(
            main_parent,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_secondary"]
        )
        self.main_frame.grid(row=row, column=column, sticky="nsew", padx=6, pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(5, weight=0)

        self._create_url_section()
        self._create_progress_section()
        # The bulky central HOME Repository block is intentionally not rendered.
        # HOME controls and counters live in the compact left DATABASE / HOME area.
        self._create_text_editor_section()
        self._create_transcript_section()
        self._create_log_section()

    def _create_url_section(self) -> None:
        """Create URL input and action buttons section."""
        url_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        url_card.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        url_card.grid_columnconfigure(0, weight=1)

        # URL input area
        url_frame = ctk.CTkFrame(url_card, fg_color="transparent")
        url_frame.pack(fill="x", padx=10, pady=(5, 1))

        url_label = ctk.CTkLabel(
            url_frame,
            text="Source URLs",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        url_label.pack(anchor="e", pady=(0, 3))

        self.url_entry = ctk.CTkTextbox(
            url_frame,
            height=46,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8
        )
        self.url_entry.pack(fill="x")

        # Placeholder handling
        self._url_placeholder = (
            "Paste Source URLs here...\n\n"
            "Supported formats:\n"
            "- youtube.com/watch?v=...\n"
            "- youtu.be/...\n"
            "- youtube.com/shorts/...\n"
            "- msn.com news article URLs"
        )
        self.url_entry.insert("1.0", self._url_placeholder)
        self.url_entry.configure(text_color=COLORS["text_muted"])
        self.url_entry.bind("<FocusIn>", self._on_url_focus_in)
        self.url_entry.bind("<FocusOut>", self._on_url_focus_out)
        self.url_entry.bind("<KeyRelease>", self._validate_urls_live)
        self.url_entry.bind("<Return>", self._on_source_url_enter)
        self.url_entry.bind("<Shift-Return>", self._on_source_url_shift_enter)
        self.url_entry.bind("<Shift-KeyPress-Return>", self._on_source_url_shift_enter)

        self.source_hint_label = ctk.CTkLabel(
            url_frame,
            text=(
                "Press Enter to add URLs. Separate multiple URLs with spaces, "
                "commas, or new lines. Shift+Enter inserts a new line."
            ),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            wraplength=820,
            justify="right",
            anchor="e",
        )
        self.source_hint_label.pack(fill="x", anchor="e", pady=(2, 0))

        # URL status
        self.url_status = ctk.CTkLabel(
            url_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.url_status.pack(anchor="e", pady=(2, 0))

        self.source_rows_frame = ctk.CTkFrame(
            url_card,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.source_rows_frame.pack(fill="x", padx=10, pady=(3, 4))
        self._refresh_source_resource_rows()

        # Filter words section
        filter_words_frame = ctk.CTkFrame(url_card, fg_color="transparent")
        filter_words_frame.pack(fill="x", padx=12, pady=(0, 6))

        filter_words_header = ctk.CTkFrame(filter_words_frame, fg_color="transparent")
        filter_words_header.pack(fill="x")

        filter_words_label = ctk.CTkLabel(
            filter_words_header,
            text="🔍 Only fetch comments with these words",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="e",
            justify="right",
        )
        filter_words_label.pack(fill="x", anchor="e")

        filter_words_hint = ctk.CTkLabel(
            filter_words_header,
            text="Comma-separated, matches any word",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="e",
            justify="right",
        )
        filter_words_hint.pack(fill="x", anchor="e", pady=(1, 0))

        self.filter_words_entry = ctk.CTkEntry(
            filter_words_frame,
            height=36,
            placeholder_text="e.g., python, tutorial, beginner",
            justify="right",
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6
        )
        self.filter_words_entry.pack(fill="x", pady=(5, 0))

        # Action buttons area. Go stays on the left. The source dropdown,
        # source-mode checkboxes, Screenshot child rows, and TXT/CSV/Excel
        # exports form one compact right-side stack. This puts the tickboxes
        # directly above the export buttons instead of leaving them stranded in
        # the middle of the card when the FILES pane is widened.
        action_area = ctk.CTkFrame(url_card, fg_color="transparent")
        action_area.pack(fill="x", padx=10, pady=(0, 6))

        action_frame = ctk.CTkFrame(action_area, fg_color="transparent")
        action_frame.pack(fill="x")
        action_frame.grid_columnconfigure(0, weight=0)
        action_frame.grid_columnconfigure(1, weight=1)
        action_frame.grid_columnconfigure(2, weight=0)

        left_action_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        left_action_frame.grid(row=1, column=1, sticky="e", padx=(0, 8), pady=(0, 0))

        right_action_panel = ctk.CTkFrame(action_frame, fg_color="transparent")
        right_action_panel.grid(row=0, column=2, rowspan=4, sticky="e")
        right_action_panel.grid_columnconfigure(0, weight=1)

        self.discussion_source_var = ctk.StringVar(value="")
        self.discussion_source_menu = ctk.CTkOptionMenu(
            right_action_panel,
            variable=self.discussion_source_var,
            values=[""],
            command=self._on_discussion_source_selected,
            width=318,
            height=30,
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_secondary"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.discussion_source_menu.grid(row=0, column=0, sticky="e", pady=(0, 5))

        self.fetch_button = ctk.CTkButton(
            left_action_frame,
            text="▶ Go",
            command=self.start_fetching,
            width=100,
            height=34,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#000000",
            corner_radius=8,
        )
        self.fetch_button.grid(row=0, column=0, sticky="w")

        checkbox_frame = ctk.CTkFrame(right_action_panel, fg_color="transparent")
        checkbox_frame.grid(row=1, column=0, sticky="e", pady=(0, 5))
        for column in range(3):
            checkbox_frame.grid_columnconfigure(column, weight=0, minsize=94)

        webpage_column = ctk.CTkFrame(checkbox_frame, fg_color="transparent")
        webpage_column.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        comments_column = ctk.CTkFrame(checkbox_frame, fg_color="transparent")
        comments_column.grid(row=0, column=1, sticky="nw", padx=(0, 10))
        livechat_column = ctk.CTkFrame(checkbox_frame, fg_color="transparent")
        livechat_column.grid(row=0, column=2, sticky="nw")
        self.extract_webpage_var = ctk.BooleanVar(value=False)
        self.extract_comments_var = ctk.BooleanVar(value=False)
        self.extract_live_chat_var = ctk.BooleanVar(value=False)
        self.webpage_screenshot_var = ctk.BooleanVar(value=False)
        self.comments_screenshot_var = ctk.BooleanVar(value=False)
        self.livechat_screenshot_var = ctk.BooleanVar(value=False)

        self.webpage_checkbox = ctk.CTkCheckBox(
            webpage_column,
            text="Webpage",
            variable=self.extract_webpage_var,
            command=self._on_discussion_mode_changed,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000",
        )
        self.webpage_checkbox.pack(anchor="w")
        self.webpage_screenshot_checkbox = ctk.CTkCheckBox(
            webpage_column,
            text="Screenshot",
            variable=self.webpage_screenshot_var,
            command=self._on_discussion_mode_changed,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000",
        )
        self.webpage_screenshot_checkbox.pack(anchor="w", pady=(4, 0))
        self.webpage_screenshot_tooltip_text = (
            "Capture a screenshot of the selected webpage. "
            "Requires a future browser-capture implementation."
        )

        self.comments_checkbox = ctk.CTkCheckBox(
            comments_column,
            text="Comments",
            variable=self.extract_comments_var,
            command=self._on_discussion_mode_changed,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000",
        )
        self.comments_checkbox.pack(anchor="w")
        self.comments_screenshot_checkbox = ctk.CTkCheckBox(
            comments_column,
            text="Screenshot",
            variable=self.comments_screenshot_var,
            command=self._on_discussion_mode_changed,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000",
        )
        self.comments_screenshot_checkbox.pack(anchor="w", pady=(4, 0))

        self.live_chat_checkbox = ctk.CTkCheckBox(
            livechat_column,
            text="Livechat",
            variable=self.extract_live_chat_var,
            command=self._on_discussion_mode_changed,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000",
        )
        self.live_chat_checkbox.pack(anchor="w")
        self.livechat_screenshot_checkbox = ctk.CTkCheckBox(
            livechat_column,
            text="Screenshot",
            variable=self.livechat_screenshot_var,
            command=self._on_discussion_mode_changed,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000",
        )
        self.livechat_screenshot_checkbox.pack(anchor="w", pady=(4, 0))

        self.cancel_button = ctk.CTkButton(
            left_action_frame,
            text="⏹ Cancel",
            command=self.cancel_fetching,
            width=100,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["error"],
            hover_color=COLORS["accent_hover"],
            corner_radius=8,
        )

        export_frame = ctk.CTkFrame(right_action_panel, fg_color="transparent")
        export_frame.grid(row=2, column=0, sticky="e", pady=(0, 0))
        self.export_excel_button = ctk.CTkButton(
            export_frame,
            text="📊 Excel",
            command=self.export_excel,
            width=90,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled",
        )
        self.export_excel_button.pack(side="right")
        self.export_button = ctk.CTkButton(
            export_frame,
            text="📥 CSV",
            command=self.export_csv,
            width=90,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled",
        )
        self.export_button.pack(side="right", padx=(0, 10))
        self.export_txt_button = ctk.CTkButton(
            export_frame,
            text="📝 TXT",
            command=self.export_txt,
            width=90,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled",
        )
        self.export_txt_button.pack(side="right", padx=(0, 10))

        self.evidence_button = self.sidebar_evidence_button
        self.screenshot_button = _NoOpSidebarControl()
        self.open_last_package_button = _NoOpSidebarControl()
        self.clear_screenshots_button = _NoOpSidebarControl()
        self._refresh_discussion_source_controls()

        self.url_card = url_card
        url_card.bind("<Configure>", self._on_url_card_configure, add="+")

    def _on_url_card_configure(self, event=None) -> None:
        """Keep Source URL helper text inside the available card width."""
        try:
            width = max(220, int(getattr(event, "width", self.url_card.winfo_width())) - 40)
            self.source_hint_label.configure(wraplength=width)
        except Exception:
            pass

    @staticmethod
    def _widget_is_descendant(widget: object, ancestor: object) -> bool:
        current = widget
        while current is not None:
            if current is ancestor:
                return True
            current = getattr(current, "master", None)
        return False

    def _bind_main_pointer_wheel_router(self) -> None:
        """Route wheel events from blank main-workspace areas to the main page."""
        if self.__dict__.get("_main_pointer_wheel_bound", False):
            return
        self._main_pointer_wheel_bound = True
        try:
            self.bind_all("<MouseWheel>", self._route_main_pointer_wheel, add="+")
            self.bind_all("<Button-4>", self._route_main_pointer_wheel, add="+")
            self.bind_all("<Button-5>", self._route_main_pointer_wheel, add="+")
        except Exception:
            self._main_pointer_wheel_bound = False

    def _route_main_pointer_wheel(self, event) -> str | None:
        try:
            target = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        except Exception:
            target = getattr(event, "widget", None)
        if target is None:
            return None
        try:
            if target.winfo_toplevel() is not self:
                return None
        except Exception:
            return None
        if self._widget_is_descendant(target, getattr(self, "sidebar_scroll", None)):
            return None
        in_main_frame = self._widget_is_descendant(
            target, getattr(self, "main_frame", None)
        )
        in_main_workspace = self._widget_is_descendant(
            target, getattr(self, "main_workspace", None)
        )
        if not in_main_frame and not in_main_workspace:
            return None

        # Preserve native scrolling for text editors and explicitly scrollable children.
        current = target
        while current is not None and current is not getattr(self, "main_frame", None):
            class_name = current.__class__.__name__
            if class_name in {"Text", "CTkTextbox", "CTkScrollableFrame", "Listbox"}:
                return None
            current = getattr(current, "master", None)

        interactive_names = {
            "Button", "CTkButton", "Entry", "CTkEntry", "CTkOptionMenu",
            "CTkCheckBox", "CTkSlider", "Scale", "Scrollbar", "CTkScrollbar",
        }
        if target.__class__.__name__ in interactive_names:
            return None
        return self._scroll_main_frame_with_mousewheel(event)

    def _bind_main_blank_scroll_targets(self, root_widget: object) -> None:
        """Refresh dynamic main-area widgets without overriding child scrollers."""
        # The root-level pointer router handles these widgets. This method is a
        # deliberate hook for dynamic source-row refreshes and test coverage.
        _ = root_widget

    def _create_progress_section(self) -> None:
        """Create the progress indicator section."""
        self.progress_section = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_section.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        # Status row
        status_row = ctk.CTkFrame(self.progress_section, fg_color="transparent")
        status_row.pack(fill="x")

        self.status_label = ctk.CTkLabel(
            status_row,
            text="Ready to fetch comments",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.status_label.pack(side="left")

        self.stats_label = ctk.CTkLabel(
            status_row,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.stats_label.pack(side="right")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.progress_section,
            height=6,
            corner_radius=3,
            fg_color=COLORS["bg_card"],
            progress_color=COLORS["accent"]
        )
        self.progress_bar.pack(fill="x", pady=(8, 0))
        self.progress_bar.set(0)

        self.editor_toggle_row = ctk.CTkFrame(self.progress_section, fg_color="transparent")
        self.editor_toggle_row.pack(fill="x", pady=(8, 0))
        self.editor_toggle_row.grid_columnconfigure(0, weight=1)
        self.editor_toggle_button_frame = ctk.CTkFrame(self.editor_toggle_row, fg_color="transparent")
        self.editor_toggle_button_frame.grid(row=0, column=1, sticky="e")

        self.show_transcript_panel_button = ctk.CTkButton(
            self.editor_toggle_button_frame,
            text="Transcript",
            command=self._toggle_transcript_panel,
            width=105,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
        )
        self.show_transcript_panel_button.pack(side="left")

        self.show_text_editor_panel_button = ctk.CTkButton(
            self.editor_toggle_button_frame,
            text="Text Editor",
            command=self._toggle_text_editor_panel,
            width=115,
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
        )
        self.show_text_editor_panel_button.pack(side="left", padx=(8, 0))

    def _show_transcript_panel(self) -> None:
        if hasattr(self, "transcript_card"):
            self.transcript_card.grid()
            try:
                self.show_transcript_panel_button.configure(fg_color=COLORS["accent"])
            except Exception:
                pass

    def _hide_transcript_panel(self) -> None:
        if hasattr(self, "transcript_card"):
            self.transcript_card.grid_remove()
            try:
                self.show_transcript_panel_button.configure(fg_color=COLORS["accent_secondary"])
            except Exception:
                pass

    def _toggle_transcript_panel(self) -> None:
        if not hasattr(self, "transcript_card"):
            return
        if self.transcript_card.winfo_ismapped():
            self._hide_transcript_panel()
        else:
            self._show_transcript_panel()

    def _show_text_editor_panel(self) -> None:
        if hasattr(self, "text_editor_card"):
            self.text_editor_card.grid()
            try:
                self.show_text_editor_panel_button.configure(fg_color=COLORS["accent"])
            except Exception:
                pass

    def _hide_text_editor_panel(self) -> None:
        if hasattr(self, "text_editor_card"):
            self._hide_text_editor_spell_popup()
            self.text_editor_card.grid_remove()
            try:
                self.show_text_editor_panel_button.configure(fg_color=COLORS["accent_secondary"])
            except Exception:
                pass

    def _toggle_text_editor_panel(self) -> None:
        if not hasattr(self, "text_editor_card"):
            return
        if self.text_editor_card.winfo_ismapped():
            self._hide_text_editor_panel()
        else:
            self._show_text_editor_panel()

    def _create_profile_media_database_workbench_panel(self) -> None:
        """Create the main Database-mode workbench panel.

        This is main-content UI, not a sidebar mini view.  It renders
        explicit Database-mode state only and does not scan, move, rename, copy,
        retrieve media, auto-label, or infer sensitive identifiers.
        """
        self.profile_media_database_workbench_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.profile_media_database_workbench_card.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.profile_media_database_workbench_card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.profile_media_database_workbench_card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 8))

        self.profile_media_database_panel_title_label = ctk.CTkLabel(
            header,
            text="HOME",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        self.profile_media_database_panel_title_label.pack(side="left")

        self.profile_media_database_panel_status_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
        )
        self.profile_media_database_panel_status_label.pack(side="left", padx=(12, 0))

        self.profile_media_database_panel_refresh_button = ctk.CTkButton(
            header,
            text="",
            command=self._refresh_profile_media_database_workbench_panel,
            width=1,
            height=1,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=7,
        )
        # V76K2: no common-user Refresh button; the HOME panel syncs after Add / Import, SAVE, and Unload.
        self.profile_media_database_panel_refresh_button.pack_forget()

        self.profile_media_database_panel_batch_button = ctk.CTkButton(
            header,
            text="Add / Import",
            command=self._select_profile_media_database_batch_json_files,
            width=104,
            height=28,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=7,
        )
        self.profile_media_database_panel_batch_button.pack(side="right", padx=(0, 6))

        self.profile_media_database_panel_clear_button = ctk.CTkButton(
            header,
            text="Unload",
            command=self._clear_profile_media_database_batch_json_files,
            width=74,
            height=28,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=7,
        )
        self.profile_media_database_panel_clear_button.pack(side="right", padx=(0, 6))

        self.profile_media_database_panel_materialize_button = ctk.CTkButton(
            header,
            text="Save to HOME",
            command=self._materialize_profile_media_database_selected_batches,
            width=112,
            height=28,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=7,
        )
        self.profile_media_database_panel_materialize_button.pack(side="right", padx=(0, 6))

        self.profile_media_database_panel_subtitle_label = ctk.CTkLabel(
            self.profile_media_database_workbench_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
            justify="left",
            wraplength=880,
        )
        self.profile_media_database_panel_subtitle_label.pack(fill="x", padx=15, pady=(0, 8))

        metrics_frame = ctk.CTkFrame(self.profile_media_database_workbench_card, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=15, pady=(0, 8))
        self.profile_media_database_panel_metric_labels = {}
        for column, key in enumerate(("primary_sources", "secondary_sources", "tertiary_sources", "persons")):
            metrics_frame.grid_columnconfigure(column, weight=1)
            metric_label = ctk.CTkLabel(
                metrics_frame,
                text="",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS["text_primary"],
                fg_color=COLORS["bg_input"],
                corner_radius=7,
                padx=8,
                pady=8,
            )
            metric_label.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            self.profile_media_database_panel_metric_labels[key] = metric_label

        review_frame = ctk.CTkFrame(self.profile_media_database_workbench_card, fg_color="transparent")
        review_frame.pack(fill="x", padx=15, pady=(0, 8))
        self.profile_media_database_panel_review_labels = {}
        for column, key in enumerate(("review_items", "safe_no_download", "safe_no_inference")):
            review_frame.grid_columnconfigure(column, weight=1)
            review_label = ctk.CTkLabel(
                review_frame,
                text="",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"],
                fg_color=COLORS["bg_input"],
                corner_radius=7,
                padx=8,
                pady=6,
            )
            review_label.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            self.profile_media_database_panel_review_labels[key] = review_label

        self.profile_media_database_panel_notice_label = ctk.CTkLabel(
            self.profile_media_database_workbench_card,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
            anchor="w",
            justify="left",
            wraplength=880,
        )
        self.profile_media_database_panel_notice_label.pack(fill="x", padx=15, pady=(0, 12))

        self._refresh_profile_media_database_workbench_panel()

    def _refresh_profile_media_database_workbench_panel(self) -> None:
        """Refresh the main Database panel using explicit safe presenter state only."""
        card = getattr(self, "profile_media_database_workbench_card", None)
        mode = self._coerce_profile_media_sidebar_mode()
        if card is not None:
            if mode == "DATABASE":
                try:
                    card.grid()
                except Exception:
                    pass
            else:
                try:
                    card.grid_remove()
                except Exception:
                    pass

        try:
            from profile_media_database_workbench_panel import build_profile_media_database_gui_panel_state

            state = build_profile_media_database_gui_panel_state(
                mode=mode,
                database_root=getattr(self, "profile_media_database_root", ""),
                batch_json_files=getattr(self, "profile_media_database_batch_json_files", ()),
                workbench_payload=getattr(self, "profile_media_database_workbench_payload", None),
            )
            self.profile_media_database_panel_state = state
        except Exception:
            logger.debug("Could not build profile/media Database GUI panel state.", exc_info=True)
            state = None

        if state is None:
            return

        try:
            display_status = "HOME / ready" if state.status == "success" else "HOME / add sources" if state.status in ("ready_for_import", "ready_no_home_selection") else f"{state.mode} / {state.status}"
            metrics = {metric.key: metric for metric in state.metrics}
            display_metrics = {metric.key: metric for metric in getattr(state, "display_metrics", ())}

            if card is not None:
                self.profile_media_database_panel_status_label.configure(text=display_status)
                self.profile_media_database_panel_subtitle_label.configure(text=state.subtitle)
                for key, label_widget in getattr(self, "profile_media_database_panel_metric_labels", {}).items():
                    metric = display_metrics.get(key) or metrics.get(key)
                    label_widget.configure(text=f"{metric.label}: {metric.value}" if metric else "")

                lanes = {lane.key: lane for lane in state.review_lanes}
                review_metric = display_metrics.get("review_items") or metrics.get("review_items")
                for key, label_widget in getattr(self, "profile_media_database_panel_review_labels", {}).items():
                    if key == "review_items" and review_metric is not None:
                        label_widget.configure(text=f"{review_metric.label}: {review_metric.value}")
                    elif key == "safe_no_download":
                        label_widget.configure(text="No media download")
                    elif key == "safe_no_inference":
                        label_widget.configure(text="No sensitive inference")
                    else:
                        lane = lanes.get(key)
                        label_widget.configure(text=f"{lane.label}: {lane.value}" if lane else "")

                notices = "\n".join(state.notices[:3])
                self.profile_media_database_panel_notice_label.configure(text=notices)

            for key, label_widget in getattr(self, "profile_media_database_sidebar_summary_labels", {}).items():
                metric = display_metrics.get(key) or metrics.get(key)
                if metric is not None:
                    label_widget.configure(text=self._profile_media_sidebar_metric_text(key, metric.label, metric.value))
            self._refresh_profile_media_home_sidebar_buttons()
        except Exception:
            logger.debug("Could not refresh profile/media Database GUI panel widgets.", exc_info=True)

    def _build_profile_media_database_workbench_payload_from_batches(self, batch_json_files: tuple[str, ...], database_root: str) -> dict[str, object] | None:
        """Build workbench payload from selected internal import files."""
        if not batch_json_files:
            return None
        from profile_media_database_session import ProfileMediaDatabaseSessionConfig
        from profile_media_database_workbench import build_workbench_state, workbench_payload

        config = ProfileMediaDatabaseSessionConfig(
            database_root=database_root,
            batch_json_files=batch_json_files,
            mode="DATABASE",
        )
        return workbench_payload(build_workbench_state(config), include_text=False)

    def _load_profile_media_database_saved_gui_state_for_startup(self) -> None:
        """Load saved explicit Database GUI state without scanning folders."""
        try:
            from profile_media_database_gui_controller import (
                build_database_gui_selection_from_saved_state,
                database_gui_selection_result_payload,
            )
            from profile_media_database_gui_state_store import default_profile_media_database_gui_state_path

            state_path = default_profile_media_database_gui_state_path()
            self.profile_media_database_gui_state_path = state_path
            result = build_database_gui_selection_from_saved_state(state_path=state_path)
            self.profile_media_database_gui_state_payload = database_gui_selection_result_payload(result)
            if result.batch_json_files:
                self.profile_media_database_batch_json_files = result.batch_json_files
                self.profile_media_database_root = result.database_root or getattr(self, "profile_media_database_root", "")
                self.profile_media_database_workbench_payload = dict(result.workbench_payload) if result.workbench_payload else None
                self.profile_media_database_batch_import_result = (
                    result.import_result.to_dict() if result.import_result else None
                )
        except Exception:
            logger.debug("Could not load saved profile/media Database GUI state.", exc_info=True)

    def _select_profile_media_database_batch_json_files(self) -> None:
        """Add/import an internal Profile-Media package; JSON remains an implementation detail."""
        try:
            selected = filedialog.askopenfilenames(
                title="Add / Import Profile-Media source package",
                filetypes=(("Profile-Media import files", "*.json"), ("All files", "*.*")),
            )
        except Exception:
            logger.debug("Could not open profile/media Database import selector.", exc_info=True)
            return

        batch_json_files = tuple(str(item) for item in selected if str(item).strip())
        if not batch_json_files:
            return

        try:
            from profile_media_database_gui_controller import (
                build_database_gui_selection_from_batch_json,
                database_gui_selection_result_payload,
            )
            from profile_media_database_gui_state_store import (
                PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
                default_profile_media_database_gui_state_path,
            )

            state_path = getattr(self, "profile_media_database_gui_state_path", None) or default_profile_media_database_gui_state_path()
            self.profile_media_database_gui_state_path = state_path
            result = build_database_gui_selection_from_batch_json(
                batch_json_files,
                database_root=getattr(self, "profile_media_database_root", ""),
                state_path=state_path,
                persist_state=True,
                confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
            )
            self.profile_media_database_gui_state_payload = database_gui_selection_result_payload(result)
            self.profile_media_database_batch_import_result = (
                result.import_result.to_dict() if result.import_result else None
            )
            self.profile_media_database_batch_json_files = result.batch_json_files
            self.profile_media_database_root = result.database_root or getattr(self, "profile_media_database_root", "")
            self.profile_media_database_workbench_payload = dict(result.workbench_payload) if result.workbench_payload else None
            self._set_profile_media_sidebar_mode("DATABASE", update_widget=True)
            self._refresh_profile_media_database_workbench_panel()
            self.log_message(
                f"Profile/media HOME loaded {len(self.profile_media_database_batch_json_files)} import package(s). "
                "No folder scan or filesystem mutation was performed.",
                "info",
            )
        except Exception as exc:
            logger.debug("Could not load profile/media Database import files.", exc_info=True)
            try:
                messagebox.showerror("Database import", f"Could not load selected import files: {exc}")
            except Exception:
                pass

    def _clear_profile_media_database_batch_json_files(self) -> None:
        """Unload the main Database HOME selection without deleting any files."""
        try:
            from profile_media_database_gui_controller import (
                build_database_gui_clear_selection,
                database_gui_selection_result_payload,
            )
            from profile_media_database_gui_state_store import (
                PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION,
                default_profile_media_database_gui_state_path,
            )

            state_path = getattr(self, "profile_media_database_gui_state_path", None) or default_profile_media_database_gui_state_path()
            self.profile_media_database_gui_state_path = state_path
            result = build_database_gui_clear_selection(
                state_path=state_path,
                clear_persisted_state=True,
                confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION,
            )
            self.profile_media_database_gui_state_payload = database_gui_selection_result_payload(result)
        except Exception:
            logger.debug("Could not clear profile/media Database GUI state file.", exc_info=True)

        self.profile_media_database_batch_json_files = ()
        self.profile_media_database_workbench_payload = None
        self.profile_media_database_batch_import_result = None
        self._refresh_profile_media_database_workbench_panel()
        try:
            self.log_message(
                "Profile/media HOME import unloaded. Source files and saved repository folders were not deleted.",
                "info",
            )
        except Exception:
            pass


    def _save_profile_media_database_to_home_repository(self) -> None:
        """Common-user SAVE action for the managed Profile/Media HOME repository."""
        return self._materialize_profile_media_database_selected_batches()

    def _unload_profile_media_database_home_selection(self) -> None:
        """Common-user Unload action for the current Profile/Media HOME selection."""
        return self._clear_profile_media_database_batch_json_files()

    def _import_profile_media_database_home_selection(self) -> None:
        """Common-user Import action for adding Profile/Media source material."""
        return self._select_profile_media_database_batch_json_files()

    def _materialize_profile_media_database_selected_batches(self) -> None:
        """Guarded save/create-folders flow for explicit Database HOME selections."""
        batch_json_files = tuple(getattr(self, "profile_media_database_batch_json_files", ()) or ())
        if not batch_json_files:
            try:
                messagebox.showinfo("Database SAVE", "Add/import source material before saving to the HOME repository.")
            except Exception:
                pass
            return

        database_root = str(getattr(self, "profile_media_database_root", "") or "").strip()
        if not database_root:
            try:
                selected_root = filedialog.askdirectory(title="Select Profile/Media HOME repository")
            except Exception:
                selected_root = ""
            database_root = str(selected_root or "").strip()
            if not database_root:
                return

        try:
            from profile_media_database_materialize_workflow import (
                PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
                apply_database_materialize_plan,
                build_database_materialize_plan,
                materialize_workflow_payload,
                render_database_materialize_plan_text,
            )
        except Exception as exc:
            logger.debug("Could not import profile/media HOME save workflow.", exc_info=True)
            try:
                messagebox.showerror("Database SAVE", f"SAVE workflow is unavailable: {exc}")
            except Exception:
                pass
            return

        try:
            preview_plan = build_database_materialize_plan(database_root=database_root, batch_json_files=batch_json_files)
            preview_text = render_database_materialize_plan_text(preview_plan)
            prompt = (
                preview_text[:2400]
                + "\n\nType this exact phrase to save reviewed folders and metadata into HOME:\n"
                + PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION
            )
            confirmation = simpledialog.askstring("Confirm Database SAVE", prompt)
            if confirmation != PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION:
                self.profile_media_database_materialize_result = materialize_workflow_payload(
                    apply_database_materialize_plan(
                        build_database_materialize_plan(
                            database_root=database_root,
                            batch_json_files=batch_json_files,
                            execute=True,
                            confirmation_phrase=str(confirmation or ""),
                        )
                    ),
                    plan=preview_plan,
                )
                try:
                    messagebox.showwarning("Database SAVE", "SAVE blocked because the exact confirmation phrase was not entered.")
                except Exception:
                    pass
                return

            execute_plan = build_database_materialize_plan(
                database_root=database_root,
                batch_json_files=batch_json_files,
                execute=True,
                confirmation_phrase=confirmation,
            )
            result = apply_database_materialize_plan(execute_plan)
            self.profile_media_database_materialize_result = materialize_workflow_payload(result, plan=execute_plan)
            self.profile_media_database_root = database_root
            self._refresh_profile_media_database_workbench_panel()
            try:
                self.log_message(
                    f"Profile/media HOME SAVE result: {result.status}; "
                    f"created_folders={len(result.created_directories)}; saved_metadata_files={len(result.written_files)}. "
                    "No folder scan, move, rename, media copy, download, automatic classification, or sensitive inference was performed.",
                    "info" if result.status == "materialized" else "warning",
                )
            except Exception:
                pass
            if result.status != "materialized":
                try:
                    messagebox.showwarning("Database SAVE", f"SAVE did not complete: {result.status}")
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("Profile/media Database SAVE failed.", exc_info=True)
            try:
                messagebox.showerror("Database SAVE", f"SAVE failed: {exc}")
            except Exception:
                pass


    def _create_text_editor_section(self) -> None:
        """Create an in-app plain text editor panel."""
        self.text_editor_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.text_editor_card.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        self.text_editor_card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self.text_editor_card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 8))

        self.text_editor_title_label = ctk.CTkLabel(
            header,
            text="📝 Text Editor",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            cursor="hand2",
        )
        self.text_editor_title_label.pack(side="right")
        self.text_editor_title_label.bind("<Button-1>", lambda _event: self._toggle_text_editor_panel(), add="+")

        self.text_editor_status_label = ctk.CTkLabel(
            header,
            text="No text file loaded",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
        )
        self.text_editor_status_label.pack(side="right", padx=(0, 12))

        action_row = ctk.CTkFrame(self.text_editor_card, fg_color="transparent")
        action_row.pack(anchor="e", padx=15, pady=(0, 8))

        self.text_editor_save_button = ctk.CTkButton(
            action_row,
            text="Save",
            command=self._save_text_editor_file,
            width=80,
            height=30,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled",
        )
        self.text_editor_save_button.pack(side="left")

        self.text_editor_external_open_button = ctk.CTkButton(
            action_row,
            text="Open externally",
            command=lambda: self._open_session_file_external(getattr(self, "active_text_editor_file_path", "")),
            width=120,
            height=30,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled",
        )
        self.text_editor_external_open_button.pack(side="left", padx=(8, 0))

        self.text_editor_textbox = ctk.CTkTextbox(
            self.text_editor_card,
            height=220,
            font=ctk.CTkFont(family="Cascadia Mono", size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            wrap="word",
        )
        self.text_editor_textbox.pack(fill="x", padx=15, pady=(0, 10))
        self.text_editor_textbox.insert("1.0", "Open a .txt file from FILES with the TXT icon.")
        self._configure_text_editor_undo_redo()
        self.text_editor_textbox.configure(state="disabled")
        self.active_text_editor_file_path = ""
        self.text_editor_spell_after_id = None
        self.text_editor_spell_popup = None
        self.text_editor_spell_popup_key = ""
        self.text_editor_spell_popup_bridge_bounds: tuple[int, int, int, int] | None = None
        self.text_editor_spell_popup_hide_after_id = None
        self.text_editor_active_spelling_word = ""
        self.text_editor_active_spelling_start = ""
        self.text_editor_active_spelling_end = ""
        self.text_editor_custom_dictionary: set[str] = set()
        self.text_editor_spellchecker = None
        self._bind_text_editor_spellcheck()
        self.text_editor_card.grid_remove()

    def _handle_text_editor_key_press(self, event: Any) -> None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return
        try:
            key = str(getattr(event, "keysym", "") or "")
            if len(str(getattr(event, "char", "") or "")) == 1 or key in {
                "BackSpace",
                "Delete",
                "Return",
                "space",
                "Tab",
            }:
                self._hide_text_editor_spell_popup()
                widget.edit_separator()
        except Exception:
            logger.debug("Could not add pre-edit Text Editor undo separator.", exc_info=True)

    def _handle_text_editor_key_release(self, event: Any) -> None:
        self._schedule_text_editor_spellcheck()
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return
        try:
            key = str(getattr(event, "keysym", "") or "")
            if len(str(getattr(event, "char", "") or "")) == 1 or key in {
                "BackSpace",
                "Delete",
                "Return",
                "space",
                "Tab",
            }:
                widget.edit_separator()
        except Exception:
            logger.debug("Could not add Text Editor undo separator.", exc_info=True)

    def _configure_text_editor_undo_redo(self) -> None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return
        try:
            widget.configure(undo=True, maxundo=-1, autoseparators=True)
        except Exception:
            logger.debug("Could not enable Text Editor undo stack.", exc_info=True)
        try:
            widget.bind("<Control-z>", lambda event: self._text_editor_undo(event), add="+")
            widget.bind("<Control-Z>", lambda event: self._text_editor_undo(event), add="+")
            widget.bind("<Control-y>", lambda event: self._text_editor_redo(event), add="+")
            widget.bind("<Control-Y>", lambda event: self._text_editor_redo(event), add="+")
        except Exception:
            logger.debug("Could not bind Text Editor undo/redo shortcuts.", exc_info=True)

    def _text_editor_undo(self, _event: Any = None) -> str:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return "break"
        try:
            widget.edit_undo()
        except tk.TclError:
            pass
        return "break"

    def _text_editor_redo(self, _event: Any = None) -> str:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return "break"
        try:
            widget.edit_redo()
        except tk.TclError:
            pass
        return "break"

    def _load_session_text_editor_file(self, normalized_path: str) -> None:
        entry = self._find_session_file_by_normalized_path(normalized_path)
        if entry is None:
            return
        try:
            text_content = Path(entry.path).read_text(encoding="utf-8", errors="replace")
        except Exception as error:
            self.log_message(f"Text Editor could not open file: {error}", "error")
            messagebox.showerror("Text Editor", str(error), parent=self)
            return
        self.active_text_editor_file_path = entry.normalized_path
        self._show_text_editor_panel()
        self.text_editor_textbox.configure(state="normal")
        self.text_editor_textbox.delete("1.0", "end")
        self.text_editor_textbox.insert("1.0", text_content)
        try:
            self._get_text_editor_text_widget().edit_reset()
        except Exception:
            pass
        self.text_editor_status_label.configure(text=entry.display_name)
        self.text_editor_save_button.configure(state="normal")
        self.text_editor_external_open_button.configure(state="normal")
        self._hide_text_editor_spell_popup()
        self._schedule_text_editor_spellcheck()
        self.log_message(f"Opened text file in Text Editor: {entry.display_name}", "success")

    def _save_text_editor_file(self) -> None:
        entry = self._find_session_file_by_normalized_path(getattr(self, "active_text_editor_file_path", ""))
        if entry is None:
            return
        try:
            content = self.text_editor_textbox.get("1.0", "end-1c")
            Path(entry.path).write_text(content, encoding="utf-8")
        except Exception as error:
            self.log_message(f"Text Editor save failed: {error}", "error")
            messagebox.showerror("Text Editor", str(error), parent=self)
            return
        try:
            self._get_text_editor_text_widget().edit_modified(False)
        except Exception:
            pass
        self._schedule_text_editor_spellcheck()
        self.log_message(f"Saved text file: {entry.display_name}", "success")

    def _get_text_editor_text_widget(self) -> Any:
        return getattr(getattr(self, "text_editor_textbox", None), "_textbox", getattr(self, "text_editor_textbox", None))

    def _bind_text_editor_spellcheck(self) -> None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return
        try:
            widget.bind("<KeyPress>", self._handle_text_editor_key_press, add="+")
            widget.bind("<KeyRelease>", self._handle_text_editor_key_release, add="+")
            widget.bind("<Button-1>", self._handle_text_editor_spell_click, add="+")
            widget.bind("<Escape>", lambda _event: (self._hide_text_editor_spell_popup(), "break")[1], add="+")
            widget.bind("<MouseWheel>", lambda _event: self._hide_text_editor_spell_popup(), add="+")
            widget.bind("<Button-4>", lambda _event: self._hide_text_editor_spell_popup(), add="+")
            widget.bind("<Button-5>", lambda _event: self._hide_text_editor_spell_popup(), add="+")
            # Motion-based hover is more reliable than tag-enter alone when
            # the app window is resized, restored, or not maximised.
            widget.bind("<Motion>", self._handle_text_editor_spell_motion, add="+")
            widget.bind("<Leave>", lambda _event: self._schedule_hide_text_editor_spell_popup(500), add="+")
            self.bind("<Unmap>", self._handle_text_editor_spell_app_unmap, add="+")
            self.bind("<FocusOut>", self._handle_text_editor_spell_app_focus_out, add="+")
        except Exception:
            logger.debug("Could not bind Text Editor spell-check events.", exc_info=True)

    def _default_text_editor_spell_words(self) -> set[str]:
        words = """
        a able about above across action actions active add added after again all allow allowed
        already also an and any app application are as asr at audio auto available back be because
        been before below best both button by can cannot car cars channel check clear click clicked
        clicking collapse collapsed comment comments completed content correct could create created
        date default description dictionary do does done download downloaded editor empty entry export
        external externally file files folder folders for from go good has have hidden icon image
        import in inside internal into is it item items jdownloader label line link links load loaded
        local media metadata move moved name new no not of on one online open opened opens or other
        output package path panel plain project quality queue ready remove removed rename root row save
        saved selected session should show source status subtitle subtitles text the them there this
        title to transcript txt ungroup updated upload url urls use video views with within word wrong
        yes your you youtube ytce

        after before between both but by can could did do does done each either every for from had
        has have having he her here him his how i if in into is it its itself just like may me more
        most my no nor not now of off on once only or other our out over own same she should so some
        such than that the their theirs them then there these they this those through to too under up
        very was we were what when where which while who whom why will with would you your yours

        title channel subscribers date views description source selected quality music original auto
        generated released provided project game soundtrack bandai namco tekken sunset

        png jpg jpeg gif bmp webp images accepted drag drop dragging dropped spell checker spelling
        weird behaviour behavior hovering hover amount meant underlined underline red opens opened
        small window popup upwards line inline description actually implement implemented corrector
        correction cursor away close closes closed menu dictionary details source details filetype
        metadata transcript editor notepad external saved saving clickable visible invisible hidden
        default reset both appear appears appeared disappear disappears copy copies copied copying
        paste pastes pasted pasting cuts cut undo redo select selected selecting prints printed friendly
        pdf inspect accessibility properties chatbot languages check checking checked words worded cursor
        delayed delay deactivate activated activation effect effects result results still working works
        misspelled misspelling misspellings checker popup box boxes window windows hover hovering
        underline underlines underlined style pattern same above below line inline exact ordinary
        """
        return {word.strip().lower() for word in words.split() if word.strip()}

    def _text_editor_spell_words(self) -> set[str]:
        if not hasattr(self, "text_editor_spell_words"):
            self.text_editor_spell_words = self._default_text_editor_spell_words()
        return set(getattr(self, "text_editor_spell_words", set())) | set(
            getattr(self, "text_editor_custom_dictionary", set())
        )

    def _get_text_editor_spellchecker(self) -> Any:
        """Return optional pyspellchecker engine when installed.

        The app stays usable without the package, but installing pyspellchecker
        gives proper English word coverage instead of relying on a tiny fallback
        list.
        """
        if hasattr(self, "text_editor_spellchecker"):
            return getattr(self, "text_editor_spellchecker")
        try:
            from spellchecker import SpellChecker  # type: ignore

            self.text_editor_spellchecker = SpellChecker(language="en")
        except Exception:
            self.text_editor_spellchecker = None
        return getattr(self, "text_editor_spellchecker")

    def _text_editor_word_is_known(self, lowered: str) -> bool:
        if not lowered:
            return True
        if lowered in self._text_editor_spell_words():
            return True
        checker = self._get_text_editor_spellchecker()
        if checker is None:
            return False
        try:
            return not checker.unknown([lowered])
        except Exception:
            return False

    def _text_editor_line_is_spellcheck_exempt(self, line_text: str) -> bool:
        line = str(line_text or "").strip()
        if not line:
            return False
        lowered = line.lower()
        metadata_prefixes = (
            "title:",
            "channel:",
            "subscribers:",
            "date:",
            "views:",
            "description:",
            "source:",
            "selected quality:",
            "selected files:",
            "selected components:",
            "plan files:",
            "ytce youtube media queue",
        )
        if lowered.startswith(metadata_prefixes):
            return True
        if re.search(r"https?://|www\.", lowered):
            return True
        if re.search(r"(^|\s)[a-zA-Z]:[\\/]", line):
            return True
        if "\\\\" in line or re.search(r"[\\/][A-Za-z0-9_. -]+[\\/]", line):
            return True
        return False

    def _should_spellcheck_word(self, word: str, *, line_text: str = "", line_offset: int = -1) -> bool:
        if line_text and self._text_editor_line_is_spellcheck_exempt(line_text):
            return False
        if len(word) < 3:
            return False
        if any(ch.isdigit() for ch in word):
            return False
        lowered = word.lower().strip("'")
        if lowered.startswith(("http", "www")):
            return False
        if any(char in word for char in "/?=&:._-\\"):
            return False
        if word.isupper() and len(word) <= 8:
            return False
        # Treat proper nouns / CamelCase / project tokens conservatively.
        if any(char.isupper() for char in word[1:]):
            return False
        if word[:1].isupper() and lowered not in self._text_editor_spell_words():
            return False
        # Do not mark metadata keys such as "Title:" or "Description:".
        if line_text and line_offset >= 0:
            colon_index = line_text.find(":")
            if colon_index != -1 and line_offset < colon_index:
                return False
        return bool(re.search(r"[A-Za-z]", word))

    def _looks_like_text_editor_gibberish(self, word: str) -> bool:
        lowered = re.sub(r"[^a-z]", "", str(word or "").lower())
        if len(lowered) < 4:
            return False
        if self._text_editor_word_is_known(lowered):
            return False
        keyboard_mash_clusters = (
            "asd",
            "sda",
            "das",
            "dsa",
            "sdf",
            "fds",
            "dsf",
            "dfg",
            "gfd",
            "gfa",
            "fga",
            "qwe",
            "ewq",
            "wer",
            "zxc",
            "xcv",
            "jkl",
            "vqe",
            "qfe",
            "oyf",
            "yfg",
        )
        if any(cluster in lowered for cluster in keyboard_mash_clusters):
            return True
        vowels = sum(1 for char in lowered if char in "aeiou")
        consonants = len(lowered) - vowels
        if vowels <= 1 and consonants >= 4:
            return True
        if re.search(r"[^aeiou]{4,}", lowered):
            return True
        # Repeated non-word-looking fragments such as adasd/dasda/gfafa.
        if len(lowered) <= 8 and len(set(lowered)) <= 4:
            return True
        # Long lower-case unknown words with few normal English bigrams are usually
        # pasted/typed gibberish in this editor; pyspellchecker handles normal words.
        common_bigrams = (
            "th", "he", "in", "er", "an", "re", "on", "at", "en", "nd", "ti", "es",
            "or", "te", "of", "ed", "is", "it", "al", "ar", "st", "to", "nt", "ng",
            "se", "ha", "as", "ou", "io", "le", "ve", "co", "me", "de", "hi", "ri",
            "ro", "ic", "ne", "ea", "ra", "ce", "li", "ch", "ll", "be", "ma", "si",
            "om", "ur", "ca", "el", "ta", "la", "ns", "di", "fo", "ho", "pe", "ec",
            "pr", "no", "ct",
        )
        if len(lowered) >= 6 and sum(1 for pair in common_bigrams if pair in lowered) <= 1:
            return True
        return False

    def _text_editor_manual_spelling_corrections(self) -> dict[str, List[str]]:
        return {
            "cobuld": ["could"],
            "woudl": ["would"],
            "teh": ["the"],
            "recieve": ["receive"],
            "seperate": ["separate"],
        }

    def _text_editor_spell_suggestions(self, word: str) -> List[str]:
        import difflib

        lowered = word.lower()
        manual = self._text_editor_manual_spelling_corrections()
        if lowered in manual:
            return [
                suggestion.capitalize() if word[:1].isupper() else suggestion
                for suggestion in manual[lowered]
            ]

        suggestions: List[str] = []
        checker = self._get_text_editor_spellchecker()
        if checker is not None:
            try:
                correction = checker.correction(lowered)
                candidates = sorted(checker.candidates(lowered) or [])
                ordered = []
                if correction:
                    ordered.append(correction)
                ordered.extend(candidate for candidate in candidates if candidate not in ordered)
                for candidate in ordered:
                    if candidate == lowered:
                        continue
                    if len(lowered) >= 4 and candidate[:1] != lowered[:1]:
                        continue
                    suggestions.append(candidate.capitalize() if word[:1].isupper() else candidate)
                    if len(suggestions) >= 4:
                        return suggestions
            except Exception:
                logger.debug("pyspellchecker suggestion lookup failed.", exc_info=True)

        matches = difflib.get_close_matches(
            lowered,
            sorted(self._text_editor_spell_words()),
            n=4,
            cutoff=0.84,
        )
        for match in matches:
            if match == lowered:
                continue
            # Avoid unrelated suggestions like copies -> opens.
            if len(lowered) >= 4 and match[:1] != lowered[:1]:
                continue
            suggestions.append(match.capitalize() if word[:1].isupper() else match)
        return suggestions

    def _schedule_text_editor_spellcheck(self) -> None:
        if not hasattr(self, "text_editor_textbox"):
            return
        previous = getattr(self, "text_editor_spell_after_id", None)
        if previous:
            try:
                self.after_cancel(previous)
            except Exception:
                pass
        self.text_editor_spell_after_id = self.after(300, self._run_text_editor_spellcheck)

    def _clear_text_editor_spell_tags(self) -> None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return
        try:
            for tag_name in tuple(widget.tag_names()):
                if str(tag_name).startswith("spell_error_"):
                    widget.tag_delete(tag_name)
        except Exception:
            logger.debug("Could not clear Text Editor spelling tags.", exc_info=True)

    def _run_text_editor_spellcheck(self) -> None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return
        self.text_editor_spell_after_id = None
        try:
            if str(widget.cget("state")) == "disabled":
                return
        except Exception:
            pass
        self._clear_text_editor_spell_tags()
        try:
            content = widget.get("1.0", "end-1c")
        except Exception:
            return
        dictionary = self._text_editor_spell_words()
        manual_corrections = self._text_editor_manual_spelling_corrections()
        line_starts: List[int] = []
        offset = 0
        for line in content.splitlines(True):
            line_starts.append(offset)
            offset += len(line)
        match_index = 0
        for line_number, line_start in enumerate(line_starts, start=1):
            line_end = line_starts[line_number] if line_number < len(line_starts) else len(content)
            line_text = content[line_start:line_end]
            for match in re.finditer(r"\b[A-Za-z][A-Za-z']*[A-Za-z]\b", line_text):
                word = match.group(0)
                lowered = word.lower().strip("'")
                if not self._should_spellcheck_word(word, line_text=line_text, line_offset=match.start()):
                    continue
                if lowered in dictionary:
                    continue
                is_known_misspelling = lowered in manual_corrections
                is_gibberish = self._looks_like_text_editor_gibberish(word)
                checker = self._get_text_editor_spellchecker()
                if checker is not None and not is_known_misspelling and not is_gibberish:
                    if self._text_editor_word_is_known(lowered):
                        continue
                    # With pyspellchecker installed, plain lower-case unknown
                    # words are safe to underline. This catches gibberish such as
                    # adasd/gfafa even when there is no good correction candidate.
                    if not word.islower() or len(lowered) < 4:
                        suggestions = self._text_editor_spell_suggestions(word)
                        if not suggestions:
                            continue
                elif not is_known_misspelling and not is_gibberish:
                    continue
                suggestions = self._text_editor_spell_suggestions(word)
                start = f"{line_number}.{match.start()}"
                end = f"{line_number}.{match.end()}"
                tag_name = f"spell_error_{match_index}"
                match_index += 1
                try:
                    widget.tag_add(tag_name, start, end)
                    self._configure_text_editor_spell_tag(widget, tag_name)
                    widget.tag_bind(
                        tag_name,
                        "<Enter>",
                        lambda event, w=word, s=start, e=end: self._show_text_editor_spell_popup(w, s, e, event),
                    )
                    widget.tag_bind(
                        tag_name,
                        "<Leave>",
                        lambda _event: self._cancel_hide_text_editor_spell_popup(),
                    )
                    widget.tag_bind(
                        tag_name,
                        "<Button-1>",
                        lambda event, w=word, s=start, e=end: self._show_text_editor_spell_popup(w, s, e, event),
                    )
                    widget.tag_bind(
                        tag_name,
                        "<Button-3>",
                        lambda event, w=word, s=start, e=end: self._show_text_editor_spell_popup(w, s, e, event),
                    )
                except Exception:
                    logger.debug("Could not tag Text Editor spelling error.", exc_info=True)

    def _configure_text_editor_spell_tag(self, widget: Any, tag_name: str) -> None:
        """Try to use a red underline without changing text colour.

        Tk 8.7 supports underlinefg. Older Tk builds do not, so the fallback is
        still a straight underline using the widget default colour.
        """
        try:
            widget.tag_configure(tag_name, underline=True, underlinefg="#ff4d4d")
        except Exception:
            try:
                widget.tag_configure(tag_name, underline=True)
            except Exception:
                pass

    def _cancel_hide_text_editor_spell_popup(self) -> None:
        after_id = getattr(self, "text_editor_spell_popup_hide_after_id", None)
        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self.text_editor_spell_popup_hide_after_id = None

    def _handle_text_editor_spell_app_unmap(self, event: Any) -> None:
        if getattr(event, "widget", None) is self:
            self._hide_text_editor_spell_popup()

    def _handle_text_editor_spell_app_focus_out(self, event: Any) -> None:
        widget = getattr(event, "widget", None)
        popup = getattr(self, "text_editor_spell_popup", None)
        try:
            if popup is not None and (widget is popup or str(widget).startswith(str(popup))):
                return
        except Exception:
            pass
        self._hide_text_editor_spell_popup()

    def _schedule_hide_text_editor_spell_popup(self, delay_ms: int = 0) -> None:
        self._cancel_hide_text_editor_spell_popup()
        if delay_ms <= 0:
            self._hide_text_editor_spell_popup()
            return
        self.text_editor_spell_popup_hide_after_id = self.after(
            delay_ms,
            self._hide_text_editor_spell_popup,
        )

    def _text_editor_spell_tag_range_at_index(self, index: str) -> tuple[str, str, str]:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return "", "", ""
        try:
            for tag_name in widget.tag_names(index):
                tag_text = str(tag_name)
                if not tag_text.startswith("spell_error_"):
                    continue
                ranges = widget.tag_ranges(tag_text)
                for start_index, end_index in zip(ranges[0::2], ranges[1::2]):
                    start = str(start_index)
                    end = str(end_index)
                    if widget.compare(start, "<=", index) and widget.compare(index, "<=", end):
                        return tag_text, start, end
        except Exception:
            logger.debug("Could not resolve spelling tag under cursor.", exc_info=True)
        return "", "", ""

    def _text_editor_pointer_in_spell_popup_bridge(self, event: Any) -> bool:
        try:
            x = int(getattr(event, "x_root", 0))
            y = int(getattr(event, "y_root", 0))
        except Exception:
            return False

        popup = getattr(self, "text_editor_spell_popup", None)
        if popup is not None:
            try:
                px1 = popup.winfo_rootx()
                py1 = popup.winfo_rooty()
                px2 = px1 + popup.winfo_width()
                py2 = py1 + popup.winfo_height()
                if px1 - 20 <= x <= px2 + 20 and py1 - 20 <= y <= py2 + 20:
                    return True
            except Exception:
                pass

        bounds = getattr(self, "text_editor_spell_popup_bridge_bounds", None)
        if not bounds:
            return False
        try:
            x1, y1, x2, y2 = bounds
            return x1 <= x <= x2 and y1 <= y <= y2
        except Exception:
            return False

    def _handle_text_editor_spell_motion(self, event: Any) -> str | None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return None
        try:
            index = widget.index(f"@{event.x},{event.y}")
            _tag_name, start, end = self._text_editor_spell_tag_range_at_index(index)
            if not start or not end:
                if getattr(self, "text_editor_spell_popup", None) is not None and not self._text_editor_pointer_in_spell_popup_bridge(event):
                    self._hide_text_editor_spell_popup()
                return None
            word = widget.get(start, end).strip()
            if not word:
                self._hide_text_editor_spell_popup()
                return None
            return self._show_text_editor_spell_popup(word, start, end, event)
        except Exception:
            logger.debug("Text Editor spell motion failed.", exc_info=True)
        return None

    def _handle_text_editor_spell_click(self, event: Any) -> str | None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return None
        try:
            index = widget.index(f"@{event.x},{event.y}")
            _tag_name, start, end = self._text_editor_spell_tag_range_at_index(index)
            if not start or not end:
                self._hide_text_editor_spell_popup()
                return None
            word = widget.get(start, end).strip()
            if not word:
                self._hide_text_editor_spell_popup()
                return None
            return self._show_text_editor_spell_popup(word, start, end, event)
        except Exception:
            logger.debug("Text Editor spell click failed.", exc_info=True)
            self._hide_text_editor_spell_popup()
        return None

    def _text_editor_spell_popup_position(self, start: str, popup_width: int, popup_height: int, event: Any) -> tuple[int, int]:
        widget = self._get_text_editor_text_widget()
        card = getattr(self, "text_editor_card", None)
        fallback_x = max(8, int(getattr(event, "x", 0)) + 10)
        fallback_y = max(8, int(getattr(event, "y", 0)) + 18)
        if widget is None or card is None:
            return fallback_x, fallback_y
        try:
            bbox = widget.bbox(start)
            if not bbox:
                return fallback_x, fallback_y
            x, y, _width, height = bbox
            word_root_x = widget.winfo_rootx() + x
            word_root_y = widget.winfo_rooty() + y
            card_root_x = card.winfo_rootx()
            card_root_y = card.winfo_rooty()
            card_width = max(240, card.winfo_width())
            card_height = max(120, card.winfo_height())
            popup_x = max(8, min(word_root_x - card_root_x, card_width - popup_width - 8))
            below_y = word_root_y - card_root_y + height + 10
            above_y = max(8, word_root_y - card_root_y - popup_height - 10)
            popup_y = below_y if below_y + popup_height + 8 < card_height else above_y
            return (popup_x, popup_y)
        except Exception:
            return fallback_x, fallback_y

    def _hide_text_editor_spell_popup(self) -> None:
        self._cancel_hide_text_editor_spell_popup()
        popup = getattr(self, "text_editor_spell_popup", None)
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass
        self.text_editor_active_spelling_word = ""
        self.text_editor_active_spelling_start = ""
        self.text_editor_active_spelling_end = ""
        self.text_editor_spell_popup = None
        self.text_editor_spell_popup_key = ""
        self.text_editor_spell_popup_bridge_bounds = None

    def _replace_text_editor_misspelling(self, start: str, end: str, replacement: str) -> None:
        widget = self._get_text_editor_text_widget()
        if widget is None:
            return
        try:
            widget.edit_separator()
            widget.delete(start, end)
            widget.insert(start, replacement)
            widget.edit_separator()
        except Exception as error:
            self.log_message(f"Spelling replacement failed: {error}", "error")
            return
        self._hide_text_editor_spell_popup()
        self._schedule_text_editor_spellcheck()

    def _add_text_editor_spelling_word(self, word: str) -> None:
        cleaned = str(word or "").lower().strip("'")
        if cleaned:
            self.text_editor_custom_dictionary.add(cleaned)
        self._hide_text_editor_spell_popup()
        self._schedule_text_editor_spellcheck()

    def _show_text_editor_spell_popup(self, word: str, start: str, end: str, event: Any) -> str:
        popup_key = f"{start}:{end}:{word}"
        existing_popup = getattr(self, "text_editor_spell_popup", None)
        existing_popup_alive = False
        if existing_popup is not None:
            try:
                existing_popup_alive = bool(existing_popup.winfo_exists())
            except Exception:
                existing_popup_alive = False
        if (
            existing_popup_alive
            and getattr(self, "text_editor_spell_popup_key", "") == popup_key
            and getattr(self, "text_editor_active_spelling_word", "")
        ):
            self._cancel_hide_text_editor_spell_popup()
            return "break"
        self._hide_text_editor_spell_popup()
        self.text_editor_spell_popup_key = popup_key
        self.text_editor_active_spelling_word = word
        self.text_editor_active_spelling_start = start
        self.text_editor_active_spelling_end = end
        suggestions = self._text_editor_spell_suggestions(word)

        parent = getattr(self, "text_editor_card", None)
        if parent is None:
            return "break"
        popup = tk.Frame(
            parent,
            bg=COLORS["bg_input"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            bd=0,
        )

        rows = [("Add to Dictionary", lambda w=word: self._add_text_editor_spelling_word(w))]
        rows.extend(
            (suggestion, lambda value=suggestion, s=start, e=end: self._replace_text_editor_misspelling(s, e, value))
            for suggestion in suggestions[:4]
        )

        def _button_enter(button: tk.Button) -> None:
            button.configure(bg=COLORS["accent"], fg=COLORS["bg_dark"])

        def _button_leave(button: tk.Button) -> None:
            button.configure(bg=COLORS["bg_input"], fg=COLORS["text_primary"])

        for index, (label, command) in enumerate(rows):
            button = tk.Button(
                popup,
                text=label,
                anchor="w",
                command=command,
                bg=COLORS["bg_input"],
                fg=COLORS["text_primary"],
                activebackground=COLORS["accent"],
                activeforeground=COLORS["bg_dark"],
                relief="flat",
                bd=0,
                padx=10,
                pady=4,
                font=("Segoe UI", 10),
                cursor="hand2",
            )
            button.bind("<Enter>", lambda _event, item=button: _button_enter(item), add="+")
            button.bind("<Leave>", lambda _event, item=button: _button_leave(item), add="+")
            button.pack(fill="x")
            if index == 0 and len(rows) > 1:
                separator = tk.Frame(popup, height=1, bg=COLORS["border"])
                separator.pack(fill="x", padx=6, pady=(1, 1))

        popup.bind("<Escape>", lambda _event: self._hide_text_editor_spell_popup())
        popup.bind("<Enter>", lambda _event: self._cancel_hide_text_editor_spell_popup(), add="+")
        popup.bind("<Leave>", lambda _event: self._schedule_hide_text_editor_spell_popup(350), add="+")
        popup.bind("<Button-1>", lambda _event: self._cancel_hide_text_editor_spell_popup(), add="+")

        self.text_editor_spell_popup = popup
        popup.update_idletasks()
        popup_width = max(150, min(240, popup.winfo_reqwidth()))
        popup_height = max(30, popup.winfo_reqheight())
        x, y = self._text_editor_spell_popup_position(start, popup_width, popup_height, event)
        popup.place(x=x, y=y, width=popup_width)
        popup.lift()
        try:
            x1 = popup.winfo_rootx() - 18
            y1 = popup.winfo_rooty() - 18
            x2 = x1 + popup_width + 36
            y2 = y1 + popup_height + 36
            self.text_editor_spell_popup_bridge_bounds = (x1, y1, x2, y2)
        except Exception:
            self.text_editor_spell_popup_bridge_bounds = None
        return "break"

    def _create_transcript_section(self) -> None:
        """Create transcript import/export section."""
        self.transcript_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.transcript_card.grid(row=4, column=0, sticky="ew", pady=(0, 15))
        self.transcript_card.grid_columnconfigure(0, weight=1)

        # Header row
        header = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 8))

        self.transcript_title_label = ctk.CTkLabel(
            header,
            text="🗣 Transcript",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            cursor="hand2",
        )
        self.transcript_title_label.pack(side="right")
        self.transcript_title_label.bind("<Button-1>", lambda _event: self._toggle_transcript_panel(), add="+")

        self.transcript_stats_label = ctk.CTkLabel(
            header,
            text="No transcript loaded",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.transcript_stats_label.pack(side="right", padx=(0, 12))

        # Keep the existing transcript controls grouped as a compact block, but
        # place that whole block on the right side where there is unused space.
        self.transcript_controls_panel = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        self.transcript_controls_panel.pack(anchor="e", padx=15, pady=(0, 8))

        # Button row
        button_row = ctk.CTkFrame(self.transcript_controls_panel, fg_color="transparent")
        button_row.pack(anchor="e", padx=15, pady=(0, 8))

        self.transcript_import_button = ctk.CTkButton(
            button_row,
            text="📂 Import",
            command=self.import_transcript_file,
            width=90,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8
        )
        self.transcript_import_button.pack(side="left")

        self.transcript_youtube_button = ctk.CTkButton(
            button_row,
            text="Get",
            command=self.download_youtube_transcript_clicked,
            width=105,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8
        )
        self.transcript_get_tooltip_text = (
            "Get transcript or source content. Current runtime support remains limited."
        )
        self.transcript_youtube_button.pack(side="left", padx=(8, 0))

        asr_button_row = ctk.CTkFrame(self.transcript_controls_panel, fg_color="transparent")
        asr_button_row.pack(anchor="e", padx=15, pady=(0, 8))

        self.transcript_asr_button_wrap = ctk.CTkFrame(
            asr_button_row,
            fg_color="transparent",
            width=150,
            height=36
        )
        self.transcript_asr_button_wrap.pack(side="left", padx=3, pady=3)
        self.transcript_asr_button_wrap.pack_propagate(False)

        self.transcript_asr_button = ctk.CTkButton(
            self.transcript_asr_button_wrap,
            text="🎙 Local ASR",
            command=self.local_asr_transcribe_clicked,
            width=150,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            anchor="w"
        )
        self.transcript_asr_button.place(x=0, y=0)

        # Transparent PNG cog over the Local ASR button.
        # The cog has its own icon-only hover: the button hover and cog hover
        # are intentionally separated.
        try:
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                asset_base_dir = sys._MEIPASS
            else:
                asset_base_dir = os.path.dirname(os.path.abspath(__file__))

            def _load_asr_cog_variant(filename: str):
                icon_path = os.path.join(asset_base_dir, "assets", filename)
                icon_image = Image.open(icon_path).convert("RGBA")
                icon_image = icon_image.resize((24, 24), Image.LANCZOS)
                return ImageTk.PhotoImage(icon_image)

            self.asr_cog_icon_image = _load_asr_cog_variant("asr_cog_normal.png")
            self.asr_cog_icon_hover_image = _load_asr_cog_variant("asr_cog_hover.png")

        except Exception as icon_error:
            logger.warning(f"Could not load ASR cog icons: {icon_error}")
            self.asr_cog_icon_image = None
            self.asr_cog_icon_hover_image = None

        if self.asr_cog_icon_image is not None:
            self.transcript_asr_settings_button = tk.Label(
                self.transcript_asr_button_wrap,
                image=self.asr_cog_icon_image,
                bg=COLORS["accent"],
                activebackground=COLORS["accent"],
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=0,
                pady=0,
                cursor="hand2"
            )
        else:
            self.transcript_asr_settings_button = tk.Label(
                self.transcript_asr_button_wrap,
                text="⚙",
                bg=COLORS["accent"],
                fg="#5f5f5f",
                activebackground=COLORS["accent"],
                activeforeground="#2f2f2f",
                bd=0,
                relief="flat",
                highlightthickness=0,
                padx=0,
                pady=0,
                font=("Segoe UI Symbol", 13, "bold"),
                cursor="hand2"
            )

        self.transcript_asr_settings_button.place(x=121, y=4, width=24, height=24)

        def _set_local_asr_button_normal() -> None:
            try:
                self.transcript_asr_button.configure(
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"]
                )
            except Exception:
                pass

            try:
                self.transcript_asr_button_wrap.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                self.transcript_asr_settings_button.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                if self.asr_cog_icon_image is not None:
                    self.transcript_asr_settings_button.configure(
                        image=self.asr_cog_icon_image
                    )
                else:
                    self.transcript_asr_settings_button.configure(fg="#5f5f5f")
            except Exception:
                pass

        def _set_local_asr_button_hover() -> None:
            try:
                self.transcript_asr_button.configure(
                    fg_color=COLORS["accent_hover"],
                    hover_color=COLORS["accent_hover"]
                )
            except Exception:
                pass

            try:
                self.transcript_asr_button_wrap.configure(bg=COLORS["accent_hover"])
            except Exception:
                pass

            try:
                self.transcript_asr_settings_button.configure(bg=COLORS["accent_hover"])
            except Exception:
                pass

            try:
                if self.asr_cog_icon_image is not None:
                    self.transcript_asr_settings_button.configure(
                        image=self.asr_cog_icon_image
                    )
                else:
                    self.transcript_asr_settings_button.configure(fg="#5f5f5f")
            except Exception:
                pass

        def _set_asr_cog_icon_hover() -> None:
            # Cog hover is icon-only. Button background stays normal orange.
            try:
                self.transcript_asr_button.configure(
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"]
                )
            except Exception:
                pass

            try:
                self.transcript_asr_button_wrap.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                self.transcript_asr_settings_button.configure(bg=COLORS["accent"])
            except Exception:
                pass

            try:
                if self.asr_cog_icon_hover_image is not None:
                    self.transcript_asr_settings_button.configure(
                        image=self.asr_cog_icon_hover_image
                    )
                else:
                    self.transcript_asr_settings_button.configure(fg="#2f2f2f")
            except Exception:
                pass

        def _sync_asr_hover_from_pointer() -> None:
            try:
                pointer_widget = self.winfo_containing(
                    self.winfo_pointerx(),
                    self.winfo_pointery()
                )
            except Exception:
                pointer_widget = None

            if pointer_widget is self.transcript_asr_settings_button:
                _set_asr_cog_icon_hover()
                return

            if pointer_widget is self.transcript_asr_button:
                _set_local_asr_button_hover()
                return

            _set_local_asr_button_normal()

        def _asr_button_enter(_event=None):
            _set_local_asr_button_hover()
            return None

        def _asr_button_leave(_event=None):
            self.after(40, _sync_asr_hover_from_pointer)
            return None

        def _asr_cog_enter(_event=None):
            _set_asr_cog_icon_hover()
            return "break"

        def _asr_cog_leave(_event=None):
            self.after(40, _sync_asr_hover_from_pointer)
            return "break"

        self.transcript_asr_button.bind("<Enter>", _asr_button_enter, add="+")
        self.transcript_asr_button.bind("<Leave>", _asr_button_leave, add="+")

        self.transcript_asr_settings_button.bind("<Enter>", _asr_cog_enter)
        self.transcript_asr_settings_button.bind("<Leave>", _asr_cog_leave)
        self.transcript_asr_settings_button.bind(
            "<Button-1>",
            lambda _event: self.open_asr_settings_clicked()
        )

        self._create_asr_action_control(
            asr_button_row,
            text=ONLINE_ASR_BUTTON_TEXT,
            command=self.online_asr_transcribe_clicked,
            settings_command=self.open_online_asr_settings_clicked,
            wrap_attr="transcript_online_asr_button_wrap",
            button_attr="transcript_online_asr_button",
            settings_attr="transcript_online_asr_settings_button",
        )


        self.transcript_media_button = ctk.CTkButton(
            asr_button_row,
            text="🎞 Media",
            command=self.choose_transcript_media_file,
            width=95,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8
        )
        self.transcript_media_button.pack(side="left", padx=(8, 0))
        self.transcript_media_button.configure(state="disabled")
        self.transcript_media_button.pack_forget()

        self.transcript_media_status_label = ctk.CTkLabel(
            asr_button_row,
            text="No media",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        self.transcript_media_status_label.pack(side="left", padx=(8, 0))

        self.transcript_media_clear_button = ctk.CTkButton(
            asr_button_row,
            text="✕",
            command=self.clear_transcript_media_link,
            width=28,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=6
        )
        self.transcript_media_clear_button.pack(side="left", padx=(4, 0))

        # Transcript editor tools row
        transcript_edit_row = ctk.CTkFrame(self.transcript_controls_panel, fg_color="transparent")
        transcript_edit_row.pack(anchor="e", padx=15, pady=(0, 8))

        self.transcript_rename_button = ctk.CTkButton(
            transcript_edit_row,
            text="👤 Rename",
            command=self.rename_transcript_speaker,
            width=110,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_rename_button.pack(side="left", padx=(8, 0))

        self.transcript_create_speaker_button = ctk.CTkButton(
            transcript_edit_row,
            text="➕ Create Speaker",
            command=self.create_transcript_speaker,
            width=135,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_create_speaker_button.pack(side="left", padx=(8, 0))

        self.transcript_edit_segment_button = ctk.CTkButton(
            transcript_edit_row,
            text="✏ Segment",
            command=self.edit_transcript_segment_speaker,
            width=105,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_edit_segment_button.pack(side="left", padx=(8, 0))

        transcript_merge_row = ctk.CTkFrame(self.transcript_controls_panel, fg_color="transparent")
        transcript_merge_row.pack(anchor="e", padx=15, pady=(0, 8))

        self.transcript_merge_up_button = ctk.CTkButton(
            transcript_merge_row,
            text="↑ Merge Up",
            command=self.merge_selected_transcript_segment_up,
            width=115,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_merge_up_button.pack(side="left", padx=(8, 0))

        self.transcript_merge_down_button = ctk.CTkButton(
            transcript_merge_row,
            text="↓ Merge Down",
            command=self.merge_selected_transcript_segment_down,
            width=130,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_merge_down_button.pack(side="left", padx=(8, 0))

        self.transcript_clear_button = ctk.CTkButton(
            transcript_merge_row,
            text="Clear",
            command=self.clear_transcript,
            width=70,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_clear_button.pack(side="left", padx=(8, 0))

        # Transcript export row
        transcript_export_row = ctk.CTkFrame(self.transcript_controls_panel, fg_color="transparent")
        transcript_export_row.pack(anchor="e", padx=15, pady=(2, 8))

        export_label = ctk.CTkLabel(
            transcript_export_row,
            text="Export:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        export_label.pack(side="left")

        self.transcript_export_txt_button = ctk.CTkButton(
            transcript_export_row,
            text="TXT",
            command=lambda: self.export_transcript_file("txt"),
            width=70,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_export_txt_button.pack(side="left", padx=(10, 0))

        self.transcript_export_srt_button = ctk.CTkButton(
            transcript_export_row,
            text="SRT",
            command=lambda: self.export_transcript_file("srt"),
            width=70,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_export_srt_button.pack(side="left", padx=(8, 0))

        self.transcript_export_vtt_button = ctk.CTkButton(
            transcript_export_row,
            text="VTT",
            command=lambda: self.export_transcript_file("vtt"),
            width=70,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_export_vtt_button.pack(side="left", padx=(8, 0))

        self.transcript_export_csv_button = ctk.CTkButton(
            transcript_export_row,
            text="CSV",
            command=lambda: self.export_transcript_file("csv"),
            width=70,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_export_csv_button.pack(side="left", padx=(8, 0))

        # Display options row
        transcript_options_row = ctk.CTkFrame(self.transcript_controls_panel, fg_color="transparent")
        transcript_options_row.pack(anchor="e", padx=15, pady=(0, 8))

        options_label = ctk.CTkLabel(
            transcript_options_row,
            text="Display:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        options_label.pack(side="left")

        self.transcript_show_speakers_checkbox = ctk.CTkCheckBox(
            transcript_options_row,
            text="Speakers",
            variable=self.transcript_show_speakers_var,
            command=self._refresh_transcript_display,
            width=90,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000"
        )
        self.transcript_show_speakers_checkbox.pack(side="left", padx=(10, 0))

        self.transcript_show_timestamps_checkbox = ctk.CTkCheckBox(
            transcript_options_row,
            text="Timestamps",
            variable=self.transcript_show_timestamps_var,
            command=self._refresh_transcript_display,
            width=110,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000"
        )
        self.transcript_show_timestamps_checkbox.pack(side="left", padx=(10, 0))

        # Transcript search row
        self.transcript_search_matches = []
        self.transcript_search_current_index = -1
        self.transcript_search_var = ctk.StringVar(value="")

        transcript_search_row = ctk.CTkFrame(self.transcript_controls_panel, fg_color="transparent")
        transcript_search_row.pack(anchor="e", padx=15, pady=(0, 8))

        search_label = ctk.CTkLabel(
            transcript_search_row,
            text="Search:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        search_label.pack(side="left")

        self.transcript_search_entry = ctk.CTkEntry(
            transcript_search_row,
            textvariable=self.transcript_search_var,
            placeholder_text="Find in transcript...",
            width=260,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_search_entry.pack(side="left", padx=(10, 0))

        self.transcript_search_prev_button = ctk.CTkButton(
            transcript_search_row,
            text="Previous",
            command=lambda: self._jump_to_transcript_search_match(-1),
            width=85,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_search_prev_button.pack(side="left", padx=(8, 0))

        self.transcript_search_next_button = ctk.CTkButton(
            transcript_search_row,
            text="Next",
            command=lambda: self._jump_to_transcript_search_match(1),
            width=70,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_search_next_button.pack(side="left", padx=(8, 0))

        self.transcript_search_count_label = ctk.CTkLabel(
            transcript_search_row,
            text="0 matches",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.transcript_search_count_label.pack(side="left", padx=(10, 0))

        self.transcript_search_var.trace_add(
            "write",
            lambda *_: self._search_transcript_changed()
        )

        transcript_qa_row = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        transcript_qa_row.pack(anchor="e", padx=15, pady=(0, 8))

        transcript_qa_label = ctk.CTkLabel(
            transcript_qa_row,
            text="Term QA:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        transcript_qa_label.pack(side="left")

        self.transcript_qa_status_label = ctk.CTkLabel(
            transcript_qa_row,
            text="No transcript loaded",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        self.transcript_qa_status_label.pack(side="left", padx=(10, 0))

        self.transcript_qa_refresh_button = ctk.CTkButton(
            transcript_qa_row,
            text="Sync",
            command=self._refresh_transcript_qa_panel,
            width=74,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.transcript_qa_refresh_button.pack(side="left", padx=(10, 0))

        self.transcript_qa_issue_frame = ctk.CTkFrame(
            self.transcript_card,
            fg_color="transparent"
        )

        self.transcript_cursor_status_label = ctk.CTkLabel(
            self.transcript_card,
            text="Click inside the transcript to select a segment.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.transcript_cursor_status_label.pack(fill="x", padx=15, pady=(0, 6))

        # Transcript preview
        self.transcript_textbox = ctk.CTkTextbox(
            self.transcript_card,
            height=320,
            font=ctk.CTkFont(family="Cascadia Mono", size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            wrap="word"
        )
        self.transcript_textbox.pack(fill="x", padx=15, pady=(0, 10))

        self.transcript_timeline_header = ctk.CTkFrame(
            self.transcript_card,
            fg_color="transparent"
        )
        self.transcript_timeline_header.pack(fill="x", padx=15, pady=(0, 4))

        self.transcript_timeline_label = ctk.CTkLabel(
            self.transcript_timeline_header,
            text="Timeline",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        self.transcript_timeline_label.pack(side="left")

        self.transcript_playback_status_label = ctk.CTkLabel(
            self.transcript_timeline_header,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        self.transcript_playback_status_label.pack(side="left", padx=(10, 0))

        self.transcript_pause_button = ctk.CTkButton(
            self.transcript_timeline_header,
            text="Pause",
            command=self.pause_transcript_timeline,
            width=64,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6,
            state="disabled"
        )
        self.transcript_pause_button.pack(side="right", padx=(6, 0))
        self.transcript_pause_button.pack_forget()

        self.transcript_play_button = ctk.CTkButton(
            self.transcript_timeline_header,
            text="▶ Play",
            command=self.toggle_transcript_timeline_playback,
            width=72,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#000000",
            corner_radius=6
        )
        self.transcript_play_button.pack(side="right")
        self.transcript_play_button.bind(
            "<Button-3>",
            lambda _event: self.check_transcript_vlc_ready(show_success=True)
        )

        self.transcript_timeline_canvas = tk.Canvas(
            self.transcript_card,
            height=125,
            bg=COLORS["bg_input"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            bd=0
        )
        self.transcript_timeline_canvas.pack(fill="x", padx=15, pady=(0, 6))
        self.transcript_timeline_canvas.bind(
            "<Configure>",
            lambda event: self._refresh_transcript_timeline()
        )
        self.transcript_timeline_canvas.bind(
            "<Button-1>",
            self._on_transcript_timeline_canvas_press
        )
        self.transcript_timeline_canvas.bind(
            "<B1-Motion>",
            self._on_transcript_timeline_canvas_drag
        )
        self.transcript_timeline_canvas.bind(
            "<ButtonRelease-1>",
            self._on_transcript_timeline_canvas_release
        )

        self.transcript_timeline_zoom_level = 1.0
        self.transcript_timeline_pan_fraction = 0.0
        self.transcript_timeline_view_fraction = 0.0
        self.transcript_position_fraction = 0.0
        self.transcript_playhead_seconds: Optional[float] = None
        self.transcript_playback_process = None
        self.transcript_playback_after_id = None
        self.transcript_playback_start_seconds: Optional[float] = None
        self.transcript_playback_start_wall_time: Optional[float] = None
        self.transcript_playback_latency_offset_seconds = 0.0
        self.transcript_playback_active_segment_index: Optional[int] = None
        self.transcript_playback_tick_ms = 30
        self.transcript_playback_generation = 0
        self.transcript_playback_requested_start_seconds: Optional[float] = None
        self.transcript_media_duration_seconds: Optional[float] = None
        self.transcript_vlc_clock_anchor_seconds: Optional[float] = None
        self.transcript_vlc_clock_anchor_wall_time: Optional[float] = None
        self.transcript_vlc_last_reported_seconds: Optional[float] = None
        self.transcript_vlc_max_interpolation_lead_seconds = 0.250
        self.transcript_playback_follow_anchor_ratio = 0.68
        self.transcript_playback_follow_hysteresis = 0.06
        self.transcript_playback_follow_active = False
        self.transcript_playback_debug_enabled = False
        self.transcript_playback_debug_ticks: List[Dict[str, Any]] = []
        self.transcript_vlc_module = None
        self.transcript_vlc_instance = None
        self.transcript_vlc_player = None
        self.transcript_vlc_media_path: Optional[str] = None
        self.transcript_playback_backend: Optional[str] = None
        self.transcript_audio_sync_offset_seconds = 0.0
        self.transcript_vlc_ready_checked = False
        self.transcript_vlc_ready = False
        self.transcript_vlc_error: Optional[str] = None
        self._transcript_timeline_view = None

        timeline_zoom_row = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        timeline_zoom_row.pack(fill="x", padx=15, pady=(0, 15))
        timeline_zoom_row.grid_columnconfigure(1, weight=1)

        self.transcript_timeline_zoom_value_label = ctk.CTkLabel(
            timeline_zoom_row,
            text="Zoom: Full",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
            width=75,
            anchor="w"
        )
        self.transcript_timeline_zoom_value_label.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.transcript_timeline_zoom_slider = ctk.CTkSlider(
            timeline_zoom_row,
            from_=1,
            to=10,
            number_of_steps=18,
            command=self._on_transcript_timeline_zoom_changed,
            height=16
        )
        self.transcript_timeline_zoom_slider.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.transcript_timeline_zoom_slider.set(1)

        self.transcript_timeline_zoom_reset_button = ctk.CTkButton(
            timeline_zoom_row,
            text="Reset",
            command=self._reset_transcript_timeline_zoom,
            width=65,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_timeline_zoom_reset_button.grid(row=0, column=2, sticky="e")

        self.transcript_waveform_button = ctk.CTkButton(
            timeline_zoom_row,
            text="Waveform",
            command=self.generate_transcript_waveform,
            width=85,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_waveform_button.grid(row=0, column=3, sticky="e", padx=(8, 0))

        self.transcript_detect_intervals_button = ctk.CTkButton(
            timeline_zoom_row,
            text="Create subtitle timings",
            command=self.detect_speech_intervals_clicked,
            width=165,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_detect_intervals_button.grid(row=0, column=5, sticky="e", padx=(8, 0))

        self.transcript_waveform_status_label = ctk.CTkLabel(
            timeline_zoom_row,
            text="No waveform",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
            width=95,
            anchor="w"
        )
        self.transcript_waveform_status_label.grid(row=0, column=4, sticky="w", padx=(8, 0))

        self.transcript_timeline_pan_label = ctk.CTkLabel(
            timeline_zoom_row,
            text="Position: Full",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
            width=75,
            anchor="w"
        )
        self.transcript_timeline_pan_label.grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))

        self.transcript_timeline_pan_slider = TranscriptPositionScrubber(
            timeline_zoom_row,
            command=self._on_transcript_timeline_pan_changed,
            height=18,
        )
        self.transcript_timeline_pan_slider.grid(
            row=1,
            column=1,
            columnspan=4,
            sticky="ew",
            pady=(6, 0)
        )
        self.transcript_timeline_pan_slider.bind(
            "<ButtonPress-1>",
            self._on_transcript_position_scrub_press,
            add="+",
        )
        self.transcript_timeline_pan_slider.bind(
            "<ButtonRelease-1>",
            self._on_transcript_position_scrub_release,
            add="+",
        )
        self.transcript_timeline_pan_slider.set(0)

        self.transcript_audio_sync_label = ctk.CTkLabel(
            timeline_zoom_row,
            text="Visual: 0 ms",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
            width=75,
            anchor="w"
        )
        self.transcript_audio_sync_label.grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(6, 0))

        self.transcript_audio_sync_minus_button = ctk.CTkButton(
            timeline_zoom_row,
            text="-50 ms",
            command=lambda: self._adjust_transcript_audio_sync_offset(-0.05),
            width=70,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_audio_sync_minus_button.grid(row=2, column=1, sticky="w", pady=(6, 0))

        self.transcript_audio_sync_plus_button = ctk.CTkButton(
            timeline_zoom_row,
            text="+50 ms",
            command=lambda: self._adjust_transcript_audio_sync_offset(0.05),
            width=70,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_audio_sync_plus_button.grid(row=2, column=1, sticky="w", padx=(78, 0), pady=(6, 0))

        self.transcript_audio_sync_reset_button = ctk.CTkButton(
            timeline_zoom_row,
            text="Sync Reset",
            command=self._reset_transcript_audio_sync_offset,
            width=85,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_audio_sync_reset_button.grid(row=2, column=2, sticky="w", padx=(8, 0), pady=(6, 0))

        self._bind_transcript_sync_controls_scroll_passthrough()

        self.transcript_audio_sync_fine_minus_button = ctk.CTkButton(
            timeline_zoom_row,
            text="-10 ms",
            command=lambda: self._adjust_transcript_audio_sync_offset(-0.01),
            width=70,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_audio_sync_fine_minus_button.grid(row=3, column=1, sticky="w", pady=(6, 0))

        self.transcript_audio_sync_fine_plus_button = ctk.CTkButton(
            timeline_zoom_row,
            text="+10 ms",
            command=lambda: self._adjust_transcript_audio_sync_offset(0.01),
            width=70,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=6
        )
        self.transcript_audio_sync_fine_plus_button.grid(row=3, column=1, sticky="w", padx=(78, 0), pady=(6, 0))

        self.transcript_audio_sync_shortcuts_label = ctk.CTkLabel(
            timeline_zoom_row,
            text="[ / ] fine sync, Ctrl+0 reset",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        self.transcript_audio_sync_shortcuts_label.grid(row=3, column=2, columnspan=3, sticky="w", padx=(8, 0), pady=(6, 0))

        self.transcript_display_ranges = []
        self.selected_transcript_segment_index = None

        transcript_text_widget = self._get_transcript_text_widget()
        transcript_text_widget.configure(
            insertbackground="#FFFFFF",
            insertwidth=2,
            insertofftime=300,
            insertontime=600
        )
        transcript_text_widget.bind("<ButtonRelease-1>", self._on_transcript_preview_interaction)
        transcript_text_widget.bind("<KeyPress>", self._on_transcript_preview_key_press)
        transcript_text_widget.bind("<KeyRelease>", self._on_transcript_preview_interaction)
        transcript_text_widget.bind("<<Paste>>", self._paste_transcript_text_at_cursor)
        self.transcript_search_entry.bind(
            "<Return>",
            lambda _event: (self._jump_to_transcript_search_match(1), "break")[1]
        )
        self.transcript_search_entry.bind(
            "<Shift-Return>",
            lambda _event: (self._jump_to_transcript_search_match(-1), "break")[1]
        )

        self._refresh_transcript_display()
        self._bind_final_file_drop_targets()

        self.transcript_card.grid_remove()

    def _create_log_section(self) -> None:
        """Create the activity log section."""
        self.log_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.log_card.grid(row=5, column=0, sticky="ew")
        self.log_card.grid_rowconfigure(1, weight=0)
        self.log_card.grid_columnconfigure(0, weight=1)

        # Log header
        log_header = ctk.CTkFrame(self.log_card, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))

        log_title = ctk.CTkLabel(
            log_header,
            text="📋 Activity Log",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        log_title.pack(side="left")

        # Stats in header
        self.footer_stats = ctk.CTkLabel(
            log_header,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.footer_stats.pack(side="right", padx=(0, 10))

        # Copy button
        self.copy_log_button = ctk.CTkButton(
            log_header,
            text="Copy",
            width=60,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            command=self.copy_activity_log_to_clipboard
        )
        self.copy_log_button.pack(side="right", padx=(0, 6))

        # Clear button
        self.clear_log_button = ctk.CTkButton(
            log_header,
            text="Clear",
            width=60,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=6,
            command=self.clear_log
        )
        self.clear_log_button.pack(side="right")

        # Log content
        self.log_frame = ctk.CTkScrollableFrame(
            self.log_card,
            height=74,
            fg_color=COLORS["bg_input"],
            corner_radius=8
        )
        self.log_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 15))

    # =========================================================================
    # DIALOG METHODS
    # =========================================================================

    def _open_blacklist_dialog(self) -> None:
        """Open dialog to edit blacklist patterns."""
        result = self._open_pattern_dialog(
            title="Blacklist Patterns",
            description="Comments containing these patterns will always be flagged as spam.\nEnter one pattern per line (case-insensitive).",
            current_patterns=self._blacklist_patterns,
            icon="🚫"
        )
        if result is not None:
            self._blacklist_patterns = result
            self._update_filter_counts()

    def _open_whitelist_dialog(self) -> None:
        """Open dialog to edit whitelist patterns."""
        result = self._open_pattern_dialog(
            title="Whitelist Patterns",
            description="Comments containing these patterns will always be allowed through.\nEnter one pattern per line (case-insensitive).",
            current_patterns=self._whitelist_patterns,
            icon="✓"
        )
        if result is not None:
            self._whitelist_patterns = result
            self._update_filter_counts()

    def _open_pattern_dialog(
        self,
        title: str,
        description: str,
        current_patterns: str,
        icon: str
    ) -> Optional[str]:
        """Open a dialog for editing patterns. Returns new patterns or None if cancelled."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry(f"{DIALOG_WIDTH}x{DIALOG_HEIGHT}")
        dialog.configure(fg_color=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - DIALOG_WIDTH) // 2
        y = self.winfo_y() + (self.winfo_height() - DIALOG_HEIGHT) // 2
        dialog.geometry(f"{DIALOG_WIDTH}x{DIALOG_HEIGHT}+{x}+{y}")

        result = {"value": None}

        # Header
        header_frame = ctk.CTkFrame(dialog, fg_color=COLORS["bg_card"], corner_radius=0)
        header_frame.pack(fill="x")

        header_label = ctk.CTkLabel(
            header_frame,
            text=f"{icon} {title}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        header_label.pack(pady=15, padx=20, anchor="w")

        # Description
        desc_label = ctk.CTkLabel(
            dialog,
            text=description,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            justify="left"
        )
        desc_label.pack(pady=(15, 10), padx=20, anchor="w")

        # Text area
        text_area = ctk.CTkTextbox(
            dialog,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8
        )
        text_area.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # Insert current patterns
        if current_patterns:
            text_area.insert("1.0", current_patterns)

        # Buttons frame
        buttons_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=(0, 20))

        def on_save():
            result["value"] = text_area.get("1.0", "end").strip()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        cancel_btn = ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=on_cancel,
            width=100,
            height=36,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            corner_radius=6
        )
        cancel_btn.pack(side="right", padx=(10, 0))

        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save",
            command=on_save,
            width=100,
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            corner_radius=6
        )
        save_btn.pack(side="right")

        # Wait for dialog to close
        dialog.wait_window()
        return result["value"]

    def _update_filter_counts(self) -> None:
        """Update the count label showing number of patterns."""
        blacklist_count = len([p for p in self._blacklist_patterns.split('\n') if p.strip()])
        whitelist_count = len([p for p in self._whitelist_patterns.split('\n') if p.strip()])

        parts = []
        if blacklist_count > 0:
            parts.append(f"{blacklist_count} blacklisted")
        if whitelist_count > 0:
            parts.append(f"{whitelist_count} whitelisted")

        label = getattr(self, "pattern_count_label", None)
        if label is not None:
            label.configure(text=" • ".join(parts) if parts else "")

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _start_internal_browser_image_discovery_service(self) -> None:
        """Start the app-owned browser image discovery service in the background.

        This is YTCE's integrated extension-like path: the app prewarms a
        Chromium/Edge rendered-discovery worker before the Images dialog opens,
        then source-row prefetch and the dialog share the same candidate cache.
        """
        # Some self-tests call this method on a deliberately uninitialised
        # Tk/App instance.  getattr() can fall through to tkinter.__getattr__
        # and recurse when ``self.tk`` is absent, so use the instance dict
        # directly for this internal guard.  Do not launch Playwright/Node from
        # those Tk stubs: the daemon prewarm can outlive the test process and
        # make Playwright's Node driver print EPIPE on interpreter shutdown.
        if self.__dict__.get("internal_browser_image_discovery_service_started", False):
            return
        self.__dict__["internal_browser_image_discovery_service_started"] = True
        if "tk" not in self.__dict__:
            return

        def _worker() -> None:
            try:
                start_internal_browser_image_discovery_service()
            except Exception:
                logger.debug("Internal browser image discovery service could not be started.", exc_info=True)

        threading.Thread(
            target=_worker,
            name="YTCEInternalBrowserImageDiscoveryService",
            daemon=True,
        ).start()

    def _on_closing(self) -> None:
        """Handle window close event - cancel any running operations."""
        if self.fetch_state.is_fetching:
            self.fetch_state.request_cancel()
            if self._fetch_thread_ref and self._fetch_thread_ref.is_alive():
                self._fetch_thread_ref.join(timeout=2.0)
        self._cleanup_webpage_image_session_downloads()
        try:
            close_rendered_browser_discovery_worker()
        except Exception:
            logger.debug("Could not close internal browser image discovery service cleanly.", exc_info=True)
        self.destroy()

    def _youtube_credential_service(self) -> YouTubeCredentialMigrationService:
        return YouTubeCredentialMigrationService(self.settings_manager)

    def _resolve_youtube_api_key_for_action(self) -> str:
        """Return a typed draft or stored YouTube key without populating the UI."""
        api_entry = getattr(self, "api_key_entry", None)
        draft = api_entry.get().strip() if api_entry is not None else ""
        if draft:
            return draft
        return self.settings_manager.load().api_key.strip()

    def _youtube_action_message(
        self,
        status: YouTubeCredentialActionStatus,
    ) -> tuple[str, str]:
        messages = {
            YouTubeCredentialActionStatus.SAVED: (
                "YouTube API key saved securely.",
                "success",
            ),
            YouTubeCredentialActionStatus.UPDATED: (
                "YouTube API key updated securely.",
                "success",
            ),
            YouTubeCredentialActionStatus.MIGRATED: (
                "Legacy YouTube API key migrated to secure storage.",
                "success",
            ),
            YouTubeCredentialActionStatus.CLEARED: (
                "YouTube API key cleared from known storage.",
                "success",
            ),
            YouTubeCredentialActionStatus.NOT_FOUND: (
                "No YouTube API key was found in known storage.",
                "warning",
            ),
            YouTubeCredentialActionStatus.PARTIAL_FAILURE: (
                "YouTube API key clear was only partially completed.",
                "warning",
            ),
            YouTubeCredentialActionStatus.LEGACY_CLEANUP_FAILED: (
                "Secure save succeeded, but legacy cleanup failed.",
                "warning",
            ),
            YouTubeCredentialActionStatus.EMPTY_CREDENTIAL_REJECTED: (
                "Enter a YouTube API key before saving.",
                "warning",
            ),
            YouTubeCredentialActionStatus.BACKEND_UNAVAILABLE: (
                "Secure credential storage is unavailable.",
                "error",
            ),
            YouTubeCredentialActionStatus.PRESENCE_VERIFICATION_FAILED: (
                "Secure credential storage could not be verified.",
                "error",
            ),
            YouTubeCredentialActionStatus.BACKEND_ERROR: (
                "Secure credential storage returned a safe error.",
                "error",
            ),
        }
        return messages.get(status, ("Credential action finished.", "info"))

    def _refresh_youtube_credential_status(self) -> None:
        state = self._youtube_credential_service().storage_status().state
        labels = {
            YouTubeCredentialStorageState.SECURE_KEYRING_ONLY: "Secure storage configured",
            YouTubeCredentialStorageState.LEGACY_PLAINTEXT_ONLY: "Legacy settings storage detected",
            YouTubeCredentialStorageState.BOTH_SECURE_AND_LEGACY: "Secure + legacy copies detected",
            YouTubeCredentialStorageState.MISSING: "API key not configured",
            YouTubeCredentialStorageState.SECURE_BACKEND_UNAVAILABLE: "Secure storage unavailable",
            YouTubeCredentialStorageState.STATUS_ERROR: "Storage status error",
        }
        storage_label = getattr(self, "storage_label", None)
        if storage_label is not None:
            storage_label.configure(text=labels.get(state, "Storage status unknown"))

    def _save_youtube_api_key_secure(self) -> None:
        api_entry = getattr(self, "api_key_entry", None)
        credential = api_entry.get().strip() if api_entry is not None else ""
        result = self._youtube_credential_service().save_secure(credential)
        if result.status in {
            YouTubeCredentialActionStatus.SAVED,
            YouTubeCredentialActionStatus.UPDATED,
        }:
            if api_entry is not None:
                api_entry.delete(0, "end")
        if api_entry is not None:
            api_entry.configure(show="*")
        self._refresh_youtube_credential_status()
        message, level = self._youtube_action_message(result.status)
        self.log_message(message, level)

    def _migrate_youtube_api_key(self) -> None:
        result = self._youtube_credential_service().migrate_legacy_to_secure()
        api_entry = getattr(self, "api_key_entry", None)
        if api_entry is not None:
            api_entry.delete(0, "end")
            api_entry.configure(show="*")
        self._refresh_youtube_credential_status()
        message, level = self._youtube_action_message(result.status)
        self.log_message(message, level)

    def _clear_youtube_api_key(self) -> None:
        result = self._youtube_credential_service().clear_all()
        api_entry = getattr(self, "api_key_entry", None)
        if api_entry is not None:
            api_entry.delete(0, "end")
            api_entry.configure(show="*")
        self._refresh_youtube_credential_status()
        message, level = self._youtube_action_message(result.status)
        self.log_message(message, level)

    def _on_spam_filter_toggle(self) -> None:
        """Handle spam filter toggle - enable/disable threshold slider."""
        enabled = self.spam_filter_var.get()
        state = "normal" if enabled else "disabled"

        self.spam_threshold_slider.configure(state=state)
        self.spam_threshold_label.configure(
            text_color=COLORS["text_secondary"] if enabled else COLORS["text_muted"]
        )
        self.spam_threshold_value_label.configure(
            text_color=COLORS["accent"] if enabled else COLORS["text_muted"]
        )

    def _on_spam_threshold_change(self, value: float) -> None:
        """Update threshold label based on slider value."""
        if value >= 0.65:
            label = "Light"
        elif value >= 0.5:
            label = "Moderate"
        elif value >= 0.4:
            label = "Aggressive"
        else:
            label = "Strict"

        self.spam_threshold_value_label.configure(text=label)

    def _on_url_focus_in(self, event: Any) -> None:
        """Clear placeholder when URL entry is focused."""
        current_text = self.url_entry.get("1.0", "end").strip()
        if current_text == self._url_placeholder.strip():
            self.url_entry.delete("1.0", "end")
            self.url_entry.configure(text_color=COLORS["text_primary"])

    def _on_url_focus_out(self, event: Any) -> None:
        """Restore placeholder if URL entry is empty."""
        current_text = self.url_entry.get("1.0", "end").strip()
        if not current_text:
            self.url_entry.insert("1.0", self._url_placeholder)
            self.url_entry.configure(text_color=COLORS["text_muted"])

    def _validate_urls_live(self, event: Any = None) -> None:
        """Validate URLs as user types."""
        current_text = self.url_entry.get("1.0", "end").strip()

        if current_text == self._url_placeholder.strip() or not current_text:
            self.url_status.configure(text="", text_color=COLORS["text_muted"])
            return

        intake = parse_source_url_intake(
            current_text,
            existing_rows=getattr(self, "source_resource_rows", ()),
            archive_auto_check_enabled=getattr(
                self,
                "source_archive_auto_check_enabled",
                True,
            ),
        )
        valid_count = len(intake.rows)
        invalid_count = len(intake.invalid_tokens)
        if valid_count == 0 and invalid_count == 0:
            status_msg = ""
        elif valid_count == 0:
            status_msg = "No supported source URLs detected"
        elif invalid_count == 0:
            suffix = "s" if valid_count != 1 else ""
            status_msg = f"{valid_count} source URL{suffix} ready to add"
        else:
            status_msg = f"{valid_count} ready, {invalid_count} invalid/unsupported"

        if valid_count == 0:
            color = COLORS["warning"]
        elif invalid_count == 0:
            color = COLORS["success"]
        else:
            color = COLORS["warning"]

        self.url_status.configure(text=status_msg, text_color=color)

    def _on_source_url_shift_enter(self, _event: Any = None) -> str:
        self.url_entry.insert("insert", "\n")
        return "break"

    def _on_source_url_enter(self, _event: Any = None) -> str:
        current_text = self.url_entry.get("1.0", "end").strip()
        if current_text == self._url_placeholder.strip() or not current_text:
            return "break"
        intake = parse_source_url_intake(
            current_text,
            existing_rows=getattr(self, "source_resource_rows", ()),
            archive_auto_check_enabled=getattr(
                self,
                "source_archive_auto_check_enabled",
                True,
            ),
        )
        if intake.rows:
            # Show the newly entered/pasted batch directly under the Source URLs
            # input while preserving the order inside that batch.
            self.source_resource_rows = list(intake.rows) + list(getattr(self, "source_resource_rows", ()))
            self._refresh_source_resource_rows()
            self._refresh_discussion_source_controls()
            self._start_youtube_source_row_metadata_probe(intake.rows)
            self._start_twitter_source_row_metadata_probe(intake.rows)
            self._start_webpage_image_source_row_prefetch(intake.rows)
            self._start_webpage_video_source_row_prefetch(intake.rows)
            self.log_message(
                f"Added {len(intake.rows)} source row(s). Metadata probes may run for supported source rows.",
                "success",
            )
        if intake.duplicate_raw_urls:
            self.log_message(
                f"Ignored {len(intake.duplicate_raw_urls)} duplicate source URL(s).",
                "muted",
            )
        self.url_entry.delete("1.0", "end")
        if intake.remaining_text:
            self.url_entry.insert("1.0", intake.remaining_text)
            self.url_entry.configure(text_color=COLORS["text_primary"])
        else:
            self.url_entry.configure(text_color=COLORS["text_primary"])
        if intake.invalid_tokens:
            self.url_status.configure(
                text=f"{len(intake.invalid_tokens)} invalid/unsupported token(s) retained",
                text_color=COLORS["warning"],
            )
        elif intake.rows:
            self.url_status.configure(
                text=f"Added {len(intake.rows)} source URL(s)",
                text_color=COLORS["success"],
            )
        else:
            self.url_status.configure(text="", text_color=COLORS["text_muted"])
        return "break"

    def _archive_status_color(self, color_name: str) -> str:
        return {
            "green": COLORS["success"],
            "red": COLORS["error"],
            "amber": COLORS["warning"],
            "gray": COLORS["accent_secondary"],
        }.get(color_name, COLORS["accent_secondary"])

    def _resource_count_text(
        self,
        label: str,
        resources: Sequence[Any],
    ) -> str:
        return f"{label} ({len(resources)})" if resources else label

    def _archive_status_label_text(self, archive_status: Any) -> str:
        if archive_status.status == "available":
            return archive_status.saved_date or "Date unavailable"
        return archive_status.label

    @staticmethod
    def _source_row_is_twitter(row: SourceResourceRowState) -> bool:
        adapter_id = (row.adapter_id or "").lower()
        domain = (row.domain or "").lower()
        return adapter_id in {"twitter", "x", "twitter_x", "x_twitter"} or domain in {
            "x.com",
            "www.x.com",
            "twitter.com",
            "www.twitter.com",
        }

    def _twitter_mode_var_for_row(self, row_id: str) -> ctk.StringVar:
        mode_vars = self.__dict__.setdefault("twitter_source_row_mode_vars", {})
        if row_id not in mode_vars:
            mode_vars[row_id] = ctk.StringVar(value="Post")
        return mode_vars[row_id]

    def _normalise_twitter_source_settings(self, row_id: str) -> dict[str, Any]:
        settings_by_row = self.__dict__.setdefault("twitter_source_row_settings", {})
        settings = dict(settings_by_row.get(row_id, {}))
        if "show_type_dropdown" not in settings:
            if "disable_type_dropdown" in settings:
                settings["show_type_dropdown"] = not bool(settings.pop("disable_type_dropdown"))
            else:
                settings["show_type_dropdown"] = True
        else:
            settings.pop("disable_type_dropdown", None)
        if str(settings.get("screenshot_mode") or "none").lower() not in TWITTER_SCREENSHOT_MODE_VALUES:
            settings["screenshot_mode"] = "none"
        settings_by_row[row_id] = settings
        return settings

    def _twitter_row_enabled_var_for_row(self, row_id: str) -> ctk.BooleanVar:
        enabled_vars = self.__dict__.setdefault("twitter_source_row_enabled_vars", {})
        if row_id not in enabled_vars:
            settings = self._normalise_twitter_source_settings(row_id)
            enabled_vars[row_id] = ctk.BooleanVar(value=bool(settings.get("row_enabled", True)))
        return enabled_vars[row_id]

    def _twitter_show_type_dropdown_var_for_row(self, row_id: str) -> ctk.BooleanVar:
        show_vars = self.__dict__.setdefault("twitter_source_row_show_type_dropdown_vars", {})
        if row_id not in show_vars:
            settings = self._normalise_twitter_source_settings(row_id)
            show_vars[row_id] = ctk.BooleanVar(value=bool(settings.get("show_type_dropdown", True)))
        return show_vars[row_id]

    def _twitter_setting_bool_var_for_row(self, row_id: str, key: str, default: bool = True) -> ctk.BooleanVar:
        vars_by_row = self.__dict__.setdefault("twitter_source_row_setting_bool_vars", {})
        row_vars = vars_by_row.setdefault(row_id, {})
        if key not in row_vars:
            settings = self._normalise_twitter_source_settings(row_id)
            row_vars[key] = ctk.BooleanVar(value=bool(settings.get(key, default)))
        return row_vars[key]

    def _twitter_screenshot_mode_var_for_row(self, row_id: str) -> ctk.StringVar:
        mode_vars = self.__dict__.setdefault("twitter_source_row_screenshot_mode_vars", {})
        if row_id not in mode_vars:
            settings = self._normalise_twitter_source_settings(row_id)
            value = str(settings.get("screenshot_mode") or "none").lower()
            mode_vars[row_id] = ctk.StringVar(value=value if value in TWITTER_SCREENSHOT_MODE_VALUES else "none")
        return mode_vars[row_id]

    def _ensure_twitter_x_icon(self) -> None:
        if hasattr(self, "twitter_x_icon_image"):
            return
        self.twitter_x_icon_image = None
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ytce_x_icon.png")
        try:
            if os.path.isfile(icon_path):
                icon_image = Image.open(icon_path).convert("RGBA")
                self.twitter_x_icon_image = ctk.CTkImage(light_image=icon_image, dark_image=icon_image, size=(16, 16))
        except Exception as icon_error:
            logger.warning(f"Could not load X/Twitter source-row icon: {icon_error}")
            self.twitter_x_icon_image = None

    def _on_twitter_source_row_mode_changed(self, row_id: str, mode: str) -> None:
        mode = mode if mode in set(TWITTER_COMPACT_MODES) else "Post"
        self.__dict__.setdefault("twitter_source_row_modes", {})[row_id] = mode
        if hasattr(self, "url_status"):
            self.url_status.configure(
                text=f"Twitter/X source mode set to {mode}. Use Go for capture; media stays inside X settings.",
                text_color=COLORS["text_secondary"],
            )

    def _on_twitter_row_enabled_changed(self, row_id: str, update_label: Any | None = None) -> None:
        enabled = bool(self._twitter_row_enabled_var_for_row(row_id).get())
        settings = self._normalise_twitter_source_settings(row_id)
        settings["row_enabled"] = enabled
        self.twitter_source_row_settings[row_id] = settings
        if update_label is not None:
            try:
                update_label.configure(
                    text_color=COLORS["text_primary"] if enabled else COLORS["text_muted"],
                    fg_color=COLORS["bg_input"],
                    cursor="hand2" if enabled else "arrow",
                )
            except Exception:
                pass
        if hasattr(self, "url_status"):
            self.url_status.configure(
                text=(
                    "Twitter/X row enabled for Go."
                    if enabled
                    else "Twitter/X row disabled for Go."
                ),
                text_color=COLORS["text_secondary"],
            )

    def _on_twitter_show_type_dropdown_changed(self, row_id: str) -> None:
        settings = self._normalise_twitter_source_settings(row_id)
        settings["show_type_dropdown"] = bool(self._twitter_show_type_dropdown_var_for_row(row_id).get())
        self.twitter_source_row_settings[row_id] = settings
        self._refresh_source_resource_rows()
        if hasattr(self, "url_status"):
            self.url_status.configure(
                text=(
                    "Twitter/X type dropdown shown on source row."
                    if settings["show_type_dropdown"]
                    else "Twitter/X type dropdown hidden from source row."
                ),
                text_color=COLORS["text_secondary"],
            )

    def _save_twitter_source_settings(self, row_id: str) -> None:
        settings = self._normalise_twitter_source_settings(row_id)
        for key, default in (
            ("post", True),
            ("threads", True),
            ("media", False),
        ):
            settings[key] = bool(self._twitter_setting_bool_var_for_row(row_id, key, default).get())
        settings["show_type_dropdown"] = bool(self._twitter_show_type_dropdown_var_for_row(row_id).get())
        settings["row_enabled"] = bool(self._twitter_row_enabled_var_for_row(row_id).get())
        screenshot_mode = self._twitter_screenshot_mode_var_for_row(row_id).get()
        settings["screenshot_mode"] = screenshot_mode if screenshot_mode in TWITTER_SCREENSHOT_MODE_VALUES else "none"
        self.twitter_source_row_settings[row_id] = settings
        self.source_screenshot_preferences[row_id] = {
            **dict(self.__dict__.setdefault("source_screenshot_preferences", {}).get(row_id, {})),
            "webpage": settings["screenshot_mode"] != "none",
            "webpage_screenshot": settings["screenshot_mode"] != "none",
            "twitter_screenshot_mode": settings["screenshot_mode"],
        }
        self._refresh_source_resource_rows()

    def _open_twitter_source_mode_dropdown_menu(self, row_id: str, anchor_widget: Any, update_widget: Any | None = None) -> None:
        if not bool(self._twitter_row_enabled_var_for_row(row_id).get()):
            return
        mode_var = self._twitter_mode_var_for_row(row_id)
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["accent"],
            activeforeground=COLORS["text_primary"],
            bd=0,
            relief="flat",
        )

        def select_mode(value: str) -> None:
            mode_var.set(value)
            self._on_twitter_source_row_mode_changed(row_id, value)
            self.after(1, self._refresh_source_resource_rows)
            self.after(1, self._refresh_discussion_source_controls)

        current = mode_var.get()
        for value in TWITTER_COMPACT_MODES:
            label = ("* " + value) if value == current else value
            menu.add_command(label=label, command=lambda selected=value: select_mode(selected))
        try:
            x = int(anchor_widget.winfo_rootx())
            y = int(anchor_widget.winfo_rooty() + anchor_widget.winfo_height())
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _open_twitter_source_settings(self, row_id: str) -> None:
        row = self._source_row_by_id(row_id)
        if row is None:
            return
        state = build_twitter_compact_row_state(row)
        window = ctk.CTkToplevel(self)
        window.title("X/Twitter source settings")
        window.geometry("460x390")
        window.transient(self)
        window.grab_set()
        window.configure(fg_color=COLORS["bg_dark"])

        ctk.CTkLabel(
            window,
            text=f"X/Twitter source settings\n{state.display_title}\n{row.domain}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(16, 8))

        body = ctk.CTkFrame(window, fg_color=COLORS["bg_input"])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        mode_var = self._twitter_mode_var_for_row(row_id)
        post_var = self._twitter_setting_bool_var_for_row(row_id, "post", True)
        threads_var = self._twitter_setting_bool_var_for_row(row_id, "threads", True)
        media_var = self._twitter_setting_bool_var_for_row(row_id, "media", False)
        show_type_dropdown_var = self._twitter_show_type_dropdown_var_for_row(row_id)
        screenshot_mode_var = self._twitter_screenshot_mode_var_for_row(row_id)
        ctk.CTkLabel(
            body,
            text="Capture mode",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkOptionMenu(
            body,
            variable=mode_var,
            values=list(TWITTER_COMPACT_MODES),
            command=lambda value: self._on_twitter_source_row_mode_changed(row_id, value),
            width=120,
            fg_color=COLORS["bg_card"],
            button_color=COLORS["accent_secondary"],
            button_hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_secondary"],
            dropdown_text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=12, pady=(0, 10))
        for label, var in (
            ("Post", post_var),
            ("Threads", threads_var),
            ("Media", media_var),
            ("Show type dropdown on X/Twitter source row", show_type_dropdown_var),
        ):
            ctk.CTkCheckBox(
                body,
                text=label,
                variable=var,
                command=(
                    (lambda row_id=row_id: self._on_twitter_show_type_dropdown_changed(row_id))
                    if label.startswith("Show type dropdown")
                    else (lambda row_id=row_id: self._save_twitter_source_settings(row_id))
                ),
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_primary"],
            ).pack(anchor="w", padx=12, pady=4)

        ctk.CTkLabel(
            body,
            text="Screenshot",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 4))
        screenshot_row = ctk.CTkFrame(body, fg_color="transparent")
        screenshot_row.pack(fill="x", padx=12, pady=(0, 8))
        for label, value in zip(TWITTER_SCREENSHOT_MODES, TWITTER_SCREENSHOT_MODE_VALUES):
            ctk.CTkRadioButton(
                screenshot_row,
                text=label,
                value=value,
                variable=screenshot_mode_var,
                command=lambda row_id=row_id: self._save_twitter_source_settings(row_id),
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_primary"],
            ).pack(side="left", padx=(0, 16))
        ctk.CTkLabel(
            body,
            text=(
                "Media download stays inside this settings path and will use "
                "the shared media capability model when the X/Twitter backend is approved."
            ),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            justify="left",
            wraplength=400,
        ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(
            body,
            text=state.account_thread_semantics,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
            justify="left",
            wraplength=400,
        ).pack(anchor="w", padx=12, pady=(4, 8))

        buttons = ctk.CTkFrame(window, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(buttons, text="Close", width=90, command=window.destroy).pack(side="right")

    @staticmethod
    def _source_row_is_youtube(row: SourceResourceRowState) -> bool:
        adapter_id = (row.adapter_id or "").lower()
        domain = (row.domain or "").lower()
        return adapter_id == "youtube" or domain in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
        }

    def _youtube_preferences_for_row(self, row_id: str) -> YouTubeGuiMediaPreferences:
        prefs = self.__dict__.setdefault("youtube_source_row_preferences", {})
        if row_id not in prefs:
            prefs[row_id] = default_youtube_gui_media_preferences()
        return prefs[row_id]

    def _youtube_quality_values_for_row(self, row_id: str) -> tuple[str, ...]:
        prefs = self._youtube_preferences_for_row(row_id)
        configured = normalized_youtube_quality_labels(prefs)
        available = self.__dict__.setdefault("youtube_source_row_available_quality_labels", {}).get(row_id, ())
        if available:
            narrowed = tuple(label for label in configured if label in available)
            return narrowed or tuple(label for label in available if label in {name for name, _height in YOUTUBE_GUI_QUALITY_PRESETS}) or available
        # Until yt-dlp or the lightweight watch-page probe has supplied real
        # formats, do not advertise fake quality levels.  Show only the saved
        # default/current quality until discovery proves more are available.
        default_label = prefs.default_quality_label if prefs.default_quality_label in configured else (configured[0] if configured else "1080")
        return (default_label,)

    def _youtube_quality_var_for_row(self, row_id: str) -> ctk.StringVar:
        vars_by_row = self.__dict__.setdefault("youtube_source_row_quality_vars", {})
        prefs = self._youtube_preferences_for_row(row_id)
        values = self._youtube_quality_values_for_row(row_id)
        default = prefs.default_quality_label if prefs.default_quality_label in values else values[0]
        if row_id not in vars_by_row:
            vars_by_row[row_id] = ctk.StringVar(value=default)
        elif vars_by_row[row_id].get() not in values:
            vars_by_row[row_id].set(default)
        return vars_by_row[row_id]

    def _youtube_quality_enabled_var_for_row(self, row_id: str) -> ctk.BooleanVar:
        vars_by_row = self.__dict__.setdefault("youtube_source_row_quality_enabled_vars", {})
        if row_id not in vars_by_row:
            vars_by_row[row_id] = ctk.BooleanVar(value=True)
        return vars_by_row[row_id]

    @staticmethod
    def _short_source_url_for_row(row: SourceResourceRowState, *, limit: int = 150) -> str:
        url = str(getattr(row, "canonical_url", "") or getattr(row, "raw_url", "") or "").strip()
        if not url:
            return str(getattr(row, "domain", "") or "").strip()
        if len(url) <= limit:
            return url
        head = max(20, limit - 18)
        return url[:head].rstrip("&?=/") + "…" + url[-14:]

    @staticmethod
    def _source_row_combo_label(row: SourceResourceRowState) -> str:
        adapter_id = (getattr(row, "adapter_id", "") or "").lower()
        domain = (getattr(row, "domain", "") or "").lower()
        if adapter_id == "youtube" or domain in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
            return f"{row.title} - YouTube"
        return row.display_label

    def _open_youtube_source_quality_picker(self, row_id: str) -> None:
        """Legacy shim retained for older tests/call sites."""
        return

    def _open_youtube_source_quality_dropdown_menu(self, row_id: str, anchor_widget: Any, update_widget: Any | None = None) -> None:
        """Open an inline menu-style dropdown for the compact YouTube quality control."""
        if not self._youtube_quality_enabled_var_for_row(row_id).get():
            return
        quality_var = self._youtube_quality_var_for_row(row_id)
        values = list(self._youtube_quality_values_for_row(row_id)) or [quality_var.get() or "1080"]
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["accent"],
            activeforeground=COLORS["text_primary"],
            bd=0,
            relief="flat",
        )

        def select_quality(value: str) -> None:
            quality_var.set(value)
            try:
                if update_widget is not None:
                    update_widget.configure(text=value)
            except Exception:
                pass
            self._on_youtube_source_quality_changed(row_id, value)

        current = quality_var.get()
        for value in values:
            label = ("✓ " + value) if value == current else value
            menu.add_command(label=label, command=lambda selected=value: select_quality(selected))
        try:
            x = int(anchor_widget.winfo_rootx())
            y = int(anchor_widget.winfo_rooty() + anchor_widget.winfo_height())
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _on_youtube_source_quality_changed(self, row_id: str, quality: str) -> None:
        if hasattr(self, "url_status"):
            self.url_status.configure(
                text=f"YouTube media quality set to {quality}. Go will add the selected YouTube media package to FILES.",
                text_color=COLORS["text_secondary"],
            )

    def _on_youtube_source_quality_enabled_changed(self, row_id: str) -> None:
        if hasattr(self, "url_status"):
            enabled = self._youtube_quality_enabled_var_for_row(row_id).get()
            self.url_status.configure(
                text="YouTube media enabled for Go." if enabled else "YouTube media disabled for Go; settings icon remains available.",
                text_color=COLORS["text_secondary"],
            )

    def _youtube_oembed_metadata_probe(self, source_url: str) -> dict[str, str]:
        """Fetch lightweight YouTube oEmbed metadata for display fields.

        oEmbed normally provides title and author_name/channel. It does not
        provide upload date or views, so those fields remain tied to yt-dlp or
        another explicit metadata source.
        """
        normalized_url = str(source_url or "").strip()
        if not normalized_url:
            return {}
        endpoint = (
            "https://www.youtube.com/oembed?format=json&url="
            + urllib.parse.quote(normalized_url, safe="")
        )
        request = urllib.request.Request(
            endpoint,
            headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = response.read().decode("utf-8", errors="replace")
        data = json.loads(payload or "{}")
        return {
            "title": str(data.get("title") or "").strip(),
            "channel": str(data.get("author_name") or "").strip(),
            "webpage_url": normalized_url,
            "video_id": self._youtube_video_id_from_url(normalized_url),
            "metadata_source": "youtube_oembed",
        }

    def _youtube_oembed_title_probe(self, source_url: str) -> str:
        """Fetch a lightweight YouTube title without needing the YouTube Data API.

        This remains a display-title fallback. Full media discovery still uses
        yt-dlp when available, and comments/livechat still use the normal
        YouTube runtime.
        """
        return str(self._youtube_oembed_metadata_probe(source_url).get("title") or "").strip()

    def _youtube_watch_html_quality_probe(self, source_url: str) -> tuple[str, ...]:
        """Best-effort quality discovery from YouTube's watch page.

        This is a fallback for row display only when yt-dlp is unavailable or
        fails. It reads YouTube's embedded player response and extracts actual
        video heights from streamingData formats/adaptiveFormats.
        """
        normalized_url = str(source_url or "").strip()
        if not normalized_url:
            return ()
        request = urllib.request.Request(
            normalized_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                "Accept-Language": "en-GB,en;q=0.9",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")
        match = re.search(r"ytInitialPlayerResponse\s*=\s*", html)
        if not match:
            return ()
        tail = html[match.end():].lstrip()
        data, _offset = json.JSONDecoder().raw_decode(tail)
        streaming = data.get("streamingData", {}) if isinstance(data, dict) else {}
        formats = []
        if isinstance(streaming, dict):
            for key in ("formats", "adaptiveFormats"):
                items = streaming.get(key)
                if isinstance(items, list):
                    formats.extend(item for item in items if isinstance(item, dict))
        heights: set[int] = set()
        for item in formats:
            mime = str(item.get("mimeType") or "")
            if "video/" not in mime:
                continue
            try:
                height = int(item.get("height") or 0)
            except (TypeError, ValueError):
                height = 0
            if height > 0:
                heights.add(height)
        labels: list[str] = []
        for label, preset_height in YOUTUBE_GUI_QUALITY_PRESETS:
            if preset_height in heights or any(abs(height - preset_height) <= 8 for height in heights):
                labels.append(label)
        return tuple(labels)

    def _apply_youtube_source_row_discovery(
        self,
        row_id: str,
        title: str,
        quality_labels: Sequence[str],
        status: str = "ready",
        metadata: dict[str, object] | None = None,
    ) -> None:
        labels = tuple(label for label in quality_labels if label in {name for name, _height in YOUTUBE_GUI_QUALITY_PRESETS})
        if labels:
            self.youtube_source_row_available_quality_labels[row_id] = labels
        self.youtube_source_row_discovery_status[row_id] = status
        if metadata:
            clean_metadata = {
                str(key): str(value)
                for key, value in metadata.items()
                if value not in (None, "")
            }
            if clean_metadata:
                self.__dict__.setdefault("youtube_source_row_discovery_metadata", {})[row_id] = clean_metadata
        updated_rows: list[SourceResourceRowState] = []
        for row in self.__dict__.get("source_resource_rows", ()):
            if row.row_id == row_id and title:
                updated_rows.append(replace(row, title=title, display_title=title, display_label=f"{title} - YouTube"))
            else:
                updated_rows.append(row)
        self.source_resource_rows = updated_rows
        quality_var = self.__dict__.setdefault("youtube_source_row_quality_vars", {}).get(row_id)
        if quality_var is not None and labels and quality_var.get() not in labels:
            quality_var.set(labels[0])
        self._refresh_source_resource_rows()
        self._refresh_discussion_source_controls()

    def _start_youtube_source_row_metadata_probe(self, rows: Sequence[SourceResourceRowState]) -> None:
        youtube_rows = [row for row in rows if self._source_row_is_youtube(row)]
        if not youtube_rows:
            return
        for row in youtube_rows:
            self.youtube_source_row_discovery_status[row.row_id] = "loading"

        def worker(snapshot: tuple[SourceResourceRowState, ...]) -> None:
            for row in snapshot:
                try:
                    discovery = discover_youtube_media_with_ytdlp(row.canonical_url)
                    title = youtube_title_from_discovery(discovery, row.title)
                    qualities = youtube_available_quality_labels_from_discovery(
                        discovery,
                        fallback=normalized_youtube_quality_labels(
                            self._youtube_preferences_for_row(row.row_id)
                        ),
                    )
                    metadata = {
                        "title": discovery.title,
                        "channel": discovery.channel or discovery.uploader,
                        "upload_date": discovery.upload_date,
                        "view_count": discovery.view_count,
                        "webpage_url": discovery.webpage_url,
                        "source_url": discovery.source_url,
                    }
                    self.after(
                        0,
                        lambda row_id=row.row_id, title=title, qualities=qualities, metadata=metadata: self._apply_youtube_source_row_discovery(
                            row_id,
                            title,
                            qualities,
                            "ready",
                            metadata,
                        ),
                    )
                    continue
                except Exception as ytdlp_error:
                    try:
                        oembed_metadata = self._youtube_oembed_metadata_probe(row.canonical_url)
                        title = oembed_metadata.get("title") or ""
                    except Exception as oembed_error:
                        self.after(
                            0,
                            lambda row_id=row.row_id, err=ytdlp_error, fallback_err=oembed_error: self._mark_youtube_source_row_discovery_failed(
                                row_id,
                                err,
                            ),
                        )
                        continue

                    try:
                        qualities = self._youtube_watch_html_quality_probe(row.canonical_url)
                    except Exception:
                        qualities = ()
                    if not qualities:
                        # Do not invent a list of qualities. Keep only the
                        # current/default quality visible until real discovery
                        # proves available formats.
                        current = self._youtube_quality_var_for_row(row.row_id).get()
                        qualities = (current,) if current else ()
                    self.after(
                        0,
                        lambda row_id=row.row_id, title=title, qualities=qualities, metadata=oembed_metadata: self._apply_youtube_source_row_discovery(
                            row_id,
                            title,
                            qualities,
                            "title_only",
                            metadata,
                        ),
                    )

        threading.Thread(target=worker, args=(tuple(youtube_rows),), daemon=True).start()

    def _mark_youtube_source_row_discovery_failed(self, row_id: str, error: Exception) -> None:
        self.youtube_source_row_discovery_status[row_id] = "failed"
        if hasattr(self, "url_status"):
            self.url_status.configure(
                text=f"YouTube details not loaded yet: {type(error).__name__}. Quality presets remain selectable.",
                text_color=COLORS["warning"],
            )

    def _twitter_oembed_text_probe(self, source_url: str) -> str:
        # Fetch a lightweight X/Twitter public post text preview for row display.
        # This uses the public publish.twitter.com oEmbed endpoint only for a
        # short display title. It does not use an X account, cookies, browser
        # automation, scraping, or the X API.
        normalized_url = str(source_url or "").strip()
        if not normalized_url:
            return ""
        preview_parts = urllib.parse.urlsplit(normalized_url)
        if preview_parts.netloc.lower() in {"x.com", "www.x.com"}:
            normalized_url = urllib.parse.urlunsplit(
                (
                    "https",
                    "twitter.com",
                    preview_parts.path,
                    preview_parts.query,
                    preview_parts.fragment,
                )
            )
        endpoint = (
            "https://publish.twitter.com/oembed?omit_script=1&dnt=1&url="
            + urllib.parse.quote(normalized_url, safe="")
        )
        request = urllib.request.Request(
            endpoint,
            headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = response.read().decode("utf-8", errors="replace")
        data = json.loads(payload or "{}")
        html_text = str(data.get("html") or "")
        title_text = str(data.get("title") or "")
        candidates: list[str] = []
        match = re.search(r"<p\b[^>]*>(.*?)</p>", html_text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidates.append(match.group(1))
        if title_text:
            candidates.append(title_text)

        for candidate in candidates:
            text = re.sub(r"<br\s*/?>", " ", candidate, flags=re.IGNORECASE)
            text = re.sub(r"<a\b[^>]*>.*?</a>", " ", text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = html.unescape(text)
            text = re.sub(r"\s+", " ", text).strip()
            text = re.sub(r"\s+pic\.twitter\.com/\S+\s*$", "", text).strip()
            if text and not re.fullmatch(r"https?://\S+", text):
                return text[:180]
        return ""

    def _apply_twitter_source_row_preview(self, row_id: str, preview_text: str) -> None:
        preview = " ".join(str(preview_text or "").split()).strip()
        if not preview:
            return
        updated_rows: list[SourceResourceRowState] = []
        changed = False
        for row in self.__dict__.get("source_resource_rows", ()):
            if row.row_id == row_id:
                updated_rows.append(
                    replace(
                        row,
                        title=preview,
                        display_title=preview,
                        display_label=f"{preview} - X/Twitter",
                        preview_text=preview,
                    )
                )
                changed = True
            else:
                updated_rows.append(row)
        if not changed:
            return
        self.source_resource_rows = updated_rows
        self._refresh_source_resource_rows()
        self._refresh_discussion_source_controls()

    def _mark_twitter_source_row_preview_failed(self, row_id: str, error: Exception) -> None:
        if hasattr(self, "url_status"):
            self.url_status.configure(
                text=f"X/Twitter post text preview unavailable: {type(error).__name__}. Fallback title kept.",
                text_color=COLORS["warning"],
            )

    def _start_twitter_source_row_metadata_probe(self, rows: Sequence[SourceResourceRowState]) -> None:
        twitter_rows = [row for row in rows if self._source_row_is_twitter(row)]
        if not twitter_rows:
            return

        def worker(snapshot: tuple[SourceResourceRowState, ...]) -> None:
            for row in snapshot:
                try:
                    preview = self._twitter_oembed_text_probe(row.canonical_url)
                except Exception as error:
                    self.after(
                        0,
                        lambda row_id=row.row_id, err=error: self._mark_twitter_source_row_preview_failed(
                            row_id,
                            err,
                        ),
                    )
                    continue
                if preview:
                    self.after(
                        0,
                        lambda row_id=row.row_id, preview=preview: self._apply_twitter_source_row_preview(
                            row_id,
                            preview,
                        ),
                    )


        threading.Thread(target=worker, args=(tuple(twitter_rows),), daemon=True).start()

    def _webpage_image_prefetch_cache_key(self, row: SourceResourceRowState) -> str:
        return str(getattr(row, "canonical_url", "") or getattr(row, "raw_url", "") or "").strip()

    def _source_row_should_prefetch_webpage_images(self, row: SourceResourceRowState) -> bool:
        if row.adapter_id in {"youtube", "twitter_x"}:
            return False
        url = self._webpage_image_prefetch_cache_key(row)
        return url.lower().startswith(("http://", "https://"))

    def _apply_prefetched_webpage_image_discovery(self, row_id: str, cache_key: str, discovery: Any) -> None:
        cache = self.__dict__.setdefault("webpage_image_discovery_cache_by_url", {})
        cache[cache_key] = discovery
        while len(cache) > 24:
            try:
                cache.pop(next(iter(cache)))
            except Exception:
                break
        updated_rows: list[SourceResourceRowState] = []
        changed = False
        target_domain = ""
        for existing_row in self.__dict__.get("source_resource_rows", ()):
            if existing_row.row_id == row_id:
                target_domain = existing_row.domain
                updated_rows.append(replace(existing_row, image_resources=discovery.resources))
                changed = True
            else:
                updated_rows.append(existing_row)
        if changed:
            self.source_resource_rows = updated_rows
        inflight = self.__dict__.setdefault("webpage_image_discovery_prefetch_inflight", set())
        inflight.discard(cache_key)
        if discovery.resources:
            self.log_message(
                (
                    f"Prefetched {len(discovery.resources)} webpage image candidate(s) for {target_domain or cache_key}; "
                    "Images can open from the cached candidate list."
                ),
                "muted",
            )

    def _mark_webpage_image_prefetch_finished(self, cache_key: str, error: Exception | None = None) -> None:
        inflight = self.__dict__.setdefault("webpage_image_discovery_prefetch_inflight", set())
        inflight.discard(cache_key)
        if error is not None:
            logger.debug("Webpage image prefetch failed for %s: %s", cache_key, error)

    def _start_webpage_image_source_row_prefetch(self, rows: Sequence[SourceResourceRowState]) -> None:
        # Source-row prefetch is a real GUI/background-network path.  Some
        # self-tests call URL intake on App.__new__(App) stubs; those objects
        # have no Tk interpreter and must not start discovery threads, otherwise
        # Playwright/Node can outlive the short test process and print EPIPE
        # during interpreter shutdown.  The real app has self.tk in __dict__.
        if "tk" not in self.__dict__:
            return
        candidates = [row for row in rows if self._source_row_should_prefetch_webpage_images(row)]
        if not candidates:
            return
        self._start_internal_browser_image_discovery_service()
        cache = self.__dict__.setdefault("webpage_image_discovery_cache_by_url", {})
        inflight = self.__dict__.setdefault("webpage_image_discovery_prefetch_inflight", set())
        work: list[SourceResourceRowState] = []
        for row in candidates:
            cache_key = self._webpage_image_prefetch_cache_key(row)
            if not cache_key or cache_key in cache or cache_key in inflight:
                continue
            inflight.add(cache_key)
            work.append(row)
        if not work:
            return

        def worker(snapshot: tuple[SourceResourceRowState, ...]) -> None:
            for row in snapshot:
                cache_key = self._webpage_image_prefetch_cache_key(row)
                try:
                    url_text = " ".join(str(part or "").lower() for part in (row.raw_url, row.canonical_url, row.domain))
                    if any(marker in url_text for marker in ("msn.com", "x.com", "twitter.com", "facebook.com", "instagram.com")):
                        prewarm_rendered_browser_discovery_worker()
                    discovery = discover_webpage_images_for_row(row)
                except Exception as error:
                    self.after(0, lambda key=cache_key, err=error: self._mark_webpage_image_prefetch_finished(key, err))
                    continue
                self.after(
                    0,
                    lambda row_id=row.row_id, key=cache_key, result=discovery: self._apply_prefetched_webpage_image_discovery(
                        row_id,
                        key,
                        result,
                    ),
                )

        threading.Thread(target=worker, args=(tuple(work),), daemon=True).start()

    def _webpage_video_prefetch_cache_key(self, row: SourceResourceRowState) -> str:
        return str(getattr(row, "canonical_url", "") or getattr(row, "raw_url", "") or "").strip()

    def _source_row_should_prefetch_webpage_videos(self, row: SourceResourceRowState) -> bool:
        # YouTube and X/Twitter keep source-specific media routes.  Generic
        # webpage/MSN-style rows can run webpage video discovery in the
        # background and still prefer JDownloader/API3128 for download routing.
        if row.adapter_id in {"youtube", "twitter_x"}:
            return False
        url = self._webpage_video_prefetch_cache_key(row)
        return url.lower().startswith(("http://", "https://"))

    def _apply_prefetched_webpage_video_discovery(self, row_id: str, cache_key: str, discovery: Any) -> None:
        cache = self.__dict__.setdefault("webpage_video_discovery_cache_by_url", {})
        cache[cache_key] = discovery
        while len(cache) > 24:
            try:
                cache.pop(next(iter(cache)))
            except Exception:
                break
        updated_rows: list[SourceResourceRowState] = []
        changed = False
        target_domain = ""
        for existing_row in self.__dict__.get("source_resource_rows", ()):
            if existing_row.row_id == row_id:
                target_domain = existing_row.domain
                updated_rows.append(replace(existing_row, video_audio_resources=discovery.resources))
                changed = True
            else:
                updated_rows.append(existing_row)
        if changed:
            self.source_resource_rows = updated_rows
            try:
                self._refresh_source_resource_rows()
            except Exception:
                logger.debug("Could not refresh source rows after video prefetch.", exc_info=True)
        inflight = self.__dict__.setdefault("webpage_video_discovery_prefetch_inflight", set())
        inflight.discard(cache_key)
        summary = getattr(discovery, "summary", {}) or {}
        if discovery.resources:
            self._start_webpage_video_hover_preview_prefetch_for_discovery(
                target_domain or cache_key,
                cache_key,
                discovery,
            )
            self.log_message(
                (
                    f"Prefetched {len(discovery.resources)} webpage video/audio candidate(s) for {target_domain or cache_key}; "
                    f"route_preference={summary.get('route_preference', 'try_jdownloader_api3128_before_yt_dlp')}; "
                    f"recommended_backend={summary.get('recommended_backend_id', 'unknown')}; "
                    "Video & Audio can open from the cached candidate list; live hover uses fast-start playback, a VDH-length ~5.15s 30fps hover loop, elapsed-clock frame selection, repaint-safe instant wrapping, and a fixed wait-poll-to-playback handoff."
                ),
                "muted",
            )

    def _start_webpage_video_hover_preview_prefetch_for_discovery(self, label: str, page_url: str, discovery: Any) -> None:
        # Make Video DownloadHelper-style hover previews ready before the user
        # opens Video & Audio.  This runs only after a user-added source row has
        # already produced cached candidates; it is not an app-startup scan.
        if "tk" not in self.__dict__:
            return
        live_mode = bool(getattr(self, "webpage_video_live_preview_enabled", True))
        # V79B: do not run source-row ffmpeg hover warm-up in live mode.
        # It can race an already-open dialog and warm a non-hovered tile, which
        # made playback appear on the wrong card. The dialog performs selected
        # tile warm-up after the concrete card is rendered, and hover can start
        # an on-demand decode for the exact card under the pointer.
        if live_mode:
            return
        live_mode_work_limit = 6
        resources = tuple(getattr(discovery, "resources", ()) or ())
        if not resources:
            return
        hover_cache = self.__dict__.setdefault("webpage_video_hover_preview_pil_frames_by_url", {})
        inflight = self.__dict__.setdefault("webpage_video_hover_preview_prefetch_inflight", set())
        cache_limit = 48
        work: list[tuple[str, str, str]] = []
        for item in resources:
            media_url = str(getattr(item, "reference_url", "") or getattr(item, "canonical_url", "") or "").strip()
            if not media_url:
                continue
            if not can_generate_video_hover_preview(
                media_url,
                extension=str(getattr(item, "extension", "") or ""),
                mime_type=str(getattr(item, "mime_type", "") or ""),
            ):
                continue
            cache_key = video_hover_preview_cache_key(media_url)
            if cache_key in hover_cache or cache_key in inflight:
                continue
            inflight.add(cache_key)
            poster_url = str(getattr(item, "thumbnail_reference", "") or "")
            work.append((cache_key, media_url, poster_url))
            if len(work) >= live_mode_work_limit:
                break
        if not work:
            return

        def worker(snapshot: tuple[tuple[str, str, str], ...]) -> None:
            added = 0
            for cache_key, media_url, poster_url in snapshot:
                try:
                    try:
                        frames = extract_video_tile_hover_stream_frames_pil(
                            media_url,
                            timeout=8.5,
                            first_frame_timeout=1.6,
                            duration_seconds=5.15,
                            fps=30,
                            referer=page_url,
                            frame_size=(168, 96),
                            max_frames=155,
                            project_root=Path(__file__).resolve().parent,
                        )
                    except Exception:
                        frames = extract_video_hover_preview_frames_pil(
                            media_url,
                            timeout=8.0,
                            seek_seconds=0.0,
                            duration_seconds=5.15,
                            fps=30,
                            referer=page_url,
                            max_frames=155,
                        )
                    if len(frames) >= 2:
                        hover_cache[cache_key] = tuple(frame.copy() for frame in frames)
                        added += 1
                        while len(hover_cache) > cache_limit:
                            try:
                                hover_cache.pop(next(iter(hover_cache)))
                            except Exception:
                                break
                except Exception as error:
                    logger.debug("Could not prefetch animated video hover preview for %s: %s", media_url, error)
                finally:
                    try:
                        inflight.discard(cache_key)
                    except Exception:
                        pass
            if added:
                try:
                    self.after(
                        0,
                        lambda count=added, target=label: self.log_message(
                            f"Prefetched {count} animated video hover preview(s) for {target}; hover playback can start from cache.",
                            "muted",
                        ),
                    )
                except Exception:
                    pass

        threading.Thread(target=worker, args=(tuple(work),), daemon=True).start()

    def _mark_webpage_video_prefetch_finished(self, cache_key: str, error: Exception | None = None) -> None:
        inflight = self.__dict__.setdefault("webpage_video_discovery_prefetch_inflight", set())
        inflight.discard(cache_key)
        if error is not None:
            logger.debug("Webpage video prefetch failed for %s: %s", cache_key, error)

    def _start_webpage_video_source_row_prefetch(self, rows: Sequence[SourceResourceRowState]) -> None:
        # Video prefetch may perform static HTML and rendered DOM/network probes.
        # It must not run from App.__new__(App) self-test stubs because those
        # objects do not own a Tk interpreter or browser lifecycle.
        if "tk" not in self.__dict__:
            return
        candidates = [row for row in rows if self._source_row_should_prefetch_webpage_videos(row)]
        if not candidates:
            return
        cache = self.__dict__.setdefault("webpage_video_discovery_cache_by_url", {})
        inflight = self.__dict__.setdefault("webpage_video_discovery_prefetch_inflight", set())
        work: list[SourceResourceRowState] = []
        for row in candidates:
            cache_key = self._webpage_video_prefetch_cache_key(row)
            if not cache_key or cache_key in cache or cache_key in inflight:
                continue
            inflight.add(cache_key)
            work.append(row)
        if not work:
            return

        def worker(snapshot: tuple[SourceResourceRowState, ...]) -> None:
            for row in snapshot:
                cache_key = self._webpage_video_prefetch_cache_key(row)
                try:
                    discovery = discover_webpage_videos_for_row(
                        row,
                        fetch_static_html=True,
                        run_rendered_probe=True,
                        rendered_probe_timeout_ms=12000,
                    )
                except Exception as error:
                    self.after(0, lambda key=cache_key, err=error: self._mark_webpage_video_prefetch_finished(key, err))
                    continue
                self.after(
                    0,
                    lambda row_id=row.row_id, key=cache_key, result=discovery: self._apply_prefetched_webpage_video_discovery(
                        row_id,
                        key,
                        result,
                    ),
                )

        threading.Thread(target=worker, args=(tuple(work),), daemon=True).start()

    def _process_youtube_source_row_media_result(self, result: Any, parent: Any | None = None, *, show_message: bool = True) -> bool:
        """Import a completed YouTube media queue result into FILES on the Tk/UI thread."""
        if result.status != YOUTUBE_GUI_MEDIA_QUEUE_STATUS_READY:
            if show_message:
                messagebox.showinfo("YouTube media", result.message, parent=parent or self)
            self.log_message(result.message.replace("\n", " "), "warning")
            return False
        added = 0
        for file_path in result.files_to_add:
            if not os.path.isfile(file_path):
                continue
            file_kind = self._session_file_kind_for_path(file_path)
            entry = self._add_session_file(file_path, file_kind, select=(added == 0))
            if entry is not None:
                added += 1
        if show_message:
            messagebox.showinfo("YouTube media", result.message, parent=parent or self)
        self.log_message(
            (
                f"YouTube media completed by Go: quality={result.selected_quality_label}; "
                f"components={', '.join(result.selected_components)}; "
                f"FILES added={added}; auto mux={'yes' if result.auto_mux else 'no'}"
            ),
            "success" if added else "warning",
        )
        return added > 0

    def _queue_youtube_source_row_media(self, row_id: str, parent: Any | None = None, *, show_message: bool = True) -> bool:
        row = self._source_row_by_id(row_id)
        if row is None:
            return False
        prefs = self._youtube_preferences_for_row(row_id)
        quality_var = self._youtube_quality_var_for_row(row_id)
        quality_enabled = self._youtube_quality_enabled_var_for_row(row_id).get()
        if not quality_enabled:
            return False
        quality = quality_var.get() if prefs.show_quality_dropdown else prefs.default_quality_label
        result = queue_youtube_gui_source_row_selection(
            row=row,
            quality_label=quality,
            preferences=prefs,
            probe_metadata=True,
        )
        return self._process_youtube_source_row_media_result(result, parent=parent, show_message=show_message)

    def _start_youtube_source_row_media_worker(self, row_id: str, parent: Any | None = None, *, show_message: bool = False) -> None:
        """Download YouTube media in a worker so the Tk window does not freeze."""
        row = self._source_row_by_id(row_id)
        if row is None:
            return
        prefs = self._youtube_preferences_for_row(row_id)
        quality_var = self._youtube_quality_var_for_row(row_id)
        quality_enabled = self._youtube_quality_enabled_var_for_row(row_id).get()
        if not quality_enabled:
            return
        quality = quality_var.get() if prefs.show_quality_dropdown else prefs.default_quality_label

        worker_token = object()
        self._youtube_media_worker_token = worker_token
        self._youtube_media_worker_cancel_requested = False

        self.fetch_state.start()
        if hasattr(self.fetch_button, "grid_remove"):
            self.fetch_button.grid_remove()
        else:
            self.fetch_button.pack_forget()
        if hasattr(self.cancel_button, "grid"):
            self.cancel_button.grid(row=0, column=0, sticky="w")
        else:
            self.cancel_button.pack(side="left")
        self.export_button.configure(state="disabled")
        self.export_excel_button.configure(state="disabled")
        self.export_txt_button.configure(state="disabled")
        self.evidence_button.configure(state="disabled")
        self.progress_bar.set(0)
        try:
            self.progress_bar.start()
        except Exception:
            logger.debug("Could not start progress animation for YouTube media worker.", exc_info=True)
        self.status_label.configure(text="Downloading YouTube media with internal JDownloader...", text_color=COLORS["text_secondary"])
        self._set_operational_capture_status("Downloading YouTube media with internal JDownloader...", "muted")
        self._refresh_export_entry_state()

        def worker() -> None:
            try:
                result = queue_youtube_gui_source_row_selection(
                    row=row,
                    quality_label=quality,
                    preferences=prefs,
                    probe_metadata=True,
                )
            except Exception as error:
                logger.exception("YouTube media worker failed")

                def fail() -> None:
                    if getattr(self, "_youtube_media_worker_token", None) is not worker_token:
                        return
                    self._youtube_media_worker_token = None
                    try:
                        self.progress_bar.stop()
                    except Exception:
                        pass
                    self.status_label.configure(text="YouTube media download failed", text_color=COLORS["error"])
                    self._set_operational_capture_status(f"YouTube media download failed: {error}", "error")
                    self.log_message(f"YouTube media download failed: {error}", "error")
                    if show_message:
                        messagebox.showerror("YouTube media", f"YouTube media download failed:\n\n{error}", parent=parent or self)
                    self._reset_fetch_ui()
                    self._refresh_export_entry_state()

                self.after(0, fail)
                return

            def complete() -> None:
                if getattr(self, "_youtube_media_worker_token", None) is not worker_token:
                    return
                self._youtube_media_worker_token = None
                try:
                    self.progress_bar.stop()
                except Exception:
                    pass
                added = self._process_youtube_source_row_media_result(result, parent=parent, show_message=show_message)
                if added:
                    self.status_label.configure(text="YouTube media downloaded and added to FILES", text_color=COLORS["success"])
                    self._set_operational_capture_status(
                        "YouTube media downloaded and added to FILES. Export will include the completed media files.",
                        "success",
                    )
                else:
                    self.status_label.configure(text="YouTube media finished but no files were added", text_color=COLORS["warning"])
                    self._set_operational_capture_status(
                        result.message or "YouTube media finished but no files were added.",
                        "warning",
                    )
                self._reset_fetch_ui()
                self._refresh_export_entry_state()

            self.after(0, complete)

        threading.Thread(target=worker, daemon=True).start()

    def _open_youtube_source_settings(self, row_id: str) -> None:
        """Open the combined YouTube settings window focused on this source row."""
        self._open_youtube_filter_settings_window(row_id=row_id)

    @staticmethod
    def _archive_service_button_text(service_id: str) -> str:
        if service_id == "internet_archive_wayback":
            return "Wayback"
        if service_id == "archive_today":
            return "archive.ph"
        if service_id == ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE:
            return "Local"
        return service_id

    def _refresh_source_resource_rows(self) -> None:
        frame = getattr(self, "source_rows_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()
        rows = list(getattr(self, "source_resource_rows", ()))
        if not rows:
            empty = ctk.CTkLabel(
                frame,
                text="No source rows yet. Press Enter in Source URLs to add local source rows.",
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_muted"],
                justify="right",
                anchor="e",
            )
            empty.pack(fill="x", anchor="e", padx=10, pady=8)
            return

        for row_index, row in enumerate(rows):
            row_is_youtube = self._source_row_is_youtube(row)
            row_is_twitter = self._source_row_is_twitter(row)
            row_height = 72 if row_is_youtube or row_is_twitter else 98
            row_frame = ctk.CTkFrame(frame, fg_color="transparent", height=row_height)
            row_frame.pack(fill="x", padx=8, pady=(8 if row_index == 0 else 4, 6))
            row_frame.grid_propagate(False)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=0)
            row_frame.grid_columnconfigure(2, weight=0)

            title_button = ctk.CTkButton(
                row_frame,
                text=row.title,
                command=lambda row_id=row.row_id: self._show_source_row_details(row_id),
                height=28,
                anchor="w",
                fg_color="transparent",
                hover_color=COLORS["bg_card"],
                text_color=COLORS["text_primary"],
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            title_button.grid(row=0, column=0, sticky="ew")
            title_button.tooltip_text = row.canonical_url

            detail_text = self._short_source_url_for_row(row)
            detail = ctk.CTkLabel(
                row_frame,
                text=detail_text,
                font=ctk.CTkFont(size=10),
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            detail.grid(row=1, column=0, sticky="ew", padx=(2, 0))
            detail.tooltip_text = row.canonical_url

            actions = ctk.CTkFrame(row_frame, fg_color="transparent")
            actions.grid(row=2, column=0, sticky="ew", pady=(6, 0))
            actions.grid_columnconfigure(0, weight=1)

            next_action_column = 1
            if row_is_youtube:
                # YouTube media is controlled directly on the source card;
                # generic row media buttons are reserved for non-YouTube rows.
                prefs = self._youtube_preferences_for_row(row.row_id)
                quality_enabled_var = self._youtube_quality_enabled_var_for_row(row.row_id)
                youtube_header = ctk.CTkFrame(row_frame, fg_color="transparent")
                youtube_header.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(8, 4), pady=(0, 0))
                youtube_header.grid_columnconfigure(0, weight=0)

                def _open_youtube_settings(row_id=row.row_id) -> None:
                    self._open_youtube_source_settings(row_id)

                if prefs.show_quality_dropdown:
                    youtube_control = ctk.CTkFrame(
                        youtube_header,
                        fg_color=COLORS["bg_input"],
                        border_width=1,
                        border_color=COLORS["border"],
                        corner_radius=7,
                        width=76,
                        height=28,
                    )
                    youtube_control.grid(row=0, column=0, sticky="ne")
                    youtube_control.grid_propagate(False)

                    quality_values = list(self._youtube_quality_values_for_row(row.row_id)) or ["1080"]
                    quality_var = self._youtube_quality_var_for_row(row.row_id)
                    if quality_var.get() not in quality_values:
                        quality_var.set(quality_values[0])

                    quality_label = ctk.CTkLabel(
                        youtube_control,
                        text=quality_var.get(),
                        fg_color=COLORS["bg_input"],
                        text_color=COLORS["text_primary"],
                        font=ctk.CTkFont(size=11, weight="bold"),
                        anchor="w",
                        width=30,
                        height=20,
                    )
                    quality_label.place(x=20, y=4)
                    quality_label.tooltip_text = "Choose one of this YouTube video's available qualities."
                    try:
                        quality_label.configure(cursor="hand2")
                    except Exception:
                        pass

                    def _sync_youtube_quality_enabled(label=quality_label, var=quality_enabled_var):
                        enabled = bool(var.get())
                        try:
                            label.configure(
                                text_color=COLORS["text_primary"] if enabled else COLORS["text_muted"],
                            )
                            label.configure(cursor="hand2" if enabled else "arrow")
                        except Exception:
                            pass

                    def _open_inline_quality_dropdown(row_id=row.row_id, label=quality_label):
                        if not self._youtube_quality_enabled_var_for_row(row_id).get():
                            return
                        self._open_youtube_source_quality_dropdown_menu(row_id, label, label)

                    def _quality_label_enter(_event=None, label=quality_label, var=quality_enabled_var):
                        if not bool(var.get()):
                            return "break"
                        try:
                            label.configure(fg_color=COLORS["border"])
                        except Exception:
                            pass
                        return "break"

                    def _quality_label_leave(_event=None, label=quality_label):
                        try:
                            label.configure(fg_color=COLORS["bg_input"])
                        except Exception:
                            pass
                        return "break"

                    quality_label.bind("<Enter>", _quality_label_enter)
                    quality_label.bind("<Leave>", _quality_label_leave)
                    quality_label.bind("<Button-1>", lambda _event: _open_inline_quality_dropdown())

                    def _toggle_youtube_quality(row_id=row.row_id):
                        self._on_youtube_source_quality_enabled_changed(row_id)
                        _sync_youtube_quality_enabled()

                    quality_checkbox = ctk.CTkCheckBox(
                        youtube_control,
                        text="",
                        variable=quality_enabled_var,
                        command=_toggle_youtube_quality,
                        width=14,
                        height=14,
                        checkbox_width=12,
                        checkbox_height=12,
                    )
                    quality_checkbox.place(x=4, y=2)
                    quality_checkbox.tooltip_text = "Enable/disable the selected YouTube media package for Go."

                    youtube_button = ctk.CTkButton(
                        youtube_control,
                        text="▶",
                        command=_open_youtube_settings,
                        width=16,
                        height=16,
                        fg_color="#ff0000",
                        hover_color="#cc0000",
                        text_color="#ffffff",
                        font=ctk.CTkFont(size=7, weight="bold"),
                        corner_radius=4,
                    )
                    youtube_button.place(x=56, y=2)
                    youtube_button.tooltip_text = "YouTube media settings."
                    _sync_youtube_quality_enabled()
                else:
                    youtube_button = ctk.CTkButton(
                        youtube_header,
                        text="▶",
                        command=_open_youtube_settings,
                        width=28,
                        height=28,
                        fg_color="#ff0000",
                        hover_color="#cc0000",
                        text_color="#ffffff",
                        font=ctk.CTkFont(size=12, weight="bold"),
                        corner_radius=6,
                    )
                    youtube_button.grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky="ne")
                    youtube_button.tooltip_text = "YouTube media settings."
                next_action_column = 1
            elif row_is_twitter:
                twitter_state = build_twitter_compact_row_state(row)
                self._ensure_twitter_x_icon()
                twitter_header = ctk.CTkFrame(row_frame, fg_color="transparent")
                twitter_header.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(8, 4), pady=(0, 0))
                twitter_header.grid_columnconfigure(0, weight=0)

                mode_var = self._twitter_mode_var_for_row(row.row_id)
                if mode_var.get() not in twitter_state.dropdown_options:
                    mode_var.set(twitter_state.dropdown_options[0])
                row_enabled_var = self._twitter_row_enabled_var_for_row(row.row_id)
                show_type_dropdown_var = self._twitter_show_type_dropdown_var_for_row(row.row_id)
                twitter_mode_text = mode_var.get()
                twitter_is_thread = twitter_mode_text == "Thread"
                twitter_mode_display_text = "Thread  " if twitter_is_thread else twitter_mode_text
                twitter_control_width = 97 if twitter_is_thread else 95
                twitter_button_width = 16
                twitter_button_height = 16
                twitter_button_right_pad = 18
                twitter_checkbox_x = 4
                twitter_label_x = 22
                twitter_button_x = twitter_control_width - twitter_button_width - twitter_button_right_pad
                twitter_label_width = max(72 if twitter_is_thread else 32, twitter_button_x - twitter_label_x)

                if bool(show_type_dropdown_var.get()):
                    twitter_control = ctk.CTkFrame(
                        twitter_header,
                        fg_color=COLORS["bg_input"],
                        border_width=1,
                        border_color=COLORS["border"],
                        corner_radius=7,
                        width=twitter_control_width,
                        height=twitter_state.compact_control_height,
                    )
                    twitter_control.grid(row=0, column=0, sticky="ne")
                    twitter_control.grid_propagate(False)

                    row_enabled_checkbox = ctk.CTkCheckBox(
                        twitter_control,
                        text="",
                        variable=row_enabled_var,
                        command=lambda row_id=row.row_id: self._on_twitter_row_enabled_changed(row_id, mode_label),
                        width=14,
                        height=14,
                        checkbox_width=12,
                        checkbox_height=12,
                    )
                    row_enabled_checkbox.place(x=twitter_checkbox_x, y=2)
                    row_enabled_checkbox.tooltip_text = "Enable/disable this X/Twitter source row for Go."

                    mode_label = ctk.CTkLabel(
                        twitter_control,
                        text=twitter_mode_display_text,
                        fg_color=COLORS["bg_input"],
                        text_color=COLORS["text_primary"] if bool(row_enabled_var.get()) else COLORS["text_muted"],
                        font=ctk.CTkFont(size=9 if twitter_is_thread else 11, weight="bold"),
                        anchor="w",
                        width=twitter_label_width,
                        height=20,
                    )
                    mode_label.place(x=twitter_label_x, y=4)
                    mode_label.tooltip_text = (
                        "X/Twitter capture mode: Post captures the current post target; "
                        "Thread captures the whole thread/conversation where supported."
                    )
                    try:
                        mode_label.configure(cursor="hand2" if bool(row_enabled_var.get()) else "arrow")
                    except Exception:
                        pass

                    def _open_inline_twitter_mode(row_id=row.row_id, label=mode_label):
                        if not bool(self._twitter_row_enabled_var_for_row(row_id).get()):
                            return "break"
                        self._open_twitter_source_mode_dropdown_menu(row_id, label, label)
                        return "break"

                    def _twitter_mode_label_enter(_event=None, label=mode_label):
                        if not bool(row_enabled_var.get()):
                            return "break"
                        try:
                            label.configure(fg_color=COLORS["border"])
                        except Exception:
                            pass
                        return "break"

                    def _twitter_mode_label_leave(_event=None, label=mode_label):
                        try:
                            label.configure(fg_color=COLORS["bg_input"])
                        except Exception:
                            pass
                        return "break"

                    mode_label.bind("<Enter>", _twitter_mode_label_enter)
                    mode_label.bind("<Leave>", _twitter_mode_label_leave)
                    mode_label.bind("<Button-1>", lambda _event: _open_inline_twitter_mode())

                    twitter_settings_button = ctk.CTkButton(
                        twitter_control,
                        text="" if self.twitter_x_icon_image is not None else "X",
                        image=self.twitter_x_icon_image,
                        command=lambda row_id=row.row_id: self._open_twitter_source_settings(row_id),
                        width=twitter_button_width,
                        height=twitter_button_height,
                        fg_color=COLORS["bg_input"],
                        hover_color=COLORS["border"],
                        text_color=COLORS["text_primary"],
                        font=ctk.CTkFont(size=11, weight="bold"),
                        corner_radius=4,
                    )
                    twitter_settings_button.place(x=twitter_button_x, y=2)
                    twitter_settings_button.tooltip_text = (
                        "X/Twitter settings. Media download stays inside X settings and uses the shared media capability model."
                    )
                else:
                    twitter_settings_button = ctk.CTkButton(
                        twitter_header,
                        text="" if self.twitter_x_icon_image is not None else "X",
                        image=self.twitter_x_icon_image,
                        command=lambda row_id=row.row_id: self._open_twitter_source_settings(row_id),
                        width=28,
                        height=28,
                        fg_color=COLORS["bg_input"],
                        hover_color=COLORS["border"],
                        text_color=COLORS["text_primary"],
                        font=ctk.CTkFont(size=12, weight="bold"),
                        corner_radius=6,
                    )
                    twitter_settings_button.grid(row=0, column=0, padx=(0, 0), pady=(0, 0), sticky="ne")
                    twitter_settings_button.tooltip_text = "X/Twitter source settings."
                next_action_column = 1
            else:
                images_button = ctk.CTkButton(
                    actions,
                    text="▧",
                    command=lambda row_id=row.row_id: self._open_source_resource_window(
                        row_id, RESOURCE_KIND_IMAGE
                    ),
                    width=34,
                    height=28,
                    fg_color=COLORS["accent_secondary"],
                    hover_color=COLORS["border"],
                )
                images_button.tooltip_text = "Images and GIFs"
                images_button.grid(row=0, column=next_action_column, padx=(0, 6), sticky="n")
                next_action_column += 1

                media_button = ctk.CTkButton(
                    actions,
                    text="▶",
                    command=lambda row_id=row.row_id: self._open_source_resource_window(
                        row_id, RESOURCE_KIND_VIDEO_AUDIO
                    ),
                    width=34,
                    height=28,
                    fg_color=COLORS["accent_secondary"],
                    hover_color=COLORS["border"],
                )
                media_button.tooltip_text = "Video and audio"
                media_button.grid(row=0, column=next_action_column, padx=(0, 6), sticky="n")
                next_action_column += 1

            if not row_is_youtube and not row_is_twitter:
                for archive_status in row.archive_statuses:
                    archive_text = self._archive_service_button_text(archive_status.service_id)
                    if archive_status.service_id == ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE:
                        self._ensure_asr_cog_icons()
                        local_wrap = ctk.CTkFrame(actions, fg_color="transparent", width=94, height=28)
                        local_wrap.grid(row=0, column=next_action_column, padx=(0, 6), sticky="n")
                        local_wrap.grid_propagate(False)
                        archive_button = ctk.CTkButton(
                            local_wrap,
                            text="Local",
                            command=lambda status=archive_status: self._show_archive_status(status),
                            width=94,
                            height=28,
                            fg_color=self._archive_status_color(archive_status.color_name),
                            hover_color=COLORS["border"],
                            text_color="#000000",
                            anchor="w",
                        )
                        archive_button.place(x=0, y=0)
                        if self.asr_cog_icon_image is not None:
                            cog_label = tk.Label(
                                local_wrap,
                                image=self.asr_cog_icon_image,
                                bg=self._archive_status_color(archive_status.color_name),
                                activebackground=self._archive_status_color(archive_status.color_name),
                                bd=0,
                                relief="flat",
                                highlightthickness=0,
                                padx=0,
                                pady=0,
                                cursor="hand2",
                            )
                        else:
                            cog_label = tk.Label(
                                local_wrap,
                                text=ASR_ACTION_BUTTON_SPEC["fallback_cog_text"],
                                bg=self._archive_status_color(archive_status.color_name),
                                fg=ASR_ACTION_BUTTON_SPEC["fallback_cog_normal_fg"],
                                activebackground=self._archive_status_color(archive_status.color_name),
                                activeforeground=ASR_ACTION_BUTTON_SPEC["fallback_cog_hover_fg"],
                                bd=0,
                                relief="flat",
                                highlightthickness=0,
                                padx=0,
                                pady=0,
                                font=ASR_ACTION_BUTTON_SPEC["fallback_cog_font"],
                                cursor="hand2",
                            )
                        cog_label.place(x=64, y=2, width=24, height=24)

                        def _local_archive_normal(button=archive_button, label=cog_label, status=archive_status):
                            color = self._archive_status_color(status.color_name)
                            try:
                                button.configure(fg_color=color, hover_color=COLORS["border"])
                                label.configure(bg=color, activebackground=color)
                                if self.asr_cog_icon_image is not None:
                                    label.configure(image=self.asr_cog_icon_image)
                                else:
                                    label.configure(fg=ASR_ACTION_BUTTON_SPEC["fallback_cog_normal_fg"])
                            except Exception:
                                pass

                        def _local_archive_button_hover(button=archive_button, label=cog_label):
                            try:
                                button.configure(fg_color=COLORS["border"], hover_color=COLORS["border"])
                                label.configure(bg=COLORS["border"], activebackground=COLORS["border"])
                                if self.asr_cog_icon_image is not None:
                                    label.configure(image=self.asr_cog_icon_image)
                                else:
                                    label.configure(fg=ASR_ACTION_BUTTON_SPEC["fallback_cog_normal_fg"])
                            except Exception:
                                pass

                        def _local_archive_cog_hover(button=archive_button, label=cog_label, status=archive_status):
                            color = self._archive_status_color(status.color_name)
                            try:
                                button.configure(fg_color=color, hover_color=COLORS["border"])
                                label.configure(bg=color, activebackground=color)
                                if self.asr_cog_icon_hover_image is not None:
                                    label.configure(image=self.asr_cog_icon_hover_image)
                                else:
                                    label.configure(fg=ASR_ACTION_BUTTON_SPEC["fallback_cog_hover_fg"])
                            except Exception:
                                pass

                        archive_button.bind("<Enter>", lambda _event: _local_archive_button_hover(), add="+")
                        archive_button.bind("<Leave>", lambda _event: _local_archive_normal(), add="+")
                        cog_label.bind("<Enter>", lambda _event: (_local_archive_cog_hover(), "break")[-1])
                        cog_label.bind("<Leave>", lambda _event: (_local_archive_normal(), "break")[-1])
                        cog_label.bind("<Button-1>", lambda _event, row_id=row.row_id, status=archive_status: self._open_local_web_archive_settings(row_id, status))
                        archive_button.tooltip_text = "Local Web Archive"
                    else:
                        archive_button = ctk.CTkButton(
                            actions,
                            text=archive_text,
                            command=lambda status=archive_status: self._show_archive_status(status),
                            width=94,
                            height=28,
                            fg_color=self._archive_status_color(archive_status.color_name),
                            hover_color=COLORS["border"],
                            text_color="#000000",
                        )
                        archive_button.grid(
                            row=0,
                            column=next_action_column,
                            padx=(0, 6),
                            sticky="n",
                        )
                        archive_button.tooltip_text = archive_status.tooltip
                    status_label = ctk.CTkLabel(
                        actions,
                        text=self._archive_status_label_text(archive_status),
                        font=ctk.CTkFont(size=9),
                        text_color=COLORS["text_primary"],
                        justify="center",
                    )
                    status_label.grid(
                        row=1,
                        column=next_action_column,
                        padx=(0, 6),
                        pady=(1, 0),
                        sticky="n",
                    )
                    next_action_column += 1

            remove_parent = row_frame if row_is_youtube or row_is_twitter else actions
            remove_button = ctk.CTkButton(
                remove_parent,
                text="×",
                command=lambda row_id=row.row_id: self._remove_source_resource_row_clicked(row_id),
                width=24 if row_is_youtube or row_is_twitter else 28,
                height=24 if row_is_youtube or row_is_twitter else 28,
                fg_color="transparent",
                hover_color=COLORS["error"],
                text_color=COLORS["text_secondary"],
            )
            remove_button.tooltip_text = "Remove source"
            if row_is_youtube or row_is_twitter:
                remove_button.grid(
                    row=0,
                    column=2,
                    rowspan=2,
                    padx=(6, 0),
                    pady=(0, 0),
                    sticky="ne",
                )
            else:
                remove_button.grid(
                    row=0,
                    column=next_action_column,
                    padx=(0, 0),
                    sticky="n",
                )

        self._bind_main_blank_scroll_targets(frame)

    def _source_row_by_id(self, row_id: str) -> SourceResourceRowState | None:
        for row in self.__dict__.get("source_resource_rows", ()):
            if row.row_id == row_id:
                return row
        return None

    def _remove_source_resource_row_clicked(self, row_id: str) -> None:
        rows, selected = remove_source_resource_row(
            tuple(self.__dict__.get("source_resource_rows", ())),
            row_id,
            selected_row_id=self.__dict__.get("selected_discussion_source_id", ""),
        )
        self.source_resource_rows = list(rows)
        self.selected_discussion_source_id = selected
        self.source_resource_selections.pop(row_id, None)
        self.source_screenshot_preferences.pop(row_id, None)
        self._refresh_source_resource_rows()
        self._refresh_discussion_source_controls()
        self.log_message("Removed local source row. Network actions performed: none.", "muted")

    def _copy_text_to_clipboard(self, value: str, log_message: str = "Copied to clipboard.") -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(str(value or ""))
            self.log_message(log_message, "success")
        except Exception:
            logger.debug("Could not copy text to clipboard.", exc_info=True)

    def _youtube_video_id_from_url(self, url: str) -> str:
        """Extract a YouTube video id for local metadata matching only."""
        try:
            parts = urllib.parse.urlsplit(str(url or "").strip())
            host = parts.netloc.lower()
            path_parts = [part for part in parts.path.split("/") if part]
            query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
            if "youtu.be" in host and path_parts:
                return path_parts[0]
            if "youtube.com" in host:
                if query.get("v"):
                    return str(query.get("v") or "")
                for marker in ("shorts", "live", "embed"):
                    if marker in path_parts:
                        index = path_parts.index(marker)
                        if index + 1 < len(path_parts):
                            return path_parts[index + 1]
        except Exception:
            logger.debug("Could not parse YouTube video id.", exc_info=True)
        return ""

    def _format_source_detail_number(self, value: object) -> str:
        """Format integer-like metadata values for source details."""
        try:
            if value in (None, ""):
                return ""
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return str(value or "").strip()

    def _format_youtube_source_detail_date(self, value: object) -> str:
        """Format yt-dlp YYYYMMDD dates without inventing missing dates."""
        text = str(value or "").strip()
        if re.fullmatch(r"\d{8}", text):
            return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
        return text

    def _youtube_source_detail_metadata(self, row: SourceResourceRowState) -> dict[str, str]:
        """Return cached YouTube metadata for the row, if discovery has loaded it."""
        cache = getattr(self, "youtube_source_row_discovery_metadata", {}) or {}
        metadata = cache.get(row.row_id, {}) if isinstance(cache, dict) else {}
        if isinstance(metadata, dict) and metadata:
            return {str(key): str(value) for key, value in metadata.items() if value not in (None, "")}

        info = getattr(self, "last_youtube_video_info", None) or {}
        if not isinstance(info, dict):
            return {}
        row_video_id = self._youtube_video_id_from_url(row.canonical_url)
        info_url = str(info.get("url") or "")
        info_video_id = str(info.get("video_id") or "") or self._youtube_video_id_from_url(info_url)
        if row_video_id and info_video_id and row_video_id == info_video_id:
            return {
                "title": str(info.get("title") or ""),
                "channel": str(info.get("channel_title") or info.get("channel") or ""),
                "upload_date": str(info.get("published_at") or info.get("upload_date") or ""),
                "view_count": str(info.get("view_count_text") or info.get("view_count") or ""),
                "webpage_url": info_url,
            }
        return {}

    def _source_row_details_fields(self, row: SourceResourceRowState) -> tuple[tuple[str, str], ...]:
        """Return copyable source-detail fields without requiring a blocking messagebox."""
        metadata = self._youtube_source_detail_metadata(row) if self._source_row_is_youtube(row) else {}
        title = (
            metadata.get("title")
            or row.title
            or row.display_title
            or row.display_label
        )
        fields: list[tuple[str, str]] = [("Title", title)]
        if self._source_row_is_youtube(row):
            channel = metadata.get("channel") or metadata.get("uploader") or ""
            published = self._format_youtube_source_detail_date(
                metadata.get("upload_date") or metadata.get("published_at") or ""
            )
            views = self._format_source_detail_number(
                metadata.get("view_count") or metadata.get("views") or ""
            )
            fields.extend([
                ("Channel", channel or "Not loaded"),
                ("Date", published or "Not loaded"),
                ("Views", views or "Not loaded"),
            ])
        else:
            fields.append(("Source", row.domain or row.adapter_display_name))
        fields.append(("URL", row.canonical_url))
        if row.warnings:
            fields.append(("Notes", "\n".join(f"- {warning}" for warning in row.warnings)))
        return tuple(fields)

    def _source_row_details_text(self, row: SourceResourceRowState) -> str:
        """Format source details for display/copy without a blocking messagebox."""
        return "\n".join(f"{label}: {value}" for label, value in self._source_row_details_fields(row))

    def _load_source_row_details_metadata_async(
        self,
        row_id: str,
        details_box: ctk.CTkTextbox,
        status_label: ctk.CTkLabel,
    ) -> None:
        """Load YouTube row metadata for Source details without freezing or beeping."""
        row = self._source_row_by_id(row_id)
        if row is None or not self._source_row_is_youtube(row):
            return
        if self._youtube_source_detail_metadata(row):
            return
        try:
            status_label.configure(text="Loading metadata…")
        except Exception:
            pass

        def worker() -> None:
            try:
                discovery = discover_youtube_media_with_ytdlp(row.canonical_url)
                metadata = {
                    "title": discovery.title,
                    "channel": discovery.channel or discovery.uploader,
                    "upload_date": discovery.upload_date,
                    "view_count": discovery.view_count,
                    "webpage_url": discovery.webpage_url,
                    "video_id": self._youtube_video_id_from_url(discovery.webpage_url or row.canonical_url),
                }
                title = youtube_title_from_discovery(discovery, row.title)
                qualities = youtube_available_quality_labels_from_discovery(
                    discovery,
                    fallback=normalized_youtube_quality_labels(
                        self._youtube_preferences_for_row(row.row_id)
                    ),
                )
            except Exception as error:
                error_text = str(error)
                try:
                    metadata = self._youtube_oembed_metadata_probe(row.canonical_url)
                    title = metadata.get("title") or row.title
                    qualities = tuple(self._youtube_quality_values_for_row(row.row_id)) or tuple(
                        normalized_youtube_quality_labels(self._youtube_preferences_for_row(row.row_id))
                    )
                    status = "title_only"
                except Exception:
                    def failed() -> None:
                        try:
                            status_label.configure(text=f"Metadata not loaded: {error_text}")
                        except Exception:
                            pass
                    try:
                        self.after(0, failed)
                    except Exception:
                        pass
                    return
            else:
                status = "ready"

            def apply() -> None:
                try:
                    self._apply_youtube_source_row_discovery(
                        row.row_id,
                        title,
                        qualities,
                        status=status,
                        metadata=metadata,
                    )
                    updated = self._source_row_by_id(row.row_id) or row
                    details_text = self._source_row_details_text(updated)
                    details_box.configure(state="normal")
                    details_box.delete("1.0", "end")
                    details_box.insert("1.0", details_text)
                    details_box.configure(state="disabled")
                    details_box._source_details_text = details_text
                    status_label.configure(
                        text="Metadata loaded" if status == "ready" else "Basic metadata loaded; date/views need yt-dlp"
                    )
                except Exception:
                    logger.debug("Could not update Source details metadata window.", exc_info=True)
            try:
                self.after(0, apply)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _show_source_row_details(self, row_id: str) -> None:
        row = self._source_row_by_id(row_id)
        if row is None:
            return
        window = ctk.CTkToplevel(self)
        window.title("Source details")
        window.geometry("560x330")
        window.transient(self)
        window.configure(fg_color=COLORS["bg_dark"])
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            window,
            text="Source details",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))

        details_text = self._source_row_details_text(row)
        details_box = ctk.CTkTextbox(
            window,
            height=168,
            fg_color=COLORS["bg_input"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            wrap="word",
        )
        details_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 6))
        details_box.insert("1.0", details_text)
        details_box.configure(state="disabled")
        details_box._source_details_text = details_text

        status_label = ctk.CTkLabel(
            window,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
        )
        status_label.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 8))

        def copy_details() -> None:
            try:
                self.clipboard_clear()
                self.clipboard_append(getattr(details_box, "_source_details_text", details_text))
                self.log_message("Source details copied to clipboard.", "success")
            except Exception:
                logger.debug("Could not copy source details.", exc_info=True)

        button_row = ctk.CTkFrame(window, fg_color="transparent")
        button_row.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))
        button_row.grid_columnconfigure(3, weight=1)
        ctk.CTkButton(button_row, text="Copy URL", width=90, command=lambda: self._copy_text_to_clipboard(row.canonical_url, "Source URL copied.")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(button_row, text="Copy details", width=110, command=copy_details).grid(row=0, column=1, sticky="w", padx=(8, 0))
        if self._source_row_is_youtube(row):
            ctk.CTkButton(
                button_row,
                text="Load metadata",
                width=120,
                command=lambda: self._load_source_row_details_metadata_async(row.row_id, details_box, status_label),
            ).grid(row=0, column=2, sticky="w", padx=(8, 0))
        ctk.CTkButton(button_row, text="Close", width=90, command=window.destroy).grid(row=0, column=4, sticky="e")

        if self._source_row_is_youtube(row) and not self._youtube_source_detail_metadata(row):
            self._load_source_row_details_metadata_async(row.row_id, details_box, status_label)


    def _local_web_archive_status_lines(self, archive_status: Any) -> tuple[str, ...]:
        state = build_local_web_archive_action_state(
            wacz_path=getattr(archive_status, "wacz_path", "") or None,
            manifest_path=getattr(archive_status, "manifest_path", "") or None,
            expected_source_url=getattr(archive_status, "source_url", "") or "",
            expected_wacz_sha256=getattr(archive_status, "wacz_sha256", "") or "",
            expected_manifest_sha256=getattr(archive_status, "manifest_sha256", "") or "",
            expected_comment_count=int(getattr(archive_status, "expected_comment_count", 0) or 0),
        )
        return local_web_archive_status_lines(state)

    def _open_local_web_archive_settings(self, row_id: str, archive_status: Any) -> None:
        row = self._source_row_by_id(row_id)
        prefs_by_row = self.__dict__.setdefault("local_web_archive_source_preferences", {})
        prefs = prefs_by_row.setdefault(row_id, {"static": True, "dynamic": True})

        window = ctk.CTkToplevel(self)
        window.title("Local archive settings")
        window.geometry("420x250")
        window.transient(self)
        window.grab_set()
        window.configure(fg_color=COLORS["bg_dark"])

        ctk.CTkLabel(
            window,
            text="Local archive settings",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"],
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(16, 8))

        static_var = ctk.BooleanVar(value=bool(prefs.get("static", True)))
        dynamic_var = ctk.BooleanVar(value=bool(prefs.get("dynamic", True)))
        ctk.CTkCheckBox(
            window,
            text="Static local snapshot",
            variable=static_var,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=20, pady=6)
        ctk.CTkCheckBox(
            window,
            text="Dynamic browser replay / WARC",
            variable=dynamic_var,
            text_color=COLORS["text_primary"],
        ).pack(anchor="w", padx=20, pady=6)

        def save_settings() -> None:
            prefs_by_row[row_id] = {"static": bool(static_var.get()), "dynamic": bool(dynamic_var.get())}
            if hasattr(self, "url_status"):
                self.url_status.configure(text="Local archive settings saved.", text_color=COLORS["text_secondary"])
            window.destroy()

        buttons = ctk.CTkFrame(window, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(16, 12))
        ctk.CTkButton(buttons, text="Cancel", width=90, command=window.destroy).pack(side="right")
        ctk.CTkButton(buttons, text="Save", width=90, command=save_settings).pack(side="right", padx=(0, 8))
        ctk.CTkButton(
            buttons,
            text="Status",
            width=90,
            command=lambda status=archive_status: self._show_archive_status(status),
        ).pack(side="left")

    def _show_archive_status(self, archive_status: Any) -> None:
        if archive_status.service_id == ARCHIVE_SERVICE_LOCAL_WEB_ARCHIVE:
            details = list(self._local_web_archive_status_lines(archive_status))
            messagebox.showinfo("Local Web Archive", "\n".join(details))
            return
        status_text = self._archive_status_label_text(archive_status)
        details = [
            f"{archive_status.service_id}: {status_text}",
            "Archive checks performed: none",
            "Archive submissions performed: none",
        ]
        messagebox.showinfo("Archive status", "\n".join(details))


    def _webpage_image_session_download_root(self) -> Path:
        root = getattr(self, "webpage_image_session_output_root", None)
        if root is None:
            root = (
                Path(tempfile.gettempdir())
                / "ytce_webpage_image_downloads"
                / f"session_{os.getpid()}_{id(self):x}"
            )
            self.webpage_image_session_output_root = root
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _cleanup_webpage_image_session_downloads(self, *, reset_state: bool = False) -> None:
        root = getattr(self, "webpage_image_session_output_root", None)
        if not root:
            if reset_state:
                self.webpage_image_session_download_cache = {}
            return
        try:
            root_path = Path(root)
            temp_root = Path(tempfile.gettempdir()).resolve()
            # Safety guard: only remove the app-managed temp subtree.
            if root_path.resolve().is_relative_to(temp_root / "ytce_webpage_image_downloads"):
                shutil.rmtree(root_path, ignore_errors=True)
        except Exception:
            logger.debug("Could not clean temporary webpage image downloads.", exc_info=True)
        finally:
            if reset_state:
                self.webpage_image_session_output_root = None
                self.webpage_image_session_download_cache = {}

    def _remember_webpage_image_session_downloads(
        self,
        *,
        row: SourceResourceRowState,
        selected_resource_ids: tuple[str, ...],
        downloaded_files: tuple[str, ...],
        manifest_json: str = "",
    ) -> None:
        cache = getattr(self, "webpage_image_session_download_cache", None)
        if cache is None:
            cache = {}
            self.webpage_image_session_download_cache = cache

        remembered = False
        if manifest_json and os.path.isfile(manifest_json):
            try:
                payload = json.loads(Path(manifest_json).read_text(encoding="utf-8"))
                for record in payload.get("records", []) or []:
                    source_resource = record.get("source_resource", {}) or {}
                    resource_id = str(source_resource.get("resource_id") or "")
                    local_path = str(record.get("local_file_path") or "")
                    if resource_id and local_path and os.path.isfile(local_path):
                        cache[(row.row_id, resource_id)] = local_path
                        remembered = True
            except Exception:
                logger.debug("Could not read webpage image download manifest for cache.", exc_info=True)

        if not remembered:
            for resource_id, local_path in zip(selected_resource_ids, downloaded_files):
                if local_path and os.path.isfile(local_path):
                    cache[(row.row_id, resource_id)] = local_path

    def _cached_webpage_image_session_paths(
        self,
        *,
        row: SourceResourceRowState,
        selected_resource_ids: tuple[str, ...],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        cache = getattr(self, "webpage_image_session_download_cache", {}) or {}
        cached_paths: list[str] = []
        missing_ids: list[str] = []
        for resource_id in selected_resource_ids:
            cached_path = cache.get((row.row_id, resource_id))
            if cached_path and os.path.isfile(cached_path):
                cached_paths.append(cached_path)
            else:
                missing_ids.append(resource_id)
        return tuple(cached_paths), tuple(missing_ids)

    def _open_source_resource_window(self, row_id: str, resource_kind: str) -> None:
        row = self._source_row_by_id(row_id)
        if row is None:
            return
        state = resource_dialog_state_for_row(row, resource_kind)
        window = ctk.CTkToplevel(self)
        window.title("Images" if resource_kind == RESOURCE_KIND_IMAGE else "Video & Audio")
        window.geometry("880x720")
        try:
            window.minsize(820, 640)
        except Exception:
            pass
        window.transient(self)
        window.grab_set()

        header = ctk.CTkLabel(
            window,
            text=f"{row.title}\n{row.domain}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"],
            justify="left",
        )
        header.pack(anchor="w", padx=16, pady=(14, 8))
        selected_ids: set[str] = set(state.selected_resource_ids)
        vars_by_id: dict[str, Any] = {}
        thumbnail_images_by_id: dict[str, ctk.CTkImage] = {}
        thumbnail_hidden_resource_ids: set[str] = set()
        thumbnail_preview_status_by_id: dict[str, str] = {}
        thumbnail_probe_thread_active = False
        thumbnail_probe_render_after_id: Any = None
        thumbnail_probe_result_after_id: Any = None
        thumbnail_probe_results: list[tuple[str, str, Any]] = []
        thumbnail_probe_results_lock = threading.Lock()
        thumbnail_preview_url_by_id: dict[str, str] = {}
        webpage_image_preview_pil_cache_by_url: dict[str, Any] = self.__dict__.setdefault(
            "webpage_image_preview_pil_cache_by_url",
            {},
        )
        webpage_video_frame_preview_pil_cache_by_url: dict[str, Any] = self.__dict__.setdefault(
            "webpage_video_frame_preview_pil_cache_by_url",
            {},
        )
        webpage_video_hover_preview_pil_frames_by_url: dict[str, Any] = self.__dict__.setdefault(
            "webpage_video_hover_preview_pil_frames_by_url",
            {},
        )
        webpage_image_preview_cache_limit = 256
        webpage_video_frame_preview_cache_limit = 96
        webpage_video_hover_preview_cache_limit = 48
        image_discovery_thread_active = False
        image_discovery_result_after_id: Any = None
        image_discovery_results: list[tuple[str, Any, str, bool]] = []
        image_discovery_results_lock = threading.Lock()
        video_discovery_thread_active = False
        video_discovery_result_after_id: Any = None
        video_discovery_results: list[tuple[str, Any, str, bool]] = []
        video_discovery_results_lock = threading.Lock()
        hidden_candidate_count = 0
        thumbnail_preview_loading_count = 0
        default_image_render_limit = 32
        hidden_image_render_limit = 24
        webpage_image_discovery_cache_by_url: dict[str, Any] = self.__dict__.setdefault(
            "webpage_image_discovery_cache_by_url",
            {},
        )
        webpage_image_discovery_cache_limit = 24
        webpage_video_discovery_cache_by_url: dict[str, Any] = self.__dict__.setdefault(
            "webpage_video_discovery_cache_by_url",
            {},
        )
        webpage_video_discovery_cache_limit = 24

        def _webpage_image_discovery_cache_key(source_row: Any) -> str:
            return str(getattr(source_row, "canonical_url", "") or getattr(source_row, "raw_url", "") or "").strip()

        def _webpage_video_discovery_cache_key(source_row: Any) -> str:
            return str(getattr(source_row, "canonical_url", "") or getattr(source_row, "raw_url", "") or "").strip()

        def _prewarm_rendered_discovery_if_js_heavy() -> None:
            if resource_kind not in {RESOURCE_KIND_IMAGE, RESOURCE_KIND_VIDEO_AUDIO} or row.adapter_id in {"youtube", "twitter_x"}:
                return
            url_text = " ".join(str(part or "").lower() for part in (row.raw_url, row.canonical_url, row.domain))
            if not any(marker in url_text for marker in ("msn.com", "x.com", "twitter.com", "facebook.com", "instagram.com")):
                return
            threading.Thread(target=prewarm_rendered_browser_discovery_worker, daemon=True).start()

        _prewarm_rendered_discovery_if_js_heavy()

        filter_frame = ctk.CTkFrame(window, fg_color=COLORS["bg_input"], corner_radius=7)
        filter_frame.pack(fill="x", padx=16, pady=(0, 8))
        filter_frame.grid_columnconfigure((0, 1), weight=1)
        url_filter_var = ctk.StringVar(value="")
        text_filter_var = ctk.StringVar(value="")
        min_width_var = ctk.StringVar(value="")
        min_height_var = ctk.StringVar(value="")

        def add_filter_label(text: str, row_index: int, column_index: int, padx: tuple[int, int]) -> None:
            ctk.CTkLabel(
                filter_frame,
                text=text,
                text_color=COLORS["text_muted"],
                font=ctk.CTkFont(size=10, weight="bold"),
                anchor="w",
            ).grid(row=row_index, column=column_index, sticky="ew", padx=padx, pady=(6 if row_index == 0 else 2, 0))

        add_filter_label("URL filter", 0, 0, (8, 4))
        add_filter_label("Type/name filter", 0, 1, (4, 8))
        url_filter_entry = ctk.CTkEntry(
            filter_frame,
            textvariable=url_filter_var,
            placeholder_text="Filter by URL",
            height=30,
            font=ctk.CTkFont(size=11),
        )
        url_filter_entry.grid(row=1, column=0, sticky="ew", padx=(8, 4), pady=(2, 5))
        text_filter_entry = ctk.CTkEntry(
            filter_frame,
            textvariable=text_filter_var,
            placeholder_text="Filter by type or name",
            height=30,
            font=ctk.CTkFont(size=11),
        )
        text_filter_entry.grid(row=1, column=1, sticky="ew", padx=(4, 8), pady=(2, 5))
        add_filter_label("Min width", 2, 0, (8, 4))
        add_filter_label("Min height", 2, 1, (4, 8))
        min_width_entry = ctk.CTkEntry(
            filter_frame,
            textvariable=min_width_var,
            placeholder_text="0 px",
            height=28,
            font=ctk.CTkFont(size=11),
        )
        min_width_entry.grid(row=3, column=0, sticky="ew", padx=(8, 4), pady=(2, 6))
        min_height_entry = ctk.CTkEntry(
            filter_frame,
            textvariable=min_height_var,
            placeholder_text="0 px",
            height=28,
            font=ctk.CTkFont(size=11),
        )
        min_height_entry.grid(row=3, column=1, sticky="ew", padx=(4, 8), pady=(2, 6))
        only_links_var = ctk.BooleanVar(value=False)
        save_subfolder_var = ctk.BooleanVar(value=True)
        rename_files_var = ctk.BooleanVar(value=False)
        show_hidden_images_var = ctk.BooleanVar(value=False)
        option_row = ctk.CTkFrame(filter_frame, fg_color="transparent")
        option_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkCheckBox(
            option_row,
            text="Only images from links" if resource_kind == RESOURCE_KIND_IMAGE else "Only media from links",
            variable=only_links_var,
            command=lambda: (render_resource_list(), refresh_count()),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_primary"],
            width=20,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(
            option_row,
            text="Save to subfolder",
            variable=save_subfolder_var,
            command=lambda: (render_resource_list(), refresh_count()),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_primary"],
            width=20,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkCheckBox(
            option_row,
            text="Rename files",
            variable=rename_files_var,
            command=lambda: (render_resource_list(), refresh_count()),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_primary"],
            width=20,
        ).pack(side="left", padx=(0, 10))
        if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"}:
            ctk.CTkCheckBox(
                option_row,
                text="Show hidden",
                variable=show_hidden_images_var,
                command=lambda: (render_resource_list(), refresh_count()),
                font=ctk.CTkFont(size=11),
                text_color=COLORS["text_primary"],
                width=20,
            ).pack(side="left")

        list_frame = ctk.CTkScrollableFrame(window, fg_color=COLORS["bg_input"])
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        active_state = state
        refresh_images_button: Any = None
        refresh_videos_button: Any = None
        rendered_tile_resource_ids: tuple[str, ...] = ()
        rendered_tile_variant_signature: tuple[tuple[str, int, str, str], ...] = ()
        rendered_tile_refreshers_by_id: dict[str, Any] = {}
        video_hover_preview_frames_by_id: dict[str, tuple[Any, ...]] = {}
        video_hover_preview_status_by_id: dict[str, str] = {}
        video_hover_probe_thread_active = False
        # V78N fast first-paint: when Video & Audio opens before the
        # source-row rendered/browser prefetch has finished, show static HTML
        # candidates first, then enrich/replace them with the slower rendered
        # browser probe.  This avoids a blank 12s+ dialog while preserving the
        # full static+rendered evidence pass.
        video_static_first_followup_pending = False
        video_fast_rendered_probe_started = False
        video_fast_rendered_probe_active = False
        video_dialog_started_at = time.perf_counter()
        video_first_paint_logged = False
        video_discovery_cache_poll_after_id: Any = None
        video_live_preview_mode_enabled = bool(getattr(self, "webpage_video_live_preview_enabled", True))
        # V78Q duplicate rendition grouping: direct MP4/WebM quality variants
        # of the same article clip should render as one card.  The grouped card
        # defaults to the best quality while the quality button can choose a
        # different selected quality variant for LIVE playback and Review selected.
        video_variant_group_members_by_rep_id: dict[str, tuple[Any, ...]] = {}
        video_variant_selected_id_by_rep_id: dict[str, str] = {}
        video_variant_rep_id_by_resource_id: dict[str, str] = {}
        video_grouped_variant_hidden_count = 0
        video_hover_animation_after_id_by_resource_id: dict[str, Any] = {}
        video_hover_animation_index_by_resource_id: dict[str, int] = {}
        # V79J: keep the animation clock separate from the currently
        # cached frame list.  When a fast seed is replaced by the full
        # loop, playback must stay based on elapsed hover time instead of
        # restarting a new long loop from whatever seed index happened to
        # be current.
        video_hover_animation_started_at_by_resource_id: dict[str, float] = {}
        # V79A: hover in live-preview mode uses an internal tile playback cache
        # decoded from the selected direct MP4/WebM URL.  It must never reuse the
        # visible manual LIVE browser/player route.
        video_live_hover_after_id_by_resource_id: dict[str, Any] = {}
        video_live_hover_opened_resource_ids: set[str] = set()
        video_hover_warm_after_id_by_url: dict[str, Any] = {}
        video_hover_warmed_urls: set[str] = set()
        # V79E: while a tile preview is actively playing, later discovery merges
        # must not destroy/rebuild the grid and interrupt the hover.  Defer any
        # disruptive repaint until the pointer leaves the active preview surface.
        video_hover_active_resource_ids: set[str] = set()
        video_hover_stop_after_id_by_resource_id: dict[str, Any] = {}
        # V79I: do not rely only on Tk <Enter>/<Leave> bookkeeping to decide
        # whether a hover tile is protected.  Discovery merges can arrive exactly
        # as the pointer crosses child widgets, so keep concrete preview-surface
        # widgets and check the pointer geometry before any repaint/rebuild.
        video_hover_surface_widgets_by_resource_id: dict[str, tuple[Any, ...]] = {}
        video_hover_repaint_deferred = False
        video_hover_repaint_after_id: Any = None

        def parse_positive_int(value: str) -> int:
            try:
                return max(0, int(str(value or "").strip()))
            except ValueError:
                return 0

        def current_filters() -> MediaResourceFilterState:
            return MediaResourceFilterState(
                url_filter=url_filter_entry.get(),
                text_filter=text_filter_entry.get(),
                min_width=parse_positive_int(min_width_entry.get()),
                min_height=parse_positive_int(min_height_entry.get()),
                only_linked_resources=bool(only_links_var.get()),
                save_to_subfolder=bool(save_subfolder_var.get()),
                rename_files=bool(rename_files_var.get()),
            )

        def _preview_url_for_item(item: Any) -> str:
            if resource_kind == RESOURCE_KIND_VIDEO_AUDIO:
                # Video/audio tiles must not try to treat MP4/HLS/DASH URLs as
                # still-image previews.  Only explicit thumbnails/posters are
                # safe to probe as images.  Direct video files without a poster
                # are handled separately through the ffmpeg first-frame preview
                # cache below.
                return str(item.thumbnail_reference or "")
            return str(item.thumbnail_reference or item.reference_url or item.canonical_url or "")

        def _video_frame_preview_url_for_item(item: Any) -> str:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return ""
            media_url = str(getattr(item, "reference_url", "") or getattr(item, "canonical_url", "") or "").strip()
            if not media_url:
                return ""
            if can_generate_video_frame_preview(
                media_url,
                extension=str(getattr(item, "extension", "") or ""),
                mime_type=str(getattr(item, "mime_type", "") or ""),
            ):
                return media_url
            return ""

        def _video_hover_preview_url_for_item(item: Any) -> str:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return ""
            # V79B: callers pass the visible representative tile. Resolve the
            # currently selected quality variant here, but keep cache/display
            # state keyed by the visible tile id so frames never appear on an
            # adjacent/non-hovered card.
            item = _video_variant_selected_item_for_rep(item)
            media_url = str(getattr(item, "reference_url", "") or getattr(item, "canonical_url", "") or "").strip()
            if not media_url:
                return ""
            if can_stream_video_tile_hover(
                media_url,
                extension=str(getattr(item, "extension", "") or ""),
                mime_type=str(getattr(item, "mime_type", "") or ""),
            ) or can_generate_video_hover_preview(
                media_url,
                extension=str(getattr(item, "extension", "") or ""),
                mime_type=str(getattr(item, "mime_type", "") or ""),
            ):
                return media_url
            return ""

        def _video_hover_fast_seek_seconds() -> float:
            # V79J: Metro-style clips can begin with a static/composite lead-in.
            # Show a first moving preview as quickly as possible, and never make
            # the wrap visibly return to that lead-in pause.
            return 0.55

        def _video_hover_seed_duration_seconds() -> float:
            return 0.25

        def _video_hover_loop_duration_seconds() -> float:
            # V79M: keep the V79L playback architecture, but restore the
            # long-loop length to the measured Video DownloadHelper-style
            # ~5.15s window.  The loop is still modulo/deadline based, so the
            # wrap itself remains immediate; only the amount of useful preview
            # shown before wrapping is increased.
            return 5.15

        def _video_hover_target_fps() -> int:
            return 30

        def _video_hover_cache_key_for_url(
            hover_url: str,
            *,
            duration_seconds: float,
            fps: int,
            seek_seconds: float,
        ) -> str:
            return (
                f"{video_tile_hover_stream_cache_key(hover_url)}"
                f":v79j:seek={max(0.0, float(seek_seconds or 0.0)):.2f}"
                f":dur={max(0.1, float(duration_seconds or 0.1)):.2f}"
                f":fps={max(1, int(fps or 1))}"
            )

        def _video_hover_cache_lookup_keys_for_url(hover_url: str) -> tuple[str, ...]:
            # Prefer the full trimmed loop, then the very small seed.  Keep the
            # older URL-only keys as read-only fallbacks so an already warm
            # session can still start instantly after this patch.
            return (
                _video_hover_cache_key_for_url(
                    hover_url,
                    duration_seconds=_video_hover_loop_duration_seconds(),
                    fps=_video_hover_target_fps(),
                    seek_seconds=_video_hover_fast_seek_seconds(),
                ),
                _video_hover_cache_key_for_url(
                    hover_url,
                    duration_seconds=_video_hover_seed_duration_seconds(),
                    fps=_video_hover_target_fps(),
                    seek_seconds=_video_hover_fast_seek_seconds(),
                ),
                video_tile_hover_stream_cache_key(hover_url),
                video_hover_preview_cache_key(hover_url),
            )

        def _video_live_preview_url_for_item(item: Any) -> str:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO or not video_live_preview_mode_enabled:
                return ""
            media_url = str(getattr(item, "reference_url", "") or getattr(item, "canonical_url", "") or "").strip()
            if not media_url:
                return ""
            if can_open_browser_video_live_preview(
                media_url,
                extension=str(getattr(item, "extension", "") or ""),
                mime_type=str(getattr(item, "mime_type", "") or ""),
            ):
                return media_url
            return ""

        def _video_variant_selected_item_for_rep(item: Any) -> Any:
            variants = video_variant_group_members_by_rep_id.get(str(getattr(item, "resource_id", "") or ""), ())
            if not variants:
                return item
            selected_id = video_variant_selected_id_by_rep_id.get(
                str(getattr(item, "resource_id", "") or ""),
                str(getattr(variants[0], "resource_id", "") or ""),
            )
            for variant in variants:
                if str(getattr(variant, "resource_id", "") or "") == selected_id:
                    return variant
            return variants[0]

        def _video_variant_button_text_for_rep(item: Any) -> str:
            return _video_variant_selected_label_for_rep(item)

        def _video_variant_option_pairs_for_rep(item: Any) -> tuple[tuple[str, Any], ...]:
            variants = video_variant_group_members_by_rep_id.get(str(getattr(item, "resource_id", "") or ""), ())
            labels = video_variant_quality_option_labels(variants)
            return tuple((label, variant) for label, variant in zip(labels, variants))

        def _video_variant_selected_label_for_rep(item: Any) -> str:
            selected_variant = _video_variant_selected_item_for_rep(item)
            selected_id = str(getattr(selected_variant, "resource_id", "") or "")
            for label_text, variant in _video_variant_option_pairs_for_rep(item):
                if str(getattr(variant, "resource_id", "") or "") == selected_id:
                    return label_text
            return video_variant_quality_label(selected_variant)

        def _group_video_rendition_display_resources(resources: tuple[Any, ...]) -> tuple[Any, ...]:
            nonlocal video_grouped_variant_hidden_count
            video_variant_group_members_by_rep_id.clear()
            video_variant_rep_id_by_resource_id.clear()
            video_grouped_variant_hidden_count = 0
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO or not video_live_preview_mode_enabled:
                return resources
            display_resources, groups_by_rep_id, rep_id_by_variant_id = group_video_rendition_items(
                resources,
                media_url_getter=_video_live_preview_url_for_item,
            )
            for rep_id, variants in groups_by_rep_id.items():
                video_variant_group_members_by_rep_id[rep_id] = variants
                previous_selected = video_variant_selected_id_by_rep_id.get(rep_id)
                valid_variant_ids = {str(getattr(variant, "resource_id", "") or "") for variant in variants}
                if previous_selected not in valid_variant_ids:
                    video_variant_selected_id_by_rep_id[rep_id] = str(getattr(variants[0], "resource_id", "") or "")
            video_variant_rep_id_by_resource_id.update(rep_id_by_variant_id)
            video_grouped_variant_hidden_count = max(
                0,
                sum(max(0, len(variants) - 1) for variants in groups_by_rep_id.values()),
            )
            return display_resources

        def _video_variant_signature_for_resources(resources: tuple[Any, ...]) -> tuple[tuple[str, int, str, str], ...]:
            """Detect when the visible ids are unchanged but quality variants appeared.

            V78Q could first paint a single direct MP4 candidate, then the shared
            rendered/source-row prefetch cache could add a second same-content
            rendition under the same representative id.  If the visible ids did
            not change, the tile refresh fast-path reused the old card and never
            rebuilt the quality selector.
            """
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO or not video_live_preview_mode_enabled:
                return ()
            signature: list[tuple[str, int, str, str]] = []
            for visible_item in resources:
                rep_id = str(getattr(visible_item, "resource_id", "") or "")
                variants = video_variant_group_members_by_rep_id.get(rep_id, ())
                if not variants:
                    signature.append((rep_id, 1, rep_id, ""))
                    continue
                selected_id = video_variant_selected_id_by_rep_id.get(
                    rep_id,
                    str(getattr(variants[0], "resource_id", "") or ""),
                )
                labels = ",".join(video_variant_quality_option_labels(variants))
                signature.append((rep_id, len(variants), selected_id, labels))
            return tuple(signature)

        def _select_video_variant_for_rep(item: Any, selected_label: str, selector_var: Any = None) -> None:
            rep_id = str(getattr(item, "resource_id", "") or "")
            variants = video_variant_group_members_by_rep_id.get(rep_id, ())
            if len(variants) < 2:
                return
            option_pairs = _video_variant_option_pairs_for_rep(item)
            selected_variant = None
            selected_option_label = str(selected_label or "")
            for label_text, variant in option_pairs:
                if label_text == selected_option_label:
                    selected_variant = variant
                    break
            if selected_variant is None:
                selected_variant = variants[0]
                selected_option_label = option_pairs[0][0] if option_pairs else video_variant_quality_label(selected_variant)
            selected_resource_id = str(getattr(selected_variant, "resource_id", "") or "")
            if not selected_resource_id:
                return
            video_variant_selected_id_by_rep_id[rep_id] = selected_resource_id
            try:
                if selector_var is not None:
                    selector_var.set(selected_option_label)
            except Exception:
                pass
            selected_variant = _video_variant_selected_item_for_rep(item)
            try:
                if selector_var is not None:
                    selector_var.set(_video_variant_selected_label_for_rep(item))
            except Exception:
                pass
            try:
                # V79B: the visible representative tile owns the in-tile hover
                # surface.  A quality change must invalidate its display frames
                # so the next warm/hover uses the newly selected URL.
                video_hover_preview_frames_by_id.pop(rep_id, None)
                video_hover_preview_status_by_id.pop(rep_id, None)
                after_id = video_hover_animation_after_id_by_resource_id.pop(rep_id, None)
                video_hover_animation_started_at_by_resource_id.pop(rep_id, None)
                if after_id is not None:
                    try:
                        window.after_cancel(after_id)
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                suffix = video_variant_url_suffix(selected_variant)
                suffix_text = f"; url suffix={suffix}" if suffix else ""
                self.log_message(
                    f"Selected video quality variant: {_video_variant_selected_label_for_rep(item)}{suffix_text}; LIVE and Review selected will use this variant.",
                    "muted",
                )
            except Exception:
                pass
            try:
                _schedule_selected_video_hover_warm(item, delay_ms=1)
            except Exception:
                pass
            try:
                # V78T: changing quality must visibly update the card, not only
                # the small selector label. Rebuild so the thumbnail, size badge,
                # detail hover, and LIVE command all resolve through the selected
                # variant immediately.
                render_resource_list()
            except Exception:
                pass
            refresh_count()

        def _open_live_video_preview_for_item(item: Any) -> None:
            item = _video_variant_selected_item_for_rep(item)
            preview_url = _video_live_preview_url_for_item(item)
            if not preview_url:
                show_image_dialog_notice(
                    "Live preview unavailable",
                    "Live browser preview is currently limited to direct MP4/WebM-style video candidates. HLS, DASH, embedded players, and audio-only items still use the existing poster/review route.",
                )
                return
            page_url = str(getattr(row, "canonical_url", "") or getattr(row, "raw_url", "") or "")
            quality_label = video_variant_quality_label(item)
            title = str(getattr(item, "display_name", "") or getattr(item, "title", "") or "Video live preview")
            if quality_label and quality_label != "quality unknown":
                title = f"{title} [{quality_label}]"
            poster_url = str(getattr(item, "thumbnail_reference", "") or "")
            try:
                preview_file = open_browser_video_live_preview(
                    preview_url,
                    title=title,
                    referer=page_url,
                    poster_url=poster_url,
                    prefer_playwright=True,
                )
                try:
                    self.log_message(
                        f"Opened live browser video preview for {label}; quality={quality_label}; url={preview_url}; file={preview_file.name}",
                        "success",
                    )
                except Exception:
                    pass
            except Exception as error:
                show_image_dialog_notice("Live preview failed", f"Could not open live browser preview:\n\n{error}")

        def _media_placeholder_text_for_item(item: Any) -> str:
            if resource_kind == RESOURCE_KIND_IMAGE:
                return "IMG"
            extension = str(getattr(item, "extension", "") or "").lower()
            media_type = str(getattr(item, "media_type", "") or "").lower()
            mime_type = str(getattr(item, "mime_type", "") or "").lower()
            provenance = str(getattr(item, "provenance", "") or "").lower()
            video_exts = {".mp4", ".m4v", ".webm", ".mov", ".mkv", ".avi", ".flv", ".ts", ".m2ts", ".3gp", ".m3u8", ".mpd", ".f4m"}
            audio_exts = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".flac"}
            if extension in audio_exts or media_type == "audio" or mime_type.startswith("audio/"):
                return "AUD"
            if extension in video_exts or media_type in {"video", "stream", "video_audio"} or mime_type.startswith("video/"):
                return "VID"
            if media_type == "embedded_player" or "embedded" in provenance:
                return "PLAY"
            return "MEDIA"

        def _media_placeholder_font_size(item: Any) -> int:
            text = _media_placeholder_text_for_item(item)
            if text == "MEDIA":
                return 52
            if text == "PLAY":
                return 58
            return 78

        def _image_candidate_is_obvious_non_preview(item: Any) -> bool:
            extension = str(getattr(item, "extension", "") or "").lower()
            url = str(getattr(item, "reference_url", "") or getattr(item, "canonical_url", "") or "").lower()
            name = str(getattr(item, "display_name", "") or "").lower()
            width = int(getattr(item, "width", 0) or 0)
            height = int(getattr(item, "height", 0) or 0)
            if extension in {".svg", ".ico"}:
                return True
            if width and height and min(width, height) < 40:
                return True
            hidden_markers = (
                "sprite",
                "button",
                "tracking",
                "pixel",
                "favicon",
                "wikimedia-button",
                "oojs_ui_icon",
                "oojs-ui-icon",
                "wikimediaui-",
            )
            return any(marker in url or marker in name for marker in hidden_markers)

        def _cache_ctk_thumbnail_for_item(item: Any, preview_image: Any) -> bool:
            try:
                ctk_image = ctk.CTkImage(
                    light_image=preview_image.copy(),
                    dark_image=preview_image.copy(),
                    size=(max(1, preview_image.width), max(1, preview_image.height)),
                )
                thumbnail_images_by_id[item.resource_id] = ctk_image
                thumbnail_hidden_resource_ids.discard(item.resource_id)
                thumbnail_preview_status_by_id[item.resource_id] = "success"
                return True
            except Exception:
                thumbnail_hidden_resource_ids.add(item.resource_id)
                thumbnail_preview_status_by_id[item.resource_id] = "failed"
                return False

        def _cache_ctk_video_hover_frames_for_item(resource_id: str, preview_frames: Any) -> bool:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return False
            try:
                ctk_frames = tuple(
                    ctk.CTkImage(
                        light_image=frame.copy(),
                        dark_image=frame.copy(),
                        size=(max(1, frame.width), max(1, frame.height)),
                    )
                    for frame in tuple(preview_frames or ())
                )
                if len(ctk_frames) < 2:
                    return False
                video_hover_preview_frames_by_id[resource_id] = ctk_frames
                return True
            except Exception:
                return False

        def _apply_cached_video_hover_preview(item: Any) -> bool:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return False
            hover_url = _video_hover_preview_url_for_item(item)
            if not hover_url:
                return False
            cached_hover_frames = None
            for candidate_cache_key in _video_hover_cache_lookup_keys_for_url(hover_url):
                cached_hover_frames = webpage_video_hover_preview_pil_frames_by_url.get(candidate_cache_key)
                if cached_hover_frames is not None:
                    break
            if cached_hover_frames is None:
                return False
            cached = _cache_ctk_video_hover_frames_for_item(item.resource_id, cached_hover_frames)
            if cached:
                video_hover_preview_status_by_id[item.resource_id] = "success"
            return cached

        def _extract_video_hover_preview_frames_cached(
            item: Any,
            hover_url: str,
            *,
            duration_seconds: float = 5.15,
            fps: int = 30,
            max_frames: int = 155,
            timeout: float = 10.5,
            first_frame_timeout: float = 1.25,
            seek_seconds: float = 0.0,
            force_refresh: bool = False,
        ) -> tuple[Any, ...]:
            # V79A: generate a real opening-segment tile playback cache from the
            # selected direct MP4/WebM URL.  This uses the bundled/available ffmpeg
            # raw-video stream path first so the hover frames are contiguous video,
            # not sparse browser screenshots or a visible LIVE browser window.
            seek_seconds = max(0.0, float(seek_seconds or 0.0))
            hover_cache_key = _video_hover_cache_key_for_url(
                hover_url,
                duration_seconds=duration_seconds,
                fps=fps,
                seek_seconds=seek_seconds,
            )
            hover_frames = None
            if not force_refresh:
                for candidate_cache_key in (hover_cache_key, *_video_hover_cache_lookup_keys_for_url(hover_url)):
                    hover_frames = webpage_video_hover_preview_pil_frames_by_url.get(candidate_cache_key)
                    if hover_frames is not None:
                        break
            if hover_frames is None:
                page_url = str(getattr(row, "canonical_url", "") or getattr(row, "raw_url", "") or "")
                try:
                    hover_frames = extract_video_tile_hover_stream_frames_pil(
                        hover_url,
                        timeout=timeout,
                        first_frame_timeout=first_frame_timeout,
                        duration_seconds=duration_seconds,
                        fps=fps,
                        seek_seconds=seek_seconds,
                        referer=page_url,
                        frame_size=(168, 96),
                        max_frames=max_frames,
                        project_root=Path(__file__).resolve().parent,
                    )
                except Exception as stream_error:
                    logger.debug("FFmpeg stream video tile hover preview failed for %s: %s", hover_url, stream_error)
                    try:
                        hover_frames = extract_video_hover_preview_frames_pil(
                            hover_url,
                            timeout=max(6.0, timeout),
                            seek_seconds=seek_seconds,
                            duration_seconds=duration_seconds,
                            fps=max(12, min(30, int(fps or 30))),
                            referer=page_url,
                            max_frames=max_frames,
                        )
                    except Exception as ffmpeg_error:
                        logger.debug("FFmpeg GIF video tile hover fallback failed for %s: %s", hover_url, ffmpeg_error)
                        hover_frames = extract_video_hover_preview_frames_pil_browser(
                            hover_url,
                            timeout=max(6.0, timeout),
                            duration_seconds=duration_seconds,
                            sample_count=max_frames,
                            frame_delay_ms=35,
                            referer=page_url,
                            poster_url=str(getattr(item, "thumbnail_reference", "") or ""),
                        )
                webpage_video_hover_preview_pil_frames_by_url[hover_cache_key] = tuple(frame.copy() for frame in hover_frames)
                while len(webpage_video_hover_preview_pil_frames_by_url) > webpage_video_hover_preview_cache_limit:
                    try:
                        webpage_video_hover_preview_pil_frames_by_url.pop(next(iter(webpage_video_hover_preview_pil_frames_by_url)))
                    except Exception:
                        break
            return tuple(frame.copy() for frame in hover_frames)

        def _extract_video_hover_preview_seed_frames(item: Any, hover_url: str) -> tuple[Any, ...]:
            # V79J: seed with the smallest useful moving segment.  The
            # previous 0.65s seed waited for too many frames before the UI could
            # start playback.  Decode from a small seek past static lead-ins so
            # first hover and loop wrap both feel immediate.
            return _extract_video_hover_preview_frames_cached(
                item,
                hover_url,
                duration_seconds=_video_hover_seed_duration_seconds(),
                fps=_video_hover_target_fps(),
                max_frames=8,
                timeout=0.85,
                first_frame_timeout=0.35,
                seek_seconds=_video_hover_fast_seek_seconds(),
            )

        def _extract_video_hover_preview_long_frames(item: Any, hover_url: str) -> tuple[Any, ...]:
            # V79M: keep V79L's fast seed, elapsed-clock playback, and fixed
            # wait-poll handoff, but use the measured Video DownloadHelper-like
            # ~5.15s long loop.  The window still starts past the static lead-in
            # so startup is quick, while the user sees a fuller preview before
            # the instant modulo wrap.
            return _extract_video_hover_preview_frames_cached(
                item,
                hover_url,
                duration_seconds=_video_hover_loop_duration_seconds(),
                fps=_video_hover_target_fps(),
                max_frames=138,
                timeout=6.5,
                first_frame_timeout=0.65,
                seek_seconds=_video_hover_fast_seek_seconds(),
                force_refresh=True,
            )

        def _apply_cached_thumbnail_preview(item: Any) -> bool:
            # A poster/thumbnail cache hit must not block animated hover-preview
            # availability.  V78J only generated hover frames when direct video
            # frame extraction was needed; Metro-style pages often provide poster
            # thumbnails, so hover previews never became ready.
            _apply_cached_video_hover_preview(item)
            preview_url = _preview_url_for_item(item)
            if preview_url:
                cached_preview = webpage_image_preview_pil_cache_by_url.get(preview_url)
                if cached_preview is not None:
                    return _cache_ctk_thumbnail_for_item(item, cached_preview)
            video_frame_url = _video_frame_preview_url_for_item(item)
            if video_frame_url:
                cached_frame = webpage_video_frame_preview_pil_cache_by_url.get(video_frame_preview_cache_key(video_frame_url))
                if cached_frame is not None:
                    _apply_cached_video_hover_preview(item)
                    return _cache_ctk_thumbnail_for_item(item, cached_frame)
            return False

        def _image_candidate_should_probe_preview(item: Any) -> bool:
            if resource_kind not in {RESOURCE_KIND_IMAGE, RESOURCE_KIND_VIDEO_AUDIO}:
                return False
            if item.resource_id in thumbnail_images_by_id:
                return False
            if thumbnail_preview_status_by_id.get(item.resource_id) in {"pending", "success", "hidden", "failed"}:
                return False
            preview_url = _preview_url_for_item(item)
            video_frame_url = _video_frame_preview_url_for_item(item)
            if not preview_url and not video_frame_url:
                thumbnail_preview_status_by_id[item.resource_id] = "hidden"
                thumbnail_hidden_resource_ids.add(item.resource_id)
                return False
            thumbnail_preview_url_by_id[item.resource_id] = preview_url or video_frame_url
            if _apply_cached_thumbnail_preview(item):
                return False
            if preview_url and _image_candidate_is_obvious_non_preview(item):
                thumbnail_preview_status_by_id[item.resource_id] = "hidden"
                thumbnail_hidden_resource_ids.add(item.resource_id)
                return False
            return True

        def _is_default_hidden_webpage_image_candidate(item: Any) -> bool:
            """Keep the default real-site grid to previewable images only."""
            if resource_kind != RESOURCE_KIND_IMAGE:
                return False
            if item.resource_id in selected_ids:
                return False
            if item.resource_id in thumbnail_images_by_id:
                return False
            status = thumbnail_preview_status_by_id.get(item.resource_id, "")
            if status in {"pending", "success"}:
                return True
            if status in {"hidden", "failed"} or item.resource_id in thumbnail_hidden_resource_ids:
                return True
            return True

        def _schedule_thumbnail_probe_render(delay_ms: int = 650) -> None:
            nonlocal thumbnail_probe_render_after_id
            if thumbnail_probe_render_after_id is not None:
                return

            def _run_render() -> None:
                nonlocal thumbnail_probe_render_after_id
                thumbnail_probe_render_after_id = None
                try:
                    if window.winfo_exists():
                        render_resource_list()
                        refresh_count()
                except Exception:
                    logger.debug("Could not refresh image preview grid after thumbnail probe.", exc_info=True)

            try:
                thumbnail_probe_render_after_id = window.after(delay_ms, _run_render)
            except Exception:
                thumbnail_probe_render_after_id = None

        def _thumbnail_probe_success(resource_id: str, preview_image: Any) -> None:
            try:
                preview_url = thumbnail_preview_url_by_id.get(resource_id, "")
                if preview_url:
                    webpage_image_preview_pil_cache_by_url[preview_url] = preview_image.copy()
                    while len(webpage_image_preview_pil_cache_by_url) > webpage_image_preview_cache_limit:
                        try:
                            webpage_image_preview_pil_cache_by_url.pop(next(iter(webpage_image_preview_pil_cache_by_url)))
                        except Exception:
                            break
                matching_item = next((candidate for candidate in state.resources if candidate.resource_id == resource_id), None)
                if matching_item is not None and _cache_ctk_thumbnail_for_item(matching_item, preview_image):
                    return
                ctk_image = ctk.CTkImage(
                    light_image=preview_image.copy(),
                    dark_image=preview_image.copy(),
                    size=(max(1, preview_image.width), max(1, preview_image.height)),
                )
                thumbnail_images_by_id[resource_id] = ctk_image
                thumbnail_hidden_resource_ids.discard(resource_id)
                thumbnail_preview_status_by_id[resource_id] = "success"
            except Exception:
                thumbnail_hidden_resource_ids.add(resource_id)
                thumbnail_preview_status_by_id[resource_id] = "failed"

        def _thumbnail_probe_failure(resource_id: str) -> None:
            thumbnail_hidden_resource_ids.add(resource_id)
            thumbnail_preview_status_by_id[resource_id] = "failed"

        def _video_hover_probe_failure(resource_id: str) -> None:
            video_hover_preview_status_by_id[resource_id] = "failed"

        def _video_hover_probe_success(resource_id: str, preview_frames: Any) -> None:
            if _cache_ctk_video_hover_frames_for_item(resource_id, preview_frames):
                video_hover_preview_status_by_id[resource_id] = "success"

        def _queue_thumbnail_probe_result(kind: str, resource_id: str = "", preview_image: Any = None) -> None:
            try:
                with thumbnail_probe_results_lock:
                    thumbnail_probe_results.append((kind, resource_id, preview_image))
            except Exception:
                pass

        def _ensure_thumbnail_probe_result_pump() -> None:
            nonlocal thumbnail_probe_result_after_id, video_hover_probe_thread_active
            if thumbnail_probe_result_after_id is not None:
                return

            def _drain_thumbnail_probe_results() -> None:
                nonlocal thumbnail_probe_thread_active, thumbnail_probe_result_after_id, video_hover_probe_thread_active
                thumbnail_probe_result_after_id = None
                queued: list[tuple[str, str, Any]] = []
                try:
                    with thumbnail_probe_results_lock:
                        queued = list(thumbnail_probe_results)
                        thumbnail_probe_results.clear()
                except Exception:
                    queued = []
                changed = False
                for kind, resource_id, preview_image in queued:
                    if kind == "success":
                        _thumbnail_probe_success(resource_id, preview_image)
                        changed = True
                    elif kind == "hover_frames":
                        _video_hover_probe_success(resource_id, preview_image)
                        changed = True
                    elif kind == "hover_failed":
                        _video_hover_probe_failure(resource_id)
                        changed = True
                    elif kind == "hover_done":
                        video_hover_probe_thread_active = False
                        changed = True
                    elif kind == "failed":
                        _thumbnail_probe_failure(resource_id)
                        changed = True
                    elif kind == "done":
                        thumbnail_probe_thread_active = False
                        changed = True
                if changed:
                    _schedule_thumbnail_probe_render(650)
                should_continue = thumbnail_probe_thread_active or video_hover_probe_thread_active
                try:
                    with thumbnail_probe_results_lock:
                        should_continue = should_continue or bool(thumbnail_probe_results)
                except Exception:
                    pass
                if should_continue:
                    try:
                        thumbnail_probe_result_after_id = window.after(35, _drain_thumbnail_probe_results)
                    except Exception:
                        thumbnail_probe_result_after_id = None

            try:
                thumbnail_probe_result_after_id = window.after(35, _drain_thumbnail_probe_results)
            except Exception:
                thumbnail_probe_result_after_id = None

        def _start_thumbnail_preview_probe(resources: tuple[Any, ...]) -> None:
            nonlocal thumbnail_probe_thread_active
            if resource_kind not in {RESOURCE_KIND_IMAGE, RESOURCE_KIND_VIDEO_AUDIO} or row.adapter_id in {"youtube", "twitter_x"}:
                return
            if thumbnail_probe_thread_active:
                _ensure_thumbnail_probe_result_pump()
                return
            candidates = [item for item in resources if _image_candidate_should_probe_preview(item)]
            if not candidates:
                return
            # Image thumbnails are cheap HTTP image fetches.  Direct video
            # frame previews can require ffmpeg startup and a ranged media read,
            # so keep the first-frame pass intentionally small.
            candidates = candidates[: (16 if resource_kind == RESOURCE_KIND_VIDEO_AUDIO else 64)]
            for candidate in candidates:
                thumbnail_preview_status_by_id[candidate.resource_id] = "pending"
            thumbnail_probe_thread_active = True
            _ensure_thumbnail_probe_result_pump()

            def _prefetch_video_hover_frames_for_item(item: Any) -> bool:
                if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                    return False
                if video_live_preview_mode_enabled:
                    return False
                hover_url = _video_hover_preview_url_for_item(item)
                if not hover_url:
                    return False
                try:
                    hover_frames = _extract_video_hover_preview_frames_cached(item, hover_url)
                except Exception:
                    return False
                _queue_thumbnail_probe_result("hover_frames", item.resource_id, tuple(frame.copy() for frame in hover_frames))
                return True

            def _probe_one_thumbnail(item: Any) -> tuple[str, str, Any]:
                resource_id = item.resource_id
                preview_url = _preview_url_for_item(item)
                if preview_url:
                    try:
                        request = urllib.request.Request(
                            preview_url,
                            headers={
                                "User-Agent": "Mozilla/5.0 YTCE media preview",
                                "Accept": "image/avif,image/webp,image/png,image/jpeg,image/*,*/*;q=0.8",
                            },
                        )
                        with urllib.request.urlopen(request, timeout=0.7) as response:
                            data = response.read(384 * 1024)
                        preview_image = Image.open(BytesIO(data))
                        if getattr(preview_image, "is_animated", False):
                            preview_image.seek(0)
                        preview_image = preview_image.convert("RGBA")
                        original_preview_width, original_preview_height = preview_image.size
                        if min(original_preview_width, original_preview_height) < 24:
                            raise ValueError("tiny preview")
                        preview_image.thumbnail((168, 128), Image.LANCZOS)
                        webpage_image_preview_pil_cache_by_url[preview_url] = preview_image.copy()
                        while len(webpage_image_preview_pil_cache_by_url) > webpage_image_preview_cache_limit:
                            try:
                                webpage_image_preview_pil_cache_by_url.pop(next(iter(webpage_image_preview_pil_cache_by_url)))
                            except Exception:
                                break
                        _prefetch_video_hover_frames_for_item(item)
                        return "success", resource_id, preview_image.copy()
                    except Exception:
                        pass

                video_frame_url = _video_frame_preview_url_for_item(item)
                if video_frame_url:
                    try:
                        cache_key = video_frame_preview_cache_key(video_frame_url)
                        cached_frame = webpage_video_frame_preview_pil_cache_by_url.get(cache_key)
                        if cached_frame is not None:
                            _prefetch_video_hover_frames_for_item(item)
                            return "success", resource_id, cached_frame.copy()
                        frame_image = extract_video_frame_preview_pil(
                            video_frame_url,
                            timeout=2.5,
                            seek_seconds=1.0,
                            referer=str(getattr(row, "canonical_url", "") or getattr(row, "raw_url", "") or ""),
                        )
                        webpage_video_frame_preview_pil_cache_by_url[cache_key] = frame_image.copy()
                        while len(webpage_video_frame_preview_pil_cache_by_url) > webpage_video_frame_preview_cache_limit:
                            try:
                                webpage_video_frame_preview_pil_cache_by_url.pop(next(iter(webpage_video_frame_preview_pil_cache_by_url)))
                            except Exception:
                                break
                        _prefetch_video_hover_frames_for_item(item)
                        return "success", resource_id, frame_image.copy()
                    except Exception:
                        return "failed", resource_id, None
                return "failed", resource_id, None

            def _worker(items: list[Any]) -> None:
                try:
                    worker_count = max(1, min(4, len(items)))
                    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                        futures = [executor.submit(_probe_one_thumbnail, item) for item in items]
                        for future in concurrent.futures.as_completed(futures):
                            try:
                                kind, resource_id, preview_image = future.result()
                            except Exception:
                                continue
                            _queue_thumbnail_probe_result(kind, resource_id, preview_image)
                finally:
                    _queue_thumbnail_probe_result("done")

            threading.Thread(target=_worker, args=(candidates,), daemon=True).start()

        def _video_hover_candidate_should_probe(item: Any) -> bool:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return False
            if item.resource_id in video_hover_preview_frames_by_id:
                return False
            status = video_hover_preview_status_by_id.get(item.resource_id, "")
            if status in {"pending", "success", "failed"}:
                return False
            hover_url = _video_hover_preview_url_for_item(item)
            if not hover_url:
                return False
            if _apply_cached_video_hover_preview(item):
                return False
            return True

        def _start_video_hover_preview_probe(resources: tuple[Any, ...]) -> None:
            nonlocal video_hover_probe_thread_active
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO or row.adapter_id in {"youtube", "twitter_x"}:
                return
            if video_hover_probe_thread_active:
                _ensure_thumbnail_probe_result_pump()
                return
            candidates = [item for item in resources if _video_hover_candidate_should_probe(item)]
            if not candidates:
                return
            # Browser-hover references preload direct video elements before hover.
            # Run this independently from thumbnail probing so a poster/thumbnail
            # cache hit cannot suppress animated hover frames again.
            candidates = candidates[: (1 if video_live_preview_mode_enabled else 6)]
            for candidate in candidates:
                video_hover_preview_status_by_id[candidate.resource_id] = "pending"
            video_hover_probe_thread_active = True
            _ensure_thumbnail_probe_result_pump()

            def _worker(items: list[Any]) -> None:
                try:
                    worker_count = max(1, min(2, len(items)))
                    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                        futures = []
                        for item in items:
                            hover_url = _video_hover_preview_url_for_item(item)
                            if hover_url:
                                futures.append((item.resource_id, hover_url, executor.submit(_extract_video_hover_preview_seed_frames, item, hover_url)))
                        long_jobs: list[tuple[str, str, Any]] = []
                        for resource_id, hover_url, future in futures:
                            try:
                                preview_frames = future.result()
                            except Exception:
                                # If the fast seed fails, still try the longer pass once before marking failed.
                                try:
                                    item_for_long = next((candidate for candidate in items if str(getattr(candidate, "resource_id", "") or "") == resource_id), None)
                                    if item_for_long is not None:
                                        long_frames = _extract_video_hover_preview_long_frames(item_for_long, hover_url)
                                        _queue_thumbnail_probe_result("hover_frames", resource_id, tuple(frame.copy() for frame in long_frames))
                                    else:
                                        _queue_thumbnail_probe_result("hover_failed", resource_id)
                                except Exception:
                                    _queue_thumbnail_probe_result("hover_failed", resource_id)
                            else:
                                _queue_thumbnail_probe_result("hover_frames", resource_id, tuple(frame.copy() for frame in preview_frames))
                                item_for_long = next((candidate for candidate in items if str(getattr(candidate, "resource_id", "") or "") == resource_id), None)
                                if item_for_long is not None:
                                    long_jobs.append((resource_id, hover_url, executor.submit(_extract_video_hover_preview_long_frames, item_for_long, hover_url)))
                        for resource_id, _hover_url, future in long_jobs:
                            try:
                                preview_frames = future.result()
                            except Exception:
                                # Keep the seed frames; hover can still loop the short segment.
                                continue
                            else:
                                _queue_thumbnail_probe_result("hover_frames", resource_id, tuple(frame.copy() for frame in preview_frames))
                finally:
                    _queue_thumbnail_probe_result("hover_done")

            threading.Thread(target=_worker, args=(candidates,), daemon=True).start()

        def _schedule_selected_video_hover_warm(item: Any, delay_ms: int = 220) -> None:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return
            hover_url = _video_hover_preview_url_for_item(item)
            if not hover_url:
                return
            if any(cache_key in webpage_video_hover_preview_pil_frames_by_url for cache_key in _video_hover_cache_lookup_keys_for_url(hover_url)):
                _apply_cached_video_hover_preview(item)
                return
            if hover_url in video_hover_warmed_urls:
                return
            if hover_url in video_hover_warm_after_id_by_url:
                return

            def _warm_now() -> None:
                video_hover_warm_after_id_by_url.pop(hover_url, None)
                video_hover_warmed_urls.add(hover_url)
                _start_video_hover_preview_probe((item,))

            try:
                video_hover_warm_after_id_by_url[hover_url] = window.after(max(1, int(delay_ms)), _warm_now)
            except Exception:
                _warm_now()

        def _image_preview_for_item(item: Any) -> ctk.CTkImage | None:
            if resource_kind not in {RESOURCE_KIND_IMAGE, RESOURCE_KIND_VIDEO_AUDIO}:
                return None
            return thumbnail_images_by_id.get(item.resource_id)

        def _cap_image_display_resources(resources: tuple[Any, ...], limit: int) -> tuple[tuple[Any, ...], int]:
            if limit <= 0 or len(resources) <= limit:
                return resources, 0
            selected_resources = [item for item in resources if item.resource_id in selected_ids]
            other_resources = [item for item in resources if item.resource_id not in selected_ids]
            remaining_slots = max(0, limit - len(selected_resources))
            capped = tuple((selected_resources + other_resources[:remaining_slots])[:limit])
            return capped, max(0, len(resources) - len(capped))

        image_detail_popup: Any = None
        image_detail_popup_hide_after_id: Any = None

        def hide_image_detail_popup() -> None:
            nonlocal image_detail_popup, image_detail_popup_hide_after_id
            if image_detail_popup_hide_after_id:
                try:
                    window.after_cancel(image_detail_popup_hide_after_id)
                except Exception:
                    pass
            image_detail_popup_hide_after_id = None
            if image_detail_popup is not None:
                try:
                    image_detail_popup.destroy()
                except Exception:
                    pass
            image_detail_popup = None

        def schedule_hide_image_detail_popup(delay_ms: int = 220) -> None:
            nonlocal image_detail_popup_hide_after_id
            if image_detail_popup_hide_after_id:
                try:
                    window.after_cancel(image_detail_popup_hide_after_id)
                except Exception:
                    pass
            image_detail_popup_hide_after_id = window.after(delay_ms, hide_image_detail_popup)

        def image_resource_detail_text(item: Any) -> str:
            lines = [str(item.display_name or item.resource_id)]
            if getattr(item, "media_type", "") or getattr(item, "extension", ""):
                lines.append(f"Type: {item.media_type or item.extension}")
            if getattr(item, "width", None) and getattr(item, "height", None):
                lines.append(f"Size: {item.width}x{item.height}")
            if getattr(item, "from_link", False):
                lines.append("Source: linked image")
            elif getattr(item, "provenance", ""):
                lines.append(f"Source: {str(item.provenance).replace('_', ' ')}")
            url = getattr(item, "reference_url", "") or getattr(item, "canonical_url", "")
            if url:
                lines.append(str(url))
            if getattr(item, "warning", ""):
                lines.append(f"Review: {item.warning}")
            return "\n".join(line for line in lines if line)

        def show_image_detail_popup(item: Any, event: Any) -> None:
            nonlocal image_detail_popup, image_detail_popup_hide_after_id
            if image_detail_popup_hide_after_id:
                try:
                    window.after_cancel(image_detail_popup_hide_after_id)
                except Exception:
                    pass
                image_detail_popup_hide_after_id = None
            if image_detail_popup is not None:
                try:
                    image_detail_popup.destroy()
                except Exception:
                    pass
            popup = tk.Frame(
                list_frame,
                bg=COLORS["bg_input"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
                bd=0,
            )
            text = image_resource_detail_text(item)
            tk.Label(
                popup,
                text=text,
                justify="left",
                anchor="w",
                bg=COLORS["bg_input"],
                fg=COLORS["text_primary"],
                padx=10,
                pady=7,
                font=("Segoe UI", 9),
                wraplength=360,
            ).pack(fill="both", expand=True)
            popup.bind("<Enter>", lambda _event: None, add="+")
            popup.bind("<Leave>", lambda _event: schedule_hide_image_detail_popup(220), add="+")
            image_detail_popup = popup
            popup.update_idletasks()
            width = max(220, min(400, popup.winfo_reqwidth()))
            height = max(48, popup.winfo_reqheight())
            try:
                x = int(getattr(event, "x_root", 0)) - list_frame.winfo_rootx() + 14
                y = int(getattr(event, "y_root", 0)) - list_frame.winfo_rooty() + 16
                x = max(4, min(x, max(4, list_frame.winfo_width() - width - 8)))
                y = max(4, min(y, max(4, list_frame.winfo_height() - height - 8)))
            except Exception:
                x, y = 12, 12
            popup.place(x=x, y=y, width=width)
            popup.lift()

        def bind_image_detail_hover(widget: Any, item: Any) -> None:
            try:
                widget.bind("<Enter>", lambda event, i=item: show_image_detail_popup(i, event), add="+")
                widget.bind("<Motion>", lambda event, i=item: show_image_detail_popup(i, event), add="+")
                widget.bind("<Leave>", lambda _event: schedule_hide_image_detail_popup(220), add="+")
            except Exception:
                pass

        def _pointer_inside_widget(widget: Any) -> bool:
            try:
                pointer_x, pointer_y = widget.winfo_pointerxy()
                root_x, root_y = widget.winfo_rootx(), widget.winfo_rooty()
                return root_x <= pointer_x <= root_x + widget.winfo_width() and root_y <= pointer_y <= root_y + widget.winfo_height()
            except Exception:
                return False

        def _video_hover_surface_has_pointer(resource_id: str = "") -> bool:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return False
            resource_ids = (str(resource_id or ""),) if resource_id else tuple(video_hover_surface_widgets_by_resource_id)
            for candidate_id in resource_ids:
                if not candidate_id:
                    continue
                for widget in video_hover_surface_widgets_by_resource_id.get(candidate_id, ()):
                    if _pointer_inside_widget(widget):
                        return True
            return False

        def _video_hover_should_protect_repaint(resource_id: str = "") -> bool:
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return False
            if resource_id and str(resource_id or "") in video_hover_active_resource_ids:
                return True
            if not resource_id and video_hover_active_resource_ids:
                return True
            return _video_hover_surface_has_pointer(resource_id)

        def show_image_dialog_notice(title: str, body: str) -> None:
            notice = ctk.CTkToplevel(window)
            notice.title(title)
            notice.geometry("460x180")
            notice.transient(window)
            notice.grab_set()
            frame = ctk.CTkFrame(notice, fg_color=COLORS["bg_card"], corner_radius=10)
            frame.pack(fill="both", expand=True, padx=12, pady=12)
            ctk.CTkLabel(
                frame,
                text=title,
                text_color=COLORS["text_primary"],
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            ).pack(anchor="w", padx=14, pady=(12, 6))
            ctk.CTkLabel(
                frame,
                text=body,
                text_color=COLORS["text_secondary"],
                font=ctk.CTkFont(size=11),
                justify="left",
                wraplength=410,
            ).pack(anchor="w", fill="x", padx=14, pady=(0, 12))
            ctk.CTkButton(frame, text="OK", width=80, command=notice.destroy).pack(anchor="e", padx=14, pady=(0, 12))
            try:
                notice.focus_set()
            except Exception:
                pass

        def _schedule_video_hover_deferred_repaint(delay_ms: int = 80) -> None:
            nonlocal video_hover_repaint_after_id, video_hover_repaint_deferred
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return
            if video_hover_repaint_after_id is not None:
                return

            def _run_deferred_repaint() -> None:
                nonlocal video_hover_repaint_after_id, video_hover_repaint_deferred
                video_hover_repaint_after_id = None
                if _video_hover_should_protect_repaint():
                    try:
                        video_hover_repaint_after_id = window.after(120, _run_deferred_repaint)
                    except Exception:
                        video_hover_repaint_after_id = None
                    return
                if not video_hover_repaint_deferred:
                    return
                video_hover_repaint_deferred = False
                try:
                    if window.winfo_exists():
                        render_resource_list()
                        refresh_count()
                except Exception:
                    logger.debug("Could not run deferred video repaint after hover finished.", exc_info=True)

            try:
                video_hover_repaint_after_id = window.after(max(1, int(delay_ms)), _run_deferred_repaint)
            except Exception:
                video_hover_repaint_after_id = None

        def render_resource_list() -> None:
            nonlocal active_state, hidden_candidate_count, thumbnail_preview_loading_count, rendered_tile_resource_ids, rendered_tile_variant_signature, video_grouped_variant_hidden_count, video_first_paint_logged, video_hover_repaint_deferred
            filtered_state = filter_resource_dialog_items(state, current_filters())
            display_resources = tuple(filtered_state.resources)
            hidden_candidate_count = 0
            thumbnail_preview_loading_count = 0
            if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"}:
                _start_thumbnail_preview_probe(display_resources)
                if not bool(show_hidden_images_var.get()):
                    kept_resources: list[Any] = []
                    hidden_resources: list[Any] = []
                    for candidate_item in display_resources:
                        if candidate_item.resource_id in selected_ids or candidate_item.resource_id in thumbnail_images_by_id:
                            kept_resources.append(candidate_item)
                        else:
                            hidden_resources.append(candidate_item)
                            if thumbnail_preview_status_by_id.get(candidate_item.resource_id) == "pending":
                                thumbnail_preview_loading_count += 1
                    display_resources, overflow_hidden_count = _cap_image_display_resources(tuple(kept_resources), default_image_render_limit)
                    hidden_candidate_count = len(hidden_resources) + overflow_hidden_count
                else:
                    display_resources, hidden_candidate_count = _cap_image_display_resources(display_resources, hidden_image_render_limit)
            elif resource_kind == RESOURCE_KIND_VIDEO_AUDIO and row.adapter_id not in {"youtube", "twitter_x"}:
                display_resources = _group_video_rendition_display_resources(tuple(display_resources))
                _start_thumbnail_preview_probe(display_resources)
                if not video_live_preview_mode_enabled:
                    _start_video_hover_preview_probe(display_resources)
            active_state = filtered_state.__class__(
                source_row_id=filtered_state.source_row_id,
                resource_kind=filtered_state.resource_kind,
                resources=display_resources,
                selected_resource_ids=tuple(resource_id for resource_id in filtered_state.selected_resource_ids if resource_id in {item.resource_id for item in display_resources}),
                committed_resource_ids=filtered_state.committed_resource_ids,
            )
            display_resource_ids = tuple(item.resource_id for item in active_state.resources)
            display_variant_signature = _video_variant_signature_for_resources(tuple(active_state.resources))
            # V78R: rebuild video tiles when a same-id representative gains
            # quality variants.  The image-only refresh path is still safe only
            # when both the visible ids and variant signature match.
            if (
                display_resource_ids
                and display_resource_ids == rendered_tile_resource_ids
                and display_variant_signature == rendered_tile_variant_signature
                and rendered_tile_refreshers_by_id
            ):
                for visible_item in active_state.resources:
                    refresher = rendered_tile_refreshers_by_id.get(visible_item.resource_id)
                    if refresher is None:
                        continue
                    try:
                        refresher(visible_item)
                    except Exception:
                        pass
                return
            if (
                resource_kind == RESOURCE_KIND_VIDEO_AUDIO
                and _video_hover_should_protect_repaint()
                and rendered_tile_resource_ids
            ):
                # V79E: a slow full-discovery merge can arrive while the user is
                # watching the tile hover preview.  Rebuilding the grid here would
                # destroy the label that is currently animating, so defer the
                # disruptive repaint until hover leave.
                video_hover_repaint_deferred = True
                _schedule_video_hover_deferred_repaint(120)
                return
            video_hover_surface_widgets_by_resource_id.clear()
            for child in list_frame.winfo_children():
                child.destroy()
            vars_by_id.clear()
            rendered_tile_refreshers_by_id.clear()
            rendered_tile_resource_ids = display_resource_ids
            rendered_tile_variant_signature = display_variant_signature
            column_count = 4 if resource_kind == RESOURCE_KIND_IMAGE else 2
            for column_index in range(column_count):
                list_frame.grid_columnconfigure(column_index, weight=1, uniform="image_cards")
            if not active_state.resources:
                empty_text = (
                    "Images are scanned automatically when this window opens. Use Refresh images to rescan the source page."
                    if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"}
                    else "No selectable media resources match this source/filter."
                )
                if hidden_candidate_count and resource_kind == RESOURCE_KIND_IMAGE and not bool(show_hidden_images_var.get()):
                    if thumbnail_preview_loading_count:
                        empty_text = f"Loading previewable image thumbnails... {thumbnail_preview_loading_count} candidate(s) still being checked. Enable Show hidden to inspect hidden/no-preview candidates."
                    else:
                        empty_text = f"No visible image previews match this source/filter. Enable Show hidden to inspect {hidden_candidate_count} hidden/no-preview candidate(s)."
                empty = ctk.CTkLabel(
                    list_frame,
                    text=empty_text,
                    text_color=COLORS["text_muted"],
                    wraplength=640,
                    justify="left",
                )
                empty.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=8)
                rendered_tile_resource_ids = ()
                rendered_tile_variant_signature = ()
                rendered_tile_refreshers_by_id.clear()
                return
            if resource_kind == RESOURCE_KIND_VIDEO_AUDIO and not video_first_paint_logged:
                video_first_paint_logged = True
                try:
                    self.log_message(f"Video dialog first paint after {int(max(0.0, (time.perf_counter() - video_dialog_started_at) * 1000.0))} ms", "muted")
                except Exception:
                    pass
            tile_checkbox_refreshers: list[Any] = []
            for index, item in enumerate(active_state.resources):
                item_var = ctk.BooleanVar(value=item.resource_id in selected_ids)
                vars_by_id[item.resource_id] = item_var

                def on_item_toggle(resource_id: str = item.resource_id, var: Any = item_var) -> None:
                    if var.get():
                        selected_ids.add(resource_id)
                    else:
                        selected_ids.discard(resource_id)
                    refresh_count()

                def toggle_item(resource_id: str = item.resource_id, var: Any = item_var) -> None:
                    if not item.selectable:
                        return
                    var.set(not bool(var.get()))
                    on_item_toggle(resource_id, var)

                warning_text = str(getattr(item, "warning", "") or "").lower()
                status_text = str(getattr(item, "status", "") or "").lower()
                needs_review = bool(warning_text or "review" in status_text)
                if resource_kind == RESOURCE_KIND_VIDEO_AUDIO:
                    # Normal webpage video candidates may carry review/download-route
                    # metadata because Review selected still does no generic download.
                    # That should not paint every tile red.  Keep red styling for
                    # real problems only.
                    serious_review_markers = ("error", "failed", "blocked", "unsupported", "drm", "permission", "denied", "missing")
                    needs_review = any(marker in warning_text or marker in status_text for marker in serious_review_markers)
                selected_now = item.resource_id in selected_ids
                item_card = ctk.CTkFrame(
                    list_frame,
                    fg_color="#3b151c" if needs_review else COLORS["bg_card"],
                    border_width=2 if selected_now else (1 if needs_review else 0),
                    border_color=COLORS["accent"] if selected_now else ("#ff5d73" if needs_review else COLORS["border"]),
                    corner_radius=8,
                    width=190,
                    height=194,
                )
                item_card.grid(
                    row=index // column_count,
                    column=index % column_count,
                    sticky="nsew",
                    padx=(6, 3) if index % column_count != column_count - 1 else (3, 6),
                    pady=6,
                )
                item_card.grid_propagate(False)
                item_card.grid_columnconfigure(0, weight=1)
                item_card.grid_rowconfigure(0, weight=1, minsize=140)
                item_card.grid_rowconfigure(1, weight=0, minsize=34)
                item_card.bind("<Button-1>", lambda _event, rid=item.resource_id, var=item_var: toggle_item(rid, var), add="+")

                preview = _image_preview_for_item(item)
                preview_box = ctk.CTkFrame(item_card, fg_color=COLORS["bg_input"], corner_radius=6, width=174, height=142)
                preview_box.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 5))
                preview_box.grid_propagate(False)
                preview_box.bind("<Button-1>", lambda _event, rid=item.resource_id, var=item_var: toggle_item(rid, var), add="+")
                image_size_text = f"{item.width}x{item.height}" if item.width and item.height else "size unknown"
                image_size_badge = ctk.CTkLabel(
                    preview_box,
                    text=image_size_text,
                    fg_color=COLORS["bg_dark"],
                    text_color=COLORS["text_primary"],
                    corner_radius=5,
                    font=ctk.CTkFont(size=10, weight="bold"),
                )

                def show_image_size_badge(
                    _event: Any = None,
                    badge: Any = image_size_badge,
                    current_item: Any = item,
                ) -> None:
                    if badge is None:
                        return
                    try:
                        # V78T: on grouped video cards the bottom size badge sits
                        # on top of the quality selector and steals the click. The
                        # selector itself already communicates the chosen quality,
                        # so suppress the hover badge for those cards.
                        if resource_kind == RESOURCE_KIND_VIDEO_AUDIO and len(video_variant_group_members_by_rep_id.get(str(getattr(current_item, "resource_id", "") or ""), ())) > 1:
                            badge.place_forget()
                            return
                        badge.place(relx=0.5, rely=1.0, anchor="s", y=-7)
                        badge.lift()
                    except Exception:
                        pass

                def hide_image_size_badge(_event: Any = None, badge: Any = image_size_badge) -> None:
                    if badge is None:
                        return
                    try:
                        badge.place_forget()
                    except Exception:
                        pass

                if preview is not None:
                    preview_label = ctk.CTkLabel(preview_box, text="", image=preview)
                    preview_label.pack(expand=True)
                    preview_label.bind("<Button-1>", lambda _event, rid=item.resource_id, var=item_var: toggle_item(rid, var), add="+")
                else:
                    placeholder_text = _media_placeholder_text_for_item(item)
                    preview_label = ctk.CTkLabel(
                        preview_box,
                        text=placeholder_text,
                        text_color=COLORS["text_secondary"],
                        font=ctk.CTkFont(size=_media_placeholder_font_size(item), weight="bold"),
                    )
                    preview_label.pack(expand=True)
                    preview_label.bind("<Button-1>", lambda _event, rid=item.resource_id, var=item_var: toggle_item(rid, var), add="+")
                if resource_kind == RESOURCE_KIND_VIDEO_AUDIO:
                    video_hover_surface_widgets_by_resource_id[str(item.resource_id)] = (preview_box, preview_label)

                live_preview_url = _video_live_preview_url_for_item(item)
                if live_preview_url:
                    live_preview_button = ctk.CTkButton(
                        preview_box,
                        text="LIVE ▶",
                        width=76,
                        height=24,
                        corner_radius=6,
                        fg_color=COLORS["accent"],
                        hover_color=COLORS["accent_hover"],
                        text_color=COLORS["text_primary"],
                        font=ctk.CTkFont(size=10, weight="bold"),
                        command=lambda current_item=item: _open_live_video_preview_for_item(current_item),
                    )
                    live_preview_button.place(relx=1.0, x=-7, y=7, anchor="ne")
                    live_preview_button.lift()
                    preview_box.bind("<Double-Button-1>", lambda _event, current_item=item: _open_live_video_preview_for_item(current_item), add="+")
                    preview_label.bind("<Double-Button-1>", lambda _event, current_item=item: _open_live_video_preview_for_item(current_item), add="+")
                variant_group = video_variant_group_members_by_rep_id.get(str(item.resource_id), ())
                if len(variant_group) > 1:
                    variant_option_pairs = _video_variant_option_pairs_for_rep(item)
                    variant_label_var = ctk.StringVar(value=_video_variant_selected_label_for_rep(item))
                    variant_quality_menu = ctk.CTkOptionMenu(
                        preview_box,
                        values=[label_text for label_text, _variant in variant_option_pairs],
                        variable=variant_label_var,
                        width=136,
                        height=24,
                        corner_radius=6,
                        fg_color=COLORS["bg_input"],
                        button_color=COLORS["accent_secondary"],
                        button_hover_color=COLORS["accent"],
                        dropdown_fg_color=COLORS["bg_card"],
                        dropdown_hover_color=COLORS["accent_secondary"],
                        text_color=COLORS["text_primary"],
                        font=ctk.CTkFont(size=9, weight="bold"),
                        command=lambda selected_label, current_item=item, label_var=variant_label_var: _select_video_variant_for_rep(current_item, selected_label, label_var),
                    )
                    variant_quality_menu.place(relx=0.0, x=7, rely=1.0, y=-7, anchor="sw")
                    variant_quality_menu.lift()

                if resource_kind == RESOURCE_KIND_VIDEO_AUDIO and video_live_preview_mode_enabled and live_preview_url:
                    _schedule_selected_video_hover_warm(item, delay_ms=1)

                def _cancel_live_hover_preview(current_item: Any = item) -> None:
                    candidate_ids = {
                        str(getattr(current_item, "resource_id", "") or ""),
                        str(getattr(_video_variant_selected_item_for_rep(current_item), "resource_id", "") or ""),
                    }
                    for resource_id in tuple(candidate_ids):
                        if not resource_id:
                            continue
                        after_id = video_live_hover_after_id_by_resource_id.pop(resource_id, None)
                        if after_id is not None:
                            try:
                                window.after_cancel(after_id)
                            except Exception:
                                pass

                def _schedule_live_hover_preview(
                    _event: Any = None,
                    current_item: Any = item,
                    image_area: Any = preview_box,
                ) -> None:
                    if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                        return
                    if video_live_preview_mode_enabled:
                        _start_video_hover_animation(_event, current_item=current_item, image_area=image_area)
                        return

                def _stop_video_hover_animation(resource_id: str = item.resource_id, label: Any = preview_label, current_item: Any = item) -> None:
                    resource_id = str(resource_id or "")
                    after_id = video_hover_animation_after_id_by_resource_id.pop(resource_id, None)
                    if after_id is not None:
                        try:
                            window.after_cancel(after_id)
                        except Exception:
                            pass
                    stop_after_id = video_hover_stop_after_id_by_resource_id.pop(resource_id, None)
                    if stop_after_id is not None:
                        try:
                            window.after_cancel(stop_after_id)
                        except Exception:
                            pass
                    video_hover_active_resource_ids.discard(resource_id)
                    video_hover_animation_index_by_resource_id[resource_id] = 0
                    video_hover_animation_started_at_by_resource_id.pop(resource_id, None)
                    try:
                        still_preview = _image_preview_for_item(current_item)
                        if still_preview is not None:
                            label.configure(text="", image=still_preview)
                    except Exception:
                        pass
                    if video_hover_repaint_deferred and not video_hover_active_resource_ids:
                        _schedule_video_hover_deferred_repaint(1)

                def _schedule_video_hover_stop(
                    _event: Any = None,
                    resource_id: str = item.resource_id,
                    label: Any = preview_label,
                    image_area: Any = preview_box,
                    current_item: Any = item,
                ) -> None:
                    # V79F: Tk can emit <Leave> while crossing child widgets in
                    # the preview area. Validate the pointer after a tiny grace
                    # window so replay does not stop/restart just because the
                    # cursor crossed the label/frame boundary.
                    resource_id = str(getattr(current_item, "resource_id", "") or resource_id or "")
                    existing_after_id = video_hover_stop_after_id_by_resource_id.pop(resource_id, None)
                    if existing_after_id is not None:
                        try:
                            window.after_cancel(existing_after_id)
                        except Exception:
                            pass

                    def _stop_if_outside() -> None:
                        video_hover_stop_after_id_by_resource_id.pop(resource_id, None)
                        try:
                            if _pointer_inside_widget(image_area):
                                return
                        except Exception:
                            pass
                        _stop_video_hover_animation(resource_id, label, current_item)

                    try:
                        video_hover_stop_after_id_by_resource_id[resource_id] = window.after(70, _stop_if_outside)
                    except Exception:
                        _stop_if_outside()

                def _start_video_hover_animation(
                    _event: Any = None,
                    resource_id: str = item.resource_id,
                    label: Any = preview_label,
                    image_area: Any = preview_box,
                    current_item: Any = item,
                ) -> None:
                    if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                        return
                    # V79A: hover may run in live-preview mode, but it must be
                    # internal tile playback only.  It never opens the manual LIVE
                    # browser/player route.
                    # V79B: keep animation state keyed by the visible tile,
                    # while _video_hover_preview_url_for_item() resolves the
                    # selected quality URL for decoding. This prevents a
                    # selected variant id from driving an adjacent/non-hovered
                    # tile's label.
                    resource_id = str(getattr(current_item, "resource_id", "") or resource_id)
                    pending_stop_after_id = video_hover_stop_after_id_by_resource_id.pop(resource_id, None)
                    if pending_stop_after_id is not None:
                        try:
                            window.after_cancel(pending_stop_after_id)
                        except Exception:
                            pass
                    # V79F: once the user has expressed hover intent, mark this
                    # visible tile as hover-active even while frames are still
                    # being generated. A slow full-discovery merge must not
                    # rebuild the grid and interrupt the pending preview.
                    video_hover_active_resource_ids.add(resource_id)
                    video_hover_animation_started_at_by_resource_id.setdefault(resource_id, time.perf_counter())
                    # V79F: if a URL-level warm cache already exists after a
                    # prior hover or deferred repaint, materialize it onto this
                    # visible tile before checking playback so re-hover starts
                    # from frame 0 without a wait/poll cycle.
                    _apply_cached_video_hover_preview(current_item)

                    def _start_cached_playback() -> bool:
                        frames = video_hover_preview_frames_by_id.get(resource_id)
                        if not frames or len(frames) < 2:
                            return False
                        if video_hover_animation_after_id_by_resource_id.get(resource_id) is not None:
                            return True
                        video_hover_active_resource_ids.add(resource_id)
                        # V79J: fresh hover starts its clock immediately, but
                        # frame selection below is derived from elapsed hover
                        # time.  That keeps playback quick when the seed is later
                        # replaced by the full loop; the full loop does not get
                        # a delayed first cycle just because it arrived late.
                        started_at = video_hover_animation_started_at_by_resource_id.setdefault(resource_id, time.perf_counter())
                        video_hover_animation_index_by_resource_id[resource_id] = 0
                        frame_interval_seconds = 1.0 / float(_video_hover_target_fps())
                        next_frame_deadline = started_at

                        def _step() -> None:
                            nonlocal next_frame_deadline
                            try:
                                if not _pointer_inside_widget(image_area):
                                    video_hover_animation_after_id_by_resource_id.pop(resource_id, None)
                                    _stop_video_hover_animation(resource_id, label, current_item)
                                    return
                                current_frames = video_hover_preview_frames_by_id.get(resource_id) or frames
                                frame_count = max(1, len(current_frames))
                                started_at_now = video_hover_animation_started_at_by_resource_id.get(resource_id)
                                if started_at_now is None:
                                    started_at_now = time.perf_counter()
                                    video_hover_animation_started_at_by_resource_id[resource_id] = started_at_now
                                now = time.perf_counter()
                                elapsed_seconds = max(0.0, now - started_at_now)
                                elapsed_frame = int(elapsed_seconds / frame_interval_seconds)
                                index_value = elapsed_frame % frame_count
                                label.configure(text="", image=current_frames[index_value])
                                video_hover_animation_index_by_resource_id[resource_id] = (index_value + 1) % frame_count

                                next_frame_deadline = started_at_now + ((elapsed_frame + 1) * frame_interval_seconds)
                                while next_frame_deadline <= now:
                                    next_frame_deadline += frame_interval_seconds
                                remaining_seconds = max(0.001, next_frame_deadline - time.perf_counter())
                                delay_ms = max(1, int(round(remaining_seconds * 1000.0)))
                                video_hover_animation_after_id_by_resource_id[resource_id] = window.after(delay_ms, _step)
                            except Exception:
                                video_hover_animation_after_id_by_resource_id.pop(resource_id, None)
                                video_hover_active_resource_ids.discard(resource_id)

                        _step()
                        return True

                    if _start_cached_playback():
                        return
                    _start_video_hover_preview_probe((current_item,))
                    if video_hover_animation_after_id_by_resource_id.get(resource_id) is not None:
                        return

                    def _wait_for_frames() -> None:
                        try:
                            # V79L: this callback was scheduled using the same
                            # dictionary that _start_cached_playback() uses to
                            # detect an active animation.  Clear the wait-poll
                            # token before trying to start playback; otherwise
                            # the first successful poll mistakes its own pending
                            # callback id for a running frame loop and returns
                            # without painting any video frame.
                            video_hover_animation_after_id_by_resource_id.pop(resource_id, None)
                            if not _pointer_inside_widget(image_area):
                                _stop_video_hover_animation(resource_id, label, current_item)
                                return
                            if _start_cached_playback():
                                return
                            video_hover_animation_after_id_by_resource_id[resource_id] = window.after(8, _wait_for_frames)
                        except Exception:
                            video_hover_animation_after_id_by_resource_id.pop(resource_id, None)

                    video_hover_animation_after_id_by_resource_id[resource_id] = window.after(8, _wait_for_frames)

                preview_box.bind("<Enter>", show_image_size_badge, add="+")
                preview_box.bind("<Motion>", show_image_size_badge, add="+")
                preview_label.bind("<Enter>", show_image_size_badge, add="+")
                preview_label.bind("<Motion>", show_image_size_badge, add="+")
                # V79B: only the actual preview surface starts video hover.
                # Binding the whole card could trigger playback while the mouse
                # was over neighbouring controls/tiles, which made the preview
                # appear to belong to the wrong card.
                preview_box.bind("<Enter>", _start_video_hover_animation, add="+")
                preview_box.bind("<Motion>", _start_video_hover_animation, add="+")
                preview_label.bind("<Enter>", _start_video_hover_animation, add="+")
                preview_label.bind("<Motion>", _start_video_hover_animation, add="+")
                preview_box.bind(
                    "<Leave>",
                    lambda event, schedule_stop=_schedule_video_hover_stop, cancel=_cancel_live_hover_preview: (hide_image_size_badge(), cancel(), schedule_stop(event)),
                    add="+",
                )
                preview_label.bind("<Leave>", _schedule_video_hover_stop, add="+")

                checkbox = ctk.CTkLabel(
                    preview_box,
                    text="☐",
                    width=25,
                    height=25,
                    corner_radius=6,
                    fg_color=COLORS["bg_input"],
                    text_color=COLORS["text_primary"],
                    font=ctk.CTkFont(size=16, weight="bold"),
                )

                checkbox_visibility_state: dict[str, Any] = {"visible": False, "selected": None}

                def _sync_tile_checkbox_style(cb: Any = checkbox, var: Any = item_var, state: dict[str, Any] = checkbox_visibility_state) -> bool:
                    try:
                        selected = bool(var.get())
                        if state.get("selected") == selected:
                            return selected
                        state["selected"] = selected
                        cb.configure(
                            text=("✓" if selected else "☐"),
                            fg_color=(COLORS["accent"] if selected else COLORS["bg_input"]),
                            text_color=(COLORS["text_primary"] if selected else "#8a969e"),
                        )
                        return selected
                    except Exception:
                        return False

                def _pointer_is_over_tile_image_area(image_area: Any = preview_box) -> bool:
                    return _pointer_inside_widget(image_area)

                def _place_tile_checkbox(cb: Any = checkbox, state: dict[str, Any] = checkbox_visibility_state) -> None:
                    if state.get("visible"):
                        return
                    cb.place(x=6, y=6)
                    cb.lift()
                    state["visible"] = True

                def _hide_tile_checkbox(cb: Any = checkbox, state: dict[str, Any] = checkbox_visibility_state) -> None:
                    if not state.get("visible"):
                        return
                    cb.place_forget()
                    state["visible"] = False

                def refresh_tile_checkbox_visibility(
                    _event: Any = None,
                    image_area: Any = preview_box,
                    cb: Any = checkbox,
                    var: Any = item_var,
                    state: dict[str, Any] = checkbox_visibility_state,
                    show_badge: Any = show_image_size_badge,
                    hide_badge: Any = hide_image_size_badge,
                ) -> None:
                    try:
                        selected = _sync_tile_checkbox_style(cb, var, state)
                        pointer_over_image = _pointer_is_over_tile_image_area(image_area)
                        if pointer_over_image:
                            show_badge()
                        else:
                            hide_badge()
                        should_show = bool(selected) or pointer_over_image
                        if should_show:
                            _place_tile_checkbox(cb, state)
                        else:
                            _hide_tile_checkbox(cb, state)
                    except Exception:
                        pass

                def toggle_item_from_checkbox(_event: Any = None, resource_id: str = item.resource_id, var: Any = item_var) -> str:
                    try:
                        toggle_item(resource_id, var)
                        refresh_tile_checkbox_visibility()
                    except Exception:
                        pass
                    return "break"

                checkbox.bind("<Button-1>", toggle_item_from_checkbox, add="+")
                try:
                    item_var.trace_add("write", lambda *_args, refresh=refresh_tile_checkbox_visibility: refresh())
                except Exception:
                    pass

                if bool(item_var.get()):
                    refresh_tile_checkbox_visibility()
                else:
                    checkbox.place_forget()
                    checkbox_visibility_state["visible"] = False
                tile_checkbox_refreshers.append(refresh_tile_checkbox_visibility)

                def refresh_rendered_tile(
                    updated_item: Any = item,
                    card: Any = item_card,
                    var: Any = item_var,
                    preview_widget: Any = preview_label,
                    image_area: Any = preview_box,
                    badge: Any = image_size_badge,
                    refresh_checkbox: Any = refresh_tile_checkbox_visibility,
                ) -> None:
                    try:
                        selected = updated_item.resource_id in selected_ids
                        var.set(selected)
                        warning_now = str(getattr(updated_item, "warning", "") or "").lower()
                        status_now = str(getattr(updated_item, "status", "") or "").lower()
                        needs_review_now = bool(warning_now or "review" in status_now)
                        if resource_kind == RESOURCE_KIND_VIDEO_AUDIO:
                            serious_review_markers = ("error", "failed", "blocked", "unsupported", "drm", "permission", "denied", "missing")
                            needs_review_now = any(marker in warning_now or marker in status_now for marker in serious_review_markers)
                        card.configure(
                            border_width=2 if selected else (1 if needs_review_now else 0),
                            border_color=COLORS["accent"] if selected else ("#ff5d73" if needs_review_now else COLORS["border"]),
                        )
                        resource_id_now = str(getattr(updated_item, "resource_id", "") or "")
                        hover_owns_preview = (
                            resource_kind == RESOURCE_KIND_VIDEO_AUDIO
                            and (
                                resource_id_now in video_hover_active_resource_ids
                                or _video_hover_surface_has_pointer(resource_id_now)
                                or _pointer_inside_widget(image_area)
                            )
                        )
                        # V79I: a same-id render refresh is still allowed to update
                        # card borders/counts, but it must not repaint the preview
                        # label while hover playback owns that label.  The V79H
                        # recording still showed a visible jump when late video
                        # discovery/long-frame results refreshed the tile during
                        # playback.
                        if not hover_owns_preview:
                            new_preview = _image_preview_for_item(updated_item)
                            if new_preview is not None:
                                preview_widget.configure(text="", image=new_preview)
                            else:
                                preview_widget.configure(
                                    text=_media_placeholder_text_for_item(updated_item),
                                    image=None,
                                    font=ctk.CTkFont(size=_media_placeholder_font_size(updated_item), weight="bold"),
                                )
                        if badge is not None:
                            badge.configure(text=(f"{updated_item.width}x{updated_item.height}" if updated_item.width and updated_item.height else "size unknown"))
                        refresh_checkbox()
                    except Exception:
                        pass

                rendered_tile_refreshers_by_id[item.resource_id] = refresh_rendered_tile

                name_text = f"{item.display_name or item.resource_id} ({item.extension or item.media_type or 'resource'})"
                variant_group = video_variant_group_members_by_rep_id.get(str(item.resource_id), ())
                if len(variant_group) > 1:
                    name_text = f"{name_text} · {len(variant_group)} qualities"
                if item.duration_seconds:
                    name_text = f"{name_text}  {item.duration_seconds:g}s"
                if len(name_text) > 30:
                    name_text = name_text[:27] + "..."
                name_label = ctk.CTkLabel(
                    item_card,
                    text=name_text,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=COLORS["text_primary"],
                    anchor="w",
                    cursor="hand2",
                )
                name_label.grid(row=1, column=0, sticky="w", padx=10, pady=(2, 0))
                name_label.bind("<Button-1>", lambda _event, rid=item.resource_id, var=item_var: toggle_item(rid, var), add="+")
                bind_image_detail_hover(name_label, item)
                for hover_widget in (preview_box, preview_label, checkbox):
                    hover_widget.bind("<Enter>", refresh_tile_checkbox_visibility, add="+")
                    hover_widget.bind("<Motion>", refresh_tile_checkbox_visibility, add="+")
                    hover_widget.bind("<Leave>", refresh_tile_checkbox_visibility, add="+")
                for boundary_widget in (item_card, name_label):
                    boundary_widget.bind("<Enter>", refresh_tile_checkbox_visibility, add="+")
                    boundary_widget.bind("<Leave>", refresh_tile_checkbox_visibility, add="+")

            tile_checkbox_watchdog: dict[str, Any] = {"after_id": None}

            def _refresh_all_tile_checkbox_visibility(_event: Any = None) -> None:
                for refresh_checkbox in tile_checkbox_refreshers:
                    try:
                        refresh_checkbox()
                    except Exception:
                        pass

            def _run_tile_checkbox_watchdog() -> None:
                try:
                    _refresh_all_tile_checkbox_visibility()
                    tile_checkbox_watchdog["after_id"] = window.after(120, _run_tile_checkbox_watchdog)
                except Exception:
                    tile_checkbox_watchdog["after_id"] = None

            try:
                tile_checkbox_watchdog["after_id"] = window.after(120, _run_tile_checkbox_watchdog)
            except Exception:
                _refresh_all_tile_checkbox_visibility()

        status_label = ctk.CTkLabel(
            window,
            text="0 selected",
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=11),
        )
        status_label.pack(anchor="w", padx=16)

        def current_state() -> Any:
            if resource_kind == RESOURCE_KIND_VIDEO_AUDIO and row.adapter_id not in {"youtube", "twitter_x"}:
                selected = tuple(
                    resource_id
                    for resource_id in (
                        str(getattr(_video_variant_selected_item_for_rep(item), "resource_id", "") or "")
                        for item in active_state.resources
                        if item.resource_id in selected_ids
                    )
                    if resource_id
                )
            else:
                selected = tuple(
                    item.resource_id for item in state.resources if item.resource_id in selected_ids
                )
            return state.__class__(
                source_row_id=state.source_row_id,
                resource_kind=state.resource_kind,
                resources=state.resources,
                selected_resource_ids=selected,
                committed_resource_ids=state.committed_resource_ids,
            )

        def refresh_count() -> None:
            selected_count = current_state().selection_count
            if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"}:
                shown_count = len(getattr(active_state, "resources", ()) or ())
                hidden_text = f" · {hidden_candidate_count} hidden" if hidden_candidate_count else ""
                loading_text = f" · {thumbnail_preview_loading_count} loading" if thumbnail_preview_loading_count else ""
                status_label.configure(text=f"{selected_count} selected · {shown_count} shown{hidden_text}{loading_text}")
            elif resource_kind == RESOURCE_KIND_VIDEO_AUDIO and row.adapter_id not in {"youtube", "twitter_x"}:
                shown_count = len(getattr(active_state, "resources", ()) or ())
                grouped_text = f" · {video_grouped_variant_hidden_count} grouped variant(s)" if video_grouped_variant_hidden_count else ""
                status_label.configure(text=f"{selected_count} selected · {shown_count} shown{grouped_text}")
            else:
                status_label.configure(text=f"{selected_count} selected")

        def sync_visible_checkboxes() -> None:
            for item in active_state.resources:
                var = vars_by_id.get(item.resource_id)
                if var is None:
                    continue
                try:
                    var.set(item.resource_id in selected_ids)
                except Exception:
                    pass

        def select_all() -> None:
            selected_state = select_all_resources(active_state)
            selected_ids.update(selected_state.selected_resource_ids)
            sync_visible_checkboxes()
            refresh_count()

        def clear_all() -> None:
            clear_resource_selection(active_state)
            for item in active_state.resources:
                selected_ids.discard(item.resource_id)
            sync_visible_checkboxes()
            refresh_count()

        def _queue_image_discovery_result(kind: str, discovery: Any = None, error_text: str = "", show_messages: bool = True) -> None:
            try:
                with image_discovery_results_lock:
                    image_discovery_results.append((kind, discovery, error_text, show_messages))
            except Exception:
                pass

        def _apply_webpage_image_discovery_result(discovery: Any, *, show_messages: bool = True) -> None:
            nonlocal row, state, active_state
            if not discovery.resources:
                warning_text = "; ".join(discovery.warnings) if discovery.warnings else "No image candidates were found."
                if show_messages:
                    show_image_dialog_notice("Image discovery", warning_text)
                self.log_message(f"Webpage image discovery found no selectable images for {row.domain}: {warning_text}", "warning")
                return
            cache_key = _webpage_image_discovery_cache_key(row)
            if cache_key:
                try:
                    webpage_image_discovery_cache_by_url[cache_key] = discovery
                    while len(webpage_image_discovery_cache_by_url) > webpage_image_discovery_cache_limit:
                        webpage_image_discovery_cache_by_url.pop(next(iter(webpage_image_discovery_cache_by_url)))
                except Exception:
                    logger.debug("Could not update webpage image discovery cache.", exc_info=True)
            previous_resource_urls = tuple((item.resource_id, item.reference_url or item.canonical_url) for item in state.resources)
            incoming_resource_urls = tuple((item.resource_id, item.reference_url or item.canonical_url) for item in discovery.resources)
            if previous_resource_urls != incoming_resource_urls:
                thumbnail_images_by_id.clear()
                thumbnail_hidden_resource_ids.clear()
                thumbnail_preview_status_by_id.clear()
            row = replace(row, image_resources=discovery.resources)
            for index, existing_row in enumerate(self.source_resource_rows):
                if existing_row.row_id == row.row_id:
                    self.source_resource_rows[index] = row
                    break
            state = resource_dialog_state_for_row(
                row,
                resource_kind,
                committed_resource_ids=tuple(selected_ids),
            )
            selected_ids.intersection_update(item.resource_id for item in state.resources)
            render_resource_list()
            refresh_count()
            try:
                self._refresh_source_resource_rows()
            except Exception:
                logger.debug("Could not refresh source rows after image discovery.", exc_info=True)
            self.log_message(
                (
                    f"Discovered {len(discovery.resources)} webpage image candidate(s) "
                    f"from {row.domain}; discovery_method={getattr(discovery, 'network_actions_performed', 'unknown')}; "
                    "preview thumbnails are probed in the background; "
                    "default view shows only candidates that successfully preview; "
                    "hidden/no-preview candidates stay hidden unless Show hidden is enabled; "
                    "candidate lists and previews are cached/prefetched for repeated opens; "
                    "visible rendering is capped and diff-refreshed for responsiveness; "
                    "downloads performed: none."
                ),
                "success",
            )

        def _ensure_image_discovery_result_pump() -> None:
            nonlocal image_discovery_thread_active, image_discovery_result_after_id
            if image_discovery_result_after_id is not None:
                return

            def _drain_image_discovery_results() -> None:
                nonlocal image_discovery_thread_active, image_discovery_result_after_id
                image_discovery_result_after_id = None
                queued: list[tuple[str, Any, str, bool]] = []
                try:
                    with image_discovery_results_lock:
                        queued = list(image_discovery_results)
                        image_discovery_results.clear()
                except Exception:
                    queued = []
                for kind, discovery, error_text, notify_user in queued:
                    if kind == "success":
                        _apply_webpage_image_discovery_result(discovery, show_messages=notify_user)
                    elif kind == "failed":
                        if notify_user:
                            show_image_dialog_notice("Image discovery failed", error_text or "Unknown image discovery failure.")
                        self.log_message(f"Webpage image discovery failed: {error_text}", "warning")
                    elif kind == "done":
                        image_discovery_thread_active = False
                        try:
                            if refresh_images_button is not None:
                                refresh_images_button.configure(state="normal", text="Refresh images")
                        except Exception:
                            pass
                should_continue = image_discovery_thread_active
                try:
                    with image_discovery_results_lock:
                        should_continue = should_continue or bool(image_discovery_results)
                except Exception:
                    pass
                if should_continue:
                    try:
                        image_discovery_result_after_id = window.after(90, _drain_image_discovery_results)
                    except Exception:
                        image_discovery_result_after_id = None

            try:
                image_discovery_result_after_id = window.after(90, _drain_image_discovery_results)
            except Exception:
                image_discovery_result_after_id = None

        def discover_page_images(*, show_messages: bool = True) -> None:
            nonlocal image_discovery_thread_active, refresh_images_button
            if resource_kind != RESOURCE_KIND_IMAGE:
                return
            if row.adapter_id in {"youtube", "twitter_x"}:
                show_image_dialog_notice(
                    "Image discovery",
                    "This source type uses its own media workflow.",
                )
                return
            if image_discovery_thread_active:
                self.log_message("Webpage image discovery is already running for this source row.", "muted")
                return
            cache_key = _webpage_image_discovery_cache_key(row)
            if not show_messages and cache_key:
                cached_discovery = webpage_image_discovery_cache_by_url.get(cache_key)
                if cached_discovery is not None:
                    self.log_message(f"Using cached webpage image candidate list for {row.domain}; Refresh images forces a rescan.", "muted")
                    _apply_webpage_image_discovery_result(cached_discovery, show_messages=False)
                    return
            image_discovery_thread_active = True
            try:
                if refresh_images_button is not None:
                    refresh_images_button.configure(state="disabled", text=("Refreshing..." if active_state.resources else "Discovering..."))
                if not active_state.resources:
                    for child in list_frame.winfo_children():
                        child.destroy()
                    ctk.CTkLabel(
                        list_frame,
                        text="Discovering image candidates in the background...",
                        text_color=COLORS["text_muted"],
                        wraplength=640,
                        justify="left",
                    ).grid(row=0, column=0, sticky="w", padx=8, pady=8)
                refresh_count()
            except Exception:
                pass
            _ensure_image_discovery_result_pump()
            row_snapshot = row
            notify_user = bool(show_messages)

            def _worker() -> None:
                try:
                    discovery = discover_webpage_images_for_row(row_snapshot)
                except Exception as exc:
                    _queue_image_discovery_result("failed", error_text=str(exc), show_messages=notify_user)
                else:
                    _queue_image_discovery_result("success", discovery=discovery, show_messages=notify_user)
                finally:
                    _queue_image_discovery_result("done", show_messages=notify_user)

            threading.Thread(target=_worker, daemon=True).start()

        def _video_source_row_prefetch_is_inflight(cache_key: str) -> bool:
            if not cache_key:
                return False
            try:
                return cache_key in self.__dict__.setdefault("webpage_video_discovery_prefetch_inflight", set())
            except Exception:
                return False

        def _schedule_video_prefetch_cache_poll(cache_key: str, *, attempts: int = 60, delay_ms: int = 250) -> None:
            # V78Q avoids launching a duplicate rendered/browser probe from the
            # dialog while the source-row prefetch is already doing the same work.
            # The dialog paints static candidates immediately and polls the shared
            # cache for the full 5-candidate result instead.
            nonlocal video_discovery_cache_poll_after_id
            if not cache_key or video_discovery_cache_poll_after_id is not None:
                return

            def _poll(remaining: int) -> None:
                nonlocal video_discovery_cache_poll_after_id
                video_discovery_cache_poll_after_id = None
                cached_discovery = webpage_video_discovery_cache_by_url.get(cache_key)
                prefetch_inflight = _video_source_row_prefetch_is_inflight(cache_key)
                if cached_discovery is not None:
                    cached_count = len(getattr(cached_discovery, "resources", ()) or ())
                    current_count = len(getattr(state, "resources", ()) or ())
                    # V78S: a static-first dialog pass may put the quick 3-candidate
                    # result in the shared cache while the source-row rendered/browser
                    # prefetch is still working toward the fuller 5-candidate result.
                    # Do not stop polling just because that early static cache entry
                    # exists; wait for a richer cached result or for prefetch to finish.
                    if cached_count > current_count or not prefetch_inflight:
                        _apply_webpage_video_discovery_result(cached_discovery, show_messages=False)
                        return
                if remaining <= 0 or not prefetch_inflight:
                    return
                try:
                    video_discovery_cache_poll_after_id = window.after(delay_ms, lambda: _poll(remaining - 1))
                except Exception:
                    video_discovery_cache_poll_after_id = None

            try:
                video_discovery_cache_poll_after_id = window.after(delay_ms, lambda: _poll(attempts))
            except Exception:
                video_discovery_cache_poll_after_id = None

        def _queue_video_discovery_result(kind: str, discovery: Any = None, error_text: str = "", show_messages: bool = True) -> None:
            try:
                with video_discovery_results_lock:
                    video_discovery_results.append((kind, discovery, error_text, show_messages))
            except Exception:
                pass

        def _merged_active_and_fast_video_discovery(discovery: Any) -> Any:
            existing_resources = tuple(getattr(active_state, "resources", ()) or ())
            new_resources = tuple(getattr(discovery, "resources", ()) or ())
            if not existing_resources:
                return discovery
            by_url: dict[str, Any] = {}
            merged: list[Any] = []
            for candidate in (*existing_resources, *new_resources):
                url_key = str(getattr(candidate, "reference_url", "") or getattr(candidate, "canonical_url", "") or getattr(candidate, "resource_id", "") or "")
                if not url_key or url_key in by_url:
                    continue
                by_url[url_key] = candidate
                merged.append(candidate)
            if len(merged) == len(new_resources) and tuple(merged) == new_resources:
                return discovery
            try:
                return replace(discovery, resources=tuple(merged))
            except Exception:
                return discovery

        def _start_fast_rendered_video_probe_once() -> None:
            nonlocal video_fast_rendered_probe_started, video_fast_rendered_probe_active
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return
            if video_fast_rendered_probe_started:
                return
            if row.adapter_id in {"youtube", "twitter_x"}:
                return
            video_fast_rendered_probe_started = True
            video_fast_rendered_probe_active = True

            def _worker() -> None:
                started = time.perf_counter()
                try:
                    discovery = discover_fast_rendered_webpage_videos_for_row(
                        row,
                        timeout_ms=3500,
                        max_candidates=8,
                    )
                    if getattr(discovery, "resources", ()):
                        elapsed_ms = int(max(0.0, (time.perf_counter() - video_dialog_started_at) * 1000.0))
                        _queue_video_discovery_result("fast_success", discovery=discovery, error_text=str(elapsed_ms), show_messages=False)
                    else:
                        warning_text = "; ".join(getattr(discovery, "warnings", ()) or ())
                        if warning_text:
                            logger.debug("Fast rendered media probe found no direct video candidates: %s", warning_text)
                except Exception as exc:
                    logger.debug("Fast rendered media probe failed: %s", exc, exc_info=True)
                finally:
                    # Keep the pump alive long enough to drain fast_success even
                    # when the normal discovery worker has already completed.
                    _queue_video_discovery_result("fast_done", error_text=str(int((time.perf_counter() - started) * 1000.0)), show_messages=False)

            _ensure_video_discovery_result_pump()
            threading.Thread(target=_worker, daemon=True).start()

        def _apply_webpage_video_discovery_result(discovery: Any, *, show_messages: bool = True) -> None:
            nonlocal row, state
            if not getattr(discovery, "resources", ()):  # discovery-only path, no downloads
                warning_text = "; ".join(getattr(discovery, "warnings", ()) or ()) or "No video/audio candidates were found."
                if show_messages:
                    show_image_dialog_notice("Video/audio discovery", warning_text)
                self.log_message(f"Webpage video/audio discovery found no selectable media for {row.domain}: {warning_text}", "warning")
                return
            cache_key = _webpage_video_discovery_cache_key(row)
            if cache_key:
                try:
                    webpage_video_discovery_cache_by_url[cache_key] = discovery
                    while len(webpage_video_discovery_cache_by_url) > webpage_video_discovery_cache_limit:
                        webpage_video_discovery_cache_by_url.pop(next(iter(webpage_video_discovery_cache_by_url)))
                except Exception:
                    logger.debug("Could not update webpage video discovery cache.", exc_info=True)
            row = replace(row, video_audio_resources=tuple(discovery.resources))
            for index, existing_row in enumerate(self.source_resource_rows):
                if existing_row.row_id == row.row_id:
                    self.source_resource_rows[index] = row
                    break
            state = resource_dialog_state_for_row(
                row,
                resource_kind,
                committed_resource_ids=tuple(selected_ids),
            )
            selected_ids.intersection_update(item.resource_id for item in state.resources)
            render_resource_list()
            refresh_count()
            try:
                self._refresh_source_resource_rows()
            except Exception:
                logger.debug("Could not refresh source rows after video discovery.", exc_info=True)
            summary = getattr(discovery, "summary", {}) or {}
            self.log_message(
                (
                    f"Discovered {len(discovery.resources)} webpage video/audio candidate(s) "
                    f"from {row.domain}; discovery_method={summary.get('discovery_method', 'merged_static_rendered_webpage_video_discovery')}; "
                    f"route_preference={summary.get('route_preference', 'try_jdownloader_api3128_before_yt_dlp')}; "
                    f"recommended_backend={summary.get('recommended_backend_id', 'unknown')}; "
                    "candidate list is cached/prefetched for repeated opens; duplicate direct-video renditions are grouped in the dialog; downloads performed: none."
                ),
                "success",
            )

        def _ensure_video_discovery_result_pump() -> None:
            nonlocal video_discovery_thread_active, video_discovery_result_after_id, video_static_first_followup_pending, video_fast_rendered_probe_active
            if video_discovery_result_after_id is not None:
                return

            def _drain_video_discovery_results() -> None:
                nonlocal video_discovery_thread_active, video_discovery_result_after_id, video_static_first_followup_pending, video_fast_rendered_probe_active
                video_discovery_result_after_id = None
                queued: list[tuple[str, Any, str, bool]] = []
                try:
                    with video_discovery_results_lock:
                        queued = list(video_discovery_results)
                        video_discovery_results.clear()
                except Exception:
                    queued = []
                for kind, discovery, error_text, notify_user in queued:
                    if kind == "success":
                        _apply_webpage_video_discovery_result(discovery, show_messages=notify_user)
                    elif kind == "fast_success":
                        fast_discovery = _merged_active_and_fast_video_discovery(discovery)
                        _apply_webpage_video_discovery_result(fast_discovery, show_messages=False)
                        self.log_message(
                            f"Video dialog fast rendered media probe after {error_text or '0'} ms; candidates={len(getattr(fast_discovery, 'resources', ()) or ())}",
                            "muted",
                        )
                    elif kind == "fast_done":
                        video_fast_rendered_probe_active = False
                    elif kind == "failed":
                        if notify_user:
                            show_image_dialog_notice("Video/audio discovery failed", error_text or "Unknown video/audio discovery failure.")
                        self.log_message(f"Webpage video/audio discovery failed: {error_text}", "warning")
                    elif kind == "done":
                        video_discovery_thread_active = False
                        try:
                            if refresh_videos_button is not None:
                                refresh_videos_button.configure(state="normal", text="Refresh videos")
                        except Exception:
                            pass
                        if video_static_first_followup_pending:
                            video_static_first_followup_pending = False
                            _start_fast_rendered_video_probe_once()
                            cache_key = _webpage_video_discovery_cache_key(row)
                            if _video_source_row_prefetch_is_inflight(cache_key):
                                _schedule_video_prefetch_cache_poll(cache_key)
                            else:
                                try:
                                    window.after(90, lambda: discover_page_videos(
                                        show_messages=False,
                                        run_rendered_probe=True,
                                        rendered_probe_timeout_ms=12000,
                                        force_refresh=True,
                                        followup_full_probe=False,
                                    ))
                                except Exception:
                                    logger.debug("Could not schedule rendered video discovery follow-up after static first paint.", exc_info=True)
                should_continue = video_discovery_thread_active or video_fast_rendered_probe_active
                try:
                    with video_discovery_results_lock:
                        should_continue = should_continue or bool(video_discovery_results)
                except Exception:
                    pass
                if should_continue:
                    try:
                        video_discovery_result_after_id = window.after(90, _drain_video_discovery_results)
                    except Exception:
                        video_discovery_result_after_id = None

            try:
                video_discovery_result_after_id = window.after(90, _drain_video_discovery_results)
            except Exception:
                video_discovery_result_after_id = None

        def discover_page_videos(
            *,
            show_messages: bool = True,
            run_rendered_probe: bool = True,
            rendered_probe_timeout_ms: int = 12000,
            force_refresh: bool = False,
            followup_full_probe: bool = False,
        ) -> None:
            nonlocal video_discovery_thread_active, refresh_videos_button, video_static_first_followup_pending
            if resource_kind != RESOURCE_KIND_VIDEO_AUDIO:
                return
            if row.adapter_id in {"youtube", "twitter_x"}:
                show_image_dialog_notice(
                    "Video/audio discovery",
                    "This source type uses its own media workflow.",
                )
                return
            if video_discovery_thread_active:
                self.log_message("Webpage video/audio discovery is already running for this source row.", "muted")
                if followup_full_probe:
                    video_static_first_followup_pending = True
                return
            cache_key = _webpage_video_discovery_cache_key(row)
            if not force_refresh and run_rendered_probe and not show_messages and cache_key:
                cached_discovery = webpage_video_discovery_cache_by_url.get(cache_key)
                if cached_discovery is not None:
                    self.log_message(f"Using cached webpage video/audio candidate list for {row.domain}; Refresh videos forces a rescan.", "muted")
                    _apply_webpage_video_discovery_result(cached_discovery, show_messages=False)
                    return
            video_discovery_thread_active = True
            try:
                if refresh_videos_button is not None:
                    refresh_videos_button.configure(
                        state="disabled",
                        text=("Refreshing..." if active_state.resources else ("Quick scan..." if not run_rendered_probe else "Discovering...")),
                    )
                if not active_state.resources:
                    for child in list_frame.winfo_children():
                        child.destroy()
                    ctk.CTkLabel(
                        list_frame,
                        text=("Quick-scanning static video/audio candidates before the slower rendered browser probe..." if not run_rendered_probe else "Discovering video/audio candidates in the background..."),
                        text_color=COLORS["text_muted"],
                        wraplength=640,
                        justify="left",
                    ).grid(row=0, column=0, sticky="w", padx=8, pady=8)
                refresh_count()
            except Exception:
                pass
            _ensure_video_discovery_result_pump()
            row_snapshot = row
            notify_user = bool(show_messages)
            video_static_first_followup_pending = bool(followup_full_probe)

            def _worker() -> None:
                try:
                    discovery = discover_webpage_videos_for_row(
                        row_snapshot,
                        fetch_static_html=True,
                        run_rendered_probe=run_rendered_probe,
                        rendered_probe_timeout_ms=rendered_probe_timeout_ms,
                    )
                except Exception as exc:
                    _queue_video_discovery_result("failed", error_text=str(exc), show_messages=notify_user)
                else:
                    _queue_video_discovery_result("success", discovery=discovery, show_messages=notify_user)
                finally:
                    _queue_video_discovery_result("done", show_messages=notify_user)

            threading.Thread(target=_worker, daemon=True).start()

        def download_selected_resources() -> None:
            selected_state = current_state()
            self.source_resource_selections[row.row_id] = selected_state.selected_resource_ids
            if not selected_state.selected_resource_ids:
                self.log_message("No media resources were selected for download.", "muted")
                return

            if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"}:
                cached_files, missing_resource_ids = self._cached_webpage_image_session_paths(
                    row=row,
                    selected_resource_ids=selected_state.selected_resource_ids,
                )
                result = None
                if missing_resource_ids:
                    missing_state = selected_state.__class__(
                        source_row_id=selected_state.source_row_id,
                        resource_kind=selected_state.resource_kind,
                        resources=selected_state.resources,
                        selected_resource_ids=missing_resource_ids,
                        committed_resource_ids=selected_state.committed_resource_ids,
                    )
                    result = download_selected_webpage_images(
                        row=row,
                        state=missing_state,
                        output_dir=self._webpage_image_session_download_root(),
                        filters=current_filters(),
                    )
                    self._remember_webpage_image_session_downloads(
                        row=row,
                        selected_resource_ids=missing_resource_ids,
                        downloaded_files=tuple(result.downloaded_files),
                        manifest_json=result.manifest_json,
                    )
                downloaded_files = tuple(result.downloaded_files) if result is not None else ()
                files_for_intake = tuple(cached_files) + downloaded_files
                if files_for_intake:
                    intake_result = self._intake_session_files(
                        files_for_intake,
                        select_first=False,
                        source_label="downloaded webpage image",
                    )
                    try:
                        self._refresh_session_files_list()
                        self._refresh_export_entry_state()
                        self.update_idletasks()
                    except Exception:
                        logger.debug("Could not refresh FILES after webpage image download.", exc_info=True)
                    added_count = len(getattr(intake_result, "added_paths", ()) or ())
                    duplicate_count = len(getattr(intake_result, "duplicate_paths", ()) or ())
                    visible_count = len(getattr(self, "session_files", ()) or ())
                    self.log_message(
                        (
                            "Downloaded webpage image FILES refresh: "
                            f"visible_entries={visible_count}; added={added_count}; duplicates={duplicate_count}; "
                            f"reused={len(cached_files)}."
                        ),
                        "success" if added_count or duplicate_count else "muted",
                    )
                newly_downloaded = result.resources_downloaded if result is not None else 0
                failed_count = result.resources_failed if result is not None else 0
                manifest_path = result.manifest_json if result is not None else "cached session files"
                if failed_count or (not newly_downloaded and not cached_files):
                    show_image_dialog_notice(
                        "Webpage image download",
                        result.message if result is not None else "No webpage images were downloaded.",
                    )
                self.log_message(
                    (
                        f"Webpage image download: selected={len(selected_state.selected_resource_ids)}; "
                        f"new_downloads={newly_downloaded}; reused={len(cached_files)}; failed={failed_count}; "
                        f"session_temp={self._webpage_image_session_download_root()}; "
                        f"manifest={manifest_path or 'not written'}"
                    ),
                    "success" if newly_downloaded or cached_files else "warning",
                )
                return

            if row.adapter_id != "msn":
                preview = build_selected_media_preservation_preview(row, selected_state)
                messagebox.showinfo("Media selection preview", preview.message)
                self.log_message(
                    (
                        f"Media selection preview retained for {row.adapter_id}; "
                        f"records={preview.selected_count}; network/download/recording actions performed: none."
                    ),
                    "muted",
                )
                return

            rendered_html = filedialog.askopenfilename(
                parent=window,
                title="Select rendered MSN article HTML",
                filetypes=(("HTML files", "*.html *.htm"), ("All files", "*.*")),
            )
            if not rendered_html:
                self.log_message("MSN media download cancelled before rendered HTML selection.", "muted")
                return

            output_dir = filedialog.askdirectory(
                parent=window,
                title="Choose folder for MSN media inventory/download results",
            )
            if not output_dir:
                self.log_message("MSN media download cancelled before output folder selection.", "muted")
                return

            review = run_source_media_gui_download(
                row=row,
                state=selected_state,
                rendered_html_path=rendered_html,
                output_dir=output_dir,
                dry_run=True,
            )
            if review.status != MEDIA_GUI_DOWNLOAD_STATUS_READY:
                messagebox.showinfo("MSN media review", review.message)
                self.log_message(review.message.replace("\n", " "), "warning")
                return

            hostnames = review.selected_direct_hostnames
            if hostnames:
                host_lines = "\n".join(f"- {host}" for host in hostnames)
                allow_download = messagebox.askyesno(
                    "Confirm media download hosts",
                    (
                        "The selected MSN media candidates are direct downloadable resources.\n\n"
                        "Allow downloads from these hostnames?\n"
                        f"{host_lines}\n\n"
                        "Choosing No keeps the inventory/review files only."
                    ),
                )
            else:
                allow_download = False

            result = run_source_media_gui_download(
                row=row,
                state=selected_state,
                rendered_html_path=rendered_html,
                output_dir=output_dir,
                allowed_hostnames=hostnames if allow_download else (),
                dry_run=not allow_download,
            )
            title = "MSN media download" if allow_download else "MSN media review"
            messagebox.showinfo(title, result.message)
            self.log_message(
                (
                    f"{title}: discovered={result.resources_discovered}; "
                    f"selected={result.resources_selected}; downloaded={result.resources_downloaded}; "
                    f"summary={result.summary_markdown or 'not written'}"
                ),
                "success" if result.resources_downloaded else "muted",
            )

        def on_filter_changed(*_args: object) -> None:
            render_resource_list()
            refresh_count()

        for filter_var in (url_filter_var, text_filter_var, min_width_var, min_height_var):
            filter_var.trace_add("write", on_filter_changed)

        media_action_hint = ctk.CTkLabel(
            window,
            text=(
                "Images are scanned automatically when this window opens. Select image tiles, then Download selected to add them to this session's temporary FILES area. Hover a file name for source details; hover an image square for dimensions; use EXPORT to choose a final output folder."
                if resource_kind == RESOURCE_KIND_IMAGE
                else "Video/audio candidates are discovered with static + rendered probes and cached/prefetched for repeated opens. JDownloader/API3128 remains the preferred download route; Review selected still performs no generic download."
            ),
            text_color=COLORS["text_muted"],
            font=ctk.CTkFont(size=10),
            wraplength=590,
            justify="left",
        )
        media_action_hint.pack(side="bottom", anchor="w", padx=16, pady=(0, 4))

        button_row = ctk.CTkFrame(window, fg_color="transparent")
        button_row.pack(side="bottom", fill="x", padx=16, pady=(8, 14))
        if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"}:
            refresh_images_button = ctk.CTkButton(
                button_row,
                text="Refresh images",
                width=128,
                command=lambda: discover_page_images(show_messages=True),
            )
            refresh_images_button.pack(side="left", padx=(0, 8))
        if resource_kind == RESOURCE_KIND_VIDEO_AUDIO and row.adapter_id not in {"youtube", "twitter_x"}:
            refresh_videos_button = ctk.CTkButton(
                button_row,
                text="Refresh videos",
                width=128,
                command=lambda: discover_page_videos(show_messages=True),
            )
            refresh_videos_button.pack(side="left", padx=(0, 8))
        ctk.CTkButton(button_row, text="Select all", width=96, command=select_all).pack(side="left")
        ctk.CTkButton(button_row, text="Clear all", width=90, command=clear_all).pack(side="left", padx=(8, 0))
        ctk.CTkButton(button_row, text="Cancel", width=90, command=window.destroy).pack(side="right")
        ctk.CTkButton(button_row, text=("Download selected" if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"} else "Review selected"), width=152, command=download_selected_resources).pack(side="right", padx=(0, 8))
        if resource_kind == RESOURCE_KIND_IMAGE and row.adapter_id not in {"youtube", "twitter_x"} and not state.resources:
            cached_discovery_on_open = webpage_image_discovery_cache_by_url.get(_webpage_image_discovery_cache_key(row))
            if cached_discovery_on_open is not None:
                _apply_webpage_image_discovery_result(cached_discovery_on_open, show_messages=False)
            else:
                render_resource_list()
                refresh_count()
                window.after(80, lambda: discover_page_images(show_messages=False))
        elif resource_kind == RESOURCE_KIND_VIDEO_AUDIO and row.adapter_id not in {"youtube", "twitter_x"} and not state.resources:
            cached_video_discovery_on_open = webpage_video_discovery_cache_by_url.get(_webpage_video_discovery_cache_key(row))
            if cached_video_discovery_on_open is not None:
                _apply_webpage_video_discovery_result(cached_video_discovery_on_open, show_messages=False)
            else:
                render_resource_list()
                refresh_count()
                cache_key_on_open = _webpage_video_discovery_cache_key(row)
                source_prefetch_inflight_on_open = _video_source_row_prefetch_is_inflight(cache_key_on_open)
                if source_prefetch_inflight_on_open:
                    _schedule_video_prefetch_cache_poll(cache_key_on_open)
                window.after(80, lambda: discover_page_videos(
                    show_messages=False,
                    run_rendered_probe=False,
                    rendered_probe_timeout_ms=0,
                    force_refresh=True,
                    followup_full_probe=not source_prefetch_inflight_on_open,
                ))
        else:
            render_resource_list()
            refresh_count()

    def _on_discussion_source_selected(self, selected_label: str) -> None:
        self._store_current_source_screenshot_preferences()
        mapping = self.__dict__.get("_discussion_source_label_to_id", {})
        self.selected_discussion_source_id = mapping.get(selected_label, "")
        self._load_source_screenshot_preferences(self.selected_discussion_source_id)
        self._refresh_discussion_source_controls()

    def _on_discussion_mode_changed(self) -> None:
        self._store_current_source_screenshot_preferences()
        self._refresh_discussion_source_controls()

    def _store_current_source_screenshot_preferences(self) -> None:
        row_id = self.__dict__.get("selected_discussion_source_id", "")
        if not row_id:
            return
        self.source_screenshot_preferences[row_id] = {
            "webpage": bool(self.extract_webpage_var.get()),
            "webpage_screenshot": bool(self.webpage_screenshot_var.get()),
            "comments_screenshot": bool(self.comments_screenshot_var.get()),
            "livechat_screenshot": bool(self.livechat_screenshot_var.get()),
        }

    def _load_source_screenshot_preferences(self, row_id: str) -> None:
        prefs = self.source_screenshot_preferences.get(row_id, {})
        self.extract_webpage_var.set(bool(prefs.get("webpage", False)))
        self.webpage_screenshot_var.set(bool(prefs.get("webpage_screenshot", False)))
        self.comments_screenshot_var.set(bool(prefs.get("comments_screenshot", False)))
        self.livechat_screenshot_var.set(bool(prefs.get("livechat_screenshot", False)))

    def _refresh_discussion_source_controls(self) -> None:
        if not hasattr(self, "discussion_source_menu"):
            return
        rows = tuple(self.__dict__.get("source_resource_rows", ()))
        previous_selected_row_id = self.__dict__.get("selected_discussion_source_id", "")
        selection = build_discussion_selection_state(
            rows,
            previous_selected_row_id,
        )
        self.selected_discussion_source_id = selection.selected_row_id
        if selection.selected_row_id != previous_selected_row_id:
            self._load_source_screenshot_preferences(selection.selected_row_id)
        label_by_id = dict(selection.options)
        label_to_id = {label: row_id for row_id, label in selection.options}
        self._discussion_source_label_to_id = label_to_id
        values = list(label_to_id) or [""]
        self.discussion_source_menu.configure(values=values)
        selected_label = label_by_id.get(selection.selected_row_id, "")
        self.discussion_source_var.set(selected_label)
        has_source = bool(selection.selected_row_id)
        self.discussion_source_menu.configure(state="normal" if has_source else "disabled")
        self.fetch_button.configure(state="normal" if has_source else "disabled")
        selected_row = self._source_row_by_id(selection.selected_row_id) if has_source else None
        youtube_selected = bool(selected_row is not None and self._source_row_is_youtube(selected_row))
        if youtube_selected:
            self.extract_webpage_var.set(False)
            self.webpage_checkbox.configure(state="disabled")
            self.webpage_screenshot_checkbox.configure(state="normal")
        else:
            self.webpage_checkbox.configure(state="normal" if has_source else "disabled")
            webpage_active = bool(self.extract_webpage_var.get()) and has_source
            self.webpage_screenshot_checkbox.configure(
                state="normal" if webpage_active else "disabled"
            )
        self.comments_checkbox.configure(
            state="normal" if has_source and selection.comments_supported else "disabled"
        )
        self.live_chat_checkbox.configure(
            state="normal" if has_source and selection.livechat_supported else "disabled"
        )
        comments_active = bool(self.extract_comments_var.get()) and selection.comments_supported
        livechat_active = bool(self.extract_live_chat_var.get()) and selection.livechat_supported
        self.comments_screenshot_checkbox.configure(
            state="normal" if has_source and comments_active else "disabled"
        )
        self.livechat_screenshot_checkbox.configure(
            state="normal" if has_source and livechat_active else "disabled"
        )

    def _selected_discussion_row(self) -> SourceResourceRowState | None:
        return self._source_row_by_id(self.__dict__.get("selected_discussion_source_id", ""))

    def _set_operational_capture_status(self, text: str, level: str = "muted") -> None:
        """Expose non-executing source-capture plan state without starting workers."""
        self.last_operational_capture_status = text
        color_by_level = {
            "error": COLORS["error"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
        }
        label = getattr(self, "url_status", None)
        if label is not None and hasattr(label, "configure"):
            label.configure(text=text, text_color=color_by_level.get(level, COLORS["text_muted"]))

    def save_last_source_evidence_workflow_review_bundle(self, output_directory: str) -> Any:
        """Save the latest Source Evidence review metadata bundle to a chosen folder."""
        from source_evidence_workflow_store import write_source_evidence_workflow_review_bundle

        workflow_state = getattr(self, "last_source_evidence_workflow_state", None)
        if workflow_state is None:
            raise ValueError("No Source Evidence workflow state is available to save")
        result = write_source_evidence_workflow_review_bundle(
            workflow_state,
            output_directory,
        )
        self.last_source_evidence_workflow_review_bundle = result
        self.log_message(
            "Source evidence review bundle saved: "
            f"{result.file_count} metadata file(s), "
            "review-required and execution-gated.",
            "success",
        )
        return result

    def build_source_app_operator_controller_state(self) -> Any:
        """Return the app/operator execution controller dashboard without running live work."""
        state = build_app_operator_controller_state()
        self.last_source_app_operator_controller_state = state
        return state

    def _record_operational_capture_review_metadata(self, plan: Any) -> Any:
        """Build app-facing review/export state for an execution-gated source plan."""
        try:
            workflow_state = build_source_evidence_workflow_state(
                plan,
                package_id=f"source_evidence_review_{plan.source_row_id}",
                app_version=APP_VERSION,
            )
        except Exception as error:
            logger.exception("Could not build source evidence workflow state")
            self.last_source_evidence_workflow_error = str(error)
            self.log_message(
                "Source evidence review metadata could not be prepared; capture plan remains execution-gated.",
                "warning",
            )
            return None

        self.last_source_evidence_workflow_state = workflow_state
        self.last_operational_capture_export_connection = workflow_state.connection
        self.last_operational_capture_queue_review_store = workflow_state.queue_review_store_document
        self.last_operational_capture_review_manifest = workflow_state.review_manifest
        self.last_source_audit_dashboard_state = workflow_state.source_audit_dashboard_state
        self.last_source_app_operator_controller_state = workflow_state.source_app_operator_controller_state
        self.log_message(
            "Source evidence review metadata ready: "
            f"{workflow_state.queue_item_count} queue item(s), "
            f"{workflow_state.review_manifest_asset_count} review manifest asset(s), "
            f"{len(workflow_state.execution_gate_action_kinds)} execution-gated action(s).",
            "muted",
        )
        return workflow_state

    # =========================================================================
    # WINDOW SIZE HELPERS
    # =========================================================================

    def _bind_window_size_shortcuts(self) -> None:
        """Bind robust keyboard shortcuts for safe window size presets."""
        shortcut_map = {
            "compact": (
                "<Control-KeyPress-1>",
                "<Control-Key-1>",
                "<Control-KeyPress-KP_1>",
                "<Control-Key-KP_1>",
            ),
            "default": (
                "<Control-KeyPress-2>",
                "<Control-Key-2>",
                "<Control-KeyPress-KP_2>",
                "<Control-Key-KP_2>",
            ),
            "wide": (
                "<Control-KeyPress-3>",
                "<Control-Key-3>",
                "<Control-KeyPress-KP_3>",
                "<Control-Key-KP_3>",
            ),
        }

        for preset, sequences in shortcut_map.items():
            for sequence in sequences:
                try:
                    self.bind_all(
                        sequence,
                        lambda event, preset=preset: self._on_window_size_shortcut(event, preset),
                        add="+",
                    )
                except Exception:
                    pass

        try:
            self.bind_all("<F11>", self._on_toggle_maximized_shortcut, add="+")
        except Exception:
            pass

    def _on_window_size_shortcut(self, event, preset: str) -> str:
        """Handle Ctrl+1/2/3 size preset shortcuts."""
        self.apply_window_size_preset(preset)
        return "break"

    def _on_toggle_maximized_shortcut(self, event=None) -> str:
        """Handle F11 maximize/restore shortcut."""
        self.toggle_window_maximized()
        return "break"

    def apply_window_size_preset(self, preset: str = "default") -> None:
        """Apply a safe app window size preset without dynamic resize handlers."""
        presets = {
            "compact": (1180, 820),
            "default": (1400, 950),
            "wide": (1650, 1000),
        }

        width, height = presets.get(preset, presets["default"])

        try:
            self.state("normal")
        except Exception:
            pass

        try:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            x = max(0, int((screen_width - width) / 2))
            y = max(0, int((screen_height - height) / 2))

            self.geometry(f"{width}x{height}+{x}+{y}")
            self.minsize(1120, 760)
            self.log_message(f"Window size preset applied: {preset}", "muted")
        except Exception as error:
            logger.warning(f"Could not apply window size preset: {error}")

    def toggle_window_maximized(self) -> None:
        """Toggle maximized window state."""
        try:
            if self.state() == "zoomed":
                self.state("normal")
                self.apply_window_size_preset("default")
            else:
                self.state("zoomed")
        except Exception:
            try:
                self.attributes("-zoomed", not bool(self.attributes("-zoomed")))
            except Exception as error:
                logger.warning(f"Could not toggle maximized window: {error}")

    # =========================================================================
    # SETTINGS MANAGEMENT
    # =========================================================================

    def _load_settings(self) -> None:
        """Load settings from storage."""
        try:
            load_preferences = getattr(
                self.settings_manager,
                "load_preferences_only",
                self.settings_manager.load,
            )
            settings = load_preferences()

            api_key_entry = self.__dict__.get("api_key_entry")
            if api_key_entry is not None:
                api_key_entry.delete(0, "end")
                api_key_entry.configure(show="*")

            self.spam_filter_var.set(settings.filter_spam)
            self.spam_threshold_var.set(settings.spam_threshold)
            self._on_spam_threshold_change(settings.spam_threshold)
            self._on_spam_filter_toggle()
            self.exclude_creator_var.set(settings.exclude_creator)

            self.min_likes_entry.delete(0, "end")
            self.min_likes_entry.insert(0, str(settings.min_likes))

            # Load max comments (only if set)
            if settings.max_comments is not None:
                self.max_comments_entry.delete(0, "end")
                self.max_comments_entry.insert(0, str(settings.max_comments))

            sort_option = SortOption(settings.sort_by) if settings.sort_by else SortOption.DATE_NEWEST
            self.sort_var.set(sort_option.display_name)

            # Load filter words
            if settings.filter_words:
                self.filter_words_entry.delete(0, "end")
                self.filter_words_entry.insert(0, settings.filter_words)

            self._blacklist_patterns = settings.blacklist_patterns or ""
            self._whitelist_patterns = settings.whitelist_patterns or ""
            self._update_filter_counts()
            self._set_online_asr_provider_id(
                getattr(settings, "online_asr_provider_id", ""),
                persist=False,
            )
            self.access_keys_added_provider_ids = tuple(
                str(entry_id)
                for entry_id in getattr(
                    settings,
                    "access_keys_added_provider_ids",
                    (),
                )
                if str(entry_id or "").strip()
            )
            self.access_keys_validation_states = dict(
                getattr(settings, "access_keys_validation_states", {}) or {}
            )
            self.source_archive_auto_check_enabled = bool(
                getattr(settings, "source_archive_auto_check_enabled", True)
            )
            if self.__dict__.get("source_resource_rows"):
                self._refresh_source_resource_rows()

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def _save_settings(self) -> bool:
        """Save current settings."""
        try:
            settings = AppSettings(
                api_key="",
                filter_spam=self.spam_filter_var.get(),
                spam_threshold=self.spam_threshold_var.get(),
                exclude_creator=self.exclude_creator_var.get(),
                min_likes=self._get_min_likes(),
                max_comments=self._get_max_comments(),
                filter_words=self.filter_words_entry.get().strip(),
                sort_by=SortOption.from_display_name(self.sort_var.get()).value,
                blacklist_patterns=self._blacklist_patterns,
                whitelist_patterns=self._whitelist_patterns,
                online_asr_provider_id=self._get_online_asr_provider_id(),
                access_keys_added_provider_ids=self._get_access_keys_added_provider_ids(),
                access_keys_validation_states=dict(
                    getattr(self, "access_keys_validation_states", {}) or {}
                ),
                source_archive_auto_check_enabled=bool(
                    self.__dict__.get("source_archive_auto_check_enabled", True)
                ),
            )
            saved = self.settings_manager.save(settings)
            if not saved:
                self.log_message("Settings were not saved safely.", "error")
            return saved
        except Exception:
            logger.error("Failed to save settings safely.")
            self.log_message("Error saving settings safely.", "error")
            return False

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _get_min_likes(self) -> int:
        """Parse min likes value with validation."""
        value, warning = MinLikesValidator.parse(self.min_likes_entry.get())
        if warning:
            self.log_message(warning, "warning")
        return value

    def _get_max_comments(self) -> Optional[int]:
        """Parse max comments value with validation."""
        value, warning = MaxCommentsValidator.parse(self.max_comments_entry.get())
        if warning:
            self.log_message(warning, "warning")
        return value

    def _get_filter_words(self) -> List[str]:
        """Parse filter words into a list."""
        return WordsFilterValidator.parse(self.filter_words_entry.get())

    def _get_date_range(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get and validate date range."""
        from_date = DateValidator.parse(self.from_date_entry.get())
        to_date = DateValidator.parse(self.to_date_entry.get())

        result = DateValidator.validate_range(from_date, to_date)
        if not result:
            return None, None, result.error_message

        return from_date, to_date, None



    def _collect_activity_log_text(self) -> str:
        """Collect Activity Log text for clipboard copy."""
        stored_messages = getattr(self, "activity_log_messages", None)

        if stored_messages:
            return "\n".join(str(message).strip() for message in stored_messages if str(message).strip())

        lines = []

        try:
            children = self.log_frame.winfo_children()
        except Exception:
            children = []

        for child in children:
            try:
                text = child.cget("text")
            except Exception:
                text = ""

            text = str(text or "").strip()

            if text:
                lines.append(text)

        return "\n".join(lines).strip()

    def copy_activity_log_to_clipboard(self) -> None:
        """Copy Activity Log text to clipboard."""
        text = self._collect_activity_log_text()

        if not text:
            messagebox.showinfo("Activity Log", "There is no Activity Log text to copy.")
            return

        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update_idletasks()
            self.log_message("Activity Log copied to clipboard.", "success")
        except Exception as error:
            logger.exception("Copy activity log failed")
            messagebox.showerror("Copy Failed", f"Could not copy Activity Log:\n\n{error}")

    def open_files_export_dialog(self) -> None:
        """Open one FILES-backed export/package dialog."""
        self._ensure_session_files_state()

        if not self.session_files and not self.transcript_segments and not self.all_comments:
            messagebox.showinfo(
                "Export",
                "Add files, import a transcript, or fetch comments before exporting.",
            )
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Export")
        dialog.geometry("520x560")
        dialog.configure(fg_color=COLORS["bg_dark"])
        dialog.transient(self)

        container = ctk.CTkFrame(dialog, fg_color=COLORS["bg_card"], corner_radius=12)
        container.pack(fill="both", expand=True, padx=16, pady=16)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            container,
            text="FILES",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            container,
            text="Choose FILES entries to export to a folder. TXT, CSV, and Excel combine selected text entries.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            wraplength=460,
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        files_frame = ctk.CTkScrollableFrame(container, fg_color=COLORS["bg_input"], height=220)
        files_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 12))

        selected_vars: dict[str, tk.BooleanVar] = {}
        for entry in self.session_files:
            var = tk.BooleanVar(value=True)
            selected_vars[entry.normalized_path] = var
            ctk.CTkCheckBox(
                files_frame,
                text=self._session_file_export_display_name(entry),
                variable=var,
                font=ctk.CTkFont(size=12),
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_primary"],
            ).pack(fill="x", padx=8, pady=(6, 0))

        if not self.session_files:
            ctk.CTkLabel(
                files_frame,
                text="No FILES entries are attached yet.",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_muted"],
                anchor="w",
            ).pack(fill="x", padx=8, pady=8)

        def set_all(value: bool) -> None:
            for var in selected_vars.values():
                var.set(value)

        def selected_entries() -> List[SessionFileEntry]:
            return [
                entry
                for entry in self.session_files
                if selected_vars.get(entry.normalized_path) and selected_vars[entry.normalized_path].get()
            ]

        def selected_text_entries() -> List[SessionFileEntry]:
            entries = selected_entries()
            compatible = [
                entry
                for entry in entries
                if entry.file_kind == SESSION_FILE_KIND_TRANSCRIPT
                or os.path.splitext(entry.path)[1].lower() in {".txt", ".srt", ".vtt", ".csv"}
            ]
            if not entries:
                messagebox.showinfo("Export FILES", "Select at least one FILES entry.")
                return []
            if len(compatible) != len(entries):
                messagebox.showinfo(
                    "Export FILES",
                    "Combined TXT, CSV, and Excel exports support selected text/transcript FILES entries only.",
                )
                return []
            return compatible

        def copy_selected_files() -> None:
            entries = selected_entries()
            if not entries:
                messagebox.showinfo("Export FILES", "Select at least one FILES entry to copy.")
                return
            folder = filedialog.askdirectory(title="Choose Export Folder")
            if not folder:
                return
            copied = 0
            for entry in entries:
                source = entry.path
                if not os.path.isfile(source):
                    continue
                destination_folder = folder
                folder_name = self._session_file_folder_for_entry(entry)
                if folder_name:
                    destination_folder = os.path.join(folder, self._safe_session_folder_name(folder_name))
                    os.makedirs(destination_folder, exist_ok=True)
                destination = os.path.join(destination_folder, os.path.basename(source))
                stem, ext = os.path.splitext(destination)
                counter = 1
                while os.path.exists(destination):
                    destination = f"{stem}_{counter}{ext}"
                    counter += 1
                shutil.copy2(source, destination)
                copied += 1
            self.log_message(f"Exported {copied} FILES item(s) to export folder.", "success")
            messagebox.showinfo("Export FILES", f"Exported {copied} file(s).")

        def read_entry_text(entry: SessionFileEntry) -> str:
            try:
                segments = import_transcript(entry.path)
            except Exception:
                try:
                    return open(entry.path, "r", encoding="utf-8", errors="replace").read()
                except Exception:
                    return ""
            parts = []
            for segment in segments:
                speaker = segment.speaker or "Speaker"
                time_part = (
                    f" [{segment.start} - {segment.end}]"
                    if segment.start or segment.end
                    else ""
                )
                parts.append(f"{speaker}{time_part}\n{segment.text}")
            return "\n\n".join(parts)

        def combine_selected_txt() -> None:
            entries = selected_text_entries()
            if not entries:
                return
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                title="Save Combined FILES Text",
            )
            if not filename:
                return
            with open(filename, "w", encoding="utf-8") as handle:
                handle.write("Combined FILES Text Export\n")
                handle.write("=" * 80 + "\n\n")
                for entry in entries:
                    handle.write(f"Source: {entry.display_name}\n")
                    handle.write(f"Kind: {entry.file_kind}\n")
                    handle.write("-" * 80 + "\n")
                    handle.write(read_entry_text(entry).rstrip())
                    handle.write("\n\n")
            self.log_message(f"Combined {len(entries)} FILES text item(s).", "success")
            messagebox.showinfo("Export FILES", f"Combined text saved:\n\n{os.path.basename(filename)}")

        def combine_selected_csv() -> None:
            entries = selected_text_entries()
            if not entries:
                return
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                title="Save Combined FILES CSV",
            )
            if not filename:
                return
            with open(filename, "w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["source", "kind", "text"])
                writer.writeheader()
                for entry in entries:
                    writer.writerow(
                        {
                            "source": entry.display_name,
                            "kind": entry.file_kind,
                            "text": read_entry_text(entry),
                        }
                    )
            self.log_message(f"Combined {len(entries)} FILES item(s) to CSV.", "success")
            messagebox.showinfo("Export FILES", f"Combined CSV saved:\n\n{os.path.basename(filename)}")

        def combine_selected_excel() -> None:
            entries = selected_text_entries()
            if not entries:
                return
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                title="Save Combined FILES Excel",
            )
            if not filename:
                return
            from openpyxl import Workbook

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Combined FILES"
            sheet.append(["source", "kind", "text"])
            for entry in entries:
                sheet.append([entry.display_name, entry.file_kind, read_entry_text(entry)])
            workbook.save(filename)
            self.log_message(f"Combined {len(entries)} FILES item(s) to Excel.", "success")
            messagebox.showinfo("Export FILES", f"Combined Excel saved:\n\n{os.path.basename(filename)}")

        select_row = ctk.CTkFrame(container, fg_color="transparent")
        select_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))
        ctk.CTkButton(
            select_row,
            text="All",
            command=lambda: set_all(True),
            width=80,
            height=28,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
        ).pack(side="left")
        ctk.CTkButton(
            select_row,
            text="Clear all",
            command=lambda: set_all(False),
            width=90,
            height=28,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            select_row,
            text="Export",
            command=copy_selected_files,
            width=120,
            height=28,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#000000",
        ).pack(side="right")

        action_row = ctk.CTkFrame(container, fg_color="transparent")
        action_row.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 12))
        for label, command in (
            ("TXT", combine_selected_txt),
            ("CSV", combine_selected_csv),
            ("Excel", combine_selected_excel),
        ):
            ctk.CTkButton(
                action_row,
                text=label,
                command=command,
                width=96,
                height=30,
                fg_color=COLORS["accent_secondary"],
                hover_color=COLORS["border"],
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            container,
            text="Close",
            command=dialog.destroy,
            height=32,
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
        ).grid(row=5, column=0, sticky="e", padx=14, pady=(0, 12))

    def clear_log(self) -> None:
        """Clear the activity log."""
        self.activity_log_messages = []

        for widget in self.log_frame.winfo_children():
            widget.destroy()

    def _scroll_log_to_bottom(self) -> None:
        """Scroll the log frame to the bottom."""
        try:
            self.log_frame._parent_canvas.yview_moveto(1.0)
        except (AttributeError, Exception):
            pass

    def log_message(self, message: str, level: str = "info") -> None:
        """Add a message to the activity log."""
        if not hasattr(self, "activity_log_messages"):
            self.activity_log_messages = []

        icon = LOG_ICONS.get(level, "→")
        self.activity_log_messages.append(f"{icon}  {message}")

        color = LOG_COLORS.get(level, COLORS["text_secondary"])

        entry = ctk.CTkLabel(
            self.log_frame,
            text=f" {icon}  {message}",
            font=ctk.CTkFont(size=12),
            text_color=color,
            anchor="w",
            justify="left"
        )
        entry.pack(fill="x", padx=10, pady=3)

        self.log_frame.after(10, self._scroll_log_to_bottom)

    def _update_stats(self) -> None:
        """Update statistics display."""
        with self._data_lock:
            videos = len(self.all_metadata)
            comments = len(self.all_comments)
            spam = len(self.all_spam)

        stats_parts = [
            f"📊 {videos} video{'s' if videos != 1 else ''}",
            f"{comments:,} comment{'s' if comments != 1 else ''}"
        ]
        if spam > 0:
            stats_parts.append(f"🚫 {spam:,} spam")

        self.footer_stats.configure(text=" • ".join(stats_parts))

    # =========================================================================
    # CORE FUNCTIONALITY
    # =========================================================================

    def cancel_fetching(self) -> None:
        """Request cancellation of the fetch operation."""
        if self.fetch_state.is_fetching:
            self.fetch_state.request_cancel()
            active_media_worker = getattr(self, "_youtube_media_worker_token", None) is not None
            if active_media_worker:
                self._youtube_media_worker_cancel_requested = True
                self._youtube_media_worker_token = None
                try:
                    self.progress_bar.stop()
                except Exception:
                    pass
                self.status_label.configure(text="Cancelled YouTube media download wait", text_color=COLORS["warning"])
                self._set_operational_capture_status(
                    "Cancelled YouTube media download wait. JDownloader may still finish any package it already received.",
                    "warning",
                )
                self.log_message(
                    "YouTube media wait cancelled in YTCE. JDownloader may still finish any package it already received.",
                    "warning",
                )
                self._reset_fetch_ui()
                self._refresh_export_entry_state()
                return
            self.status_label.configure(text="Cancelling...", text_color=COLORS["warning"])
            self.log_message("Cancellation requested...", "warning")

    def start_fetching(self) -> None:
        """Start the comment fetching process."""
        if self.fetch_state.is_fetching:
            return

        selected_discussion_row = self._selected_discussion_row()
        extract_webpage = self.extract_webpage_var.get()
        extract_comments = self.extract_comments_var.get()
        extract_live_chat = self.extract_live_chat_var.get()
        youtube_media_requested = bool(
            selected_discussion_row is not None
            and self._source_row_is_youtube(selected_discussion_row)
            and self._youtube_quality_enabled_var_for_row(selected_discussion_row.row_id).get()
        )
        youtube_screenshot_requested = bool(
            selected_discussion_row is not None
            and self._source_row_is_youtube(selected_discussion_row)
            and self.webpage_screenshot_var.get()
        )
        if not extract_webpage and not extract_comments and not extract_live_chat and not youtube_media_requested and not youtube_screenshot_requested:
            self._set_operational_capture_status("Skipped: no selected source scopes.", "warning")
            messagebox.showerror(
                "Selection Required",
                "Tick Comments, Livechat, a screenshot option, or enable YouTube media before pressing Go."
            )
            return

        if youtube_media_requested and selected_discussion_row is not None:
            if not extract_webpage and not extract_comments and not extract_live_chat:
                self._start_youtube_source_row_media_worker(selected_discussion_row.row_id, self, show_message=False)
                return
            self._queue_youtube_source_row_media(selected_discussion_row.row_id, self, show_message=False)

        if selected_discussion_row is not None:
            discussion = build_discussion_capture_options(
                tuple(getattr(self, "source_resource_rows", ())),
                selected_row_id=selected_discussion_row.row_id,
                webpage_selected=extract_webpage,
                comments_selected=extract_comments,
                livechat_selected=extract_live_chat,
                webpage_screenshot_requested=self.webpage_screenshot_var.get(),
                comments_screenshot_requested=self.comments_screenshot_var.get(),
                livechat_screenshot_requested=self.livechat_screenshot_var.get(),
            )
            if selected_discussion_row.adapter_id != "youtube" or (
                discussion.webpage_active
                and not discussion.comments_selected
                and not discussion.livechat_selected
            ):
                plan = build_operational_capture_plan(
                    row=selected_discussion_row,
                    discussion=discussion,
                )
                self.last_operational_capture_plan = plan
                workflow_state = self._record_operational_capture_review_metadata(plan)
                self._set_operational_capture_status(
                    "Fixture/model-only capture plan ready. Review/export metadata ready; manual live-site smoke pending.",
                    "success",
                )
                scaffold_message = format_operational_capture_plan_message(plan)
                if workflow_state is not None:
                    scaffold_message = "\n\n".join(
                        (scaffold_message, workflow_state.to_summary_text())
                    )
                messagebox.showinfo(
                    "Discussion action scaffold",
                    scaffold_message,
                )
                self.log_message(
                    "Discussion action scaffold only; no fetch, screenshot, archive, download, WARC/WACZ, or provider action executed.",
                    "muted",
                )
                return
            current_text = selected_discussion_row.canonical_url
        else:
            current_text = self.url_entry.get("1.0", "end").strip()
            if current_text == self._url_placeholder.strip():
                current_text = ""

        valid_urls, _ = URLValidator.parse_url_list(current_text)

        # Get and validate inputs
        api_key = self._resolve_youtube_api_key_for_action()

        # Validate API key
        api_result = APIKeyValidator.validate(api_key)
        if not api_result:
            messagebox.showerror("Invalid API Key", api_result.error_message)
            return

        # Validate URLs
        if not valid_urls:
            messagebox.showerror(
                "Missing URLs",
                "Please enter at least one valid Source URL.\n"
                "Currently supported: YouTube video URLs.\n\n"
                "Supported formats:\n"
                "• youtube.com/watch?v=...\n"
                "• youtu.be/...\n"
                "• youtube.com/shorts/..."
            )
            return

        # Validate date range
        date_from, date_to, date_error = self._get_date_range()
        if date_error:
            messagebox.showerror("Invalid Date Range", date_error)
            return

        # Save settings
        self._save_settings()

        # Update UI state
        self.fetch_state.start()
        if hasattr(self.fetch_button, "grid_remove"):
            self.fetch_button.grid_remove()
        else:
            self.fetch_button.pack_forget()
        if hasattr(self.cancel_button, "grid"):
            self.cancel_button.grid(row=0, column=0, sticky="w")
        else:
            self.cancel_button.pack(side="left")
        self.export_button.configure(state="disabled")
        self.export_excel_button.configure(state="disabled")
        self.export_txt_button.configure(state="disabled")
        self.evidence_button.configure(state="disabled")
        self.progress_bar.set(0)
        self.status_label.configure(text="Initializing...", text_color=COLORS["text_secondary"])

        # Clear previous data
        self.clear_log()
        with self._data_lock:
            self.all_metadata = []
            self.all_comments = []
            self.all_spam = []
        self._update_stats()

        # Get custom filter patterns
        blacklist_patterns = [p.strip() for p in self._blacklist_patterns.split('\n') if p.strip()]
        whitelist_patterns = [p.strip() for p in self._whitelist_patterns.split('\n') if p.strip()]

        # Create extractor with spam threshold and custom patterns
        self.extractor = YouTubeCommentExtractor(
            api_key,
            spam_threshold=self.spam_threshold_var.get(),
            blacklist_patterns=blacklist_patterns if blacklist_patterns else None,
            whitelist_patterns=whitelist_patterns if whitelist_patterns else None,
        )

        # Get filter words
        filter_words = self._get_filter_words()
        max_comments = self._get_max_comments()

        # Log start
        self.log_message(f"Starting extraction for {len(valid_urls)} video(s)...", "info")
        if blacklist_patterns:
            self.log_message(f"Using {len(blacklist_patterns)} blacklist pattern(s)", "muted")
        if whitelist_patterns:
            self.log_message(f"Using {len(whitelist_patterns)} whitelist pattern(s)", "muted")
        if filter_words:
            self.log_message(f"Filtering for words: {', '.join(filter_words)}", "muted")
        if max_comments:
            self.log_message(f"Max {max_comments} comments per video", "muted")

        self._fetch_thread_ref = threading.Thread(
            target=self._fetch_thread,
            args=(
                valid_urls,
                self.spam_filter_var.get(),
                self._get_min_likes(),
                SortOption.from_display_name(self.sort_var.get()).value,
                self.exclude_creator_var.get(),
                date_from,
                date_to,
                filter_words,
                max_comments,
                extract_comments,
                extract_live_chat,
            ),
            daemon=True
        )
        self._fetch_thread_ref.start()

    def _fetch_thread(
        self,
        urls: List[str],
        filter_spam: bool,
        min_likes: int,
        sort_by: str,
        exclude_creator: bool,
        date_from: Optional[str],
        date_to: Optional[str],
        filter_words: List[str],
        max_comments: Optional[int],
        extract_comments: bool,
        extract_live_chat: bool,
    ) -> None:
        """Background thread for fetching comments."""
        total_videos = len(urls)

        try:
            for i, url in enumerate(urls):
                if self.fetch_state.cancel_requested:
                    self.after(0, lambda: self.log_message("Fetch cancelled by user", "warning"))
                    break

                video_num = i + 1
                self.after(0, lambda v=video_num, t=total_videos:
                    self.status_label.configure(
                        text=f"Processing video {v}/{t}...",
                        text_color=COLORS["text_secondary"]
                    ))
                self.after(0, lambda u=url: self.log_message(f"Fetching: {u}", "info"))

                try:
                    metadata, comments, spam = self.extractor.process_video(
                        url,
                        max_results=max_comments,
                        progress_callback=None,
                        filter_spam=filter_spam,
                        min_likes=min_likes,
                        sort_by=sort_by,
                        exclude_creator=exclude_creator,
                        date_from=date_from,
                        date_to=date_to,
                        filter_words=filter_words if filter_words else None,
                        cancel_event=self.fetch_state.cancel_event,
                        extract_comments=extract_comments,
                        extract_live_chat=extract_live_chat,
                    )

                    with self._data_lock:
                        self.all_metadata.append(metadata)
                        self.all_comments.extend(comments)
                        self.all_spam.extend(spam)

                    log_msg = f"Retrieved {len(comments):,} comments"
                    if len(spam) > 0:
                        log_msg += f" (filtered {len(spam)} spam)"
                    self.after(0, lambda msg=log_msg: self.log_message(msg, "success"))
                    self.after(0, self._update_stats)

                except CommentsDisabledError:
                    self.after(0, lambda:
                        self.log_message("Error: Comments are disabled for this video", "error"))
                except VideoNotFoundError:
                    self.after(0, lambda:
                        self.log_message("Error: Video not found", "error"))
                except QuotaExceededError:
                    self.after(0, lambda:
                        self.log_message("Error: API quota exceeded. Try again tomorrow.", "error"))
                except Exception as e:
                    self.after(0, lambda err=str(e):
                        self.log_message(f"Error: {err}", "error"))

                progress = video_num / total_videos
                self.after(0, lambda p=progress: self.progress_bar.set(p))

                if i < total_videos - 1 and not self.fetch_state.cancel_requested:
                    delay = random.uniform(API_DELAY_BETWEEN_VIDEOS_MIN, API_DELAY_BETWEEN_VIDEOS_MAX)
                    self.after(0, lambda d=delay:
                        self.log_message(f"Rate limit delay: {d:.1f}s", "muted"))
                    time.sleep(delay)

            # Get counts with thread-safe access
            with self._data_lock:
                video_count = len(self.all_metadata)
                has_comments = len(self.all_comments) > 0

            if self.fetch_state.cancel_requested:
                self.after(0, lambda c=video_count: self.status_label.configure(
                    text=f"Cancelled — {c} video(s) processed",
                    text_color=COLORS["warning"]
                ))
            else:
                self.after(0, lambda c=video_count: self.status_label.configure(
                    text=f"✓ Completed — {c} video(s) processed",
                    text_color=COLORS["success"]
                ))
                self.after(0, lambda: self.log_message("Extraction complete!", "success"))

            if has_comments:
                self.after(0, lambda: self.export_button.configure(state="normal"))
                self.after(0, lambda: self.export_excel_button.configure(state="normal"))
                self.after(0, lambda: self.export_txt_button.configure(state="normal"))
                self.after(0, lambda: self.evidence_button.configure(state="normal"))

        except Exception as e:
            logger.exception("Fetch thread error")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.after(0, lambda: self.status_label.configure(
                text="Error occurred",
                text_color=COLORS["error"]
            ))
        finally:
            self.after(0, self._reset_fetch_ui)

    def _reset_fetch_ui(self) -> None:
        """Reset UI after fetch completes or is cancelled."""
        self.fetch_state.stop()
        if hasattr(self.cancel_button, "grid_remove"):
            self.cancel_button.grid_remove()
        else:
            self.cancel_button.pack_forget()
        if hasattr(self.fetch_button, "grid"):
            self.fetch_button.grid(row=0, column=0, sticky="w")
        else:
            self.fetch_button.pack(side="left")

    def _guard_export_allowed(
        self,
        exportable_count: int,
        no_data_title: str,
        no_data_message: str,
    ) -> bool:
        """Prevent export hotkeys/buttons from snapshotting incomplete fetch data."""
        if self.fetch_state.is_fetching or self.fetch_state.cancel_requested:
            messagebox.showwarning(
                "Fetch In Progress",
                "Please wait for the current fetch to finish or cancel before exporting."
            )
            self.log_message("Export blocked while fetch is active.", "warning")
            return False

        if not is_export_allowed(self.fetch_state, exportable_count):
            messagebox.showwarning(no_data_title, no_data_message)
            return False

        return True

    def export_txt(self) -> None:
        """Export data to a readable TXT file for Notepad."""
        with self._data_lock:
            metadata = list(self.all_metadata)
            comments = list(self.all_comments)
            spam = list(self.all_spam)

        if not self._guard_export_allowed(
            len(comments),
            "No Data",
            "No comments to export. Fetch comments first."
        ):
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            title="Save Readable Comments Text"
        )

        if filename:
            try:
                self.extractor.save_to_txt(
                    metadata,
                    comments,
                    filename,
                    spam_list=spam if spam else None
                )
                self.log_message(f"Exported readable text to: {os.path.basename(filename)}", "success")
                messagebox.showinfo(
                    "Export Successful",
                    f"Text file saved:\n\n• {os.path.basename(filename)}"
                )
            except Exception as e:
                logger.exception("TXT export error")
                self.log_message(f"Export failed: {e}", "error")
                messagebox.showerror("Export Error", f"Failed to save text file:\n{e}")

    def export_csv(self) -> None:
        """Export data to CSV files."""
        with self._data_lock:
            metadata = list(self.all_metadata)
            comments = list(self.all_comments)
            spam = list(self.all_spam)

        if not self._guard_export_allowed(
            len(comments),
            "No Data",
            "No comments to export. Fetch comments first."
        ):
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Comments Data"
        )

        if filename:
            base_filename = os.path.splitext(filename)[0]
            try:
                self.extractor.save_to_csv(
                    metadata,
                    comments,
                    base_filename,
                    spam_list=spam if spam else None
                )

                files_saved = [
                    f"• {os.path.basename(base_filename)}_metadata.csv",
                    f"• {os.path.basename(base_filename)}_comments.csv"
                ]
                if spam:
                    files_saved.append(f"• {os.path.basename(base_filename)}_spam.csv")

                self.log_message(f"Exported {len(files_saved)} files", "success")
                messagebox.showinfo(
                    "Export Successful",
                    f"Files saved:\n\n" + "\n".join(files_saved)
                )
            except Exception as e:
                logger.exception("CSV export error")
                self.log_message(f"Export failed: {e}", "error")
                messagebox.showerror("Export Error", f"Failed to save files:\n{e}")

    def export_excel(self) -> None:
        """Export data to Excel file."""
        with self._data_lock:
            metadata = list(self.all_metadata)
            comments = list(self.all_comments)
            spam = list(self.all_spam)

        if not self._guard_export_allowed(
            len(comments),
            "No Data",
            "No comments to export. Fetch comments first."
        ):
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Save Comments Data"
        )

        if filename:
            try:
                self.extractor.save_to_excel(
                    metadata,
                    comments,
                    filename,
                    spam_list=spam if spam else None
                )

                sheets = ["Metadata", "Comments"]
                if spam:
                    sheets.append("Flagged Spam")

                self.log_message(f"Exported to: {os.path.basename(filename)}", "success")
                messagebox.showinfo(
                    "Export Successful",
                    f"Excel file saved:\n\n• {os.path.basename(filename)}\n\nSheets: {', '.join(sheets)}"
                )
            except Exception as e:
                logger.exception("Excel export error")
                self.log_message(f"Export failed: {e}", "error")
                messagebox.showerror("Export Error", f"Failed to save file:\n{e}")

    def attach_screenshots(self) -> None:
        """Attach manually captured page screenshots for evidence export."""
        files = filedialog.askopenfilenames(
            title="Select screenshot images",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*"),
            ],
        )

        if not files:
            return

        added = 0
        for file_path in files:
            if file_path not in self.attached_screenshots:
                self.attached_screenshots.append(file_path)
                added += 1

        self.log_message(
            f"Attached {added} screenshot(s). Total attached: {len(self.attached_screenshots)}",
            "success"
        )

        if self.attached_screenshots:
            self.evidence_button.configure(state="normal")
            self.clear_screenshots_button.configure(state="normal")

    def clear_attached_screenshots(self) -> None:
        ...
        self.log_message("Attached screenshots cleared.", "muted")

    def open_last_package(self) -> None:
        """Open the last created package folder in File Explorer."""
        if not self.last_package_dir or not os.path.isdir(self.last_package_dir):
            messagebox.showwarning(
                "No Package Folder",
                "No package folder is available yet."
            )
            self.open_last_package_button.configure(state="disabled")
            return

        try:
            os.startfile(self.last_package_dir)
        except Exception as e:
            logger.exception("Open package folder error")
            messagebox.showerror(
                "Open Folder Error",
                f"Could not open package folder:\n\n{e}"
            )

    def _get_current_source_urls(self) -> List[str]:
        """Return URLs currently present in the URL text box."""
        current_text = self.url_entry.get("1.0", "end").strip()
        if current_text == self._url_placeholder.strip():
            return []

        valid_urls, _ = URLValidator.parse_url_list(current_text)
        return valid_urls


    def _get_transcript_playback_metadata(self) -> Dict[str, str]:
        """Return transcript playback/editor metadata for package/source exports."""
        metadata: Dict[str, str] = {}

        linked_media = getattr(self, "linked_transcript_media_path", None)

        if linked_media:
            metadata["Linked Media"] = linked_media

        try:
            visual_sync_ms = int(round(
                float(getattr(self, "transcript_audio_sync_offset_seconds", 0.0)) * 1000
            ))
        except Exception:
            visual_sync_ms = 0

        metadata["Visual Sync Offset"] = f"{visual_sync_ms:+d} ms"
        metadata["Playback Backend"] = "VLC"

        waveform_peaks = getattr(self, "transcript_waveform_peaks", None) or []
        waveform_source = getattr(self, "transcript_waveform_source_path", None)

        if waveform_peaks and waveform_source:
            metadata["Waveform"] = (
                f"Generated from {os.path.basename(waveform_source)} "
                f"({len(waveform_peaks):,} peak samples)"
            )
        else:
            metadata["Waveform"] = "Not generated"

        return metadata

    def _append_transcript_playback_metadata_to_source_info(self, package_dir: str) -> None:
        """Append transcript media/playback metadata to source_info.txt."""
        metadata = self._get_transcript_playback_metadata()

        if not metadata:
            return

        source_info_path = os.path.join(package_dir, "source_info.txt")

        try:
            with open(source_info_path, "a", encoding="utf-8", newline="\n") as f:
                f.write("\n\nTranscript Playback Metadata\n")
                f.write("-" * 80)
                f.write("\n")

                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")

        except Exception as error:
            logger.warning(f"Could not append transcript playback metadata: {error}")


    def _append_youtube_metadata_to_source_info(self, package_dir: str) -> None:
        """Append YouTube video metadata to source_info.txt when available."""
        if not self.last_youtube_video_info:
            return

        info = self.last_youtube_video_info
        source_info_path = os.path.join(package_dir, "source_info.txt")

        lines = []
        lines.append("")
        lines.append("")
        lines.append("YouTube Video Metadata")
        lines.append("=" * 80)

        fields = [
            ("Title", "title"),
            ("URL", "url"),
            ("Video ID", "video_id"),
            ("Channel", "channel_title"),
            ("Channel ID", "channel_id"),
            ("Subscribers", "subscriber_count_text"),
            ("Published At", "published_at"),
            ("Views", "view_count_text"),
            ("Likes", "like_count_text"),
            ("Comments", "comment_count_text"),
        ]

        for label, key in fields:
            value = info.get(key)
            if value not in (None, ""):
                lines.append(f"{label}: {value}")

        description = (info.get("description") or "").strip()

        if description:
            lines.append("")
            lines.append("Description")
            lines.append("-" * 80)
            lines.append(description)

        lines.append("")

        with open(source_info_path, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))


    def _append_asr_metadata_to_source_info(self, package_dir: str) -> None:
        """Append Local ASR metadata to source_info.txt when available."""
        if not self.last_asr_metadata:
            return

        info = self.last_asr_metadata
        source_info_path = os.path.join(package_dir, "source_info.txt")

        probability = info.get("language_probability")

        if probability is not None:
            try:
                probability_text = f"{float(probability):.2%}"
            except Exception:
                probability_text = str(probability)
        else:
            probability_text = "unknown"

        fields = [
            ("Source File", "source_file"),
            ("Source File Name", "source_file_name"),
            ("Source File Size Bytes", "source_file_size_bytes"),
            ("Source File SHA256", "source_file_sha256"),
            ("Normalized PCM SHA256", "normalized_pcm_sha256"),
            ("Model SHA256", "model_sha256"),
            ("Resolved Runner", "resolved_runner"),
            ("Sanitized Command Manifest", "sanitized_command_manifest"),
            ("Engine", "selected_asr_engine"),
            ("Model", "model_name"),
            ("Device", "device"),
            ("Compute Type", "compute_type"),
            ("Speaker Label", "speaker_name"),
            ("Language Setting", "requested_language"),
            ("Detected Language", "language"),
            ("Language Confidence", None),
            ("Known Words / Context Prompt", "initial_prompt"),
            ("VAD Filter", "vad_filter"),
            ("Beam Size", "beam_size"),
            ("Segment Count", "segment_count"),
            ("Duration", "duration"),
            ("Duration After VAD", "duration_after_vad"),
        ]

        lines = []
        lines.append("")
        lines.append("")
        lines.append("Local ASR Metadata")
        lines.append("=" * 80)

        for label, key in fields:
            if key is None:
                value = probability_text
            else:
                value = info.get(key)

            if value not in (None, ""):
                lines.append(f"{label}: {value}")

        lines.append("")
        lines.append("Note")
        lines.append("-" * 80)
        lines.append(
            "Local ASR transcripts are machine-generated drafts. "
            "They may contain transcription errors and do not include speaker diarization."
        )
        lines.append("")

        with open(source_info_path, "a", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines))

    def export_evidence_folder(self) -> None:
        """Export comments, metadata, source info, and attached screenshots into one folder."""
        with self._data_lock:
            metadata = list(self.all_metadata)
            comments = list(self.all_comments)
            spam = list(self.all_spam)

        exportable_count = len(comments) + len(self.attached_screenshots) + len(self.transcript_segments)
        if not self._guard_export_allowed(
            exportable_count,
            "Nothing to Package",
            "Fetch comments, attach screenshots, or import a transcript first."
        ):
            return

        output_parent = filedialog.askdirectory(
            title="Choose parent folder for the export package"
        )

        if not output_parent:
            return

        settings = {
            "Filter Spam": self.spam_filter_var.get(),
            "Sensitivity": self.spam_threshold_var.get(),
            "Exclude Creator": self.exclude_creator_var.get(),
            "Min Likes": self._get_min_likes(),
            "Max Comments": self._get_max_comments(),
            "Sort By": self.sort_var.get(),
            "Date From": self.from_date_entry.get().strip(),
            "Date To": self.to_date_entry.get().strip(),
            "Filter Words": self.filter_words_entry.get().strip(),
            "Comments Selected": self.extract_comments_var.get(),
            "Livechat Selected": self.extract_live_chat_var.get(),
            "Transcript Segments": len(self.transcript_segments),
            "Transcript Source": self.last_transcript_source or "",
        }
        settings.update(self._get_transcript_playback_metadata())

        try:
            package_dir = create_evidence_package(
                output_parent=output_parent,
                metadata=metadata,
                comments=comments,
                spam=spam,
                screenshots=list(self.attached_screenshots),
                source_urls=self._get_current_source_urls(),
                app_version=APP_VERSION,
                settings=settings,
            )

            if self.transcript_segments:
                transcript_dir = os.path.join(package_dir, "transcript")
                os.makedirs(transcript_dir, exist_ok=True)

                self._export_readable_transcript_txt(
                    self.transcript_segments,
                    os.path.join(transcript_dir, "transcript_readable.txt")
                )
                export_transcript_csv(
                    self.transcript_segments,
                    os.path.join(transcript_dir, "transcript.csv")
                )
                export_transcript_srt(
                    self.transcript_segments,
                    os.path.join(transcript_dir, "transcript.srt")
                )
                export_transcript_vtt(
                    self.transcript_segments,
                    os.path.join(transcript_dir, "transcript.vtt")
                )

                self.log_message("Added transcript files to export package.", "success")
            self._append_youtube_metadata_to_source_info(package_dir)
            self._append_asr_metadata_to_source_info(package_dir)
            self._append_transcript_playback_metadata_to_source_info(package_dir)

            self.last_package_dir = package_dir
            self.open_last_package_button.configure(state="normal")

            self.log_message(f"Export package created: {package_dir}", "success")
            messagebox.showinfo(
                "Package Export Complete",
                f"Export package saved:\n\n{package_dir}"
            )

        except Exception as e:
            logger.exception("Evidence export error")
            self.log_message(f"Evidence export failed: {e}", "error")
            messagebox.showerror("Evidence Export Error", str(e))

    def check_for_updates_clicked(self) -> None:
        """Check GitHub Releases for a newer version without freezing the UI."""
        self.update_button.configure(state="disabled", text="Checking...")
        self.log_message("Checking GitHub for updates...", "info")

        def worker():
            result = check_for_updates(APP_VERSION)

            def show_result():
                self.update_button.configure(state="normal", text="UPDATES")

                if not result.ok:
                    messagebox.showwarning(
                        "Update Check Failed",
                        f"Could not check for updates.\n\n{result.error}"
                    )
                    self.log_message(f"Update check failed: {result.error}", "warning")
                    return

                if result.update_available:
                    answer = messagebox.askyesno(
                        "Update Available",
                        f"A newer version is available.\n\n"
                        f"Current version: {result.current_version}\n"
                        f"Latest version: {result.latest_version}\n\n"
                        f"Open the Releases page?"
                    )
                    self.log_message(
                        f"Update available: {result.latest_version}",
                        "success"
                    )
                    if answer:
                        webbrowser.open(result.release_url)
                else:
                    messagebox.showinfo(
                        "No Update Available",
                        f"You are using the latest version.\n\n"
                        f"Current version: {result.current_version}"
                    )
                    self.log_message("No update available.", "success")

            self.after(0, show_result)

        threading.Thread(target=worker, daemon=True).start()

    def _set_transcript_buttons_state(self, state: str) -> None:
        """Enable or disable transcript-related buttons."""
        self.transcript_export_txt_button.configure(state=state)
        self.transcript_export_srt_button.configure(state=state)
        self.transcript_export_vtt_button.configure(state=state)
        self.transcript_export_csv_button.configure(state=state)
        self.transcript_rename_button.configure(state=state)
        if hasattr(self, "transcript_create_speaker_button"):
            self.transcript_create_speaker_button.configure(state=state)
        if hasattr(self, "transcript_edit_segment_button"):
            self.transcript_edit_segment_button.configure(state=state)
        if hasattr(self, "transcript_merge_up_button"):
            self.transcript_merge_up_button.configure(state=state)
        if hasattr(self, "transcript_merge_down_button"):
            self.transcript_merge_down_button.configure(state=state)
        if hasattr(self, "transcript_qa_refresh_button"):
            self.transcript_qa_refresh_button.configure(state=state)
        self.transcript_clear_button.configure(state=state)

    @staticmethod
    def _apply_speaker_label_rule(
        segments: List[TranscriptSegment],
        single_speaker_name: str
    ) -> None:
        """
        Speaker label rule:
        - If only one speaker exists, use the channel/source name.
        - If multiple speakers exist, normalise labels to Speaker 1, Speaker 2, etc.
        """
        speakers: List[str] = []

        for segment in segments:
            speaker = (segment.speaker or "").strip()
            if speaker and speaker not in speakers:
                speakers.append(speaker)

        if len(speakers) <= 1:
            for segment in segments:
                segment.speaker = single_speaker_name or "YouTube"
            return

        speaker_map = {
            speaker: f"Speaker {index}"
            for index, speaker in enumerate(speakers, start=1)
        }

        for segment in segments:
            old_speaker = (segment.speaker or "").strip()
            segment.speaker = speaker_map.get(old_speaker, "Speaker")

    def _get_readable_transcript_segments(self) -> List[TranscriptSegment]:
        """
        Combine consecutive same-speaker segments into full speaker turns.

        For a one-speaker YouTube video, this produces one readable speaker turn.
        The preview will truncate for speed, but TXT/package export will include all text.
        """
        if not self.transcript_segments:
            return []

        readable: List[TranscriptSegment] = []

        current = TranscriptSegment(
            speaker=self.transcript_segments[0].speaker,
            start=self.transcript_segments[0].start,
            end=self.transcript_segments[0].end,
            text=self.transcript_segments[0].text.strip(),
        )

        for segment in self.transcript_segments[1:]:
            same_speaker = (segment.speaker or "") == (current.speaker or "")

            if same_speaker:
                current.text = f"{current.text.rstrip()} {segment.text.strip()}".strip()
                current.end = segment.end
            else:
                readable.append(current)
                current = TranscriptSegment(
                    speaker=segment.speaker,
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                )

        readable.append(current)
        return readable

    @staticmethod
    def _split_readable_text(text: str, max_chars: int = 1800) -> List[str]:
        """Split long transcript text into readable paragraphs without changing timestamps."""
        words = " ".join((text or "").split()).split()

        if not words:
            return []

        paragraphs: List[str] = []
        current_words: List[str] = []
        current_len = 0

        for word in words:
            extra_len = len(word) + (1 if current_words else 0)

            if current_words and current_len + extra_len > max_chars:
                paragraphs.append(" ".join(current_words))
                current_words = [word]
                current_len = len(word)
            else:
                current_words.append(word)
                current_len += extra_len

        if current_words:
            paragraphs.append(" ".join(current_words))

        return paragraphs


    def _clone_transcript_segments(self) -> List[TranscriptSegment]:
        """Create a safe copy of the current transcript segments."""
        return [
            TranscriptSegment(
                speaker=segment.speaker,
                start=segment.start,
                end=segment.end,
                text=segment.text,
            )
            for segment in self.transcript_segments
        ]

    @staticmethod
    def _blank_text_preserving_transcript_boundaries(
        segments: List[TranscriptSegment],
    ) -> List[TranscriptSegment]:
        """Return editable blank cues without merging ASR timing boundaries."""
        return [
            TranscriptSegment(
                speaker=segment.speaker,
                start=segment.start,
                end=segment.end,
                text="",
            )
            for segment in segments
        ]

    def _build_subtitle_timing_cues(
        self,
        segments: List[TranscriptSegment],
        *,
        media_duration_seconds: Optional[float] = None,
        word_timestamps: Optional[List[Dict[str, Any]]] = None,
        pause_gap_seconds: float = 0.35,
        max_cue_duration_seconds: float = 6.0,
        max_cue_chars: int = 90,
    ) -> List[TranscriptSegment]:
        """Build editable subtitle cues from ASR timing evidence."""
        media_limit = (
            float(media_duration_seconds)
            if isinstance(media_duration_seconds, (int, float)) and media_duration_seconds > 0
            else None
        )

        words: List[Dict[str, Any]] = []
        for word in word_timestamps or []:
            if not isinstance(word, dict):
                continue
            try:
                start_seconds = float(word.get("start"))
                end_seconds = float(word.get("end"))
            except Exception:
                continue
            text = " ".join(str(word.get("text") or "").split())
            if not text or end_seconds <= start_seconds:
                continue
            start_seconds = max(0.0, start_seconds)
            end_seconds = max(start_seconds, end_seconds)
            if media_limit is not None:
                if start_seconds >= media_limit:
                    continue
                end_seconds = min(end_seconds, media_limit)
            words.append(
                {
                    "start": start_seconds,
                    "end": end_seconds,
                    "text": text,
                }
            )

        if words:
            words.sort(key=lambda item: (float(item["start"]), float(item["end"])))
            return self._build_word_timestamp_subtitle_cues(
                words,
                speaker=(segments[0].speaker if segments else "Speaker 1"),
                media_limit=media_limit,
                pause_gap_seconds=pause_gap_seconds,
                max_cue_duration_seconds=max_cue_duration_seconds,
                max_cue_chars=max_cue_chars,
            )

        cues: List[TranscriptSegment] = []
        for segment in segments:
            start_seconds = self._transcript_time_to_seconds(segment.start)
            end_seconds = self._transcript_time_to_seconds(segment.end)
            text = " ".join((segment.text or "").split())
            if start_seconds is None or end_seconds is None:
                if text:
                    cues.append(
                        TranscriptSegment(
                            speaker=segment.speaker,
                            start=segment.start,
                            end=segment.end,
                            text=text,
                        )
                    )
                continue
            start_seconds = max(0.0, float(start_seconds))
            end_seconds = max(start_seconds, float(end_seconds))
            if media_limit is not None:
                start_seconds = min(start_seconds, media_limit)
                end_seconds = min(end_seconds, media_limit)
            if end_seconds <= start_seconds:
                continue
            cues.append(
                TranscriptSegment(
                    speaker=segment.speaker,
                    start=self._seconds_to_transcript_time(start_seconds),
                    end=self._seconds_to_transcript_time(end_seconds),
                    text=text,
                )
            )
        return cues

    def _build_word_timestamp_subtitle_cues(
        self,
        words: List[Dict[str, Any]],
        *,
        speaker: str,
        media_limit: Optional[float],
        pause_gap_seconds: float,
        max_cue_duration_seconds: float,
        max_cue_chars: int,
    ) -> List[TranscriptSegment]:
        """Build cues from timestamped words/tokens without filling silent gaps."""
        groups: List[Dict[str, Any]] = []
        current: List[Dict[str, Any]] = []
        gap_threshold = max(0.15, float(pause_gap_seconds))

        def emit_current() -> None:
            if not current:
                return
            start_seconds = max(0.0, float(current[0]["start"]))
            end_seconds = float(current[-1]["end"])
            text = " ".join(str(item["text"]) for item in current).strip()
            if not text:
                return
            groups.append({"start": start_seconds, "end": end_seconds, "text": text})

        for word in words:
            if current:
                previous = current[-1]
                gap = float(word["start"]) - float(previous["end"])
                projected_duration = float(word["end"]) - float(current[0]["start"])
                projected_text = " ".join(
                    [str(item["text"]) for item in current] + [str(word["text"])]
                )
                previous_text = str(previous["text"])
                split_for_pause = gap >= gap_threshold
                split_for_punctuation = (
                    previous_text.endswith((".", "?", "!"))
                    and projected_duration >= 1.0
                )
                split_for_size = (
                    projected_duration > max_cue_duration_seconds
                    or len(projected_text) > max_cue_chars
                )
                if split_for_pause or split_for_punctuation or split_for_size:
                    emit_current()
                    current = []
            current.append(word)

        emit_current()

        cues: List[TranscriptSegment] = []
        for index, group in enumerate(groups):
            start_seconds = float(group["start"])
            end_seconds = float(group["end"])
            previous_end = float(groups[index - 1]["end"]) if index > 0 else 0.0
            next_start = (
                float(groups[index + 1]["start"])
                if index + 1 < len(groups)
                else (float(media_limit) if media_limit is not None else end_seconds + 1.0)
            )
            leading_gap = max(0.0, start_seconds - previous_end)
            trailing_gap = max(0.0, next_start - end_seconds)
            leading_pad = min(0.030, leading_gap / 2.0)
            trailing_pad = min(0.040, trailing_gap / 2.0)
            cue_start = max(0.0, start_seconds - leading_pad)
            cue_end = end_seconds + trailing_pad
            if media_limit is not None:
                cue_end = min(cue_end, float(media_limit))
            if cues:
                previous_cue_end = self._transcript_time_to_seconds(cues[-1].end)
                if previous_cue_end is not None:
                    cue_start = max(cue_start, float(previous_cue_end))
            cue_end = max(cue_start + 0.050, cue_end)
            cues.append(
                TranscriptSegment(
                    speaker=speaker or "Speaker 1",
                    start=self._seconds_to_transcript_time(cue_start),
                    end=self._seconds_to_transcript_time(cue_end),
                    text=str(group["text"]),
                )
            )
        return cues

    def _subtitle_timing_quality_report(
        self,
        cues: List[TranscriptSegment],
        *,
        media_duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Return deterministic timing diagnostics for generated subtitle cues."""
        intervals: List[Tuple[float, float]] = []
        blank_count = 0
        for cue in cues:
            start_seconds = self._transcript_time_to_seconds(cue.start)
            end_seconds = self._transcript_time_to_seconds(cue.end)
            if start_seconds is None or end_seconds is None or end_seconds <= start_seconds:
                continue
            intervals.append((float(start_seconds), float(end_seconds)))
            if not (cue.text or "").strip():
                blank_count += 1

        intervals.sort()
        durations = [end - start for start, end in intervals]
        gaps = [
            max(0.0, intervals[index][0] - intervals[index - 1][1])
            for index in range(1, len(intervals))
        ]
        overlaps = [
            max(0.0, intervals[index - 1][1] - intervals[index][0])
            for index in range(1, len(intervals))
        ]
        positive_gaps = [gap for gap in gaps if gap > 0.001]
        positive_overlaps = [overlap for overlap in overlaps if overlap > 0.001]
        covered_duration = sum(durations)
        malformed_count = 0
        for cue in cues:
            text = " ".join((cue.text or "").split())
            if re.search(r"\b[A-Za-z]\s+[A-Za-z]{1,3}\s+[A-Za-z]{1,5}\b", text):
                malformed_count += 1
        median_duration = 0.0
        if durations:
            ordered = sorted(durations)
            middle = len(ordered) // 2
            if len(ordered) % 2:
                median_duration = ordered[middle]
            else:
                median_duration = (ordered[middle - 1] + ordered[middle]) / 2.0
        media_duration = (
            float(media_duration_seconds)
            if isinstance(media_duration_seconds, (int, float)) and media_duration_seconds > 0
            else 0.0
        )
        coverage = (covered_duration / media_duration * 100.0) if media_duration else 0.0
        return {
            "cue_count": len(cues),
            "covered_duration_seconds": round(covered_duration, 3),
            "positive_gap_count": len(positive_gaps),
            "overlap_count": len(positive_overlaps),
            "median_cue_duration_seconds": round(median_duration, 3),
            "max_cue_duration_seconds": round(max(durations) if durations else 0.0, 3),
            "blank_cue_count": blank_count,
            "malformed_word_cue_count": malformed_count,
            "coverage_percent": round(coverage, 2),
        }

    def _subtitle_timing_quality_warnings(self, report: Dict[str, Any]) -> List[str]:
        warnings: List[str] = []
        try:
            overlap_count = int(report.get("overlap_count", 0))
        except Exception:
            overlap_count = 0
        try:
            positive_gap_count = int(report.get("positive_gap_count", 0))
        except Exception:
            positive_gap_count = 0
        try:
            coverage_percent = float(report.get("coverage_percent", 0.0))
        except Exception:
            coverage_percent = 0.0
        try:
            malformed_count = int(report.get("malformed_word_cue_count", 0))
        except Exception:
            malformed_count = 0

        if overlap_count > 0:
            warnings.append(f"{overlap_count} overlapping cue pair(s)")
        if coverage_percent > 90.0:
            warnings.append(f"{coverage_percent:.2f}% media coverage")
        if positive_gap_count < 6:
            warnings.append(f"only {positive_gap_count} positive gap(s)")
        if malformed_count > 0:
            warnings.append(f"{malformed_count} cue(s) with suspicious token spacing")
        return warnings

    def _ask_low_quality_subtitle_timing_choice(
        self,
        report: Dict[str, Any],
        warnings: List[str],
    ) -> str:
        override = vars(self).get("_low_quality_subtitle_timing_choice_override")
        if override in {"raw", "review", "cancel"}:
            return str(override)
        if "tk" not in vars(self):
            return "review"
        message = (
            "The ASR timing evidence looks low quality.\n\n"
            + "\n".join(f"- {warning}" for warning in warnings)
            + "\n\n"
            "Yes: use raw ASR segments\n"
            "No: review the low-quality draft\n"
            "Cancel: keep the current transcript"
        )
        answer = messagebox.askyesnocancel(
            "Review Subtitle Timing Quality",
            message,
        )
        if answer is True:
            return "raw"
        if answer is False:
            return "review"
        return "cancel"

    def _push_transcript_undo_state(self, reason: str = "") -> None:
        """Save the current transcript state before an edit."""
        if not self.transcript_segments:
            return

        snapshot = self._clone_transcript_segments()

        if self.transcript_undo_stack:
            last = self.transcript_undo_stack[-1]
            if [
                (x.speaker, x.start, x.end, x.text)
                for x in last
            ] == [
                (x.speaker, x.start, x.end, x.text)
                for x in snapshot
            ]:
                return

        self.transcript_undo_stack.append(snapshot)

        if len(self.transcript_undo_stack) > self.transcript_history_limit:
            self.transcript_undo_stack.pop(0)

        self.transcript_redo_stack.clear()
        self.transcript_has_unsaved_edits = True
        self._refresh_session_files_list()

    def _restore_transcript_snapshot(self, snapshot: List[TranscriptSegment], label: str) -> None:
        """Restore transcript segments from a snapshot."""
        self.transcript_segments = [
            TranscriptSegment(
                speaker=segment.speaker,
                start=segment.start,
                end=segment.end,
                text=segment.text,
            )
            for segment in snapshot
        ]

        self._refresh_transcript_display()

        if hasattr(self, "evidence_button"):
            self.evidence_button.configure(
                state="normal" if self.transcript_segments else "disabled"
            )

        self.log_message(f"{label} transcript edit", "success")

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"{label} transcript edit",
                text_color=COLORS["text_primary"]
            )

    def undo_transcript_edit(self, event=None):
        """Undo the previous transcript edit."""
        if not self.transcript_undo_stack:
            if hasattr(self, "transcript_cursor_status_label"):
                self.transcript_cursor_status_label.configure(
                    text="Nothing to undo.",
                    text_color=COLORS["text_muted"]
                )
            return "break"

        current_snapshot = self._clone_transcript_segments()
        previous_snapshot = self.transcript_undo_stack.pop()

        if current_snapshot:
            self.transcript_redo_stack.append(current_snapshot)

        self._restore_transcript_snapshot(previous_snapshot, "Undid")
        self.transcript_has_unsaved_edits = True
        self._refresh_session_files_list()
        return "break"

    def redo_transcript_edit(self, event=None):
        """Redo the previous undone transcript edit."""
        if not self.transcript_redo_stack:
            if hasattr(self, "transcript_cursor_status_label"):
                self.transcript_cursor_status_label.configure(
                    text="Nothing to redo.",
                    text_color=COLORS["text_muted"]
                )
            return "break"

        current_snapshot = self._clone_transcript_segments()
        next_snapshot = self.transcript_redo_stack.pop()

        if current_snapshot:
            self.transcript_undo_stack.append(current_snapshot)

        self._restore_transcript_snapshot(next_snapshot, "Redid")
        self.transcript_has_unsaved_edits = True
        self._refresh_session_files_list()
        return "break"

    def _transcript_empty_state_text(self) -> str:
        if getattr(self, "linked_transcript_media_path", None):
            return (
                "No transcript loaded. Playback and waveform are available for the active media. "
                "Add, drop, import, create subtitle timings, or transcribe to create transcript segments."
            )
        return (
            "No transcript loaded. Add media with FILES + or drag/drop, then import, drop, "
            "create subtitle timings, or transcribe to create transcript segments."
        )

    def _refresh_transcript_display(self) -> None:
        """Refresh transcript preview, stats, and inline editor mapping."""
        view_state = self._capture_transcript_view_state()
        has_transcript = len(self.transcript_segments) > 0
        state = "normal" if has_transcript else "disabled"

        self._set_transcript_buttons_state(state)

        if hasattr(self, "transcript_search_entry"):
            self.transcript_search_entry.configure(state=state)

        self.transcript_display_ranges = []

        current_selected_index = getattr(self, "selected_transcript_segment_index", None)

        if (
            has_transcript
            and isinstance(current_selected_index, int)
            and 0 <= current_selected_index < len(self.transcript_segments)
        ):
            self.selected_transcript_segment_index = current_selected_index
        else:
            self.selected_transcript_segment_index = None

        if hasattr(self, "transcript_cursor_status_label"):
            if has_transcript:
                self.transcript_cursor_status_label.configure(
                    text="Click inside the transcript to select a segment. Click a speaker button to change that segment.",
                    text_color=COLORS["text_muted"]
                )
            else:
                self.transcript_cursor_status_label.configure(
                    text=self._transcript_empty_state_text(),
                    text_color=COLORS["text_muted"]
                )

        self.transcript_textbox.configure(state="normal")
        self.transcript_textbox.delete("1.0", "end")

        text_widget = self._get_transcript_text_widget()

        for tag_name in text_widget.tag_names():
            tag_name = str(tag_name)
            if (
                tag_name.startswith("transcript_speaker_label_")
                or tag_name.startswith("transcript_segment_text_wrap_")
                or tag_name.startswith("transcript_segment_click_")
                or tag_name.startswith("transcript_qa_issue_")
                or tag_name == "transcript_timestamp"
            ):
                text_widget.tag_delete(tag_name)

        text_widget.tag_configure(
            "transcript_timestamp",
            foreground="#93C5FD"
        )

        if not has_transcript:
            self.transcript_stats_label.configure(
                text="No transcript loaded",
                text_color=COLORS["text_muted"]
            )
            self.transcript_textbox.insert(
                "1.0",
                self._transcript_empty_state_text()
            )
            self.transcript_textbox.configure(state="disabled")
            if hasattr(self, "transcript_search_count_label"):
                self._update_transcript_search_matches(reset_index=True)
            self._render_transcript_qa_issues([])
            self._refresh_transcript_timeline()
            return

        speakers = sorted({
            segment.speaker for segment in self.transcript_segments
            if segment.speaker
        })

        self.transcript_stats_label.configure(
            text=f"{len(self.transcript_segments):,} segment(s) • {len(speakers)} speaker(s)",
            text_color=COLORS["text_muted"]
        )

        preview_char_limit = 12000
        chars_written = 0
        truncated = False

        show_speakers = self.transcript_show_speakers_var.get()
        show_timestamps = self.transcript_show_timestamps_var.get()

        # Dynamic speaker column keeps all transcript text aligned.
        # Text begins 2 spaces after the longest visible speaker button.
        longest_speaker_name_length = max(
            [len((segment.speaker or "Speaker").strip()) for segment in self.transcript_segments]
            + [len("Speaker")]
        )
        speaker_column_width = longest_speaker_name_length + 2
        text_gap = 2

        def make_speaker_button_text(value: str) -> str:
            value = (value or "Speaker").strip()
            max_len = speaker_column_width - 2

            if len(value) > max_len:
                value = value[:max_len - 1].rstrip() + "…"

            return f" {value} "

        for segment_index, segment in enumerate(self.transcript_segments):
            if chars_written >= preview_char_limit:
                truncated = True
                break

            speaker = segment.speaker or "Speaker"
            start_time = segment.start or "no start"
            end_time = segment.end or "no end"
            text = segment.text or ""

            readable_text = " ".join((text or "").split())
            remaining_chars = preview_char_limit - chars_written

            if remaining_chars <= 0:
                truncated = True
                break

            if len(readable_text) > remaining_chars:
                readable_text = readable_text[:remaining_chars].rstrip() + "..."
                truncated = True

            segment_start_index = self.transcript_textbox.index("end-1c")
            speaker_label_start_index = ""
            speaker_label_end_index = ""
            prefix_width = 0

            if show_speakers:
                speaker_button_text = make_speaker_button_text(speaker)

                speaker_label_start_index = self.transcript_textbox.index("end-1c")
                self.transcript_textbox.insert("end", speaker_button_text)
                speaker_label_end_index = self.transcript_textbox.index("end-1c")

                speaker_tag = f"transcript_speaker_label_{segment_index}"
                text_widget.tag_add(
                    speaker_tag,
                    speaker_label_start_index,
                    speaker_label_end_index
                )
                text_widget.tag_configure(
                    speaker_tag,
                    background=COLORS["accent_secondary"],
                    foreground=COLORS["text_primary"],
                    relief="raised",
                    borderwidth=2
                )

                # Break Button-1 so the click does not also move the text cursor.
                text_widget.tag_bind(
                    speaker_tag,
                    "<Button-1>",
                    lambda event: "break"
                )

                # Open after mouse release to avoid the popup opening and instantly closing.
                text_widget.tag_bind(
                    speaker_tag,
                    "<ButtonRelease-1>",
                    lambda event, idx=segment_index: (
                        self.after(90, lambda: self._open_inline_speaker_picker(idx)),
                        "break"
                    )[1]
                )

                text_widget.tag_bind(
                    speaker_tag,
                    "<Enter>",
                    lambda event: text_widget.configure(cursor="hand2")
                )
                text_widget.tag_bind(
                    speaker_tag,
                    "<Leave>",
                    lambda event: text_widget.configure(cursor="xterm")
                )

                # Non-clickable padding after the visible speaker button.
                padding_after_button = max(
                    0,
                    speaker_column_width - len(speaker_button_text)
                )
                self.transcript_textbox.insert(
                    "end",
                    (" " * padding_after_button) + (" " * text_gap)
                )

                prefix_width = speaker_column_width + text_gap

            segment_text_start_index = self.transcript_textbox.index("end-1c")
            self.transcript_textbox.insert("end", readable_text)
            segment_text_end_index = self.transcript_textbox.index("end-1c")

            # Keep visually wrapped lines aligned under the transcript text column.
            # This fixes long merged segments wrapping back under the speaker buttons.
            wrap_tag = f"transcript_segment_text_wrap_{segment_index}"
            try:
                char_width_px = 9
                wrap_indent_px = max(0, prefix_width * char_width_px)
                text_widget.tag_add(
                    wrap_tag,
                    segment_text_start_index,
                    segment_text_end_index
                )
                text_widget.tag_configure(
                    wrap_tag,
                    lmargin2=wrap_indent_px
                )
            except Exception:
                pass

            chars_written += len(readable_text)

            if show_timestamps:
                timestamp_text = f"[{start_time} - {end_time}]"

                # Center timestamp under only the segment text.
                center_offset_inside_text = max(
                    0,
                    (len(readable_text) - len(timestamp_text)) // 2
                )
                timestamp_padding = prefix_width + center_offset_inside_text

                self.transcript_textbox.insert("end", "\n")
                timestamp_start_index = self.transcript_textbox.index("end-1c")
                self.transcript_textbox.insert(
                    "end",
                    f"{' ' * timestamp_padding}{timestamp_text}"
                )
                timestamp_end_index = self.transcript_textbox.index("end-1c")
                text_widget.tag_add(
                    "transcript_timestamp",
                    timestamp_start_index,
                    timestamp_end_index
                )

            self.transcript_textbox.insert("end", "\n\n")

            segment_end_index = self.transcript_textbox.index("end-1c")

            click_tag = f"transcript_segment_click_{segment_index}"

            try:
                text_widget_for_click = self._get_transcript_text_widget()
                text_widget_for_click.tag_add(
                    click_tag,
                    segment_start_index,
                    segment_end_index
                )
                text_widget_for_click.tag_bind(
                    click_tag,
                    "<ButtonRelease-1>",
                    lambda event, idx=segment_index: self._select_transcript_segment_from_preview(idx, event)
                )
            except Exception:
                pass

            self.transcript_display_ranges.append({
                "segment_index": segment_index,
                "start": segment_start_index,
                "end": segment_end_index,
                "text_start": segment_text_start_index,
                "text_end": segment_text_end_index,
                "speaker_label_start": speaker_label_start_index,
                "speaker_label_end": speaker_label_end_index,
                "text": text,
                "speaker": speaker,
                "start_time": segment.start,
                "end_time": segment.end,
            })

            if truncated:
                break

        if truncated:
            self.transcript_textbox.insert(
                "end",
                "... preview truncated for speed. Export TXT or Package for the full readable transcript.\n"
            )

        self.transcript_textbox.configure(state="normal")
        if hasattr(self, "transcript_search_count_label"):
            self._update_transcript_search_matches(reset_index=True)

        self._restore_transcript_view_state(view_state)
        self._schedule_transcript_qa_refresh()
        self._refresh_transcript_timeline()


    def _capture_transcript_view_state(self) -> Dict[str, Any]:
        """Capture transcript cursor and scroll before rebuilding the preview."""
        state: Dict[str, Any] = {
            "selected_segment_index": getattr(self, "selected_transcript_segment_index", None),
            "segment_index": None,
            "char_offset": None,
            "yview": None,
        }

        if not hasattr(self, "transcript_textbox"):
            return state

        text_widget = self._get_transcript_text_widget()

        try:
            state["yview"] = text_widget.yview()
        except Exception:
            pass

        try:
            text_index = text_widget.index("insert")
        except Exception:
            return state

        info = self._get_editable_transcript_text_info(text_index)

        if not info:
            info = self._get_transcript_segment_at_text_index(text_index)

        if info:
            segment_index = info.get("segment_index")

            if isinstance(segment_index, int):
                state["segment_index"] = segment_index
                state["char_offset"] = self._estimate_text_offset_in_segment(info, text_index)

        return state

    def _restore_transcript_view_state(self, state: Optional[Dict[str, Any]]) -> None:
        """Restore transcript cursor and scroll after rebuilding the preview."""
        if not state or not hasattr(self, "transcript_textbox"):
            return

        selected_index = state.get("selected_segment_index")

        if (
            isinstance(selected_index, int)
            and 0 <= selected_index < len(self.transcript_segments)
        ):
            self.selected_transcript_segment_index = selected_index

        text_widget = self._get_transcript_text_widget()
        segment_index = state.get("segment_index")
        char_offset = state.get("char_offset")

        if isinstance(segment_index, int) and isinstance(char_offset, int):
            for info in getattr(self, "transcript_display_ranges", []):
                if info.get("segment_index") != segment_index:
                    continue

                text_start = info.get("text_start")
                text_end = info.get("text_end")

                if not text_start or not text_end:
                    break

                segment_text = self.transcript_segments[segment_index].text or ""
                char_offset = max(0, min(int(char_offset), len(segment_text)))

                try:
                    target_index = f"{text_start}+{char_offset}c"

                    if text_widget.compare(target_index, ">", text_end):
                        target_index = text_end

                    text_widget.mark_set("insert", target_index)
                except Exception:
                    pass

                break

        yview = state.get("yview")

        if yview:
            try:
                text_widget.yview_moveto(float(yview[0]))
            except Exception:
                pass


    def _schedule_transcript_qa_refresh(self) -> None:
        """Debounce transcript QA scans so inline editing stays responsive."""
        if not hasattr(self, "transcript_qa_status_label"):
            return

        if getattr(self, "transcript_qa_after_id", None):
            try:
                self.after_cancel(self.transcript_qa_after_id)
            except Exception:
                pass

        if not self.transcript_segments:
            self.transcript_qa_after_id = None
            self._render_transcript_qa_issues([])
            return

        self.transcript_qa_status_label.configure(
            text="Checking glossary terms...",
            text_color=COLORS["text_muted"]
        )
        self.transcript_qa_after_id = self.after(250, self._refresh_transcript_qa_panel)

    def _transcript_qa_words(self, text: str) -> List[str]:
        """Return normalized words for local transcript QA checks."""
        return [
            match.group(0).lower()
            for match in re.finditer(r"[A-Za-z0-9']+", text or "")
        ]

    def _transcript_qa_word_spans(self, text: str) -> List[Dict[str, Any]]:
        """Return normalized words with character spans for QA replacements."""
        return [
            {
                "word": match.group(0).lower(),
                "start": match.start(),
                "end": match.end(),
            }
            for match in re.finditer(r"[A-Za-z0-9']+", text or "")
        ]

    def _transcript_qa_word_matches(self, candidate_word: str, glossary_word: str, is_final_word: bool) -> bool:
        if candidate_word == glossary_word:
            return True

        return is_final_word and candidate_word == f"{glossary_word}'s"

    def _transcript_qa_has_glossary_sequence(self, words: List[str], glossary_words: List[str]) -> bool:
        if not glossary_words or len(words) < len(glossary_words):
            return False

        for start in range(0, len(words) - len(glossary_words) + 1):
            matched = True

            for offset, glossary_word in enumerate(glossary_words):
                candidate_word = words[start + offset]
                is_final_word = offset == len(glossary_words) - 1

                if not self._transcript_qa_word_matches(candidate_word, glossary_word, is_final_word):
                    matched = False
                    break

            if matched:
                return True

        return False

    def _transcript_qa_edit_distance(self, left: str, right: str) -> int:
        if not left:
            return len(right)

        if not right:
            return len(left)

        previous = list(range(len(right) + 1))

        for i, left_char in enumerate(left, start=1):
            current = [i]

            for j, right_char in enumerate(right, start=1):
                current.append(
                    min(
                        previous[j] + 1,
                        current[j - 1] + 1,
                        previous[j - 1] + (0 if left_char == right_char else 1),
                    )
                )

            previous = current

        return previous[-1]

    def _transcript_qa_find_glossary_issues(self, max_issues: int = 40) -> List[Dict[str, Any]]:
        """Find likely glossary term mistakes without changing transcript text."""
        glossary_terms = [
            term.strip()
            for term in getattr(self, "transcript_glossary_terms", [])
            if term and term.strip()
        ]
        glossary_word_lists = [
            (term, self._transcript_qa_words(term))
            for term in glossary_terms
        ]
        known_confusions = [
            (alias, canonical, self._transcript_qa_words(alias))
            for alias, canonical in getattr(self, "transcript_qa_known_confusions", [])
            if alias and canonical
        ]
        issues: List[Dict[str, Any]] = []
        seen = set()

        for segment_index, segment in enumerate(self.transcript_segments):
            word_spans = self._transcript_qa_word_spans(segment.text or "")
            words = [item["word"] for item in word_spans]

            if not words:
                continue

            for alias, canonical, alias_words in known_confusions:
                if not alias_words or len(words) < len(alias_words):
                    continue

                for start in range(0, len(words) - len(alias_words) + 1):
                    window = words[start:start + len(alias_words)]
                    matched = True

                    for offset, alias_word in enumerate(alias_words):
                        is_final_word = offset == len(alias_words) - 1

                        if not self._transcript_qa_word_matches(window[offset], alias_word, is_final_word):
                            matched = False
                            break

                    if not matched:
                        continue

                    observed = " ".join(window)
                    key = (segment_index, observed, canonical)

                    if key in seen:
                        continue

                    seen.add(key)
                    issues.append({
                        "segment_index": segment_index,
                        "observed": observed,
                        "suggestion": canonical,
                        "word_start": start,
                        "word_count": len(alias_words),
                        "reason": "known ASR confusion",
                    })

                    if len(issues) >= max_issues:
                        return issues

            for term, glossary_words in glossary_word_lists:
                if not glossary_words:
                    continue

                if self._transcript_qa_has_glossary_sequence(words, glossary_words):
                    continue

                if len(glossary_words) > 1:
                    max_distance = 2

                    for start in range(0, len(words) - len(glossary_words) + 1):
                        window = words[start:start + len(glossary_words)]
                        distances = [
                            self._transcript_qa_edit_distance(
                                candidate_word.rstrip("'s") if offset == len(glossary_words) - 1 else candidate_word,
                                glossary_word,
                            )
                            for offset, (candidate_word, glossary_word) in enumerate(zip(window, glossary_words))
                        ]

                        if sum(distances) <= max_distance and any(distance > 0 for distance in distances):
                            observed = " ".join(window)
                            key = (segment_index, observed, term)

                            if key in seen:
                                continue

                            seen.add(key)
                            issues.append({
                                "segment_index": segment_index,
                                "observed": observed,
                                "suggestion": term,
                                "word_start": start,
                                "word_count": len(glossary_words),
                                "reason": "possible glossary phrase",
                            })

                            if len(issues) >= max_issues:
                                return issues

                            break

                    continue

                glossary_word = glossary_words[0]

                if len(glossary_word) < 5:
                    continue

                max_distance = 1 if len(glossary_word) <= 7 else 2

                for word_index, word in enumerate(words):
                    if word == glossary_word or word == f"{glossary_word}'s":
                        continue

                    if abs(len(word) - len(glossary_word)) > max_distance:
                        continue

                    distance = self._transcript_qa_edit_distance(
                        word.rstrip("'s"),
                        glossary_word
                    )

                    if distance <= max_distance:
                        key = (segment_index, word, term)

                        if key in seen:
                            continue

                        seen.add(key)
                        issues.append({
                            "segment_index": segment_index,
                            "observed": word,
                            "suggestion": term,
                            "word_start": word_index,
                            "word_count": 1,
                            "reason": "possible glossary term",
                        })

                        if len(issues) >= max_issues:
                            return issues

                        break

        return issues

    def _refresh_transcript_qa_panel(self) -> None:
        """Refresh the local transcript QA warning panel."""
        self.transcript_qa_after_id = None
        issues = self._transcript_qa_find_glossary_issues()
        self.transcript_qa_issues = issues
        self._render_transcript_qa_issues(issues)

    def _render_transcript_qa_issues(self, issues: List[Dict[str, Any]]) -> None:
        """Render a compact, clickable list of local transcript QA warnings."""
        if not hasattr(self, "transcript_qa_issue_frame"):
            return

        text_widget = self._get_transcript_text_widget()

        for tag_name in text_widget.tag_names():
            tag_name = str(tag_name)
            if tag_name.startswith("transcript_qa_issue_"):
                text_widget.tag_delete(tag_name)

        for child in self.transcript_qa_issue_frame.winfo_children():
            child.destroy()

        if not self.transcript_segments:
            self.transcript_qa_issue_frame.pack_forget()
            self.transcript_qa_status_label.configure(
                text="No transcript loaded",
                text_color=COLORS["text_muted"]
            )
            return

        if not issues:
            self.transcript_qa_issue_frame.pack_forget()
            self.transcript_qa_status_label.configure(
                text="No glossary term warnings",
                text_color=COLORS["success"]
            )
            return

        hidden_count = max(0, len(issues) - 6)
        suffix = f" (+{hidden_count} more)" if hidden_count else ""
        self.transcript_qa_status_label.configure(
            text=f"{len(issues):,} possible glossary term warning(s){suffix}",
            text_color=COLORS["warning"]
        )

        try:
            self.transcript_qa_issue_frame.pack(
                fill="x",
                padx=15,
                pady=(0, 8),
                before=self.transcript_cursor_status_label
            )
        except Exception:
            self.transcript_qa_issue_frame.pack(fill="x", padx=15, pady=(0, 8))

        for issue_index, issue in enumerate(issues):
            self._tag_transcript_qa_issue(issue_index, issue)

        for issue_index, issue in enumerate(issues[:6]):
            segment_index = int(issue.get("segment_index", 0))
            observed = str(issue.get("observed") or "").strip()
            suggestion = str(issue.get("suggestion") or "").strip()
            button_text = f"{segment_index + 1}: {observed} -> {suggestion}"

            issue_button = ctk.CTkButton(
                self.transcript_qa_issue_frame,
                text=button_text,
                command=lambda idx=segment_index: self._jump_to_transcript_qa_issue(idx),
                width=170,
                height=26,
                font=ctk.CTkFont(size=10),
                fg_color=COLORS["accent_secondary"],
                hover_color=COLORS["border"],
                corner_radius=6
            )
            issue_button.pack(side="left", padx=(0, 6), pady=(0, 4))

    def _tag_transcript_qa_issue(self, issue_index: int, issue: Dict[str, Any]) -> None:
        """Apply a simple underline/highlight tag to a suspect transcript term."""
        segment_index = issue.get("segment_index")

        if not isinstance(segment_index, int):
            return

        text_widget = self._get_transcript_text_widget()

        for info in getattr(self, "transcript_display_ranges", []):
            if info.get("segment_index") != segment_index:
                continue

            text_start = info.get("text_start")
            text_end = info.get("text_end")
            observed = str(issue.get("observed") or "").strip()

            if not text_start or not text_end or not observed:
                return

            try:
                start_index = text_widget.search(
                    observed,
                    text_start,
                    stopindex=text_end,
                    nocase=True
                )

                if not start_index:
                    return

                end_index = f"{start_index}+{len(observed)}c"
                tag_name = f"transcript_qa_issue_{issue_index}"
                text_widget.tag_add(tag_name, start_index, end_index)
                text_widget.tag_configure(
                    tag_name,
                    underline=True,
                    foreground=COLORS["warning"]
                )
                text_widget.tag_bind(
                    tag_name,
                    "<Button-3>",
                    lambda event, idx=issue_index: self._show_transcript_qa_context_menu(event, idx)
                )
            except Exception:
                return

            return

    def _show_transcript_qa_context_menu(self, event, issue_index: int):
        """Show an explicit correction menu for a suspect glossary term."""
        if issue_index < 0 or issue_index >= len(getattr(self, "transcript_qa_issues", [])):
            return "break"

        issue = self.transcript_qa_issues[issue_index]
        suggestion = str(issue.get("suggestion") or "").strip()

        if not suggestion:
            return "break"

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label=f"Replace with '{suggestion}'",
            command=lambda: self._apply_transcript_qa_suggestion(issue_index)
        )
        menu.add_separator()
        menu.add_command(label="Ignore", command=lambda: None)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

        return "break"

    def _apply_transcript_qa_suggestion(self, issue_index: int) -> None:
        """Apply a user-selected glossary suggestion to one suspect span."""
        if issue_index < 0 or issue_index >= len(getattr(self, "transcript_qa_issues", [])):
            return

        issue = self.transcript_qa_issues[issue_index]
        segment_index = issue.get("segment_index")
        suggestion = str(issue.get("suggestion") or "").strip()
        word_start = issue.get("word_start")
        word_count = issue.get("word_count")

        if (
            not isinstance(segment_index, int)
            or not isinstance(word_start, int)
            or not isinstance(word_count, int)
            or not suggestion
            or segment_index < 0
            or segment_index >= len(self.transcript_segments)
            or word_count <= 0
        ):
            return

        segment = self.transcript_segments[segment_index]
        text = segment.text or ""
        word_spans = self._transcript_qa_word_spans(text)

        if word_start < 0 or word_start + word_count > len(word_spans):
            return

        start_char = int(word_spans[word_start]["start"])
        end_char = int(word_spans[word_start + word_count - 1]["end"])

        self._end_transcript_text_edit_phase()
        self._push_transcript_undo_state("term QA correction")
        segment.text = text[:start_char] + suggestion + text[end_char:]
        self.selected_transcript_segment_index = segment_index
        self._refresh_transcript_display()
        self._place_transcript_cursor_at_segment_offset(segment_index, start_char + len(suggestion))

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=(
                    f"Applied Term QA suggestion in segment {segment_index + 1:,}. "
                    "Ctrl+Z undo."
                ),
                text_color=COLORS["text_primary"]
            )

    def _jump_to_transcript_qa_issue(self, segment_index: int) -> None:
        """Select and scroll to a segment with a transcript QA warning."""
        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return

        self.selected_transcript_segment_index = segment_index
        self._refresh_transcript_display()

        text_widget = self._get_transcript_text_widget()

        for info in getattr(self, "transcript_display_ranges", []):
            if info.get("segment_index") != segment_index:
                continue

            try:
                target_index = info.get("text_start") or info.get("start")
                text_widget.mark_set("insert", target_index)
                text_widget.see(target_index)
            except Exception:
                pass

            break

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=(
                    f"QA selected segment {segment_index + 1:,}/{len(self.transcript_segments):,}. "
                    "Review warning; no text was changed."
                ),
                text_color=COLORS["warning"]
            )

        if hasattr(self, "_refresh_transcript_timeline"):
            self._refresh_transcript_timeline()


    def _transcript_time_to_seconds(self, value: str) -> Optional[float]:
        """Convert transcript time to seconds."""
        if not value:
            return None

        value = value.strip().replace(",", ".")
        parts = value.split(":")

        try:
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds

            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds

            return float(value)

        except ValueError:
            return None

    def _seconds_to_transcript_time(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS.mmm transcript time."""
        seconds = max(0.0, float(seconds))
        hours = int(seconds // 3600)
        seconds -= hours * 3600
        minutes = int(seconds // 60)
        seconds -= minutes * 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    def _estimate_segment_cursor_time(self, segment_index: int, char_offset: int) -> str:
        """Estimate transcript time for a cursor offset within one segment."""
        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return ""

        segment = self.transcript_segments[segment_index]
        start_seconds = self._transcript_time_to_seconds(segment.start)
        end_seconds = self._transcript_time_to_seconds(segment.end)

        if start_seconds is None or end_seconds is None:
            return ""

        if end_seconds <= start_seconds:
            return ""

        text_length = max(1, len(segment.text or ""))
        ratio = max(0.0, min(1.0, char_offset / text_length))
        cursor_seconds = start_seconds + ((end_seconds - start_seconds) * ratio)
        return self._seconds_to_transcript_time(cursor_seconds)

    def _get_transcript_segment_at_text_index(self, text_index: str) -> Optional[dict]:
        """Return displayed segment range for a textbox index."""
        if not hasattr(self, "transcript_display_ranges"):
            return None

        text_widget = self._get_transcript_text_widget()

        for info in self.transcript_display_ranges:
            try:
                after_start = text_widget.compare(text_index, ">=", info["start"])
                before_end = text_widget.compare(text_index, "<=", info["end"])
            except Exception:
                continue

            if after_start and before_end:
                return info

        return None

    def _estimate_text_offset_in_segment(self, info: dict, text_index: str) -> int:
        """Estimate character offset in the actual segment text for a textbox index."""
        text_widget = self._get_transcript_text_widget()
        segment_text = info.get("text") or ""

        if not segment_text:
            return 0

        text_start = info.get("text_start") or info.get("start")
        text_end = info.get("text_end") or info.get("end")

        try:
            if text_widget.compare(text_index, "<", text_start):
                return 0

            if text_widget.compare(text_index, ">", text_end):
                return len(segment_text)

            display_text_before_cursor = text_widget.get(text_start, text_index)

        except Exception:
            return 0

        # In the normal segment preview, displayed text matches segment.text.
        # Use exact length first instead of a ratio.
        exact_offset = len(display_text_before_cursor)

        if 0 <= exact_offset <= len(segment_text):
            return exact_offset

        # Fallback for paragraph-wrapped/preview-modified text.
        try:
            display_text_full = text_widget.get(text_start, text_end)
        except Exception:
            display_text_full = display_text_before_cursor

        visible_chars = max(1, len(display_text_full))
        ratio = max(0.0, min(1.0, len(display_text_before_cursor) / visible_chars))
        return int(round(len(segment_text) * ratio))

    def _snap_transcript_split_offset_to_word_boundary(self, text: str, offset: int) -> int:
        """Snap a split offset to the nearest word boundary to avoid broken words."""
        if not text:
            return offset

        offset = max(0, min(len(text), int(offset)))

        if offset <= 0 or offset >= len(text):
            return offset

        # If the cursor is already on whitespace, keep that clean boundary.
        if text[offset].isspace() or text[offset - 1].isspace():
            return offset

        # Cursor is inside a word. Find the word span.
        left = offset
        while left > 0 and not text[left - 1].isspace():
            left -= 1

        right = offset
        while right < len(text) and not text[right].isspace():
            right += 1

        # Prefer the nearest boundary. On ties, prefer the right boundary,
        # because users usually click near a word to split after it.
        distance_left = offset - left
        distance_right = right - offset

        if distance_right <= distance_left:
            return right

        return left


    def _get_editable_transcript_text_info(self, text_index: str) -> Optional[dict]:
        """Return segment info if text_index is inside editable segment text."""
        info = self._get_transcript_segment_at_text_index(text_index)

        if not info:
            return None

        text_widget = self._get_transcript_text_widget()
        text_start = info.get("text_start")
        text_end = info.get("text_end")

        if not text_start or not text_end:
            return None

        try:
            inside_text = (
                text_widget.compare(text_index, ">=", text_start)
                and text_widget.compare(text_index, "<=", text_end)
            )
        except Exception:
            return None

        return info if inside_text else None

    def _place_transcript_cursor_at_segment_offset(self, segment_index: int, char_offset: int) -> None:
        """Place the textbox cursor back inside a segment after preview redraw."""
        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return

        if not hasattr(self, "transcript_display_ranges"):
            return

        text_widget = self._get_transcript_text_widget()

        for info in self.transcript_display_ranges:
            if info.get("segment_index") != segment_index:
                continue

            text_start = info.get("text_start")
            text_end = info.get("text_end")

            if not text_start or not text_end:
                return

            segment_text = self.transcript_segments[segment_index].text or ""
            char_offset = max(0, min(int(char_offset), len(segment_text)))

            try:
                target_index = f"{text_start}+{char_offset}c"

                if text_widget.compare(target_index, ">", text_end):
                    target_index = text_end

                text_widget.mark_set("insert", target_index)
                text_widget.see(target_index)
                self.selected_transcript_segment_index = segment_index
                self._on_transcript_preview_cursor_changed()
            except Exception:
                return

            return

    def _begin_transcript_text_edit_phase(self, segment_index: int) -> None:
        """Create one undo checkpoint for a continuous edit phase."""
        if self.transcript_text_edit_phase_segment_index != segment_index:
            self._push_transcript_undo_state("text edit")
            self.transcript_text_edit_phase_segment_index = segment_index

    def _end_transcript_text_edit_phase(self) -> None:
        """End current text edit phase so the next edit gets a new undo checkpoint."""
        self.transcript_text_edit_phase_segment_index = None

    def _edit_transcript_segment_text_at_cursor(self, event, info: dict) -> str:
        """Apply a typing/deletion key directly to the selected segment model."""
        keysym = getattr(event, "keysym", "")
        char = getattr(event, "char", "")

        segment_index = info.get("segment_index")
        if not isinstance(segment_index, int):
            return "break"

        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return "break"

        text_widget = self._get_transcript_text_widget()

        try:
            text_index = text_widget.index("insert")
        except Exception:
            return "break"

        segment = self.transcript_segments[segment_index]
        original_text = segment.text or ""
        offset = self._estimate_text_offset_in_segment(info, text_index)
        offset = max(0, min(offset, len(original_text)))

        new_offset = offset
        new_text = original_text

        if keysym == "BackSpace":
            if offset <= 0:
                return "break"

            self._begin_transcript_text_edit_phase(segment_index)
            new_text = original_text[:offset - 1] + original_text[offset:]
            new_offset = offset - 1

        elif keysym == "Delete":
            if offset >= len(original_text):
                return "break"

            self._begin_transcript_text_edit_phase(segment_index)
            new_text = original_text[:offset] + original_text[offset + 1:]
            new_offset = offset

        elif char:
            self._begin_transcript_text_edit_phase(segment_index)
            new_text = original_text[:offset] + char + original_text[offset:]
            new_offset = offset + len(char)

        else:
            return "break"

        segment.text = new_text
        self.selected_transcript_segment_index = segment_index

        self._refresh_transcript_display()
        self._place_transcript_cursor_at_segment_offset(segment_index, new_offset)

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"Editing segment {segment_index + 1:,}. Ctrl+Z undo, Ctrl+Y redo.",
                text_color=COLORS["text_primary"]
            )

        return "break"

    def _paste_transcript_text_at_cursor(self, event=None):
        """Paste clipboard text into the selected transcript segment model."""
        if not self.transcript_segments:
            return "break"

        try:
            paste_text = self.clipboard_get()
        except Exception:
            return "break"

        if not paste_text:
            return "break"

        text_widget = self._get_transcript_text_widget()

        try:
            text_index = text_widget.index("insert")
        except Exception:
            return "break"

        info = self._get_editable_transcript_text_info(text_index)

        if not info:
            return "break"

        segment_index = info.get("segment_index")

        if (
            not isinstance(segment_index, int)
            or segment_index < 0
            or segment_index >= len(self.transcript_segments)
        ):
            return "break"

        segment = self.transcript_segments[segment_index]
        original_text = segment.text or ""
        start_offset = self._estimate_text_offset_in_segment(info, text_index)
        end_offset = start_offset

        try:
            selection_ranges = text_widget.tag_ranges("sel")
        except Exception:
            selection_ranges = ()

        if len(selection_ranges) >= 2:
            selection_start = str(selection_ranges[0])
            selection_end = str(selection_ranges[1])
            start_info = self._get_editable_transcript_text_info(selection_start)
            end_info = self._get_editable_transcript_text_info(selection_end)

            if (
                start_info
                and end_info
                and start_info.get("segment_index") == segment_index
                and end_info.get("segment_index") == segment_index
            ):
                start_offset = self._estimate_text_offset_in_segment(info, selection_start)
                end_offset = self._estimate_text_offset_in_segment(info, selection_end)

        start_offset = max(0, min(start_offset, len(original_text)))
        end_offset = max(start_offset, min(end_offset, len(original_text)))
        normalized_paste = paste_text.replace("\r\n", "\n").replace("\r", "\n")

        self._begin_transcript_text_edit_phase(segment_index)
        segment.text = original_text[:start_offset] + normalized_paste + original_text[end_offset:]
        self.selected_transcript_segment_index = segment_index

        new_offset = start_offset + len(normalized_paste)
        self._refresh_transcript_display()
        self._place_transcript_cursor_at_segment_offset(segment_index, new_offset)

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"Pasted into segment {segment_index + 1:,}. Ctrl+Z undo, Ctrl+Y redo.",
                text_color=COLORS["text_primary"]
            )

        return "break"

    def _on_transcript_preview_key_press(self, event=None):
        """Model-based inline editing: edit only segment.text, never the formatted preview."""
        if event is None:
            return None

        keysym = getattr(event, "keysym", "")
        ctrl_pressed = bool(getattr(event, "state", 0) & 0x4)

        if ctrl_pressed:
            if keysym.lower() == "z":
                self._end_transcript_text_edit_phase()
                self.undo_transcript_edit()
                return "break"

            if keysym.lower() == "y":
                self._end_transcript_text_edit_phase()
                self.redo_transcript_edit()
                return "break"

            if keysym.lower() in {"c", "a"}:
                return None

            if keysym.lower() == "v":
                return self._paste_transcript_text_at_cursor(event)

            return "break"

        allowed_navigation_keys = {
            "Left", "Right", "Up", "Down",
            "Home", "End", "Prior", "Next",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Escape",
        }

        if keysym in allowed_navigation_keys:
            return None

        if keysym in {"Return", "KP_Enter"}:
            self._end_transcript_text_edit_phase()
            self._split_selected_transcript_segment_at_cursor()
            return "break"

        text_widget = self._get_transcript_text_widget()

        try:
            text_index = text_widget.index("insert")
        except Exception:
            return "break"

        info = self._get_editable_transcript_text_info(text_index)

        if not info:
            if getattr(event, "char", "") or keysym in {"BackSpace", "Delete", "Tab"}:
                return "break"
            return None

        if keysym == "Tab":
            return "break"

        if keysym in {"BackSpace", "Delete"} or getattr(event, "char", ""):
            return self._edit_transcript_segment_text_at_cursor(event, info)

        return None


    def _split_selected_transcript_segment_at_cursor(self) -> None:
        """Split the selected transcript segment at the current cursor position."""
        if not self.transcript_segments:
            return

        text_widget = self._get_transcript_text_widget()

        try:
            text_index = text_widget.index("insert")
        except Exception:
            return

        info = self._get_transcript_segment_at_text_index(text_index)
        if not info:
            messagebox.showwarning(
                "No Segment Selected",
                "Click inside a transcript segment before pressing Enter."
            )
            return

        segment_index = info["segment_index"]

        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return

        # Only split from the actual text body, not the speaker label or timestamp line.
        text_start = info.get("text_start")
        text_end = info.get("text_end")

        if text_start and text_end:
            try:
                if text_widget.compare(text_index, "<", text_start) or text_widget.compare(text_index, ">", text_end):
                    messagebox.showwarning(
                        "Invalid Split Point",
                        "Click inside the transcript text, not the speaker name or timestamp."
                    )
                    return
            except Exception:
                pass

        original = self.transcript_segments[segment_index]
        original_text = original.text or ""

        self._end_transcript_text_edit_phase()
        self._push_transcript_undo_state("split segment")

        char_offset = self._estimate_text_offset_in_segment(info, text_index)
        snapped_offset = self._snap_transcript_split_offset_to_word_boundary(
            original_text,
            char_offset
        )

        if snapped_offset != char_offset:
            char_offset = snapped_offset

        if char_offset <= 0 or char_offset >= len(original_text):
            messagebox.showwarning(
                "Invalid Split Point",
                "Click inside the text first. The split point cannot be at the very beginning or end."
            )
            return

        part1_text = original_text[:char_offset].strip()
        part2_text = original_text[char_offset:].strip()

        if not part1_text or not part2_text:
            messagebox.showwarning(
                "Invalid Split Point",
                "Both split parts need text."
            )
            return

        split_time = self._estimate_segment_cursor_time(segment_index, char_offset)

        part1 = TranscriptSegment(
            speaker=original.speaker,
            start=original.start,
            end=split_time,
            text=part1_text,
        )

        part2 = TranscriptSegment(
            speaker=original.speaker,
            start=split_time,
            end=original.end,
            text=part2_text,
        )

        self.transcript_segments[segment_index:segment_index + 1] = [part1, part2]

        self._refresh_transcript_display()

        time_note = f" at {split_time}" if split_time else ""
        self.log_message(
            f"Split segment {segment_index + 1:,}{time_note}",
            "success"
        )

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=(
                    f"Split segment {segment_index + 1:,} into two segments"
                    f"{time_note}."
                ),
                text_color=COLORS["text_primary"]
            )



    def _on_transcript_preview_interaction(self, event=None):
        """Handle transcript preview click/key interaction, then sync timeline selection."""
        try:
            self._on_transcript_preview_cursor_changed(event)
        finally:
            if hasattr(self, "_refresh_transcript_timeline"):
                self.after(75, self._refresh_transcript_timeline)

        return None


    def _on_transcript_preview_cursor_changed(self, event=None):
        """Update selected segment details when the transcript cursor changes."""
        if not self.transcript_segments:
            return

        text_widget = self._get_transcript_text_widget()

        try:
            text_index = text_widget.index("insert")
        except Exception:
            return

        info = self._get_transcript_segment_at_text_index(text_index)
        if not info:
            if hasattr(self, "transcript_cursor_status_label"):
                self.transcript_cursor_status_label.configure(
                    text="No segment selected.",
                    text_color=COLORS["text_muted"]
                )

        if hasattr(self, "_refresh_transcript_timeline"):
            self._refresh_transcript_timeline()
            return

        segment_index = info["segment_index"]
        self.selected_transcript_segment_index = segment_index
        segment = self.transcript_segments[segment_index]

        char_offset = self._estimate_text_offset_in_segment(info, text_index)
        estimated_time = self._estimate_segment_cursor_time(segment_index, char_offset)

        time_text = f" • estimated time {estimated_time}" if estimated_time else ""
        speaker = segment.speaker or "Speaker"

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=(
                    f"Selected segment {segment_index + 1:,}/{len(self.transcript_segments):,} "
                    f"• {speaker} • character {char_offset:,}/{len(segment.text or ''):,}"
                    f"{time_text}"
                ),
                text_color=COLORS["text_primary"]
            )


    def _select_transcript_segment_from_preview(self, segment_index: int, event=None):
        """Select a transcript segment when the user clicks its rendered preview text."""
        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return None

        self.selected_transcript_segment_index = segment_index

        segment = self.transcript_segments[segment_index]
        speaker = segment.speaker or "Speaker"
        start = segment.start or "no start"
        end = segment.end or "no end"

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=(
                    f"Selected segment {segment_index + 1:,}/{len(self.transcript_segments):,} "
                    f"from transcript • {speaker} • {start} → {end}"
                ),
                text_color=COLORS["text_primary"]
            )

        if hasattr(self, "_refresh_transcript_timeline"):
            self._refresh_transcript_timeline()
            self.after(50, self._refresh_transcript_timeline)

        return None






    def _get_transcript_segment_index_at_time(self, seconds: float) -> Optional[int]:
        """Return the transcript segment index that contains the given time."""
        try:
            seconds = float(seconds)
        except Exception:
            return None

        for index, segment in enumerate(self.transcript_segments):
            start_seconds = self._transcript_time_to_seconds(segment.start)
            end_seconds = self._transcript_time_to_seconds(segment.end)

            if start_seconds is None or end_seconds is None:
                continue

            if end_seconds < start_seconds:
                continue

            if start_seconds <= seconds <= end_seconds:
                return index

        return None

    def _sync_transcript_selection_to_playback_time(self, seconds: float) -> None:
        """Update selected/current transcript segment while playback moves."""
        segment_index = self._get_transcript_segment_index_at_time(seconds)

        if segment_index is None:
            return

        if getattr(self, "transcript_playback_active_segment_index", None) == segment_index:
            return

        self.transcript_playback_active_segment_index = segment_index

        if getattr(self, "selected_transcript_segment_index", None) != segment_index:
            self.selected_transcript_segment_index = segment_index
            self._refresh_transcript_display()






    def _restore_main_scroll_focus(self) -> None:
        """Return focus to the main scroll area after clicking small controls."""
        try:
            self.main_frame._parent_canvas.focus_set()
            return
        except Exception:
            pass

        try:
            self.focus_set()
        except Exception:
            pass

    def _scroll_main_frame_with_mousewheel(self, event) -> str:
        """Scroll the main app at a normal Windows wheel speed."""
        try:
            canvas = self.main_frame._parent_canvas
        except Exception:
            return "break"

        delta = getattr(event, "delta", 0)
        lines_per_notch = 5

        if delta:
            notches = int(delta / 120)
            if notches:
                units = -lines_per_notch * notches
            else:
                # Preserve high-resolution wheel/touchpad input without making
                # a full Windows wheel notch crawl by only one line.
                units = -1 if delta > 0 else 1
        else:
            # Linux/X11 fallback if ever used.
            button_number = getattr(event, "num", None)
            units = -lines_per_notch if button_number == 4 else lines_per_notch

        try:
            canvas.yview_scroll(units, "units")
        except Exception:
            pass

        return "break"

    def _bind_transcript_sync_controls_scroll_passthrough(self) -> None:
        """Keep main mouse-wheel scrolling working after using sync controls."""
        sync_widgets = [
            getattr(self, "transcript_audio_sync_label", None),
            getattr(self, "transcript_audio_sync_minus_button", None),
            getattr(self, "transcript_audio_sync_plus_button", None),
            getattr(self, "transcript_audio_sync_reset_button", None),
            getattr(self, "transcript_audio_sync_fine_minus_button", None),
            getattr(self, "transcript_audio_sync_fine_plus_button", None),
            getattr(self, "transcript_audio_sync_shortcuts_label", None),
            getattr(self, "transcript_timeline_pan_slider", None),
            getattr(self, "transcript_timeline_zoom_slider", None),
        ]

        for widget in sync_widgets:
            if widget is None:
                continue

            try:
                widget.bind("<MouseWheel>", self._scroll_main_frame_with_mousewheel)
                widget.bind("<Button-4>", self._scroll_main_frame_with_mousewheel)
                widget.bind("<Button-5>", self._scroll_main_frame_with_mousewheel)
                widget.bind("<ButtonRelease-1>", lambda _event: self._restore_main_scroll_focus())
                widget.bind("<Leave>", lambda _event: self._restore_main_scroll_focus())
            except Exception:
                pass



    def _on_visual_sync_minus_shortcut(self, event=None):
        """Keyboard shortcut: fine visual sync backward."""
        self._adjust_transcript_audio_sync_offset(-0.01)
        return "break"

    def _on_visual_sync_plus_shortcut(self, event=None):
        """Keyboard shortcut: fine visual sync forward."""
        self._adjust_transcript_audio_sync_offset(0.01)
        return "break"

    def _on_visual_sync_reset_shortcut(self, event=None):
        """Keyboard shortcut: reset visual sync offset."""
        self._reset_transcript_audio_sync_offset()
        return "break"


    def _get_transcript_audio_sync_offset_seconds(self) -> float:
        """Return visual sync offset in seconds."""
        try:
            return float(getattr(self, "transcript_audio_sync_offset_seconds", 0.0))
        except Exception:
            return 0.0

    def _update_transcript_audio_sync_label(self) -> None:
        """Refresh audio sync label."""
        if not hasattr(self, "transcript_audio_sync_label"):
            return

        offset_seconds = self._get_transcript_audio_sync_offset_seconds()
        offset_ms = int(round(offset_seconds * 1000))

        if offset_ms > 0:
            label = f"Visual: +{offset_ms} ms"
        elif offset_ms < 0:
            label = f"Visual: {offset_ms} ms"
        else:
            label = "Visual: 0 ms"

        self.transcript_audio_sync_label.configure(
            text=label,
            text_color=COLORS["text_secondary"] if offset_ms else COLORS["text_muted"]
        )

    def _adjust_transcript_audio_sync_offset(self, delta_seconds: float) -> None:
        """Shift visual timeline marker relative to VLC audio clock."""
        current = self._get_transcript_audio_sync_offset_seconds()
        new_value = max(-2.0, min(2.0, current + float(delta_seconds)))
        self.transcript_audio_sync_offset_seconds = new_value
        self._update_transcript_audio_sync_label()

        if hasattr(self, "transcript_cursor_status_label"):
            offset_ms = int(round(new_value * 1000))
            self.transcript_cursor_status_label.configure(
                text=f"Audio sync offset: {offset_ms:+d} ms",
                text_color=COLORS["text_primary"]
            )

        self._refresh_transcript_timeline()
        self._restore_main_scroll_focus()

    def _reset_transcript_audio_sync_offset(self) -> None:
        """Reset visual/audio sync offset."""
        self.transcript_audio_sync_offset_seconds = 0.0
        self._update_transcript_audio_sync_label()

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text="Audio sync offset reset.",
                text_color=COLORS["text_muted"]
            )

        self._refresh_transcript_timeline()
        self._restore_main_scroll_focus()


    def check_transcript_vlc_ready(self, show_success: bool = False) -> bool:
        """Check whether VLC playback is available."""
        try:
            self._get_or_create_transcript_vlc_player()
        except Exception as error:
            self.transcript_vlc_ready_checked = True
            self.transcript_vlc_ready = False
            self.transcript_vlc_error = str(error)

            messagebox.showerror(
                "VLC Playback Not Ready",
                (
                    "VLC playback is not ready.\n\n"
                    f"{error}\n\n"
                    "Install VLC Media Player and make sure python-vlc is installed "
                    "inside this app's virtual environment."
                )
            )
            return False

        self.transcript_vlc_ready_checked = True
        self.transcript_vlc_ready = True
        self.transcript_vlc_error = None

        if show_success:
            messagebox.showinfo(
                "VLC Ready",
                "VLC playback is ready."
            )

        return True


    def _get_transcript_vlc_module(self):
        """Load python-vlc and help it find VLC on Windows."""
        cached_module = getattr(self, "transcript_vlc_module", None)

        if cached_module is not None:
            return cached_module

        if os.name == "nt":
            for vlc_dir in (
                r"C:\Program Files\VideoLAN\VLC",
                r"C:\Program Files (x86)\VideoLAN\VLC",
            ):
                libvlc_path = os.path.join(vlc_dir, "libvlc.dll")

                if os.path.exists(libvlc_path):
                    try:
                        os.add_dll_directory(vlc_dir)
                    except Exception:
                        pass

                    if vlc_dir not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = vlc_dir + os.pathsep + os.environ.get("PATH", "")

                    break

        try:
            import vlc
        except Exception as error:
            raise RuntimeError(
                "VLC playback is not available. Install VLC Media Player, then run "
                "'python -m pip install python-vlc==3.0.21203' inside the app venv."
            ) from error

        self.transcript_vlc_module = vlc
        return vlc

    def _get_or_create_transcript_vlc_player(self):
        """Create or reuse an audio-only VLC media player."""
        self._get_transcript_vlc_module()

        if getattr(self, "transcript_vlc_instance", None) is None:
            self.transcript_vlc_instance = self.transcript_vlc_module.Instance(
                "--quiet",
                "--intf=dummy",
                "--no-video",
                "--vout=dummy",
                "--no-video-title-show"
            )

        if getattr(self, "transcript_vlc_player", None) is None:
            self.transcript_vlc_player = self.transcript_vlc_instance.media_player_new()

        return self.transcript_vlc_player


    def _set_transcript_vlc_media(self, media_path: str, start_seconds: Optional[float] = None) -> None:
        """Attach a media file to the VLC player."""
        player = self._get_or_create_transcript_vlc_player()
        media_path = os.path.abspath(media_path)

        try:
            media = self.transcript_vlc_instance.media_new_path(media_path)
        except Exception:
            media = self.transcript_vlc_instance.media_new(media_path)

        try:
            media.add_option(":no-video")
            media.add_option(":vout=dummy")
            media.add_option(":no-video-title-show")

            if start_seconds is not None:
                media.add_option(f":start-time={max(0.0, float(start_seconds)):.3f}")
        except Exception:
            pass

        player.set_media(media)
        self.transcript_vlc_media_path = media_path
        self.transcript_media_duration_seconds = None


    def _is_transcript_vlc_playing(self) -> bool:
        """Return whether VLC is actively playing."""
        player = getattr(self, "transcript_vlc_player", None)

        if player is None:
            return False

        try:
            return bool(player.is_playing())
        except Exception:
            return False


    def _get_transcript_playback_start_time(self) -> Optional[float]:
        """Return timeline playback start time in seconds."""
        playhead_seconds = getattr(self, "transcript_playhead_seconds", None)

        if isinstance(playhead_seconds, (int, float)):
            return float(playhead_seconds)

        selected_time = self._get_transcript_selected_segment_center_time()

        if selected_time is not None:
            return selected_time

        min_time, _max_time = self._get_transcript_timeline_bounds()
        return min_time

    def _update_transcript_playback_buttons(self, playing: bool) -> None:
        """Update single Play/Pause toggle button state."""
        if hasattr(self, "transcript_play_button"):
            self.transcript_play_button.configure(
                state="normal",
                text="Pause" if playing else "▶ Play",
                fg_color=COLORS["accent_secondary"] if playing else COLORS["accent"],
                hover_color=COLORS["border"] if playing else COLORS["accent_hover"],
                text_color=COLORS["text_primary"] if playing else "#000000"
            )

        if hasattr(self, "transcript_pause_button"):
            try:
                self.transcript_pause_button.pack_forget()
            except Exception:
                pass

        if hasattr(self, "transcript_playback_status_label"):
            self.transcript_playback_status_label.configure(
                text="Playing" if playing else "",
                text_color=COLORS["accent"] if playing else COLORS["text_muted"]
            )


    def _stop_transcript_playback_process(self) -> None:
        """Stop active transcript playback and cancel timers."""
        self.transcript_playback_generation = getattr(self, "transcript_playback_generation", 0) + 1
        after_id = getattr(self, "transcript_playback_after_id", None)

        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass

        self.transcript_playback_after_id = None

        player = getattr(self, "transcript_vlc_player", None)

        if player is not None:
            try:
                player.stop()
            except Exception:
                pass

        process = getattr(self, "transcript_playback_process", None)

        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

        self.transcript_playback_process = None
        self.transcript_playback_backend = None
        self.transcript_playback_start_seconds = None
        self.transcript_playback_start_wall_time = None
        self.transcript_playback_requested_start_seconds = None
        self.transcript_vlc_clock_anchor_seconds = None
        self.transcript_vlc_clock_anchor_wall_time = None
        self.transcript_vlc_last_reported_seconds = None

    def _schedule_transcript_playback_tick(self) -> None:
        after_id = getattr(self, "transcript_playback_after_id", None)
        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        generation = getattr(self, "transcript_playback_generation", 0)

        def tick_if_current() -> None:
            if generation != getattr(self, "transcript_playback_generation", 0):
                return
            self.transcript_playback_after_id = None
            self._tick_transcript_timeline_playback(generation=generation)

        self.transcript_playback_after_id = self.after(
            int(getattr(self, "transcript_playback_tick_ms", 30)),
            tick_if_current,
        )


    def toggle_transcript_timeline_playback(self) -> None:
        """Toggle transcript timeline playback from one button."""
        if self._is_transcript_vlc_playing():
            self.pause_transcript_timeline()
            return

        process = getattr(self, "transcript_playback_process", None)

        if process is not None:
            try:
                if process.poll() is None:
                    self.pause_transcript_timeline()
                    return
            except Exception:
                pass

        self.play_transcript_timeline()


    def play_transcript_timeline(self) -> None:
        """Play linked media audio from the current transcript timeline marker using VLC."""
        media_path = getattr(self, "linked_transcript_media_path", None)

        if not media_path:
            messagebox.showwarning(
                "No Linked Media",
                "Choose a media file first."
            )
            return

        if not os.path.exists(media_path):
            self._set_linked_transcript_media(None)
            messagebox.showerror(
                "Linked Media Missing",
                "The linked media file could not be found. Choose the media file again."
            )
            return

        if not self.check_transcript_vlc_ready(show_success=False):
            self._update_transcript_playback_buttons(False)
            return

        media_path = os.path.abspath(media_path)
        visual_start_seconds = self._get_transcript_playback_start_time()

        if visual_start_seconds is None:
            messagebox.showwarning(
                "No Timeline Time",
                "The transcript needs timestamps before playback can start."
            )
            return

        visual_start_seconds = float(visual_start_seconds)
        sync_offset = self._get_transcript_audio_sync_offset_seconds()
        media_start_seconds = max(0.0, visual_start_seconds - sync_offset)

        try:
            player = self._get_or_create_transcript_vlc_player()
        except Exception as error:
            messagebox.showerror("VLC Playback Error", str(error))
            self._update_transcript_playback_buttons(False)
            return

        self._stop_transcript_playback_process()

        try:
            self._set_transcript_vlc_media(media_path, start_seconds=media_start_seconds)
            player = self.transcript_vlc_player

            result = player.play()

            if result == -1:
                raise RuntimeError("VLC could not start playback.")

            # One safety seek only. Repeated seeking caused startup stutter.
            target_ms = int(media_start_seconds * 1000)

            def apply_single_start_seek() -> None:
                current_player = getattr(self, "transcript_vlc_player", None)

                if current_player is None or current_player is not player:
                    return

                try:
                    current_ms = current_player.get_time()
                except Exception:
                    current_ms = -1

                if current_ms >= 0 and abs(current_ms - target_ms) < 350:
                    return

                try:
                    current_player.set_time(target_ms)
                except Exception:
                    pass

            self.after(120, apply_single_start_seek)

        except Exception as error:
            self._stop_transcript_playback_process()
            messagebox.showerror("VLC Playback Error", str(error))
            self._update_transcript_playback_buttons(False)
            return

        self.transcript_playback_backend = "vlc"
        self.transcript_playback_generation = getattr(self, "transcript_playback_generation", 0) + 1
        self.transcript_playback_requested_start_seconds = media_start_seconds
        self.transcript_playback_start_seconds = media_start_seconds
        start_wall = self._transcript_playback_now()
        self.transcript_playback_start_wall_time = start_wall
        self.transcript_vlc_clock_anchor_seconds = media_start_seconds
        self.transcript_vlc_clock_anchor_wall_time = start_wall
        self.transcript_vlc_last_reported_seconds = None
        self.transcript_playhead_seconds = visual_start_seconds
        self.transcript_playback_active_segment_index = None
        self.transcript_playback_follow_active = False
        self.transcript_timeline_center_lock_active = True
        self.transcript_timeline_center_time = visual_start_seconds
        try:
            length_ms = player.get_length()
        except Exception:
            length_ms = -1
        if isinstance(length_ms, (int, float)) and length_ms > 0:
            self.transcript_media_duration_seconds = float(length_ms) / 1000.0

        if hasattr(self, "_center_transcript_timeline_pan_on_time"):
            self._center_transcript_timeline_pan_on_time(visual_start_seconds)

        self._sync_transcript_selection_to_playback_time(visual_start_seconds)
        self._refresh_transcript_timeline()

        self._update_transcript_playback_buttons(True)
        self._schedule_transcript_playback_tick()


    def pause_transcript_timeline(self) -> None:
        """Pause transcript timeline playback at the current marker."""
        current_seconds = self._update_transcript_playhead_from_playback_clock()

        if current_seconds is not None:
            self._sync_transcript_selection_to_playback_time(current_seconds)

        after_id = getattr(self, "transcript_playback_after_id", None)
        self.transcript_playback_generation = getattr(self, "transcript_playback_generation", 0) + 1

        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass

        self.transcript_playback_after_id = None

        player = getattr(self, "transcript_vlc_player", None)

        if player is not None and getattr(self, "transcript_playback_backend", None) == "vlc":
            try:
                player.pause()
                self.transcript_playback_backend = "vlc_paused"
            except Exception:
                self._stop_transcript_playback_process()
        else:
            self._stop_transcript_playback_process()

        self._update_transcript_playback_buttons(False)
        self.transcript_timeline_center_lock_active = False
        self._refresh_transcript_timeline()

    def _transcript_playback_now(self) -> float:
        clock = getattr(self, "_transcript_playback_clock", None)
        if callable(clock):
            try:
                return float(clock())
            except Exception:
                pass
        return time.perf_counter()

    def _update_transcript_playhead_from_playback_clock(self) -> Optional[float]:
        """Update playhead from VLC's media clock, with sync offset and monotonic smoothing."""
        backend = getattr(self, "transcript_playback_backend", None)

        if backend not in {"vlc", "vlc_paused"}:
            return None

        player = getattr(self, "transcript_vlc_player", None)

        if player is None:
            return None

        now = self._transcript_playback_now()

        try:
            raw_ms = player.get_time()
        except Exception:
            raw_ms = -1

        raw_media_seconds = None

        if raw_ms is not None and raw_ms >= 0:
            raw_media_seconds = raw_ms / 1000.0
        self.transcript_vlc_last_raw_media_seconds_for_debug = raw_media_seconds

        requested_media_start = getattr(self, "transcript_playback_requested_start_seconds", None)
        start_wall_time = getattr(self, "transcript_playback_start_wall_time", None)
        previous_displayed = getattr(self, "transcript_playhead_seconds", None)
        sync_offset = self._get_transcript_audio_sync_offset_seconds()

        # During startup, VLC may briefly report 0 before start-time lands.
        if (
            raw_media_seconds is not None
            and isinstance(requested_media_start, (int, float))
            and isinstance(start_wall_time, (int, float))
            and float(requested_media_start) > 0.5
            and raw_media_seconds < float(requested_media_start) - 0.5
            and now - float(start_wall_time) < 1.0
        ):
            raw_media_seconds = float(requested_media_start)

        last_reported = getattr(self, "transcript_vlc_last_reported_seconds", None)

        if raw_media_seconds is not None:
            raw_display_seconds = raw_media_seconds + sync_offset
            safe_to_anchor = True

            if (
                backend == "vlc"
                and isinstance(previous_displayed, (int, float))
                and raw_display_seconds < float(previous_displayed) - 0.040
            ):
                safe_to_anchor = False

            if safe_to_anchor:
                if last_reported is None or abs(raw_media_seconds - float(last_reported)) >= 0.010:
                    self.transcript_vlc_clock_anchor_seconds = raw_media_seconds
                    self.transcript_vlc_clock_anchor_wall_time = now
                    self.transcript_vlc_last_reported_seconds = raw_media_seconds

        anchor_media_seconds = getattr(self, "transcript_vlc_clock_anchor_seconds", None)
        anchor_wall = getattr(self, "transcript_vlc_clock_anchor_wall_time", None)

        if anchor_media_seconds is None:
            if isinstance(raw_media_seconds, (int, float)):
                anchor_media_seconds = float(raw_media_seconds)
                anchor_wall = now
            elif isinstance(requested_media_start, (int, float)):
                anchor_media_seconds = float(requested_media_start)
                anchor_wall = now
            else:
                return None

        if anchor_wall is None:
            anchor_wall = now

        if backend == "vlc" and self._is_transcript_vlc_playing():
            elapsed = max(0.0, now - float(anchor_wall))
            lead_limit = float(getattr(self, "transcript_vlc_max_interpolation_lead_seconds", 0.250))
            media_seconds = float(anchor_media_seconds) + min(elapsed, max(0.0, lead_limit))
        else:
            media_seconds = float(anchor_media_seconds)

        current_seconds = media_seconds + sync_offset

        if (
            raw_media_seconds is not None
            and isinstance(previous_displayed, (int, float))
        ):
            raw_display_seconds = raw_media_seconds + sync_offset

            if raw_display_seconds > current_seconds + 0.180:
                current_seconds = float(previous_displayed) + min(
                    0.080,
                    raw_display_seconds - float(previous_displayed)
                )

        # Do not jitter backwards during normal playback.
        if backend == "vlc" and isinstance(previous_displayed, (int, float)):
            if current_seconds < float(previous_displayed):
                current_seconds = float(previous_displayed)

        min_time, max_time = self._get_transcript_timeline_bounds()

        if min_time is not None and max_time is not None:
            current_seconds = max(float(min_time), min(float(max_time), current_seconds))

        self.transcript_playhead_seconds = current_seconds
        media_duration = self._get_linked_media_duration_seconds()
        if (
            not getattr(self, "transcript_position_scrubbing", False)
            and isinstance(media_duration, (int, float))
            and media_duration > 0
        ):
            self._set_transcript_position_slider(float(current_seconds) / float(media_duration))

        if "transcript_cursor_status_label" in vars(self):
            self.transcript_cursor_status_label.configure(
                text=f"Playing: {self._format_timeline_time(current_seconds)}",
                text_color=COLORS["accent"]
            )

        return current_seconds


    def _tick_transcript_timeline_playback(self, *, generation: Optional[int] = None) -> None:
        """Move playhead marker smoothly while VLC is playing."""
        if generation is not None and generation != getattr(self, "transcript_playback_generation", 0):
            return
        backend = getattr(self, "transcript_playback_backend", None)

        if backend == "vlc":
            player = getattr(self, "transcript_vlc_player", None)

            if player is None:
                self._update_transcript_playback_buttons(False)
                return

            try:
                state_text = str(player.get_state()).lower()
            except Exception:
                state_text = ""

            if "ended" in state_text or "stopped" in state_text or "error" in state_text:
                self._stop_transcript_playback_process()
                self._update_transcript_playback_buttons(False)
                self._refresh_transcript_timeline()
                return

            current_seconds = self._update_transcript_playhead_from_playback_clock()

            if current_seconds is not None:
                self._sync_transcript_selection_to_playback_time(current_seconds)

                try:
                    zoom_level = float(getattr(self, "transcript_timeline_zoom_level", 1.0))
                except Exception:
                    zoom_level = 1.0

                viewport_moved = False
                if zoom_level > 1.05 and hasattr(self, "_keep_transcript_playhead_visible"):
                    viewport_moved = bool(self._keep_transcript_playhead_visible(current_seconds))

                if viewport_moved:
                    self._refresh_transcript_timeline()
                    redraw_type = "viewport move"
                else:
                    marker_updated = self._draw_transcript_playhead_marker(current_seconds)
                    if marker_updated:
                        redraw_type = "playhead-only"
                    else:
                        self._refresh_transcript_timeline()
                        redraw_type = "full waveform redraw"
                self._record_transcript_playback_debug_tick(
                    raw_seconds=vars(self).get("transcript_vlc_last_raw_media_seconds_for_debug"),
                    display_seconds=current_seconds,
                    redraw_type=redraw_type,
                    viewport_moved=viewport_moved,
                )

            self._schedule_transcript_playback_tick()
            return

        self._update_transcript_playback_buttons(False)


    def _get_transcript_selected_segment_center_time(self) -> Optional[float]:
        """Return selected segment midpoint in seconds, if available."""
        selected_index = getattr(self, "selected_transcript_segment_index", None)

        if not (
            isinstance(selected_index, int)
            and 0 <= selected_index < len(self.transcript_segments)
        ):
            return None

        segment = self.transcript_segments[selected_index]
        start_seconds = self._transcript_time_to_seconds(segment.start)
        end_seconds = self._transcript_time_to_seconds(segment.end)

        if start_seconds is not None and end_seconds is not None:
            return (start_seconds + end_seconds) / 2

        if start_seconds is not None:
            return start_seconds

        return end_seconds

    def _get_transcript_playhead_time(self) -> Optional[float]:
        """Return movable playhead time, falling back to selected segment midpoint."""
        playhead_seconds = getattr(self, "transcript_playhead_seconds", None)

        if isinstance(playhead_seconds, (int, float)):
            return float(playhead_seconds)

        return self._get_transcript_selected_segment_center_time()

    def _set_transcript_playhead_time(self, seconds: float, refresh: bool = True) -> None:
        """Move the transcript timeline playhead marker."""
        min_time, max_time = self._get_transcript_timeline_bounds()

        if min_time is None or max_time is None:
            return

        try:
            seconds = float(seconds)
        except Exception:
            return

        seconds = max(float(min_time), min(float(max_time), seconds))
        self.transcript_playhead_seconds = seconds
        self.transcript_playback_follow_active = False

        sync_offset = self._get_transcript_audio_sync_offset_seconds()
        media_seconds = max(0.0, seconds - sync_offset)
        self.transcript_vlc_clock_anchor_seconds = media_seconds
        self.transcript_vlc_clock_anchor_wall_time = self._transcript_playback_now()
        self.transcript_vlc_last_reported_seconds = media_seconds

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"Timeline marker: {self._format_timeline_time(seconds)}",
                text_color=COLORS["text_primary"]
            )

        if refresh:
            try:
                zoom_level = float(getattr(self, "transcript_timeline_zoom_level", 1.0))
            except Exception:
                zoom_level = 1.0

            if zoom_level > 1.05 and hasattr(self, "_center_transcript_timeline_pan_on_time"):
                self._center_transcript_timeline_pan_on_time(seconds)

            self._refresh_transcript_timeline()

    def _seek_transcript_vlc_to_seconds(self, seconds: float) -> None:
        """Seek linked VLC playback once and reset interpolation anchors."""
        sync_offset = self._get_transcript_audio_sync_offset_seconds()
        media_seconds = max(0.0, float(seconds) - sync_offset)
        player = getattr(self, "transcript_vlc_player", None)
        if player is not None:
            try:
                player.set_time(int(media_seconds * 1000))
            except Exception:
                pass
        now = self._transcript_playback_now()
        self.transcript_playhead_seconds = float(seconds)
        self.transcript_vlc_clock_anchor_seconds = media_seconds
        self.transcript_vlc_clock_anchor_wall_time = now
        self.transcript_vlc_last_reported_seconds = media_seconds
        self.transcript_playback_start_wall_time = now
        self.transcript_playback_start_seconds = media_seconds
        self.transcript_playback_requested_start_seconds = media_seconds

    def _begin_transcript_authoritative_scrub(self) -> None:
        if vars(self).get("transcript_authoritative_scrubbing", False):
            return
        self.transcript_authoritative_scrubbing = True
        self.transcript_scrub_was_playing = self._is_transcript_vlc_playing()
        self.transcript_timeline_center_lock_active = False
        after_id = getattr(self, "transcript_playback_after_id", None)
        self.transcript_playback_generation = getattr(self, "transcript_playback_generation", 0) + 1
        if after_id:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self.transcript_playback_after_id = None
        if self.transcript_scrub_was_playing:
            player = getattr(self, "transcript_vlc_player", None)
            if player is not None:
                try:
                    player.pause()
                    self.transcript_playback_backend = "vlc_paused"
                except Exception:
                    pass
            self._update_transcript_playback_buttons(False)

    def _preview_transcript_authoritative_scrub(self, seconds: float) -> None:
        min_time, max_time = self._get_transcript_timeline_bounds()
        if min_time is None or max_time is None:
            return
        seconds = max(float(min_time), min(float(max_time), float(seconds)))
        self.transcript_playhead_seconds = seconds
        self.transcript_timeline_center_time = seconds
        media_duration = self._get_linked_media_duration_seconds()
        if isinstance(media_duration, (int, float)) and media_duration > 0:
            self._set_transcript_position_slider(float(seconds) / float(media_duration))
        else:
            duration = max(1.0, float(max_time) - float(min_time))
            self._set_transcript_position_slider((seconds - float(min_time)) / duration)
        if "transcript_cursor_status_label" in vars(self):
            self.transcript_cursor_status_label.configure(
                text=f"Preview position: {self._format_timeline_time(seconds)}",
                text_color=COLORS["text_primary"],
            )
        self._refresh_transcript_timeline()

    def _finish_transcript_authoritative_scrub(self, seconds: float) -> None:
        self.transcript_authoritative_scrubbing = False
        self.transcript_position_scrubbing = False
        self._preview_transcript_authoritative_scrub(seconds)
        self._seek_transcript_vlc_to_seconds(seconds)
        self._sync_transcript_selection_to_playback_time(seconds)
        self.transcript_timeline_center_lock_active = bool(
            vars(self).get("transcript_scrub_was_playing", False)
        )
        self.transcript_timeline_center_time = seconds
        self._refresh_transcript_timeline()
        if vars(self).get("transcript_scrub_was_playing", False):
            player = getattr(self, "transcript_vlc_player", None)
            if player is not None:
                try:
                    player.play()
                    self.transcript_playback_backend = "vlc"
                    self.transcript_playback_generation = getattr(self, "transcript_playback_generation", 0) + 1
                    self._update_transcript_playback_buttons(True)
                    self._schedule_transcript_playback_tick()
                except Exception:
                    self._update_transcript_playback_buttons(False)
        self.transcript_scrub_was_playing = False

    def _timeline_canvas_event_to_seconds(self, event) -> Optional[float]:
        """Convert timeline canvas x position into transcript seconds."""
        view = getattr(self, "_transcript_timeline_view", None)

        if not view:
            return None

        left_margin = view.get("left_margin", 90)
        timeline_width = max(1, view.get("timeline_width", 1))
        min_time = view.get("min_time")
        max_time = view.get("max_time")

        if min_time is None or max_time is None:
            return None

        x = max(left_margin, min(event.x, left_margin + timeline_width))
        fraction = (x - left_margin) / timeline_width

        return float(min_time) + (float(max_time) - float(min_time)) * fraction

    def _on_transcript_timeline_canvas_press(self, event) -> None:
        """Begin authoritative timeline scrub from the waveform/timeline."""
        seconds = self._timeline_canvas_event_to_seconds(event)

        if seconds is None:
            return

        self._begin_transcript_authoritative_scrub()
        self._preview_transcript_authoritative_scrub(seconds)

    def _on_transcript_timeline_canvas_drag(self, event) -> None:
        """Scrub playhead marker while dragging over the timeline."""
        seconds = self._timeline_canvas_event_to_seconds(event)

        if seconds is None:
            return

        self._preview_transcript_authoritative_scrub(seconds)

    def _on_transcript_timeline_canvas_release(self, event) -> None:
        """Finalize playhead marker position after dragging."""
        seconds = self._timeline_canvas_event_to_seconds(event)

        if seconds is None:
            return

        self._finish_transcript_authoritative_scrub(seconds)


    def _update_transcript_waveform_status(self, text: Optional[str] = None, color: Optional[str] = None) -> None:
        """Refresh waveform status label."""
        if not hasattr(self, "transcript_waveform_status_label"):
            return

        if text is None:
            if (
                getattr(self, "transcript_waveform_peaks", None)
                and getattr(self, "transcript_waveform_source_path", None)
                == getattr(self, "linked_transcript_media_path", None)
            ):
                text = "Waveform ready"
                color = COLORS["text_secondary"]
            else:
                text = "No waveform"
                color = COLORS["text_muted"]

        self.transcript_waveform_status_label.configure(
            text=text,
            text_color=color or COLORS["text_muted"]
        )

    def _clear_transcript_waveform(self, refresh: bool = True) -> None:
        """Clear cached waveform data."""
        self.transcript_waveform_peaks = []
        self.transcript_waveform_source_path = None
        self._update_transcript_waveform_status()

        if refresh and hasattr(self, "transcript_timeline_canvas"):
            self._refresh_transcript_timeline()

    def _extract_transcript_waveform_peaks(self, media_path: str, peak_count: int = 1200) -> List[float]:
        """Extract normalized mono waveform peaks using ffmpeg."""
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            media_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-f",
            "s16le",
            "-"
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=240
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                "ffmpeg was not found. Install ffmpeg and make sure it is available on PATH, then try Generate Waveform again."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("ffmpeg took too long while generating waveform peaks.") from error

        if result.returncode != 0:
            stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(stderr_text or "ffmpeg failed to read the linked media file.")

        raw_audio = result.stdout

        if not raw_audio:
            raise RuntimeError("No audio samples were extracted from the linked media file.")

        usable_length = len(raw_audio) - (len(raw_audio) % 2)
        samples = array.array("h")
        samples.frombytes(raw_audio[:usable_length])

        if not samples:
            raise RuntimeError("No usable audio samples were extracted from the linked media file.")

        sample_count = len(samples)
        peak_count = max(200, min(int(peak_count), 4000))
        chunk_size = max(1, sample_count // peak_count)
        peaks = []

        for start in range(0, sample_count, chunk_size):
            chunk = samples[start:start + chunk_size]

            if not chunk:
                continue

            peak = max(abs(value) for value in chunk)
            peaks.append(min(1.0, peak / 32768.0))

        return peaks or [0.0]

    def generate_transcript_waveform(self) -> None:
        """Generate waveform peaks for the linked transcript media."""
        media_path = getattr(self, "linked_transcript_media_path", None)

        if not media_path:
            messagebox.showwarning(
                "No Linked Media",
                "Choose a media file first, then generate the waveform."
            )
            return

        if not os.path.exists(media_path):
            self._set_linked_transcript_media(None)
            messagebox.showerror(
                "Linked Media Missing",
                "The linked media file could not be found. Choose the media file again."
            )
            return

        if hasattr(self, "transcript_waveform_button"):
            self.transcript_waveform_button.configure(state="disabled", text="Working...")

        self._update_transcript_waveform_status("Generating...", COLORS["text_secondary"])

        def worker() -> None:
            try:
                peaks = self._extract_transcript_waveform_peaks(media_path)
            except Exception as error:
                def on_error() -> None:
                    if hasattr(self, "transcript_waveform_button"):
                        self.transcript_waveform_button.configure(state="normal", text="Waveform")

                    self._clear_transcript_waveform(refresh=True)
                    messagebox.showerror("Waveform Error", str(error))

                self.after(0, on_error)
                return

            def on_success() -> None:
                if getattr(self, "linked_transcript_media_path", None) != media_path:
                    if hasattr(self, "transcript_waveform_button"):
                        self.transcript_waveform_button.configure(state="normal", text="Waveform")
                    self._update_transcript_waveform_status()
                    return

                self.transcript_waveform_peaks = peaks
                self.transcript_waveform_source_path = media_path

                if hasattr(self, "transcript_waveform_button"):
                    self.transcript_waveform_button.configure(state="normal", text="Waveform")

                self._update_transcript_waveform_status("Waveform ready", COLORS["text_secondary"])
                self._refresh_transcript_timeline()
                self.log_message(
                    f"Generated waveform peaks for: {os.path.basename(media_path)}",
                    "success"
                )

            self.after(0, on_success)

        threading.Thread(target=worker, daemon=True).start()

    def detect_speech_intervals_clicked(self) -> None:
        """Choose a local workflow for creating editable subtitle timing segments."""
        if getattr(self, "speech_interval_detection_busy", False):
            self.speech_interval_detection_cancel_requested = True
            if hasattr(self, "transcript_cursor_status_label"):
                self.transcript_cursor_status_label.configure(
                    text="Cancelling subtitle timing creation...",
                    text_color=COLORS["text_muted"],
                )
            return

        media_path = getattr(self, "linked_transcript_media_path", None)
        if not media_path:
            messagebox.showinfo(
                "Create Subtitle Timings",
                "Add or select a media file first. This workflow creates editable subtitle timing segments from local audio.",
            )
            return

        choice = self._ask_create_subtitle_timings_choice()
        if choice == "cancel":
            return
        if choice == "accurate_draft":
            self.local_asr_timing_mode_after_completion = "draft"
            self.local_asr_transcribe_clicked(media_file=media_path, force_full=True)
            return
        if choice == "accurate_blank":
            self.local_asr_timing_mode_after_completion = "blank"
            self.local_asr_blank_text_after_completion = True
            self.local_asr_transcribe_clicked(media_file=media_path, force_full=True)
            return
        self._start_fast_vad_subtitle_timings(media_path)

    def _ask_create_subtitle_timings_choice(self) -> str:
        """Ask how to create subtitle timings without inventing transcript text."""
        override = vars(self).get("_create_subtitle_timings_choice_override")
        if override in {"accurate_draft", "accurate_blank", "fast_vad", "cancel"}:
            return str(override)
        if "tk" not in vars(self):
            return "fast_vad"

        dialog = ctk.CTkToplevel(self)
        dialog.title("Create Subtitle Timings")
        dialog.geometry("520x310")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        result = {"choice": "cancel"}

        content = ctk.CTkFrame(dialog, fg_color=COLORS["bg_card"], corner_radius=10)
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content,
            text="Create subtitle timings",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            content,
            text=(
                "Accurate local ASR timings are recommended. You can keep draft text, "
                "create blank timed segments from ASR timings, or use fast WebRTC VAD "
                "for clean speech only."
            ),
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            wraplength=460,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

        def choose(value: str) -> None:
            result["choice"] = value
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        button_specs = (
            ("Accurate local ASR timings - keep draft text", "accurate_draft"),
            ("Accurate local ASR timings - blank segments", "accurate_blank"),
            ("Fast WebRTC VAD - clean speech only", "fast_vad"),
            ("Cancel", "cancel"),
        )
        for row, (label, value) in enumerate(button_specs, start=2):
            ctk.CTkButton(
                content,
                text=label,
                command=lambda value=value: choose(value),
                height=34,
                fg_color=COLORS["accent"] if row == 2 else COLORS["accent_secondary"],
                hover_color=COLORS["accent_hover"] if row == 2 else COLORS["border"],
                corner_radius=8,
            ).grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 8))

        dialog.protocol("WM_DELETE_WINDOW", lambda: choose("cancel"))
        self.wait_window(dialog)
        return str(result["choice"])

    def _start_fast_vad_subtitle_timings(self, media_path: str) -> None:
        """Create blank editable subtitle segments from local WebRTC VAD intervals."""
        if self.transcript_segments:
            answer = messagebox.askyesno(
                "Replace Current Transcript?",
                (
                    "Fast VAD subtitle timing will replace the current editor contents with blank timed segments.\n\n"
                    "The active media file and any transcript files in FILES will remain attached. Continue?"
                ),
            )
            if not answer:
                return

        self.speech_interval_detection_busy = True
        self.speech_interval_detection_cancel_requested = False
        if hasattr(self, "transcript_detect_intervals_button"):
            self.transcript_detect_intervals_button.configure(text="Cancel intervals")
        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text="Creating fast VAD subtitle timings locally...",
                text_color=COLORS["text_muted"],
            )

        def progress_callback(value: float) -> None:
            percent = int(max(0.0, min(1.0, float(value))) * 100)
            self.after(
                0,
                lambda percent=percent: (
                    hasattr(self, "transcript_cursor_status_label")
                    and self.transcript_cursor_status_label.configure(
                        text=f"Creating fast VAD subtitle timings locally... {percent}%",
                        text_color=COLORS["text_muted"],
                    )
                ),
            )

        def cancel_check() -> bool:
            return bool(getattr(self, "speech_interval_detection_cancel_requested", False))

        def finish() -> None:
            self.speech_interval_detection_busy = False
            self.speech_interval_detection_cancel_requested = False
            if hasattr(self, "transcript_detect_intervals_button"):
                self.transcript_detect_intervals_button.configure(text="Create subtitle timings")

        def worker() -> None:
            try:
                intervals = detect_speech_intervals_for_media_file(
                    media_path,
                    progress_callback=progress_callback,
                    cancel_check=cancel_check,
                )
            except RuntimeError as error:
                if str(error) == "speech_interval_detection_cancelled":
                    self.after(0, lambda: self._finish_speech_interval_detection_cancelled(finish))
                    return
                self.after(0, lambda error=error: self._finish_speech_interval_detection_error(error, finish))
                return
            except Exception as error:
                self.after(0, lambda error=error: self._finish_speech_interval_detection_error(error, finish))
                return

            self.after(0, lambda intervals=intervals: self._finish_speech_interval_detection(intervals, finish))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_speech_interval_detection_cancelled(self, finish_callback) -> None:
        finish_callback()
        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text="Subtitle timing creation cancelled.",
                text_color=COLORS["text_muted"],
            )

    def _finish_speech_interval_detection_error(self, error: Exception, finish_callback) -> None:
        finish_callback()
        messagebox.showerror("Create Subtitle Timings", str(error))
        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text="Fast VAD subtitle timing failed.",
                text_color=COLORS["error"],
            )

    def _finish_speech_interval_detection(self, intervals, finish_callback) -> None:
        finish_callback()
        if not intervals:
            messagebox.showinfo(
                "Create Subtitle Timings",
                "No clean-speech VAD intervals were detected. No transcript text was invented.",
            )
            return
        if self.transcript_segments:
            self._push_transcript_undo_state()
        self.transcript_segments = [
            TranscriptSegment(
                speaker="Speaker 1",
                start=self._seconds_to_transcript_time(interval.start_seconds),
                end=self._seconds_to_transcript_time(interval.end_seconds),
                text="",
            )
            for interval in intervals
        ]
        self.last_transcript_source = "Fast local VAD subtitle timings"
        self.transcript_has_unsaved_edits = True
        self.transcript_redo_stack = []
        self.selected_transcript_segment_index = 0
        self._refresh_transcript_display()
        self._refresh_transcript_timeline()
        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"Created {len(intervals)} blank fast-VAD timing segment(s).",
                text_color=COLORS["text_primary"],
            )
        if hasattr(self, "evidence_button"):
            self.evidence_button.configure(state="normal")


    def _get_transcript_active_waveform_range(self):
        """Return the segment time range currently under the playhead marker."""
        playhead_seconds = self._get_transcript_playhead_time()

        if playhead_seconds is None:
            return None

        explicit_playhead = getattr(self, "transcript_playhead_seconds", None)
        selected_index = getattr(self, "selected_transcript_segment_index", None)

        def get_segment_range(index: int):
            if not isinstance(index, int) or not (0 <= index < len(self.transcript_segments)):
                return None

            segment = self.transcript_segments[index]
            start_seconds = self._transcript_time_to_seconds(segment.start)
            end_seconds = self._transcript_time_to_seconds(segment.end)

            if start_seconds is None or end_seconds is None:
                return None

            if end_seconds < start_seconds:
                return None

            return float(start_seconds), float(end_seconds)

        # Prefer selected segment if the playhead is inside it.
        selected_range = get_segment_range(selected_index)

        if selected_range:
            start_seconds, end_seconds = selected_range

            if start_seconds <= playhead_seconds <= end_seconds:
                return selected_range

        # Otherwise find whichever timed segment the playhead is over.
        for index in range(len(self.transcript_segments)):
            segment_range = get_segment_range(index)

            if not segment_range:
                continue

            start_seconds, end_seconds = segment_range

            if start_seconds <= playhead_seconds <= end_seconds:
                return segment_range

        # Before the marker has been manually moved, highlight the selected segment.
        if explicit_playhead is None and selected_range:
            return selected_range

        return None


    def _draw_transcript_waveform(
        self,
        canvas,
        min_time: float,
        max_time: float,
        full_min_time: float,
        full_max_time: float,
        left_margin: int,
        right_margin: int,
        top_margin: int,
        bottom_margin: int,
        width: int,
        canvas_height: int,
        timeline_width: int
    ) -> None:
        """Draw cached waveform peaks behind transcript timeline blocks."""
        peaks = getattr(self, "transcript_waveform_peaks", None)

        if not peaks:
            return

        if (
            getattr(self, "transcript_waveform_source_path", None)
            != getattr(self, "linked_transcript_media_path", None)
        ):
            return

        media_duration = self._get_linked_media_duration_seconds()
        if not isinstance(media_duration, (int, float)) or media_duration <= 0:
            return
        full_duration = max(1.0, float(media_duration))
        visible_duration = max(0.001, max_time - min_time)

        wave_top = top_margin
        wave_bottom = max(wave_top + 20, canvas_height - bottom_margin)
        wave_mid = (wave_top + wave_bottom) / 2
        wave_amp = max(8, (wave_bottom - wave_top) * 0.42)
        x_start = int(left_margin)
        x_end = int(width - right_margin)

        active_waveform_range = self._get_transcript_active_waveform_range()
        active_start = None
        active_end = None

        if active_waveform_range:
            active_start, active_end = active_waveform_range

            if active_end >= min_time and active_start <= max_time:
                active_visible_start = max(active_start, min_time)
                active_visible_end = min(active_end, max_time)
                active_x1 = left_margin + ((active_visible_start - min_time) / visible_duration) * timeline_width
                active_x2 = left_margin + ((active_visible_end - min_time) / visible_duration) * timeline_width

                canvas.create_rectangle(
                    active_x1,
                    wave_top,
                    active_x2,
                    wave_bottom,
                    fill="#2A1717",
                    outline=""
                )

        for x in range(x_start, x_end + 1, 2):
            fraction = (x - left_margin) / max(1, timeline_width)
            time_at_x = min_time + visible_duration * fraction
            if time_at_x < 0 or time_at_x > full_duration:
                continue
            peak_position = int(
                (time_at_x / full_duration)
                * max(0, len(peaks) - 1)
            )
            peak_position = max(0, min(len(peaks) - 1, peak_position))
            amplitude = peaks[peak_position]

            y1 = wave_mid - amplitude * wave_amp
            y2 = wave_mid + amplitude * wave_amp

            is_active_wave = (
                active_start is not None
                and active_end is not None
                and active_start <= time_at_x <= active_end
            )
            wave_color = "#EF4444" if is_active_wave else "#334155"
            wave_width = 2 if is_active_wave else 1

            canvas.create_line(
                x,
                y1,
                x,
                y2,
                fill=wave_color,
                width=wave_width
            )


    def _get_linked_media_duration_seconds(self) -> Optional[float]:
        state = vars(self)
        media_path = state.get("linked_transcript_media_path")
        if not media_path:
            return None

        duration = self._probe_media_duration_seconds(media_path)
        if isinstance(duration, (int, float)) and duration > 0:
            self.transcript_media_duration_seconds = float(duration)
            return float(duration)

        cached = state.get("transcript_media_duration_seconds")
        cached_key = state.get("transcript_media_duration_cache_key")
        current_key = self._media_duration_cache_key(media_path)
        if (
            isinstance(cached, (int, float))
            and cached > 0
            and cached_key is not None
            and cached_key == current_key
        ):
            return float(cached)

        player = state.get("transcript_vlc_player")
        if player is not None:
            try:
                length_ms = player.get_length()
            except Exception:
                length_ms = -1
            if isinstance(length_ms, (int, float)) and length_ms > 0:
                self.transcript_media_duration_seconds = float(length_ms) / 1000.0
                self.transcript_media_duration_cache_key = current_key
                return self.transcript_media_duration_seconds

        return None

    def _media_duration_cache_key(self, media_path: str) -> Optional[tuple[str, int, int]]:
        try:
            normalized = os.path.normcase(os.path.abspath(os.path.expanduser(media_path or "")))
            stat = os.stat(normalized)
            return (normalized, int(stat.st_size), int(stat.st_mtime_ns))
        except Exception:
            return None

    def _probe_media_duration_seconds(self, media_path: str) -> Optional[float]:
        cache_key = self._media_duration_cache_key(media_path)
        if cache_key is None:
            return None
        cache = vars(self).setdefault("_media_duration_seconds_cache", {})
        if isinstance(cache, dict) and cache_key in cache:
            cached = cache.get(cache_key)
            return float(cached) if isinstance(cached, (int, float)) and cached > 0 else None

        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            os.path.abspath(os.path.expanduser(media_path or "")),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
        except Exception:
            return None
        if result.returncode != 0:
            return None
        try:
            duration = float((result.stdout or "").strip())
        except Exception:
            return None
        if duration <= 0:
            return None
        if isinstance(cache, dict):
            cache[cache_key] = duration
        self.transcript_media_duration_cache_key = cache_key
        return duration

    def _get_transcript_duration_seconds(self) -> Optional[float]:
        times = []
        for segment in self.transcript_segments:
            for value in (segment.start, segment.end):
                seconds = self._transcript_time_to_seconds(value)
                if seconds is not None:
                    times.append(float(seconds))
        if not times:
            return None
        return max(times)

    def _get_transcript_timeline_durations(self) -> Dict[str, Optional[float]]:
        media_duration = self._get_linked_media_duration_seconds()
        transcript_duration = self._get_transcript_duration_seconds()
        positive = [
            float(value)
            for value in (media_duration, transcript_duration)
            if isinstance(value, (int, float)) and value > 0
        ]
        display_duration = max(positive) if positive else None
        return {
            "media_duration": media_duration,
            "transcript_duration": transcript_duration,
            "display_duration": display_duration,
        }

    def _transcript_media_duration_warning(self) -> str:
        durations = self._get_transcript_timeline_durations()
        media_duration = durations.get("media_duration")
        transcript_duration = durations.get("transcript_duration")
        if not (
            isinstance(media_duration, (int, float))
            and isinstance(transcript_duration, (int, float))
            and media_duration > 0
            and transcript_duration > 0
        ):
            return ""
        difference = abs(float(media_duration) - float(transcript_duration))
        material = difference >= 5.0 and difference / max(float(media_duration), 1.0) >= 0.08
        if not material:
            return ""
        return (
            f"Transcript duration {self._format_timeline_time(float(transcript_duration))} "
            f"differs from media duration {self._format_timeline_time(float(media_duration))}."
        )

    def _get_transcript_timeline_bounds(self):
        """Return min/max seconds for transcript timeline drawing."""
        durations = self._get_transcript_timeline_durations()
        display_duration = durations.get("display_duration")
        if display_duration is None:
            return None, None
        return 0.0, max(1.0, float(display_duration))

    def _format_timeline_time(self, seconds: float) -> str:
        """Format seconds as compact timeline label."""
        seconds = max(0.0, float(seconds))
        minutes = int(seconds // 60)
        sec = int(seconds % 60)

        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours:d}:{minutes:02d}:{sec:02d}"

        return f"{minutes:d}:{sec:02d}"

    def _get_timeline_speakers(self):
        """Return speakers in first-seen transcript order."""
        speakers = []

        for segment in self.transcript_segments:
            speaker = segment.speaker or "Speaker"

            if speaker not in speakers:
                speakers.append(speaker)

        return speakers



    def _set_transcript_position_slider(self, fraction: float) -> None:
        """Update the absolute media Position slider without a redraw loop."""
        fraction = max(0.0, min(1.0, float(fraction)))
        self.transcript_position_fraction = fraction

        slider = vars(self).get("transcript_timeline_pan_slider")
        if slider is None:
            return

        try:
            self._updating_transcript_timeline_pan_slider = True
            if (
                getattr(self, "transcript_position_scrubbing", False)
                or getattr(self, "transcript_authoritative_scrubbing", False)
            ) and hasattr(slider, "set_immediate"):
                slider.set_immediate(fraction * 100.0)
            else:
                slider.set(fraction * 100.0)
        finally:
            self._updating_transcript_timeline_pan_slider = False

    def _set_transcript_timeline_view_fraction(self, fraction: float) -> None:
        """Update only the waveform/timeline viewport follow fraction."""
        self.transcript_timeline_view_fraction = max(0.0, min(1.0, float(fraction)))

    def _set_transcript_timeline_pan_slider(self, fraction: float) -> None:
        """Backward-compatible alias for the absolute Position slider."""
        self._set_transcript_position_slider(fraction)


    def _center_transcript_timeline_pan_on_time(self, center_time: float) -> None:
        """Center the zoomed timeline view around a specific time."""
        min_time, max_time = self._get_transcript_timeline_bounds()

        if min_time is None or max_time is None:
            self._set_transcript_timeline_view_fraction(0.0)
            return

        try:
            center_time = float(center_time)
        except Exception:
            return

        full_duration = max(1.0, max_time - min_time)

        try:
            zoom_level = float(getattr(self, "transcript_timeline_zoom_level", 1.0))
        except Exception:
            zoom_level = 1.0

        zoom_level = max(1.0, min(10.0, zoom_level))

        if zoom_level <= 1.05:
            self._set_transcript_timeline_view_fraction(0.0)
            return

        visible_duration = max(1.0, full_duration / zoom_level)
        max_pan_seconds = max(0.0, full_duration - visible_duration)

        if max_pan_seconds <= 0:
            self._set_transcript_timeline_view_fraction(0.0)
            return

        center_time = max(min_time, min(max_time, center_time))
        visible_min = center_time - visible_duration / 2
        fraction = (visible_min - min_time) / max_pan_seconds

        self._set_transcript_timeline_view_fraction(fraction)

    def _keep_transcript_playhead_visible(self, seconds: float) -> bool:
        """Keep playback locked to a fixed centre playhead."""
        try:
            seconds = float(seconds)
        except Exception:
            return False

        previous_center = vars(self).get("transcript_timeline_center_time")
        self.transcript_timeline_center_lock_active = True
        self.transcript_timeline_center_time = seconds
        view = vars(self).get("_transcript_timeline_view") or {}
        try:
            full_min_time = float(view.get("full_min_time", 0.0))
            duration = max(
                1.0,
                float(view.get("full_max_time", 0.0)) - full_min_time,
            )
            absolute_fraction = (seconds - full_min_time) / duration
            self._set_transcript_timeline_view_fraction(absolute_fraction)
            media_duration = self._get_linked_media_duration_seconds()
            if isinstance(media_duration, (int, float)) and media_duration > 0:
                self._set_transcript_position_slider(seconds / float(media_duration))
            else:
                self._set_transcript_position_slider(absolute_fraction)
        except Exception:
            pass
        return previous_center is None or abs(float(previous_center) - seconds) >= 0.001

    def _draw_transcript_playhead_marker(self, seconds: float) -> bool:
        view = getattr(self, "_transcript_timeline_view", None)
        if not view or not hasattr(self, "transcript_timeline_canvas"):
            return False
        try:
            min_time = float(view["min_time"])
            max_time = float(view["max_time"])
            left_margin = float(view["left_margin"])
            top_margin = float(view["top_margin"])
            bottom_margin = float(view["bottom_margin"])
            timeline_width = float(view["timeline_width"])
            canvas_height = float(view["canvas_height"])
            duration = max(0.001, max_time - min_time)
            seconds = float(seconds)
        except Exception:
            return False
        canvas = self.transcript_timeline_canvas
        try:
            canvas.delete("transcript_playhead_marker")
        except Exception:
            return False
        if not (min_time <= seconds <= max_time):
            return False
        if bool(view.get("center_lock")):
            marker_x = left_margin + timeline_width / 2.0
        else:
            marker_x = left_margin + ((seconds - min_time) / duration) * timeline_width
        marker_color = "#38BDF8"
        canvas.create_polygon(
            marker_x - 6,
            top_margin - 17,
            marker_x + 6,
            top_margin - 17,
            marker_x,
            top_margin - 6,
            fill=marker_color,
            outline=marker_color,
            tags=("transcript_playhead_marker",),
        )
        canvas.create_line(
            marker_x,
            top_margin - 5,
            marker_x,
            canvas_height - bottom_margin + 4,
            fill=marker_color,
            width=1,
            tags=("transcript_playhead_marker",),
        )
        return True

    def _record_transcript_playback_debug_tick(
        self,
        *,
        raw_seconds: Optional[float],
        display_seconds: Optional[float],
        redraw_type: str,
        viewport_moved: bool,
    ) -> None:
        if not getattr(self, "transcript_playback_debug_enabled", False):
            return
        ticks = getattr(self, "transcript_playback_debug_ticks", None)
        if ticks is None:
            ticks = []
            self.transcript_playback_debug_ticks = ticks
        view = getattr(self, "_transcript_timeline_view", None) or {}
        position_slider_value = None
        if "transcript_timeline_pan_slider" in vars(self):
            try:
                position_slider_value = self.transcript_timeline_pan_slider.get()
            except Exception:
                position_slider_value = None
        timeline_width = view.get("timeline_width")
        left_margin = view.get("left_margin")
        center_playhead_x = None
        if isinstance(timeline_width, (int, float)) and isinstance(left_margin, (int, float)):
            center_playhead_x = float(left_margin) + (float(timeline_width) / 2.0)
        ticks.append(
            {
                "monotonic": self._transcript_playback_now(),
                "raw_player_time": raw_seconds,
                "display_time": display_seconds,
                "generation": getattr(self, "transcript_playback_generation", 0),
                "pending_callback": bool(getattr(self, "transcript_playback_after_id", None)),
                "pan_fraction": vars(self).get("transcript_timeline_view_fraction", 0.0),
                "position_fraction": vars(self).get("transcript_position_fraction", 0.0),
                "viewport_min": view.get("min_time"),
                "viewport_max": view.get("max_time"),
                "follow_active": bool(vars(self).get("transcript_playback_follow_active", False)),
                "viewport_moved": bool(viewport_moved),
                "redraw_type": redraw_type,
                "render_center_time": vars(self).get("transcript_timeline_center_time"),
                "center_playhead_x": center_playhead_x,
                "position_slider_value": position_slider_value,
                "slider_feedback_blocked": bool(
                    vars(self).get("_updating_transcript_timeline_pan_slider", False)
                ),
            }
        )


    def _center_transcript_timeline_pan_on_selected(self) -> None:
        """Set pan fraction so the selected segment is near the middle when zooming."""
        min_time, max_time = self._get_transcript_timeline_bounds()

        if min_time is None or max_time is None:
            self._set_transcript_timeline_view_fraction(0.0)
            return

        full_duration = max(1.0, max_time - min_time)

        try:
            zoom_level = float(getattr(self, "transcript_timeline_zoom_level", 1.0))
        except Exception:
            zoom_level = 1.0

        zoom_level = max(1.0, min(10.0, zoom_level))

        if zoom_level <= 1.05:
            self._set_transcript_timeline_view_fraction(0.0)
            return

        playhead_seconds = getattr(self, "transcript_playhead_seconds", None)

        if isinstance(playhead_seconds, (int, float)):
            self._center_transcript_timeline_pan_on_time(float(playhead_seconds))
            return

        visible_duration = max(1.0, full_duration / zoom_level)
        max_pan_seconds = max(0.0, full_duration - visible_duration)

        if max_pan_seconds <= 0:
            self._set_transcript_timeline_view_fraction(0.0)
            return

        center_time = min_time + full_duration / 2
        playhead_seconds = getattr(self, "transcript_playhead_seconds", None)

        if isinstance(playhead_seconds, (int, float)):
            center_time = max(min_time, min(max_time, float(playhead_seconds)))
        else:
            selected_index = getattr(self, "selected_transcript_segment_index", None)

            if isinstance(selected_index, int) and 0 <= selected_index < len(self.transcript_segments):
                segment = self.transcript_segments[selected_index]
                start_seconds = self._transcript_time_to_seconds(segment.start)
                end_seconds = self._transcript_time_to_seconds(segment.end)

                if start_seconds is not None and end_seconds is not None:
                    center_time = (start_seconds + end_seconds) / 2

        target_visible_min = center_time - visible_duration / 2
        fraction = (target_visible_min - min_time) / max_pan_seconds
        self._set_transcript_timeline_view_fraction(fraction)

    def _position_slider_fraction_to_seconds(self, value) -> Optional[float]:
        try:
            fraction = max(0.0, min(1.0, float(value) / 100.0))
        except Exception:
            fraction = 0.0
        min_time, max_time = self._get_transcript_timeline_bounds()
        media_duration = self._get_linked_media_duration_seconds()
        if isinstance(media_duration, (int, float)) and media_duration > 0:
            return float(media_duration) * fraction
        if min_time is None or max_time is None:
            return None
        return float(min_time) + (float(max_time) - float(min_time)) * fraction

    def _on_transcript_position_scrub_press(self, event) -> None:
        self.transcript_position_scrubbing = True
        self._begin_transcript_authoritative_scrub()

    def _on_transcript_position_scrub_release(self, event) -> None:
        if not getattr(self, "transcript_position_scrubbing", False):
            return
        current_value = getattr(self, "transcript_position_fraction", 0.0) * 100.0
        seconds = self._position_slider_fraction_to_seconds(current_value)
        if seconds is None:
            self.transcript_position_scrubbing = False
            return
        self._finish_transcript_authoritative_scrub(seconds)

    def _on_transcript_timeline_pan_changed(self, value) -> None:
        """Preview a concrete playhead position from the Position scrubber."""
        if getattr(self, "_updating_transcript_timeline_pan_slider", False):
            return

        seconds = self._position_slider_fraction_to_seconds(value)
        if seconds is None:
            return
        try:
            fraction = float(value) / 100.0
        except Exception:
            fraction = 0.0
        self.transcript_position_fraction = max(0.0, min(1.0, fraction))
        if getattr(self, "transcript_position_scrubbing", False):
            self._preview_transcript_authoritative_scrub(seconds)
            return
        self.transcript_playhead_seconds = seconds
        self.transcript_timeline_center_time = seconds
        self.transcript_timeline_center_lock_active = False
        self._refresh_transcript_timeline()


    def _on_transcript_timeline_zoom_changed(self, value) -> None:
        """Update timeline zoom and redraw timeline."""
        try:
            zoom_level = float(value)
        except Exception:
            zoom_level = 1.0

        zoom_level = max(1.0, min(10.0, zoom_level))
        previous_zoom_level = float(getattr(self, "transcript_timeline_zoom_level", 1.0))
        self.transcript_timeline_zoom_level = zoom_level

        if zoom_level > 1.05:
            playhead_seconds = getattr(self, "transcript_playhead_seconds", None)

            if isinstance(playhead_seconds, (int, float)):
                self._center_transcript_timeline_pan_on_time(float(playhead_seconds))
            elif previous_zoom_level <= 1.05:
                self._center_transcript_timeline_pan_on_selected()
        else:
            self._set_transcript_timeline_view_fraction(0.0)

        if hasattr(self, "transcript_timeline_zoom_value_label"):
            if zoom_level <= 1.05:
                label = "Zoom: Full"
            else:
                label = f"Zoom: {zoom_level:.1f}x"

            self.transcript_timeline_zoom_value_label.configure(text=label)

        self._refresh_transcript_timeline()

    def _reset_transcript_timeline_zoom(self) -> None:
        """Reset timeline zoom to full transcript view."""
        self.transcript_timeline_zoom_level = 1.0
        self._set_transcript_timeline_view_fraction(0.0)

        if hasattr(self, "transcript_timeline_zoom_slider"):
            self.transcript_timeline_zoom_slider.set(1.0)

        if hasattr(self, "transcript_timeline_zoom_value_label"):
            self.transcript_timeline_zoom_value_label.configure(text="Zoom: Full")

        self._refresh_transcript_timeline()


    def _refresh_transcript_timeline(self) -> None:
        """Draw a simple timestamp-based transcript timeline."""
        if "transcript_timeline_canvas" not in vars(self):
            return

        canvas = self.transcript_timeline_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 300)

        min_time, max_time = self._get_transcript_timeline_bounds()

        if min_time is None or max_time is None:
            canvas.configure(height=70)
            canvas.create_text(
                14,
                34,
                text="Timeline needs segment timestamps.",
                anchor="w",
                fill=COLORS["text_muted"],
                font=("Cascadia Mono", 10)
            )
            return

        full_min_time = min_time
        full_max_time = max_time
        full_duration = max(1.0, full_max_time - full_min_time)

        try:
            zoom_level = float(getattr(self, "transcript_timeline_zoom_level", 1.0))
        except Exception:
            zoom_level = 1.0

        zoom_level = max(1.0, min(10.0, zoom_level))

        selected_index = getattr(self, "selected_transcript_segment_index", None)
        center_time = None

        if isinstance(selected_index, int) and 0 <= selected_index < len(self.transcript_segments):
            selected_segment = self.transcript_segments[selected_index]
            selected_start = self._transcript_time_to_seconds(selected_segment.start)
            selected_end = self._transcript_time_to_seconds(selected_segment.end)

            if selected_start is not None and selected_end is not None:
                center_time = (selected_start + selected_end) / 2

        if center_time is None:
            center_time = full_min_time + full_duration / 2

        if zoom_level > 1.05:
            visible_duration = max(1.0, full_duration / zoom_level)

            try:
                pan_fraction = float(getattr(self, "transcript_timeline_view_fraction", 0.0))
            except Exception:
                pan_fraction = 0.0

            pan_fraction = max(0.0, min(1.0, pan_fraction))
            if getattr(self, "transcript_timeline_center_lock_active", False):
                locked_center = getattr(self, "transcript_timeline_center_time", center_time)
                try:
                    center_time = float(locked_center)
                except Exception:
                    center_time = full_min_time + full_duration * pan_fraction
                visible_min = center_time - visible_duration / 2.0
                pan_fraction = max(
                    0.0,
                    min(1.0, (center_time - full_min_time) / full_duration),
                )
                self.transcript_timeline_view_fraction = pan_fraction
            else:
                center_time = full_min_time + full_duration * pan_fraction
                visible_min = center_time - visible_duration / 2.0
            visible_max = visible_min + visible_duration

            min_time = visible_min
            max_time = visible_max

            if hasattr(self, "transcript_timeline_pan_label"):
                self.transcript_timeline_pan_label.configure(
                    text=f"Position: {pan_fraction * 100:.0f}%"
                )
        else:
            self.transcript_timeline_view_fraction = 0.0
            if hasattr(self, "transcript_timeline_pan_label"):
                self.transcript_timeline_pan_label.configure(text="Position: Full")

        speakers = self._get_timeline_speakers()
        if not speakers:
            speakers = ["Media"]
        lane_height = 28
        top_margin = 26
        bottom_margin = 16
        left_margin = 90
        right_margin = 18
        timeline_width = max(1, width - left_margin - right_margin)
        canvas_height = max(95, top_margin + bottom_margin + len(speakers) * lane_height)

        canvas.configure(height=canvas_height)

        duration = max_time - min_time
        self._transcript_timeline_view = {
            "min_time": min_time,
            "max_time": max_time,
            "full_min_time": full_min_time,
            "full_max_time": full_max_time,
            "media_duration": self._get_linked_media_duration_seconds(),
            "transcript_duration": self._get_transcript_duration_seconds(),
            "center_lock": bool(getattr(self, "transcript_timeline_center_lock_active", False)),
            "left_margin": left_margin,
            "right_margin": right_margin,
            "top_margin": top_margin,
            "bottom_margin": bottom_margin,
            "timeline_width": timeline_width,
            "canvas_height": canvas_height,
            "width": width,
            "duration": duration,
        }
        warning_text = self._transcript_media_duration_warning()
        if warning_text and hasattr(self, "transcript_waveform_status_label"):
            self.transcript_waveform_status_label.configure(
                text="Duration mismatch",
                text_color=COLORS["warning"],
            )
        elif hasattr(self, "transcript_waveform_status_label"):
            try:
                current_status = self.transcript_waveform_status_label.cget("text")
            except Exception:
                current_status = ""
            if current_status == "Duration mismatch":
                self._update_transcript_waveform_status()
        selected_index = getattr(self, "selected_transcript_segment_index", None)

        speaker_palette = [
            "#60A5FA",
            "#A78BFA",
            "#34D399",
            "#FBBF24",
            "#F87171",
            "#22D3EE",
            "#F472B6",
            "#A3E635",
        ]

        speaker_to_lane = {
            speaker: index
            for index, speaker in enumerate(speakers)
        }

        speaker_to_color = {
            speaker: speaker_palette[index % len(speaker_palette)]
            for index, speaker in enumerate(speakers)
        }

        self._draw_transcript_waveform(
            canvas,
            min_time,
            max_time,
            full_min_time,
            full_max_time,
            left_margin,
            right_margin,
            top_margin,
            bottom_margin,
            width,
            canvas_height,
            timeline_width
        )

        # Time ticks
        tick_count = 5
        for tick in range(tick_count + 1):
            fraction = tick / tick_count
            tick_time = min_time + duration * fraction
            x = left_margin + timeline_width * fraction

            canvas.create_line(
                x,
                18,
                x,
                canvas_height - 8,
                fill=COLORS["border"]
            )
            canvas.create_text(
                x,
                9,
                text=self._format_timeline_time(tick_time),
                anchor="n",
                fill=COLORS["text_muted"],
                font=("Cascadia Mono", 8)
            )

        # Selected segment / movable playhead marker
        selected_marker_time = self._get_transcript_playhead_time()

        if selected_marker_time is not None and min_time <= selected_marker_time <= max_time:
            if getattr(self, "transcript_timeline_center_lock_active", False):
                marker_x = left_margin + timeline_width / 2.0
            else:
                marker_x = left_margin + ((selected_marker_time - min_time) / duration) * timeline_width
            marker_color = "#38BDF8"

            canvas.create_polygon(
                marker_x - 6,
                top_margin - 17,
                marker_x + 6,
                top_margin - 17,
                marker_x,
                top_margin - 6,
                fill=marker_color,
                outline=marker_color,
                tags=("transcript_playhead_marker",)
            )
            canvas.create_line(
                marker_x,
                top_margin - 5,
                marker_x,
                canvas_height - bottom_margin + 4,
                fill=marker_color,
                width=1,
                tags=("transcript_playhead_marker",)
            )

        # Speaker/media lanes
        for speaker in speakers:
            lane = speaker_to_lane[speaker]
            y = top_margin + lane * lane_height + lane_height // 2

            canvas.create_text(
                8,
                y,
                text=speaker[:13],
                anchor="w",
                fill=COLORS["text_secondary"],
                font=("Cascadia Mono", 9, "bold")
            )

            canvas.create_line(
                left_margin,
                y,
                width - right_margin,
                y,
                fill=COLORS["border"]
            )

        # Segment blocks
        media_duration = self._get_linked_media_duration_seconds()
        for segment_index, segment in enumerate(self.transcript_segments):
            start_seconds = self._transcript_time_to_seconds(segment.start)
            end_seconds = self._transcript_time_to_seconds(segment.end)

            if start_seconds is None or end_seconds is None:
                continue

            if end_seconds < start_seconds:
                continue

            if end_seconds < min_time or start_seconds > max_time:
                continue

            visible_start_seconds = max(start_seconds, min_time)
            visible_end_seconds = min(end_seconds, max_time)

            speaker = segment.speaker or "Speaker"
            lane = speaker_to_lane.get(speaker, 0)
            color = speaker_to_color.get(speaker, COLORS["accent"])

            x1 = left_margin + ((visible_start_seconds - min_time) / duration) * timeline_width
            x2 = left_margin + ((visible_end_seconds - min_time) / duration) * timeline_width

            if x2 - x1 < 5:
                x2 = x1 + 5

            y = top_margin + lane * lane_height + lane_height // 2
            y1 = y - 8
            y2 = y + 8

            is_selected = selected_index == segment_index
            out_of_range = (
                isinstance(media_duration, (int, float))
                and media_duration > 0
                and start_seconds >= float(media_duration)
            )
            fill_color = "#475569" if out_of_range else color
            outline = "#FFFFFF" if is_selected else ("#F59E0B" if out_of_range else color)
            outline_width = 2 if is_selected else 1

            tag = f"timeline_segment_{segment_index}"

            canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=fill_color,
                outline=outline,
                width=outline_width,
                tags=(tag,)
            )
            if out_of_range:
                canvas.create_line(
                    x1,
                    y1,
                    x2,
                    y2,
                    fill="#F59E0B",
                    width=1,
                    tags=(tag,),
                )

            if x2 - x1 > 38:
                canvas.create_text(
                    x1 + 4,
                    y,
                    text=str(segment_index + 1),
                    anchor="w",
                    fill="#000000",
                    font=("Cascadia Mono", 8, "bold"),
                    tags=(tag,)
                )

            canvas.tag_bind(
                tag,
                "<Button-1>",
                lambda event, idx=segment_index: self._select_transcript_segment_from_timeline(idx)
            )
            canvas.tag_bind(
                tag,
                "<Enter>",
                lambda event: canvas.configure(cursor="hand2")
            )
            canvas.tag_bind(
                tag,
                "<Leave>",
                lambda event: canvas.configure(cursor="")
            )



    def _scroll_transcript_segment_into_view(self, segment_index: int) -> None:
        """Scroll selected transcript segment into a comfortable visible position."""
        if not hasattr(self, "transcript_textbox"):
            return

        if not hasattr(self, "transcript_display_ranges"):
            return

        target_info = None

        for info in self.transcript_display_ranges:
            if info.get("segment_index") == segment_index:
                target_info = info
                break

        if not target_info:
            return

        start_index = target_info.get("start")
        end_index = target_info.get("end")

        if not start_index or not end_index:
            return

        text_widget = self._get_transcript_text_widget()

        try:
            # First guarantee it is visible at all.
            text_widget.see(end_index)
            text_widget.see(start_index)

            # Then move it closer to the upper-middle of the visible area.
            start_line = int(str(text_widget.index(start_index)).split(".", 1)[0])
            total_lines = int(str(text_widget.index("end-1c")).split(".", 1)[0])
            total_lines = max(total_lines, 1)

            # Keep a few lines of context above the selected segment.
            target_fraction = max(0.0, min(1.0, (start_line - 4) / total_lines))
            text_widget.yview_moveto(target_fraction)

            # Re-assert visibility after yview move.
            text_widget.see(start_index)
        except Exception:
            try:
                text_widget.see(start_index)
            except Exception:
                pass


    def _flash_transcript_segment_selection(self, segment_index: int, duration_ms: int = 1500) -> None:
        """Temporarily highlight the selected transcript segment in the preview."""
        if not hasattr(self, "transcript_textbox"):
            return

        if not hasattr(self, "transcript_display_ranges"):
            return

        text_widget = self._get_transcript_text_widget()
        tag_name = "transcript_timeline_flash"

        # Each flash gets a token so old delayed clear callbacks cannot
        # clear a newer flash early when the user clicks timeline blocks quickly.
        flash_token = getattr(self, "_transcript_timeline_flash_token", 0) + 1
        self._transcript_timeline_flash_token = flash_token

        try:
            text_widget.tag_remove(tag_name, "1.0", "end")
            text_widget.tag_configure(
                tag_name,
                background="#334155",
                foreground="#FFFFFF"
            )
            text_widget.tag_raise(tag_name)
        except Exception:
            return

        target_info = None

        for info in self.transcript_display_ranges:
            if info.get("segment_index") == segment_index:
                target_info = info
                break

        if not target_info:
            return

        start_index = target_info.get("start")
        end_index = target_info.get("end")

        if not start_index or not end_index:
            return

        try:
            text_widget.tag_add(tag_name, start_index, end_index)
            self._scroll_transcript_segment_into_view(segment_index)
        except Exception:
            return

        def clear_flash() -> None:
            if getattr(self, "_transcript_timeline_flash_token", None) != flash_token:
                return

            try:
                text_widget.tag_remove(tag_name, "1.0", "end")
            except Exception:
                pass

        self.after(duration_ms, clear_flash)


    def _select_transcript_segment_from_timeline(self, segment_index: int) -> None:
        """Select a transcript segment from the timeline."""
        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return

        self.selected_transcript_segment_index = segment_index

        segment = self.transcript_segments[segment_index]
        playhead_time = None
        start_seconds = self._transcript_time_to_seconds(segment.start)
        end_seconds = self._transcript_time_to_seconds(segment.end)

        if start_seconds is not None and end_seconds is not None:
            playhead_time = (start_seconds + end_seconds) / 2
        elif start_seconds is not None:
            playhead_time = start_seconds
        elif end_seconds is not None:
            playhead_time = end_seconds

        if playhead_time is not None:
            self.transcript_playhead_seconds = playhead_time

        if hasattr(self, "_place_transcript_cursor_at_segment_offset"):
            self._place_transcript_cursor_at_segment_offset(segment_index, 0)

        if hasattr(self, "_scroll_transcript_segment_into_view"):
            self._scroll_transcript_segment_into_view(segment_index)

        self._flash_transcript_segment_selection(segment_index)

        segment = self.transcript_segments[segment_index]
        speaker = segment.speaker or "Speaker"
        start = segment.start or "no start"
        end = segment.end or "no end"

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"Selected segment {segment_index + 1:,}/{len(self.transcript_segments):,} from timeline • {speaker} • {start} → {end}",
                text_color=COLORS["text_primary"]
            )

        self._refresh_transcript_timeline()


    def _get_transcript_text_widget(self):
        """Return the underlying Tk text widget used by CTkTextbox."""
        return getattr(self.transcript_textbox, "_textbox", self.transcript_textbox)

    def _search_transcript_changed(self) -> None:
        """Update transcript search matches after the query changes."""
        self._update_transcript_search_matches(reset_index=True)

    def _set_transcript_search_navigation_state(self, enabled: bool) -> None:
        """Enable or disable transcript search navigation controls."""
        if not hasattr(self, "transcript_search_prev_button"):
            return

        state = "normal" if enabled else "disabled"
        self.transcript_search_prev_button.configure(state=state)
        self.transcript_search_next_button.configure(state=state)

    def _clear_transcript_search_tags(self) -> None:
        """Remove transcript search highlight tags."""
        if not hasattr(self, "transcript_textbox"):
            return

        text_widget = self._get_transcript_text_widget()
        try:
            text_widget.tag_remove("transcript_search_match", "1.0", "end")
            text_widget.tag_remove("transcript_search_current", "1.0", "end")
        except Exception:
            pass

    def _update_transcript_search_matches(self, reset_index: bool = False) -> None:
        """Find and highlight all matches in the transcript preview."""
        if not hasattr(self, "transcript_search_var"):
            return

        query = self.transcript_search_var.get().strip()
        self.transcript_search_matches = []

        text_widget = self._get_transcript_text_widget()

        previous_state = "normal"
        try:
            previous_state = self.transcript_textbox.cget("state")
        except Exception:
            pass

        try:
            self.transcript_textbox.configure(state="normal")
            self._clear_transcript_search_tags()

            text_widget.tag_configure(
                "transcript_search_match",
                background="#854D0E",
                foreground="#FFFFFF"
            )
            text_widget.tag_configure(
                "transcript_search_current",
                background="#F97316",
                foreground="#000000"
            )

            if not query or not self.transcript_segments:
                self.transcript_search_current_index = -1
                self.transcript_search_count_label.configure(
                    text="0 matches",
                    text_color=COLORS["text_muted"]
                )
                self._set_transcript_search_navigation_state(False)
                return

            full_text = text_widget.get("1.0", "end-1c")
            haystack = full_text.lower()
            needle = query.lower()

            search_from = 0
            needle_length = len(needle)

            while True:
                found_at = haystack.find(needle, search_from)
                if found_at == -1:
                    break

                start_index = f"1.0+{found_at}c"
                end_index = f"1.0+{found_at + needle_length}c"

                self.transcript_search_matches.append((start_index, end_index))
                text_widget.tag_add("transcript_search_match", start_index, end_index)

                search_from = found_at + max(1, needle_length)

            total = len(self.transcript_search_matches)

            if total == 0:
                self.transcript_search_current_index = -1
                self.transcript_search_count_label.configure(
                    text="0 matches",
                    text_color=COLORS["warning"]
                )
                self._set_transcript_search_navigation_state(False)
                return

            if reset_index or self.transcript_search_current_index < 0:
                self.transcript_search_current_index = 0
            elif self.transcript_search_current_index >= total:
                self.transcript_search_current_index = total - 1

            self._set_transcript_search_navigation_state(True)
            self._apply_current_transcript_search_match()

        finally:
            if previous_state == "disabled":
                self.transcript_textbox.configure(state="disabled")


    def _apply_current_transcript_search_match(self) -> None:
        """Highlight and scroll to the current transcript search match."""
        if not self.transcript_search_matches:
            return

        text_widget = self._get_transcript_text_widget()

        previous_state = "normal"
        try:
            previous_state = self.transcript_textbox.cget("state")
        except Exception:
            pass

        try:
            self.transcript_textbox.configure(state="normal")
            text_widget.tag_remove("transcript_search_current", "1.0", "end")

            current_match = self.transcript_search_matches[self.transcript_search_current_index]

            if isinstance(current_match, tuple):
                current_index, current_end = current_match
            else:
                query = self.transcript_search_var.get().strip()
                current_index = current_match
                current_end = f"{current_index}+{len(query)}c"

            text_widget.tag_add("transcript_search_current", current_index, current_end)
            text_widget.see(current_index)
            text_widget.mark_set("insert", current_index)

            self.transcript_search_count_label.configure(
                text=(
                    f"{self.transcript_search_current_index + 1}/"
                    f"{len(self.transcript_search_matches)} matches"
                ),
                text_color=COLORS["text_primary"]
            )

            self._on_transcript_preview_cursor_changed()

        finally:
            if previous_state == "disabled":
                self.transcript_textbox.configure(state="disabled")


    def _jump_to_transcript_search_match(self, direction: int) -> None:
        """Jump to the previous or next transcript search match."""
        if not self.transcript_search_matches:
            return

        total = len(self.transcript_search_matches)
        self.transcript_search_current_index = (
            self.transcript_search_current_index + direction
        ) % total

        self._apply_current_transcript_search_match()



    def _update_transcript_media_status(self) -> None:
        """Refresh linked transcript media display."""
        if not hasattr(self, "transcript_media_status_label"):
            return

        media_path = getattr(self, "linked_transcript_media_path", None)

        if media_path:
            self.transcript_media_status_label.configure(
                text=os.path.basename(media_path),
                text_color=COLORS["text_secondary"]
            )
        else:
            self.transcript_media_status_label.configure(
                text="No media",
                text_color=COLORS["text_muted"]
            )

    def _set_linked_transcript_media(self, media_path: Optional[str], log: bool = False) -> None:
        """Store linked media path for future waveform/timeline features."""
        previous_media_path = getattr(self, "linked_transcript_media_path", None)
        new_media_path = media_path or None

        if previous_media_path != new_media_path and hasattr(self, "_clear_transcript_waveform"):
            self._clear_transcript_waveform(refresh=True)
            self.transcript_media_duration_seconds = None
            self.transcript_media_duration_cache_key = None
            self.transcript_playback_follow_active = False

        self.linked_transcript_media_path = new_media_path
        if new_media_path:
            self.active_media_file_path = self._normalise_session_file_path(new_media_path)
        else:
            self.active_media_file_path = ""
        self._update_transcript_media_status()

        if log and media_path:
            self.log_message(
                f"Linked transcript media: {os.path.basename(media_path)}",
                "success"
            )


    def clear_transcript_media_link(self) -> None:
        """Clear only the linked transcript media file."""
        had_media = getattr(self, "linked_transcript_media_path", None)
        self._stop_transcript_playback_process()
        self._update_transcript_playback_buttons(False)
        self._set_linked_transcript_media(None)

        if hasattr(self, '_refresh_transcript_timeline'):
            self._refresh_transcript_timeline()

        if had_media:
            self.log_message("Cleared linked transcript media.", "info")

            if hasattr(self, "transcript_cursor_status_label"):
                self.transcript_cursor_status_label.configure(
                    text="Linked media cleared.",
                    text_color=COLORS["text_muted"]
                )


    def choose_transcript_media_file(self) -> None:
        """Choose a local media file to link to the current transcript."""
        filename = filedialog.askopenfilename(
            title="Choose Media for Transcript",
            filetypes=[
                ("Media files", "*.mp4 *.mkv *.mov *.avi *.webm *.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm"),
                ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                ("All files", "*.*"),
            ]
        )

        if not filename:
            return

        if not os.path.exists(filename):
            messagebox.showerror(
                "Media Not Found",
                "The selected media file does not exist."
            )
            return

        self._set_linked_transcript_media(filename, log=True)
        self._add_session_file(filename, self._session_file_kind_for_path(filename), select=True)

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"Linked media: {os.path.basename(filename)}",
                text_color=COLORS["text_primary"]
            )


    def import_transcript_file(self) -> None:
        """Import SRT, VTT, or TXT transcript file."""
        filename = filedialog.askopenfilename(
            title="Import Transcript",
            filetypes=[
                ("Transcript files", "*.srt *.vtt *.txt"),
                ("SRT files", "*.srt"),
                ("VTT files", "*.vtt"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if not filename:
            return

        try:
            segments = import_transcript(filename)

            if not segments:
                messagebox.showwarning(
                    "No Transcript Segments",
                    "No transcript segments could be imported from this file."
                )
                return

            self.transcript_segments = segments
            self.last_transcript_source = f"Imported file: {os.path.basename(filename)}"
            self.transcript_has_unsaved_edits = False
            self.transcript_undo_stack = []
            self.transcript_redo_stack = []
            self._set_linked_transcript_media(None)
            self._refresh_transcript_display()
            self.evidence_button.configure(state="normal")
            self._add_session_file(filename, SESSION_FILE_KIND_TRANSCRIPT, select=True)

            self.log_message(
                f"Imported transcript: {len(segments):,} segment(s) from {os.path.basename(filename)}",
                "success"
            )

        except Exception as e:
            logger.exception("Transcript import error")
            self.log_message(f"Transcript import failed: {e}", "error")
            messagebox.showerror("Transcript Import Error", str(e))

    def download_youtube_transcript_clicked(self) -> None:
        """Download YouTube captions/transcript for the first URL in the Source URLs box."""
        urls = self._get_current_source_urls()

        if not urls:
            messagebox.showwarning(
                "No YouTube URL",
                "Paste a YouTube video URL into the Source URLs box first."
            )
            return

        selected_url = urls[0]

        language_text = simpledialog.askstring(
            "YouTube Transcript Languages",
            "Language priority, comma-separated.\n\nExample: en, en-GB, ar",
            initialvalue="en"
        )

        if not language_text:
            return

        languages = [
            item.strip()
            for item in language_text.split(",")
            if item.strip()
        ]

        if not languages:
            languages = ["en"]

        prefer_manual_answer = messagebox.askyesno(
            "Transcript Preference",
            "Prefer manually created captions if available?\n\n"
            "Yes = manual captions first\n"
            "No = auto-generated captions first"
        )

        self.transcript_youtube_button.configure(state="disabled", text="Loading...")
        self.log_message(
            f"Downloading YouTube transcript for: {selected_url}",
            "info"
        )

        def worker() -> None:
            try:
                segments, info = download_youtube_transcript(
                    selected_url,
                    languages=languages,
                    prefer_manual=prefer_manual_answer,
                )

                video_info: Dict[str, Any] = {}
                speaker_name = "YouTube"

                api_key = self._resolve_youtube_api_key_for_action()

                if api_key:
                    try:
                        video_info = fetch_youtube_video_metadata(
                            selected_url,
                            api_key
                        )
                        speaker_name = video_info.get("channel_title") or "YouTube"
                    except Exception as metadata_error:
                        logger.warning(f"Could not fetch YouTube video metadata: {metadata_error}")

                segments = merge_transcript_segments(
                    segments,
                    speaker_name=speaker_name,
                )

                self._apply_speaker_label_rule(
                    segments,
                    single_speaker_name=speaker_name,
                )

                def on_success() -> None:
                    transcript_type = "auto-generated" if info.get("is_generated") else "manual"
                    language_code = info.get("language_code") or ", ".join(languages)

                    self.transcript_segments = segments
                    self.last_asr_metadata = None
                    self.last_youtube_video_info = video_info or None
                    self.last_transcript_source = (
                        f"YouTube {transcript_type} transcript "
                        f"({language_code}) for {selected_url}"
                    )

                    self._refresh_transcript_display()
                    self.evidence_button.configure(state="normal")

                    self.log_message(
                        f"Downloaded YouTube transcript: {len(segments):,} segment(s), "
                        f"{transcript_type}, language {language_code}",
                        "success"
                    )

                    messagebox.showinfo(
                        "YouTube Transcript Downloaded",
                        f"Transcript loaded into the Transcript section.\n\n"
                        f"Segments: {len(segments):,}\n"
                        f"Type: {transcript_type}\n"
                        f"Language: {language_code}"
                    )

                self.after(0, on_success)

            except Exception as e:
                error_message = str(e)

                def on_error() -> None:
                    self.log_message(
                        f"YouTube transcript download failed: {error_message}",
                        "error"
                    )
                    messagebox.showerror(
                        "YouTube Transcript Error",
                        "Could not download a transcript for this video.\n\n"
                        "Possible reasons:\n"
                        "• No captions are available\n"
                        "• Requested language is unavailable\n"
                        "• Captions are disabled\n"
                        "• YouTube blocked the request\n"
                        "• YouTube changed how captions are exposed\n\n"
                        f"Error:\n{error_message}"
                    )

                self.after(0, on_error)

            finally:
                def reset_button() -> None:
                    self.transcript_youtube_button.configure(
                        state="normal",
                        text="Get"
                    )

                self.after(0, reset_button)

        threading.Thread(target=worker, daemon=True).start()

    def _export_readable_transcript_txt(
        self,
        segments: List[TranscriptSegment],
        path: str
    ) -> None:
        """Export readable transcript TXT using current speaker/timestamp display options."""
        show_speakers = self.transcript_show_speakers_var.get()
        show_timestamps = self.transcript_show_timestamps_var.get()

        readable_segments = self._get_readable_transcript_segments()

        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("Transcript Export\n")
            f.write("=" * 80)
            f.write("\n\n")

            if self.last_transcript_source:
                f.write(f"Source: {self.last_transcript_source}\n")

            if getattr(self, "linked_transcript_media_path", None):
                f.write(f"Linked Media: {self.linked_transcript_media_path}\n")

            playback_metadata = self._get_transcript_playback_metadata()

            for metadata_key in ("Visual Sync Offset", "Playback Backend", "Waveform"):
                metadata_value = playback_metadata.get(metadata_key)

                if metadata_value:
                    f.write(f"{metadata_key}: {metadata_value}\n")

            if (
                self.last_transcript_source
                or getattr(self, "linked_transcript_media_path", None)
                or playback_metadata
            ):
                f.write("\n")

            if self.last_asr_metadata:
                f.write("ASR Warning:\n")
                f.write("-" * 80)
                f.write("\n")
                f.write(
                    "This transcript was generated using local automatic speech recognition. "
                    "It is a machine-generated draft and may contain transcription errors. "
                    "Speaker diarization is not included. Verify important lines against the original media."
                )
                f.write("\n\n")

            last_displayed_speaker = None

            for segment in readable_segments:
                speaker = segment.speaker or "Speaker"
                start = segment.start or ""
                end = segment.end or ""

                if show_speakers and speaker != last_displayed_speaker:
                    f.write(f"{speaker}\n")
                    last_displayed_speaker = speaker

                for paragraph in self._split_readable_text(segment.text):
                    f.write(paragraph)
                    f.write("\n\n")

                if show_timestamps and start and end:
                    f.write(f"[{start} - {end}]\n")

                f.write("\n")


        # Remove blank line directly before timestamp lines.
        # Keeps one blank line between transcript blocks, but changes:
        # text
        #
        # [time]
        # into:
        # text
        # [time]
        with open(path, "r", encoding="utf-8") as f:
            readable_content = f.read()

        readable_content = readable_content.replace("\n\n[", "\n[")

        with open(path, "w", encoding="utf-8") as f:
            f.write(readable_content)



    def open_asr_settings_clicked(self) -> None:
        """Open and save Local ASR default settings."""
        asr_defaults = load_asr_defaults()

        settings = ask_asr_settings(
            self,
            asr_defaults,
            title="Local ASR Defaults",
            action_label="Save Defaults",
        )

        if not settings:
            return

        save_asr_defaults(
            model_name=settings.get("model_name", "small"),
            speaker_name=settings.get("speaker_name", "Speaker 1"),
            language=settings.get("language", ""),
            initial_prompt=settings.get("initial_prompt", ""),
            device=settings.get("device", "cpu"),
            compute_type=settings.get("compute_type", "int8"),
            engine=settings.get("engine", "faster_whisper"),
            profile_name=settings.get("profile_name", "Custom"),
        )

        self.log_message(
            "Saved Local ASR defaults: "
            f"engine={settings.get('engine', 'faster_whisper')}, "
            f"model={settings.get('model_name')}, "
            f"language={settings.get('language') or 'auto-detect'}, "
            f"device={settings.get('device')}, "
            f"compute={settings.get('compute_type')}",
            "success"
        )

        messagebox.showinfo(
            "ASR Settings Saved",
            "Local ASR defaults were saved for future transcriptions."
        )

    def _online_asr_provider_option(
        self,
        provider_id: str,
    ) -> OnlineASRProviderOption:
        normalized = (provider_id or "").strip()
        for option in ONLINE_ASR_PROVIDER_OPTIONS:
            if option.provider_id == normalized:
                return option
        return ONLINE_ASR_PROVIDER_OPTIONS[0]

    def _normalize_online_asr_provider_id(self, provider_id: str) -> tuple[str, str]:
        normalized = (provider_id or "").strip()
        supported_ids = {option.provider_id for option in ONLINE_ASR_PROVIDER_OPTIONS}
        if normalized in supported_ids:
            return normalized, ""
        return (
            ONLINE_ASR_DEFAULT_PROVIDER_ID,
            "Unsupported Online ASR provider selection was reset to ElevenLabs Scribe v2.",
        )

    def _get_online_asr_provider_id(self) -> str:
        provider_id, status = self._normalize_online_asr_provider_id(
            getattr(self, "online_asr_provider_id", ONLINE_ASR_DEFAULT_PROVIDER_ID)
        )
        self.online_asr_provider_id = provider_id
        self.online_asr_provider_selection_status = status
        return provider_id

    def _set_online_asr_provider_id(
        self,
        provider_id: str,
        *,
        persist: bool = True,
    ) -> str:
        normalized, status = self._normalize_online_asr_provider_id(provider_id)
        self.online_asr_provider_id = normalized
        self.online_asr_provider_selection_status = status
        if persist:
            self._persist_online_asr_provider_id(normalized)
        return normalized

    def _persist_online_asr_provider_id(self, provider_id: str) -> bool:
        try:
            load_preferences = getattr(
                self.settings_manager,
                "load_preferences_only",
                self.settings_manager.load,
            )
            settings = load_preferences()
            settings.api_key = ""
            settings.online_asr_provider_id = provider_id
            return self.settings_manager.save(settings)
        except Exception:
            logger.error("Failed to persist Online ASR provider selection safely.")
            return False

    def _online_asr_credential_statuses(self) -> Dict[str, CredentialRuntimeStatus]:
        provider = self.__dict__.get("_online_asr_credential_status_provider")
        if callable(provider):
            return dict(provider())
        settings_manager = self.__dict__.get("settings_manager")
        if settings_manager is None:
            return {}
        return dict(
            build_runtime_credential_statuses(
                settings_manager=settings_manager,
                youtube_configured=False,
                credential_store=SystemKeyringCredentialStore(),
            )
        )

    def _online_asr_provider_credential_status(
        self,
        option: OnlineASRProviderOption,
    ) -> CredentialRuntimeStatus | None:
        statuses = self._online_asr_credential_statuses()
        return statuses.get(option.credential_entry_id)

    def _online_asr_status_label(
        self,
        status: CredentialRuntimeStatus | None,
        *,
        provider_id: str = ELEVENLABS_SCRIBE_PROVIDER_ID,
    ) -> str:
        if status is None:
            return "Unavailable"
        if status.state is CredentialPresenceState.CONFIGURED:
            record = normalize_validation_records(
                self._get_access_keys_validation_records()
            ).get(provider_id)
            if record is not None:
                return validation_status_text_for_state(record.state)
            return validation_status_text_for_state("not_yet_validated")
        if status.state is CredentialPresenceState.MISSING:
            return KEY_STATUS_NO_KEY_CONFIGURED
        if status.state is CredentialPresenceState.BACKEND_UNAVAILABLE:
            return "Unavailable"
        return "Status error"

    def open_online_asr_settings_clicked(self):
        """Open or focus the dedicated Online ASR provider-selection window."""
        existing = getattr(self, "online_asr_provider_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.focus()
                return existing
        except Exception:
            pass

        window = ctk.CTkToplevel(self)
        self.online_asr_provider_window = window
        window.title(ONLINE_ASR_PROVIDERS_WINDOW_TITLE)
        window.geometry("560x360")
        window.transient(self)
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(0, weight=1)

        def close_window() -> None:
            self.online_asr_provider_window = None
            try:
                window.destroy()
            except Exception:
                pass

        window.protocol("WM_DELETE_WINDOW", close_window)

        content = ctk.CTkFrame(window, fg_color=COLORS["bg_card"], corner_radius=10)
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            content,
            text=ONLINE_ASR_PROVIDERS_WINDOW_TITLE,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 2))

        ctk.CTkLabel(
            content,
            text=(
                "Choose the provider used by the Online ASR Transcribe action. "
                "No provider request is sent from this window."
            ),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="new", padx=14, pady=(0, 10))

        list_frame = ctk.CTkFrame(content, fg_color="transparent")
        list_frame.grid(row=2, column=0, sticky="nsew", padx=(14, 8), pady=(0, 12))

        detail_frame = ctk.CTkFrame(
            content,
            fg_color=COLORS["bg_input"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["border"],
        )
        detail_frame.grid(row=2, column=1, sticky="nsew", padx=(8, 14), pady=(0, 12))
        detail_frame.grid_columnconfigure(0, weight=1)

        selected_provider_var = tk.StringVar(value=self._get_online_asr_provider_id())
        selected_option = self._online_asr_provider_option(selected_provider_var.get())
        selected_status = self._online_asr_provider_credential_status(selected_option)

        detail_title_var = tk.StringVar(value=selected_option.display_name)
        detail_model_var = tk.StringVar(value=f"Model: {selected_option.model_id}")
        detail_status_var = tk.StringVar(
            value=self._online_asr_status_label(
                selected_status,
                provider_id=selected_option.provider_id,
            )
        )
        detail_note_var = tk.StringVar(
            value=(
                self.online_asr_provider_selection_status
                or "Provider selection is local metadata only."
            )
        )

        def select_provider(option: OnlineASRProviderOption) -> None:
            selected_provider_var.set(option.provider_id)
            status = self._online_asr_provider_credential_status(option)
            detail_title_var.set(option.display_name)
            detail_model_var.set(f"Model: {option.model_id}")
            detail_status_var.set(
                self._online_asr_status_label(
                    status,
                    provider_id=option.provider_id,
                )
            )
            detail_note_var.set("Provider selection is local metadata only.")

        for option in ONLINE_ASR_PROVIDER_OPTIONS:
            button = ctk.CTkButton(
                list_frame,
                text=option.display_name,
                command=lambda option=option: select_provider(option),
                height=34,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=(
                    COLORS["accent"]
                    if option.provider_id == selected_provider_var.get()
                    else COLORS["accent_secondary"]
                ),
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_primary"],
                corner_radius=8,
                anchor="w",
            )
            button.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            detail_frame,
            textvariable=detail_title_var,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"],
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 6))

        ctk.CTkLabel(
            detail_frame,
            textvariable=detail_model_var,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 5))

        ctk.CTkLabel(
            detail_frame,
            textvariable=detail_status_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 5))

        ctk.CTkLabel(
            detail_frame,
            textvariable=detail_note_var,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            wraplength=300,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 14))

        actions = ctk.CTkFrame(content, fg_color="transparent")
        actions.grid(row=3, column=0, columnspan=2, sticky="e", padx=14, pady=(0, 12))

        def use_selected_provider() -> None:
            option = self._online_asr_provider_option(selected_provider_var.get())
            self._set_online_asr_provider_id(option.provider_id, persist=True)
            detail_note_var.set(f"Using {option.display_name} for Online ASR.")

        def manage_key() -> None:
            access_window = self.open_access_keys_window()
            try:
                select_entry = getattr(access_window, "_select_entry", None)
                if callable(select_entry):
                    option = self._online_asr_provider_option(selected_provider_var.get())
                    select_entry(option.credential_entry_id)
            except Exception:
                pass

        ctk.CTkButton(
            actions,
            text="Close",
            command=close_window,
            width=90,
            height=34,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            actions,
            text="Manage key",
            command=manage_key,
            width=110,
            height=34,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            actions,
            text="Use provider",
            command=use_selected_provider,
            width=120,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
        ).pack(side="right")

        return window

    def online_asr_transcribe_clicked(self) -> None:
        """Open the explicit Online ASR workflow without dispatching a provider call."""
        existing = getattr(self, "online_asr_window", None)
        try:
            if existing is not None and existing.winfo_exists():
                existing.focus()
                return
        except Exception:
            pass

        dialog = ctk.CTkToplevel(self)
        self.online_asr_window = dialog
        dialog.title("Online ASR")
        dialog.geometry("540x260")
        dialog.transient(self)
        dialog.grid_columnconfigure(0, weight=1)

        content = ctk.CTkFrame(dialog, fg_color=COLORS["bg_card"], corner_radius=10)
        content.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        content.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            content,
            text="Online ASR",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"],
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 4))

        description = ctk.CTkLabel(
            content,
            text="ElevenLabs Scribe v2; local file only. No request is sent until Transcribe is pressed.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        description.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 10))

        file_var = tk.StringVar(value="")
        media_options = self._session_media_options()
        media_label_to_path = {label: path for label, path in media_options}
        default_media_path = self._default_session_media_path()
        selected_label = ""
        for label, path in media_options:
            if default_media_path and os.path.abspath(path) == os.path.abspath(default_media_path):
                selected_label = label
                break
        if not selected_label and len(media_options) == 1:
            selected_label = media_options[0][0]
        media_label_var = tk.StringVar(value=selected_label)
        if selected_label:
            file_var.set(media_label_to_path[selected_label])

        def on_media_selected(label: str) -> None:
            file_var.set(media_label_to_path.get(label, ""))

        ctk.CTkLabel(
            content,
            text="Media file",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 4))

        if media_options:
            file_selector = ctk.CTkComboBox(
                content,
                values=[label for label, _path in media_options],
                variable=media_label_var,
                command=on_media_selected,
                height=34,
            )
            file_selector.grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))
        else:
            ctk.CTkLabel(
                content,
                text="Add media with FILES + or drag/drop first.",
                font=ctk.CTkFont(size=11),
                text_color="#ffc107",
                anchor="w",
            ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 8))

        status_var = tk.StringVar(value="Ready. Choose a local media file, then press Transcribe.")
        status_label = ctk.CTkLabel(
            content,
            textvariable=status_var,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        status_label.grid(row=4, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))

        actions = ctk.CTkFrame(content, fg_color="transparent")
        actions.grid(row=5, column=0, columnspan=2, sticky="e", padx=14, pady=(0, 12))

        def close_dialog() -> None:
            self.online_asr_window = None
            try:
                dialog.destroy()
            except Exception:
                pass

        close_button = ctk.CTkButton(
            actions,
            text="Close",
            command=close_dialog,
            width=90,
            height=34,
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
        )
        close_button.pack(side="right", padx=(8, 0))

        start_button = ctk.CTkButton(
            actions,
            text="Transcribe",
            command=lambda: self._start_online_asr_transcription(
                file_var.get(),
                status_var=status_var,
                start_button=start_button,
                close_button=close_button,
                dialog=dialog,
            ),
            width=110,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
        )
        start_button.pack(side="right")

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

    def _online_asr_set_busy(
        self,
        busy: bool,
        *,
        status_var: object | None = None,
        start_button: object | None = None,
        browse_button: object | None = None,
        close_button: object | None = None,
    ) -> None:
        self.online_asr_busy = bool(busy)
        state = "disabled" if busy else "normal"
        for widget in (
            getattr(self, "transcript_online_asr_button", None),
            start_button,
            browse_button,
            close_button,
        ):
            try:
                if widget is not None:
                    widget.configure(state=state)
            except Exception:
                pass
        if status_var is not None and busy:
            try:
                status_var.set("Online ASR request is running...")
            except Exception:
                pass

    def _dispatch_online_asr_provider_action(
        self,
        media_file: str,
        *,
        coordinator_factory: object = ASRProviderActionCoordinator,
        executor_factory: object = create_elevenlabs_scribe_sdk_provider_executor,
    ) -> tuple[object, ElevenLabsScribeResult | None]:
        provider_id = self._get_online_asr_provider_id()
        option = self._online_asr_provider_option(provider_id)
        request = ElevenLabsScribeRequest(
            file_path=media_file,
            tag_audio_events=False,
            diarize=False,
            timestamps_granularity="word",
            keyterms=(),
        )
        inner_executor = executor_factory(request)
        result_holder: Dict[str, ElevenLabsScribeResult] = {}

        def trusted_executor(provider_id: str, action_kind: str, credential: str) -> object:
            result = inner_executor(provider_id, action_kind, credential)
            if isinstance(result, ElevenLabsScribeResult):
                result_holder["result"] = result
            return result

        coordinator = coordinator_factory(
            executors={
                (option.provider_id, ASR_PROVIDER_ACTION_TRANSCRIBE): trusted_executor
            }
        )
        action_result = coordinator.dispatch_provider_action(
            option.provider_id,
            action_kind=ASR_PROVIDER_ACTION_TRANSCRIBE,
        )
        return action_result, result_holder.get("result")

    def _online_asr_result_to_segments(
        self,
        result: ElevenLabsScribeResult,
    ) -> List[TranscriptSegment]:
        segments: List[TranscriptSegment] = []
        for item in result.words:
            word_type = (item.word_type or "word").strip().casefold()
            if word_type not in {"", "word", "words"}:
                continue
            text = (item.text or "").strip()
            if not text:
                continue
            start = self._seconds_to_transcript_time(item.start or 0.0)
            end = self._seconds_to_transcript_time(
                item.end if item.end is not None else item.start or 0.0
            )
            speaker = item.speaker_id.strip() if item.speaker_id else "Speaker 1"
            segments.append(
                TranscriptSegment(
                    speaker=speaker or "Speaker 1",
                    start=start,
                    end=end,
                    text=text,
                )
            )
        if not segments and result.text.strip():
            segments.append(
                TranscriptSegment(
                    speaker="Speaker 1",
                    start=self._seconds_to_transcript_time(0.0),
                    end=self._seconds_to_transcript_time(0.0),
                    text=result.text.strip(),
                )
            )
        return segments

    def _apply_online_asr_success(
        self,
        media_file: str,
        result: ElevenLabsScribeResult,
    ) -> None:
        segments = self._online_asr_result_to_segments(result)
        self.transcript_segments = segments
        self.last_youtube_video_info = None
        self.last_asr_metadata = {
            "engine": "online_asr",
            "provider_id": result.provider_id,
            "model_id": result.model_id,
            "language": result.language_code or "unknown",
            "language_probability": result.language_probability,
            "segment_count": len(segments),
            "word_item_count": len(result.words),
            "audio_event_item_count": len(
                [
                    item
                    for item in result.words
                    if (item.word_type or "").strip().casefold() not in {"", "word", "words"}
                ]
            ),
        }
        self._set_linked_transcript_media(media_file)
        self.last_transcript_source = (
            f"Online ASR transcript from {os.path.basename(media_file)} "
            f"using ElevenLabs Scribe v2"
        )
        self._refresh_transcript_display()
        self.evidence_button.configure(state="normal")
        probability = result.language_probability
        probability_text = f"{probability:.2%}" if probability is not None else "unknown"
        self.log_message(
            f"Online ASR complete: {len(segments):,} segment(s), "
            f"language={result.language_code or 'unknown'}, confidence={probability_text}",
            "success",
        )
        messagebox.showinfo(
            "Online ASR Complete",
            (
                f"Transcribed file:\n\n{os.path.basename(media_file)}\n\n"
                f"Segments: {len(segments):,}\n"
                f"Detected language: {result.language_code or 'unknown'}\n"
                f"Language confidence: {probability_text}"
            ),
        )

    def _online_asr_failure_message(self, action_result: object) -> str:
        diagnostic = getattr(action_result, "safe_diagnostic", "") or "online_asr_failed"
        status = getattr(getattr(action_result, "status", None), "value", "")
        if status:
            return f"Online ASR failed safely: {status} / {diagnostic}"
        return f"Online ASR failed safely: {diagnostic}"

    def _build_online_asr_provider_call_gate(self, media_file: str) -> tuple[object, object]:
        """Build a metadata-only Online ASR provider-call gate without dispatching."""
        option = self._online_asr_provider_option(self._get_online_asr_provider_id())
        statuses = self._online_asr_credential_statuses()
        plan, summary = build_online_asr_execution_gate_plan(
            selected_provider=option,
            provider_options=ONLINE_ASR_PROVIDER_OPTIONS,
            credential_statuses=statuses,
            media_file_selected=bool((media_file or "").strip()),
            media_file_name=os.path.basename(media_file or ""),
        )
        self.last_online_asr_execution_gate_plan = plan
        self.last_online_asr_execution_gate_summary = summary
        return plan, summary

    def _record_online_asr_provider_call_gate(self, media_file: str) -> tuple[object, object]:
        """Record Online ASR gate metadata for UI/status review without secrets."""
        plan, summary = self._build_online_asr_provider_call_gate(media_file)
        self.last_online_asr_execution_gate_text = (
            render_online_asr_execution_gate_summary_text(summary, plan=plan)
        )
        return plan, summary

    def _start_online_asr_transcription(
        self,
        media_file: str,
        *,
        status_var: object | None = None,
        start_button: object | None = None,
        browse_button: object | None = None,
        close_button: object | None = None,
        dialog: object | None = None,
    ) -> bool:
        if getattr(self, "online_asr_busy", False):
            return False

        media_file = (media_file or "").strip()
        if not media_file:
            if status_var is not None:
                status_var.set("Choose a local media file before transcribing.")
            return False

        _gate_plan, gate_summary = self._record_online_asr_provider_call_gate(media_file)
        if not getattr(gate_summary, "credential_configured", False):
            message = (
                "Online ASR requires a configured provider key/account in KEYS/ACCOUNTS "
                "before any provider call can be dispatched."
            )
            if status_var is not None:
                status_var.set(message)
            self.log_message(message, "warning")
            try:
                self.open_online_asr_settings_clicked()
            except Exception:
                pass
            return False

        self._online_asr_set_busy(
            True,
            status_var=status_var,
            start_button=start_button,
            browse_button=browse_button,
            close_button=close_button,
        )
        self.log_message(
            f"Starting Online ASR with ElevenLabs Scribe v2 for {os.path.basename(media_file)}",
            "info",
        )

        def ui_call(callback: object) -> None:
            try:
                if dialog is not None and not dialog.winfo_exists():
                    return
            except Exception:
                pass
            self.after(0, callback)

        def worker() -> None:
            try:
                action_result, provider_result = self._dispatch_online_asr_provider_action(media_file)
                if getattr(action_result, "action_succeeded", False) and provider_result is not None:
                    def on_success() -> None:
                        self._apply_online_asr_success(media_file, provider_result)
                        if status_var is not None:
                            status_var.set("Online ASR complete.")

                    ui_call(on_success)
                else:
                    def on_failure() -> None:
                        message = self._online_asr_failure_message(action_result)
                        if status_var is not None:
                            status_var.set(message)
                        self.log_message(message, "error")
                        messagebox.showerror("Online ASR Error", message)

                    ui_call(on_failure)
            except ElevenLabsScribeValidationError as validation_error:
                fixed_message = f"Online ASR request rejected: {validation_error}"

                def on_validation_error() -> None:
                    if status_var is not None:
                        status_var.set(fixed_message)
                    self.log_message(fixed_message, "error")
                    messagebox.showerror("Online ASR Error", fixed_message)

                ui_call(on_validation_error)
            except (KeyboardInterrupt, SystemExit, GeneratorExit):
                raise
            except Exception:
                fixed_message = "Online ASR failed safely: online_asr_unexpected_local_error"

                def on_unexpected_error() -> None:
                    if status_var is not None:
                        status_var.set(fixed_message)
                    self.log_message(fixed_message, "error")
                    messagebox.showerror("Online ASR Error", fixed_message)

                ui_call(on_unexpected_error)
            finally:
                self.after(
                    0,
                    lambda: self._online_asr_set_busy(
                        False,
                        status_var=status_var,
                        start_button=start_button,
                        browse_button=browse_button,
                        close_button=close_button,
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()
        return True


    def _build_asr_auto_probe_candidates(
        self,
        selected_model: str,
        selected_device: str,
        selected_compute_type: str,
    ) -> List[Dict[str, Any]]:
        """Return ASR candidates to test for Auto Quality Probe.

        Accuracy is priority. The fast default list tests AMD/whisper.cpp Vulkan
        candidates plus the strongest CPU baseline. Set ASR_AUTO_PROBE_FULL=1
        to run the larger CPU/faster-whisper matrix.
        """
        candidates: List[Dict[str, Any]] = []

        def add_whispercpp(label: str, model: str, prompt_mode: str) -> None:
            candidates.append({
                "label": label,
                "model_name": model,
                "device": "vulkan",
                "compute_type": "",
                "vad_filter": False,
                "condition_on_previous_text": None,
                "use_reference_hotwords": prompt_mode == "terms",
                "use_reference_text_prompt": prompt_mode == "phrases",
                "whispercpp_prompt_mode": prompt_mode,
                "engine": "whispercpp_vulkan",
                "beam_size": 5,
                "audio_filter": None,
            })

        selected_is_whispercpp = (
            str(selected_device or "").strip().lower()
            in {"vulkan", "whispercpp", "whisper.cpp"}
            or str(selected_compute_type or "").strip().lower()
            in {"vulkan", "whispercpp", "whisper.cpp"}
        )

        if selected_is_whispercpp:
            add_whispercpp(
                "Current selected whisper.cpp Vulkan large-v3",
                selected_model or "large-v3",
                "phrases",
            )
            add_whispercpp(
                "Current selected whisper.cpp Vulkan large-v3 unprompted",
                selected_model or "large-v3",
                "none",
            )
            return candidates

        if is_whispercpp_vulkan_available("large-v3"):
            add_whispercpp("AMD GPU — whisper.cpp large-v3 phrase prompt", "large-v3", "phrases")
            add_whispercpp("AMD GPU — whisper.cpp large-v3 unprompted", "large-v3", "none")

        if is_whispercpp_vulkan_available("large-v3-turbo"):
            add_whispercpp("AMD GPU — whisper.cpp large-v3-turbo phrase prompt", "large-v3-turbo", "phrases")
            add_whispercpp("AMD GPU — whisper.cpp large-v3-turbo terms only", "large-v3-turbo", "terms")

        def add(
            label: str,
            model: str,
            device: str,
            compute: str,
            vad_filter: bool = True,
            condition_on_previous_text: Optional[bool] = None,
            use_reference_hotwords: bool = False,
            audio_filter: Optional[str] = None,
            beam_size: int = 5,
        ) -> None:
            key = (
                model,
                device,
                compute,
                bool(vad_filter),
                condition_on_previous_text,
                bool(use_reference_hotwords),
                audio_filter or "",
                int(beam_size or 5),
            )

            if any(
                (
                    item["model_name"],
                    item["device"],
                    item["compute_type"],
                    bool(item.get("vad_filter", True)),
                    item.get("condition_on_previous_text"),
                    bool(item.get("use_reference_hotwords", False)),
                    item.get("audio_filter") or "",
                    int(item.get("beam_size") or 5),
                ) == key
                for item in candidates
            ):
                return

            candidates.append({
                "label": label,
                "model_name": model,
                "device": device,
                "compute_type": compute,
                "vad_filter": bool(vad_filter),
                "condition_on_previous_text": condition_on_previous_text,
                "use_reference_hotwords": bool(use_reference_hotwords),
                "use_reference_text_prompt": False,
                "engine": "faster_whisper",
                "audio_filter": audio_filter or None,
                "beam_size": int(beam_size or 5),
            })

        add("Draft CPU", "small", "cpu", "int8", vad_filter=True)
        add("Recommended CPU", "medium", "cpu", "int8", vad_filter=True)
        add("Accurate CPU", "large-v3", "cpu", "int8", vad_filter=True)
        add("Accurate CPU + beam 8", "large-v3", "cpu", "int8", vad_filter=True, beam_size=8)
        add("Accurate CPU + beam 12", "large-v3", "cpu", "int8", vad_filter=True, beam_size=12)
        add("Accurate CPU + float32", "large-v3", "cpu", "float32", vad_filter=True)
        add("Accurate CPU + float32 + beam 8", "large-v3", "cpu", "float32", vad_filter=True, beam_size=8)
        add("Accurate CPU + loudnorm", "large-v3", "cpu", "int8", vad_filter=True, audio_filter="loudnorm")
        add("Accurate CPU + speech clean", "large-v3", "cpu", "int8", vad_filter=True, audio_filter="speech_clean")
        add("Accurate CPU + voice EQ", "large-v3", "cpu", "int8", vad_filter=True, audio_filter="voice_eq")
        add("Accurate CPU + denoise", "large-v3", "cpu", "int8", vad_filter=True, audio_filter="denoise")
        add("Accurate CPU + denoise+loudnorm", "large-v3", "cpu", "int8", vad_filter=True, audio_filter="denoise_loudnorm")
        add("Accurate CPU - no VAD", "large-v3", "cpu", "int8", vad_filter=False)
        add("Accurate CPU - no VAD + beam 8", "large-v3", "cpu", "int8", vad_filter=False, beam_size=8)
        add("Accurate CPU - no VAD + float32", "large-v3", "cpu", "float32", vad_filter=False)
        add("Accurate CPU - no VAD + float32 + beam 8", "large-v3", "cpu", "float32", vad_filter=False, beam_size=8)
        add("Accurate CPU - no VAD + loudnorm", "large-v3", "cpu", "int8", vad_filter=False, audio_filter="loudnorm")
        add("Accurate CPU - no VAD + speech clean", "large-v3", "cpu", "int8", vad_filter=False, audio_filter="speech_clean")
        add("Accurate CPU - no VAD + no context carry", "large-v3", "cpu", "int8", vad_filter=False, condition_on_previous_text=False)
        add("Accurate CPU - no VAD + hotwords", "large-v3", "cpu", "int8", vad_filter=False, condition_on_previous_text=False, use_reference_hotwords=True)

        if selected_device == "cuda":
            add("GPU Accurate", "large-v3", "cuda", "float16", vad_filter=True)
            add("GPU Accurate - no VAD", "large-v3", "cuda", "float16", vad_filter=False)

        add("Current Selected", selected_model, selected_device, selected_compute_type, vad_filter=True)

        if os.environ.get("ASR_AUTO_PROBE_FULL", "").strip().lower() not in {"1", "true", "yes", "full"}:
            fast_candidates = []
            for candidate in candidates:
                label_lower = str(candidate.get("label", "")).strip().lower()
                if "whisper.cpp" in label_lower:
                    fast_candidates.append(candidate)
                    continue
                if label_lower == "accurate cpu":
                    fast_candidates.append(candidate)
                    continue
            if fast_candidates:
                return fast_candidates

        return candidates

    def _plain_text_from_segments(self, segments: List[TranscriptSegment]) -> str:
        """Return plain text from transcript segments."""
        return "\n".join((segment.text or "").strip() for segment in segments if (segment.text or "").strip())

    def _asr_probe_timestamp_to_seconds(self, value: str) -> float:
        """Parse HH:MM:SS.mmm or MM:SS.mmm timestamp strings."""
        text = str(value or "").strip()

        if not text:
            return 0.0

        try:
            parts = text.split(":")

            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600.0 + minutes * 60.0 + seconds

            if len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60.0 + seconds

            return float(text)
        except Exception:
            return 0.0

    def _reference_text_for_probe(
        self,
        reference_segments: List[TranscriptSegment],
        probe_seconds: int,
    ) -> str:
        """Build reference text from existing transcript segments inside probe range."""
        pieces: List[str] = []
        limit = max(1.0, float(probe_seconds))

        for segment in reference_segments:
            start_seconds = self._asr_probe_timestamp_to_seconds(getattr(segment, "start", "0"))
            end_seconds = self._asr_probe_timestamp_to_seconds(getattr(segment, "end", "0"))

            # Keep scoring fair: do not include a reference line that mostly belongs
            # outside the probe clip.
            if start_seconds > limit:
                continue

            if end_seconds and end_seconds > limit + 0.35:
                continue

            text = (getattr(segment, "text", "") or "").strip()

            if text:
                pieces.append(text)

        return " ".join(pieces).strip()



    def _asr_reference_glossary_terms(self, reference_segments=None):
        import re

        ignored = {
            "the", "and", "for", "that", "this", "you", "your", "are", "was", "were",
            "with", "but", "not", "care", "honest", "great", "content", "there",
            "think", "when", "screen", "event", "trying", "insinuate", "understand",
            "blindfold", "saying", "okay", "scene", "cut", "lot", "digest", "more",
            "need", "like", "what", "have", "cleared", "black", "blacked", "yeah",
            "all", "hmm", "mm-hmm", "mhm", "shut", "cool", "oh", "uh", "um",
            "im", "i'm", "ive", "i've", "whats", "what's", "youre", "you're"
        }

        terms = []
        seen = set()

        def clean(term):
            term = (term or "").strip(" .,:;!?()[]{}<>\"'‘’“”")
            term = re.sub(r"\s+", " ", term).strip()
            term = re.sub(r"[’']s$", "", term, flags=re.IGNORECASE)
            term = term.strip(" .,:;!?()[]{}<>\"'‘’“”")
            return term

        def good(term):
            term = clean(term)

            if len(term) < 3 or len(term) > 80:
                return False

            lower = term.lower().replace("’", "'").strip("- ")

            if lower in ignored:
                return False

            if "youtube" in lower:
                return False

            if lower.endswith("-"):
                return False

            # Drop contractions/fillers such as I'm, I've, What's, You're.
            if "'" in lower or "’" in lower:
                return False

            # Drop plain common words. Keep only proper-noun-looking terms.
            has_signal = (
                term[:1].isupper()
                or any(ch.isupper() for ch in term[1:])
                or any(ch.isdigit() for ch in term)
                or any(ord(ch) > 127 for ch in term)
            )

            if not has_signal:
                return False

            # Avoid short all-caps/generic noise.
            if term.isupper() and len(term) <= 8:
                return False

            return True

        def add(term):
            term = clean(term)

            if not good(term):
                return

            key = term.lower().replace("’", "'")

            if key in seen:
                return

            seen.add(key)
            terms.append(term)

        def get_value(segment, *keys):
            if isinstance(segment, dict):
                for key in keys:
                    value = segment.get(key)
                    if value:
                        return str(value)
                return ""

            for key in keys:
                value = getattr(segment, key, None)
                if value:
                    return str(value)

            return ""

        def collect(value):
            value = value or ""

            # Multi-word proper nouns first: Nicolas Cage, etc.
            for phrase in re.findall(r"(?:[A-Z][A-Za-z0-9_-]{2,}\s+){1,4}[A-Z][A-Za-z0-9_-]{2,}", value):
                add(phrase)

            # Single proper nouns / mixed-case names: ZoneX, Caltheris, Nyxara.
            for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9_-]{2,50}(?:[’']s)?", value):
                add(token)

        for segment in list(reference_segments or []):
            collect(get_value(segment, "speaker", "speaker_name", "name", "label"))
            collect(get_value(segment, "text", "content", "caption", "line"))

            if len(terms) >= 80:
                break

        # If a multi-word term exists, remove its component words.
        multiword_parts = set()
        for term in terms:
            if " " in term:
                for part in term.split():
                    multiword_parts.add(part.lower())

        pruned = []
        pruned_seen = set()

        for term in terms:
            key = term.lower()

            if " " not in term and key in multiword_parts:
                continue

            if key in pruned_seen:
                continue

            pruned_seen.add(key)
            pruned.append(term)

        return pruned[:40]


    def _build_asr_reference_glossary_prompt(self, reference_segments=None, base_prompt=None):
        terms = self._asr_reference_glossary_terms(reference_segments)

        # Important: do not append glossary lists into initial_prompt.
        # Faster-whisper can treat prompt text as transcript context and hallucinate it.
        # The cleaned terms are returned for metadata/scoring and tightly-filtered hotwords only.
        return base_prompt, terms

    def _normalise_asr_compare_text(self, text: str) -> List[str]:
        """Normalize text into comparable words."""
        import re

        text = str(text or "").lower()
        text = text.replace("’", "'")
        text = re.sub(r"[^a-z0-9']+", " ", text)
        return [word for word in text.split() if word]

    def _levenshtein_distance(self, a: List[str], b: List[str]) -> int:
        """Return Levenshtein edit distance for two token lists."""
        if not a:
            return len(b)

        if not b:
            return len(a)

        previous = list(range(len(b) + 1))

        for i, token_a in enumerate(a, start=1):
            current = [i]

            for j, token_b in enumerate(b, start=1):
                cost = 0 if token_a == token_b else 1
                current.append(
                    min(
                        previous[j] + 1,
                        current[j - 1] + 1,
                        previous[j - 1] + cost,
                    )
                )

            previous = current

        return previous[-1]

    def _asr_reference_error_rate(self, reference_text: str, candidate_text: str) -> Optional[float]:
        """Return word error rate against reference text, or None if no reference."""
        reference_words = self._normalise_asr_compare_text(reference_text)
        candidate_words = self._normalise_asr_compare_text(candidate_text)

        if not reference_words:
            return None

        return self._levenshtein_distance(reference_words, candidate_words) / max(1, len(reference_words))

    def _asr_reference_acceptance_threshold(self) -> float:
        """Minimum reference word accuracy required before accepting an ASR probe."""
        return 0.95

    def _show_asr_auto_probe_results(
        self,
        media_file: str,
        results: List[Dict[str, Any]],
        best_index: int,
        probe_seconds: int,
    ) -> None:
        """Show Auto Probe results in a comparison window."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("ASR Auto Quality Probe Results")
        dialog.geometry("980x720")
        dialog.minsize(760, 520)
        dialog.transient(self)

        try:
            x = self.winfo_x() + 80
            y = self.winfo_y() + 60
            dialog.geometry(f"980x720+{x}+{y}")
        except Exception:
            pass

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        title = ctk.CTkLabel(
            dialog,
            text=f"ASR Auto Quality Probe — first {probe_seconds}s of {os.path.basename(media_file)}",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))

        textbox = ctk.CTkTextbox(dialog, wrap="word", font=ctk.CTkFont(size=12))
        textbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))

        lines: List[str] = []

        if 0 <= best_index < len(results):
            best = results[best_index]
            best_metadata = best.get("metadata") or {}
            best_reference_scored = bool(best_metadata.get("reference_scored"))
            best_reference_accuracy = best_metadata.get("reference_word_accuracy")
            reference_threshold = self._asr_reference_acceptance_threshold()

            best_failed_reference_gate = (
                best_reference_scored
                and best_reference_accuracy is not None
                and best_reference_accuracy < reference_threshold
            )

            if best_failed_reference_gate:
                lines.append("BEST PROBE CANDIDATE — FAILED REFERENCE THRESHOLD")
            elif best_reference_scored:
                lines.append("SELECTED BEST PROBE — PASSED REFERENCE THRESHOLD")
            else:
                lines.append("SELECTED BEST PROBE — CONFIDENCE-SCORED ONLY")

            lines.append("=" * 80)
            lines.append(
                f"{best.get('label')} — "
                f"model={best.get('model_name')} / "
                f"device={best.get('device')} / "
                f"compute={best.get('compute_type')}"
            )

            metadata = best.get("metadata") or {}
            score = metadata.get("quality_score")

            if score is not None:
                lines.append(f"Probe quality score: {score:.2f}")

            if best_reference_scored:
                lines.append(
                    f"Reference word accuracy: {best_reference_accuracy:.2%}"
                    if best_reference_accuracy is not None
                    else "Reference word accuracy: unknown"
                )
                lines.append(f"Reference pass threshold: {reference_threshold:.2%}")
                lines.append("Status: FAILED — keep reference transcript / try stronger method" if best_failed_reference_gate else "Status: PASSED")

            lines.append("")

        lines.append("ALL PROBE RESULTS")
        lines.append("=" * 80)

        for index, result in enumerate(results, start=1):
            lines.append("")
            lines.append("-" * 80)
            prefix = "BEST: " if index - 1 == best_index else ""
            lines.append(
                f"{prefix}{index}. {result.get('label')} — "
                f"model={result.get('model_name')} / "
                f"device={result.get('device')} / "
                f"compute={result.get('compute_type')}"
            )

            if result.get("error"):
                lines.append(f"ERROR: {result.get('error')}")
                continue

            metadata = result.get("metadata") or {}
            score = metadata.get("quality_score")
            language = metadata.get("language") or "unknown"
            probability = metadata.get("language_probability")
            avg_logprob = metadata.get("avg_logprob_mean")
            compression = metadata.get("compression_ratio_mean")
            no_speech = metadata.get("no_speech_prob_mean")

            reference_scored = bool(metadata.get("reference_scored"))
            reference_word_error_rate = metadata.get("reference_word_error_rate")
            reference_word_accuracy = metadata.get("reference_word_accuracy")
            phrase_hints = metadata.get("auto_probe_reference_glossary_terms") or []

            lines.append(f"Segments: {len(result.get('segments') or [])}")
            lines.append(f"Language: {language}")
            lines.append(f"Language probability: {probability:.2%}" if probability is not None else "Language probability: unknown")
            lines.append(f"Quality score: {score:.2f}" if score is not None else "Quality score: unknown")
            lines.append(f"VAD filter: {'on' if metadata.get('auto_probe_candidate_vad_filter', True) else 'off'}")
            lines.append(
                "Condition on previous text: "
                + (
                    "default"
                    if metadata.get("auto_probe_candidate_condition_on_previous_text") is None
                    else str(bool(metadata.get("auto_probe_candidate_condition_on_previous_text"))).lower()
                )
            )
            lines.append(f"Hotwords parameter used: {'yes' if metadata.get('auto_probe_candidate_hotwords_used') else 'no'}")

            if phrase_hints:
                preview = ", ".join(str(term) for term in phrase_hints[:20])
                suffix = " ..." if len(phrase_hints) > 20 else ""
                lines.append(f"Reference glossary hints: {preview}{suffix}")
            else:
                lines.append("Reference glossary hints: none")

            if reference_scored:
                lines.append(
                    f"Reference word accuracy: {reference_word_accuracy:.2%}"
                    if reference_word_accuracy is not None
                    else "Reference word accuracy: unknown"
                )
                lines.append(
                    f"Reference word error rate: {reference_word_error_rate:.2%}"
                    if reference_word_error_rate is not None
                    else "Reference word error rate: unknown"
                )
            else:
                lines.append("Reference scoring: unavailable")

            lines.append(f"Avg logprob: {avg_logprob:.4f}" if avg_logprob is not None else "Avg logprob: unknown")
            lines.append(f"Compression ratio: {compression:.4f}" if compression is not None else "Compression ratio: unknown")
            lines.append(f"No speech probability: {no_speech:.4f}" if no_speech is not None else "No speech probability: unknown")
            elapsed_seconds = metadata.get("elapsed_seconds")
            speed_x = metadata.get("processing_speed_x_realtime")
            if elapsed_seconds is not None:
                try:
                    elapsed_value = float(elapsed_seconds)
                    if speed_x is not None:
                        lines.append(f"Elapsed: {elapsed_value:.2f}s ({float(speed_x):.2f}x realtime)")
                    else:
                        lines.append(f"Elapsed: {elapsed_value:.2f}s")
                except Exception:
                    pass

            if reference_scored and result.get("reference_text"):
                lines.append("")
                lines.append("Reference:")
                lines.append(result.get("reference_text") or "")

            lines.append("")
            lines.append("Transcript:")
            lines.append(result.get("text") or "")

        lines.append("")
        lines.append("=" * 80)
        lines.append("Note:")

        reference_scoring_used = any(
            bool((result.get("metadata") or {}).get("reference_scored"))
            for result in results
        )

        calibration_probe_used = any(
            bool((result.get("metadata") or {}).get("asr_calibration_probe"))
            for result in results
        )

        best_failed_reference_gate = False

        if 0 <= best_index < len(results):
            best_metadata = results[best_index].get("metadata") or {}
            best_reference_accuracy = best_metadata.get("reference_word_accuracy")
            best_failed_reference_gate = (
                bool(best_metadata.get("reference_scored"))
                and best_reference_accuracy is not None
                and best_reference_accuracy < self._asr_reference_acceptance_threshold()
            )

        if calibration_probe_used:
            lines.append("- ASR calibration self-test used a built-in local reference clip.")
            lines.append("- The current user transcript was not changed.")
            lines.append(f"- Passing threshold: {self._asr_reference_acceptance_threshold():.2%} reference word accuracy.")
        elif reference_scoring_used:
            lines.append("- Reference scoring was used because a transcript was already imported.")
            lines.append(f"- Passing threshold: {self._asr_reference_acceptance_threshold():.2%} reference word accuracy.")
        else:
            lines.append("- Auto Probe compared settings without a reference transcript, so the score is a guide, not proof.")

        lines.append("- If common words or names are wrong on clear audio, that method should not be accepted for full subtitles.")

        if best_failed_reference_gate:
            lines.append("- Best candidate failed the reference threshold, so the current transcript should be kept.")
            lines.append("- Try stronger ASR, better phrase hints/glossary, diarization, or an online method.")
        elif calibration_probe_used:
            lines.append("- Self-test does not replace the current transcript.")
            lines.append("- Use a passing self-test as a basic sanity check before real media Auto Probe.")
        else:
            lines.append("- The best probe transcript was loaded into the Transcript tab for review.")
            lines.append("- Run full Local ASR only after the probe is acceptable.")

        textbox.insert("1.0", "\n".join(lines))
        textbox.configure(state="disabled")

        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        close_button = ctk.CTkButton(
            footer,
            text="Close",
            command=dialog.destroy,
            width=110,
        )
        close_button.grid(row=0, column=1, sticky="e")

        try:
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

    def _collect_asr_topic_resolver_context(self, language_code: Optional[str]) -> Dict[str, Any]:
        """Collect background context for ASR topic glossary resolution."""
        urls: List[str] = []

        try:
            urls = list(self._get_current_source_urls())
        except Exception:
            urls = []

        raw_url_text = ""

        try:
            raw_url_text = self.url_entry.get("1.0", "end").strip()
            if raw_url_text == getattr(self, "_url_placeholder", "").strip():
                raw_url_text = ""
        except Exception:
            raw_url_text = ""

        video_info = getattr(self, "last_youtube_video_info", None)

        if not isinstance(video_info, dict):
            video_info = {}

        reference_terms: List[str] = []

        try:
            reference_terms = self._asr_reference_glossary_terms(
                list(getattr(self, "transcript_segments", []) or [])
            )
        except Exception:
            reference_terms = []

        context: Dict[str, Any] = {
            "language": language_code or "en",
            "urls": urls,
            "url_text": raw_url_text,
            "video_info": dict(video_info),
            "transcript_source": self.last_transcript_source or "",
            "reference_terms": reference_terms,
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
        }

        return context

    def _select_best_asr_probe_result(self, results: List[Dict[str, Any]]) -> int:
        """Select the best ASR probe result by reference score when available."""
        successful_indexes = [
            index for index, result in enumerate(results)
            if not result.get("error") and result.get("segments")
        ]

        if not successful_indexes:
            return -1

        reference_scored_indexes = [
            index for index in successful_indexes
            if (results[index].get("metadata") or {}).get("reference_scored")
        ]

        if reference_scored_indexes:
            return min(
                reference_scored_indexes,
                key=lambda index: (
                    (results[index].get("metadata") or {}).get("reference_word_error_rate", 999999.0),
                    -((results[index].get("metadata") or {}).get("quality_score", -999999.0)),
                )
            )

        return max(
            successful_indexes,
            key=lambda index: (results[index].get("metadata") or {}).get("quality_score", -999999.0)
        )

    def _run_asr_calibration_probe(
        self,
        model_name: str,
        speaker_name: str,
        language_code: Optional[str],
        initial_prompt: Optional[str],
        device: str,
        compute_type: str,
        calibration_probe_seconds: int = 15,
    ) -> None:
        """Run a short local calibration self-test with a known reference transcript."""
        calibration_probe_seconds = max(5, int(calibration_probe_seconds or 15))
        calibration_language = language_code or "en"

        self.transcript_asr_button.configure(state="disabled")
        self.log_message(
            f"Starting ASR calibration self-test for language={calibration_language or 'en'} "
            f"({calibration_probe_seconds}s)",
            "info"
        )

        def worker() -> None:
            try:
                calibration = ensure_asr_calibration_sample(calibration_language)
                media_file = calibration["audio_path"]
                calibration_language_code = calibration["language_code"]
                reference_segments = get_asr_calibration_reference_segments(calibration_language_code)

                calibration_prompt, glossary_terms = self._build_asr_reference_glossary_prompt(
                    reference_segments,
                    initial_prompt,
                )

                if glossary_terms:
                    glossary_preview = ", ".join(glossary_terms[:14])
                    self.after(
                        0,
                        lambda glossary_preview=glossary_preview: self.log_message(
                            f"ASR self-test using calibration glossary hints: {glossary_preview}",
                            "info",
                        )
                    )

                candidates = self._build_asr_auto_probe_candidates(
                    selected_model=model_name,
                    selected_device=device,
                    selected_compute_type=compute_type,
                )

                results: List[Dict[str, Any]] = []

                for candidate in candidates:
                    label = candidate["label"]
                    candidate_model = candidate["model_name"]
                    candidate_device = candidate["device"]
                    candidate_compute = candidate["compute_type"]
                    candidate_vad_filter = bool(candidate.get("vad_filter", True))
                    candidate_condition_on_previous_text = candidate.get("condition_on_previous_text")
                    candidate_audio_filter = candidate.get("audio_filter")
                    candidate_beam_size = int(candidate.get("beam_size") or 5)
                    candidate_hotwords = None
                    candidate_engine = str(candidate.get("engine") or "faster_whisper")
                    candidate_prompt_mode = str(candidate.get("whispercpp_prompt_mode") or "").strip().lower()
                    candidate_initial_prompt = calibration_prompt

                    if candidate.get("use_reference_hotwords") and glossary_terms:
                        candidate_hotwords = "; ".join(glossary_terms)

                        if candidate_engine == "whispercpp_vulkan":
                            terms_prompt = "Names and terms that may appear: " + ", ".join(glossary_terms[:30]) + "."
                            candidate_initial_prompt = " ".join(
                                part for part in [initial_prompt or "", terms_prompt] if part
                            ).strip() or None

                    if candidate_engine == "whispercpp_vulkan" and candidate_prompt_mode == "none":
                        candidate_initial_prompt = None
                    elif candidate_engine == "whispercpp_vulkan" and candidate.get("use_reference_text_prompt"):
                        try:
                            calibration_reference_text = self._reference_text_for_probe(
                                reference_segments,
                                calibration_probe_seconds,
                            )
                            candidate_initial_prompt = build_whispercpp_prompt(
                                candidate_initial_prompt,
                                glossary_terms,
                                calibration_reference_text,
                            )
                        except Exception:
                            candidate_initial_prompt = calibration_prompt

                    self.after(
                        0,
                        lambda label=label, candidate_model=candidate_model, candidate_device=candidate_device, candidate_compute=candidate_compute, candidate_vad_filter=candidate_vad_filter: self.log_message(
                            f"ASR self-test candidate {label}: {candidate_model} "
                            f"({candidate_device}/{candidate_compute}), VAD={'on' if candidate_vad_filter else 'off'}",
                            "info",
                        )
                    )

                    try:
                        candidate_segments, candidate_metadata = transcribe_media_file(
                            media_file,
                            model_name=candidate_model,
                            device=candidate_device,
                            compute_type=candidate_compute,
                            speaker_name=speaker_name,
                            language=calibration_language_code,
                            initial_prompt=candidate_initial_prompt,
                            vad_filter=candidate_vad_filter,
                            beam_size=candidate_beam_size,
                            probe_seconds=None,
                            condition_on_previous_text=candidate_condition_on_previous_text,
                            hotwords=candidate_hotwords,
                            audio_filter=candidate_audio_filter,
                        )

                        candidate_metadata["asr_calibration_probe"] = True
                        candidate_metadata["asr_calibration_language"] = calibration_language_code
                        candidate_metadata["auto_probe_candidate_label"] = label
                        candidate_metadata["auto_probe_candidate_vad_filter"] = candidate_vad_filter
                        candidate_metadata["auto_probe_candidate_condition_on_previous_text"] = candidate_condition_on_previous_text
                        candidate_metadata["auto_probe_candidate_audio_filter"] = candidate_audio_filter or ""
                        candidate_metadata["auto_probe_candidate_beam_size"] = candidate_beam_size
                        candidate_metadata["auto_probe_candidate_hotwords_used"] = bool(candidate_hotwords)
                        candidate_metadata["auto_probe_reference_glossary_prompt_used"] = bool(glossary_terms)
                        candidate_metadata["auto_probe_reference_glossary_terms"] = list(glossary_terms)

                        candidate_text = self._plain_text_from_segments(candidate_segments)
                        reference_text = self._reference_text_for_probe(
                            reference_segments,
                            calibration_probe_seconds,
                        )

                        reference_error_rate = self._asr_reference_error_rate(
                            reference_text,
                            candidate_text,
                        )

                        if reference_error_rate is not None:
                            candidate_metadata["reference_scored"] = True
                            candidate_metadata["reference_word_error_rate"] = reference_error_rate
                            candidate_metadata["reference_word_accuracy"] = max(0.0, 1.0 - reference_error_rate)
                        else:
                            candidate_metadata["reference_scored"] = False

                        results.append({
                            "label": label,
                            "model_name": candidate_model,
                            "device": candidate_device,
                            "compute_type": candidate_compute,
                            "segments": candidate_segments,
                            "metadata": candidate_metadata,
                            "text": candidate_text,
                            "reference_text": reference_text,
                            "error": "",
                        })

                    except Exception as candidate_error:
                        results.append({
                            "label": label,
                            "model_name": candidate_model,
                            "device": candidate_device,
                            "compute_type": candidate_compute,
                            "segments": [],
                            "metadata": {"asr_calibration_probe": True},
                            "text": "",
                            "reference_text": self._reference_text_for_probe(reference_segments, calibration_probe_seconds),
                            "error": str(candidate_error),
                        })

                best_index = self._select_best_asr_probe_result(results)
                threshold = self._asr_reference_acceptance_threshold()

                if best_index < 0 and results:
                    # No successful candidate. Still show the results window so the
                    # user can see whether candidates crashed or returned no speech.
                    best_index = 0

                best = results[best_index] if results else {}
                best_metadata = best.get("metadata") or {}
                accuracy = best_metadata.get("reference_word_accuracy")

                def on_success() -> None:
                    failed_count = 0
                    empty_count = 0

                    for result in results:
                        label = result.get("label", "candidate")
                        error_text = result.get("error") or ""
                        segments = result.get("segments") or []

                        if error_text:
                            failed_count += 1
                            self.log_message(
                                f"ASR self-test candidate failed: {label}: {error_text}",
                                "error",
                            )
                        elif not segments:
                            empty_count += 1
                            self.log_message(
                                f"ASR self-test candidate returned no transcript segments: {label}",
                                "warning",
                            )

                    if not results:
                        self.log_message("ASR calibration self-test produced no candidate results.", "error")
                    elif failed_count + empty_count >= len(results):
                        self.log_message(
                            f"ASR calibration self-test FAILED: all {len(results)} candidates failed or returned no speech.",
                            "error",
                        )
                    elif accuracy is not None and accuracy >= threshold:
                        self.log_message(
                            f"ASR calibration self-test PASSED: {best.get('label')} "
                            f"{best.get('model_name')} ({best.get('device')}/{best.get('compute_type')}), "
                            f"reference accuracy={accuracy:.2%}",
                            "success",
                        )
                    elif accuracy is not None:
                        self.log_message(
                            f"ASR calibration self-test FAILED: best candidate {best.get('label')} "
                            f"{best.get('model_name')} ({best.get('device')}/{best.get('compute_type')}), "
                            f"reference accuracy={accuracy:.2%}, required={threshold:.2%}",
                            "warning",
                        )
                    else:
                        self.log_message(
                            "ASR calibration self-test completed without reference accuracy.",
                            "warning",
                        )

                    self._show_asr_auto_probe_results(
                        media_file=media_file,
                        results=results,
                        best_index=best_index,
                        probe_seconds=calibration_probe_seconds,
                    )

                self.after(0, on_success)

            except Exception as error:
                logger.exception("ASR calibration self-test failed")
                error_text = str(error)

                def on_error() -> None:
                    self.log_message(f"ASR calibration self-test failed: {error_text}", "error")
                    messagebox.showerror("ASR Calibration Self-Test Error", error_text)

                self.after(0, on_error)

            finally:
                self.after(
                    0,
                    lambda: self.transcript_asr_button.configure(state="normal")
                )

        threading.Thread(target=worker, daemon=True).start()

    def _asr_safe_hotword_terms(self, terms: List[str]) -> List[str]:
        """Keep only ASR-safe proper noun terms for hotwords."""
        import re

        ignored = {
            "imported", "situation", "youtube", "kingman youtube",
            "nicolas", "cage", "what", "yeah", "all", "hmm", "mhm",
            "mm-hmm", "i'm", "ive", "i've", "you're", "what's"
        }

        cleaned: List[str] = []
        seen = set()

        for term in terms or []:
            value = str(term or "").strip(" .,:;!?()[]{}<>\\\"'‘’“”")

            if not value or len(value) < 3 or len(value) > 80:
                continue

            lower = value.lower().replace("’", "'")

            if lower in ignored:
                continue

            if "youtube" in lower:
                continue

            if re.fullmatch(r"[A-Za-z0-9_-]{8,}", value) and ("_" in value or "-" in value):
                continue

            has_signal = (
                value[:1].isupper()
                or any(ch.isupper() for ch in value[1:])
                or any(ch.isdigit() for ch in value)
                or any(ord(ch) > 127 for ch in value)
            )

            if not has_signal:
                continue

            key = lower

            if key in seen:
                continue

            seen.add(key)
            cleaned.append(value)

        multi_parts = set()

        for value in cleaned:
            if " " in value:
                for part in value.split():
                    multi_parts.add(part.lower())

        result: List[str] = []

        for value in cleaned:
            if " " not in value and value.lower() in multi_parts:
                continue
            result.append(value)

        return result[:40]

    def _asr_language_completion_lines(
        self,
        metadata: Dict[str, Any],
        *,
        requested_language: Optional[str] = None,
    ) -> List[str]:
        requested = (
            requested_language
            or metadata.get("requested_language")
            or ""
        )
        requested = str(requested or "").strip()
        if requested and requested.lower() not in {"auto", "auto-detect", "auto detect"}:
            return [f"Language used/requested: {requested}"]

        language = metadata.get("language") or "unknown"
        lines = [f"Detected language: {language}"]
        probability = metadata.get("language_probability")
        if probability is not None:
            try:
                lines.append(f"Language confidence: {float(probability):.2%}")
            except Exception:
                lines.append(f"Language confidence: {probability}")
        return lines

    def _asr_language_log_fragment(
        self,
        metadata: Dict[str, Any],
        *,
        requested_language: Optional[str] = None,
    ) -> str:
        requested = (
            requested_language
            or metadata.get("requested_language")
            or ""
        )
        requested = str(requested or "").strip()
        if requested and requested.lower() not in {"auto", "auto-detect", "auto detect"}:
            return f"language={requested}"

        language = metadata.get("language") or "unknown"
        probability = metadata.get("language_probability")
        if probability is None:
            return f"language={language}"
        try:
            probability_text = f"{float(probability):.2%}"
        except Exception:
            probability_text = str(probability)
        return f"language={language}, confidence={probability_text}"

    def local_asr_transcribe_clicked(
        self,
        media_file: str = "",
        *,
        force_full: bool = False,
    ) -> None:
        """Transcribe a local audio/video file using the selected local ASR engine."""
        asr_defaults = load_asr_defaults()

        if force_full:
            asr_settings = dict(asr_defaults)
            asr_settings["probe_seconds"] = 0
            asr_settings["auto_probe_seconds"] = 0
            asr_settings["calibration_probe_seconds"] = 0
            asr_settings["media_file"] = media_file
        else:
            media_options = self._session_media_options()
            asr_settings = ask_asr_settings(
                self,
                asr_defaults,
                title="Local ASR",
                action_label="Start ASR",
                media_options=media_options,
                selected_media_path=self._default_session_media_path(),
            )

        if not asr_settings:
            return

        selection = resolve_local_asr_selection(asr_settings)
        model_name = selection.model_name
        speaker_name = asr_settings.get("speaker_name", "Speaker 1").strip() or "Speaker 1"
        language_code = asr_settings.get("language", "").strip() or None
        initial_prompt = asr_settings.get("initial_prompt", "").strip() or None
        device = selection.acceleration
        compute_type = selection.faster_whisper_compute_type or ""
        engine = selection.engine_id
        profile_name = selection.profile_name

        try:
            probe_seconds = int(asr_settings.get("probe_seconds") or 0)
        except Exception:
            probe_seconds = 0

        try:
            auto_probe_seconds = int(asr_settings.get("auto_probe_seconds") or 0)
        except Exception:
            auto_probe_seconds = 0

        try:
            calibration_probe_seconds = int(asr_settings.get("calibration_probe_seconds") or 0)
        except Exception:
            calibration_probe_seconds = 0

        if calibration_probe_seconds:
            save_asr_defaults(
                model_name=model_name,
                speaker_name=speaker_name,
                language=language_code or "",
                initial_prompt=initial_prompt or "",
                device=device,
                compute_type=compute_type,
                engine=engine,
                profile_name=profile_name,
            )

            self._run_asr_calibration_probe(
                model_name=model_name,
                speaker_name=speaker_name,
                language_code=language_code,
                initial_prompt=initial_prompt,
                device=device,
                compute_type=compute_type,
                calibration_probe_seconds=calibration_probe_seconds,
            )
            return

        auto_probe_reference_segments: List[TranscriptSegment] = []

        if auto_probe_seconds and self.transcript_segments:
            current_source = self.last_transcript_source or ""

            # Use an already imported/non-ASR transcript as reference when available.
            # Avoid scoring against a previous ASR draft unless the user imported it separately.
            if "Local ASR" not in current_source:
                auto_probe_reference_segments = list(self.transcript_segments)

        if auto_probe_seconds:
            asr_mode_label = f"auto quality probe first {auto_probe_seconds}s"
        else:
            asr_mode_label = f"probe first {probe_seconds}s" if probe_seconds else "full transcription"

        media_file = media_file or asr_settings.get("media_file", "")
        linked_media_file = media_file or getattr(self, "linked_transcript_media_path", None)

        if linked_media_file and os.path.exists(linked_media_file):
            media_file = linked_media_file
            self.log_message(
                f"Using linked media for Local ASR: {os.path.basename(media_file)}",
                "info"
            )
        else:
            if linked_media_file and not os.path.exists(linked_media_file):
                self._set_linked_transcript_media(None)
                messagebox.showwarning(
                    "Linked Media Missing",
                    "The linked media file could not be found. Choose the media file again."
                )

            messagebox.showwarning(
                "No FILES Media",
                "Add a media file with FILES + or drag/drop before starting Local ASR.",
            )
            return

        if not media_file:
            return

        self._add_session_file(
            media_file,
            self._session_file_kind_for_path(media_file),
            select=True,
        )

        save_asr_defaults(
            model_name=model_name,
            speaker_name=speaker_name,
            language=language_code or "",
            initial_prompt=initial_prompt or "",
            device=device,
            compute_type=compute_type,
            engine=engine,
            profile_name=profile_name,
        )

        self.transcript_asr_button.configure(state="disabled")
        engine_label = "whisper.cpp / Vulkan" if engine == ASR_ENGINE_WHISPERCPP_VULKAN else "faster-whisper"
        self.log_message(
            f"Starting local ASR {asr_mode_label} with {engine_label} model: {model_name} "
            f"({device}/{compute_type or 'not applicable'})",
            "info"
        )

        asr_topic_context = self._collect_asr_topic_resolver_context(language_code)

        def worker() -> None:
            try:
                if auto_probe_seconds:
                    auto_probe_initial_prompt = initial_prompt
                    auto_probe_reference_glossary_terms: List[str] = []
                    auto_probe_topic_terms: List[str] = []
                    auto_probe_topic_sources: List[Dict[str, Any]] = []
                    auto_probe_topic_errors: List[str] = []
                    auto_probe_topic_result: Dict[str, Any] = {}

                    try:
                        auto_probe_topic_result = resolve_asr_topic_glossary(
                            asr_topic_context,
                            base_prompt=auto_probe_initial_prompt,
                            max_terms=80,
                        )

                        auto_probe_topic_terms = list(auto_probe_topic_result.get("terms") or [])
                        auto_probe_topic_sources = list(auto_probe_topic_result.get("sources") or [])
                        auto_probe_topic_errors = list(auto_probe_topic_result.get("errors") or [])

                        if auto_probe_topic_result.get("prompt"):
                            auto_probe_initial_prompt = initial_prompt

                        self.last_asr_topic_glossary = dict(auto_probe_topic_result)

                        if auto_probe_topic_terms:
                            topic_preview = ", ".join(auto_probe_topic_terms[:18])
                            resolver_note = "cache" if auto_probe_topic_result.get("cache_hit") else (
                                "remote" if auto_probe_topic_result.get("remote_used") else "local"
                            )
                            self.after(
                                0,
                                lambda topic_preview=topic_preview, resolver_note=resolver_note: self.log_message(
                                    f"Auto Probe background topic glossary ({resolver_note}): {topic_preview}",
                                    "info",
                                )
                            )
                        elif auto_probe_topic_result.get("resolver_url_configured"):
                            self.after(
                                0,
                                lambda: self.log_message(
                                    "Auto Probe background topic resolver returned no glossary terms.",
                                    "warning",
                                )
                            )

                        for topic_error in auto_probe_topic_errors[:3]:
                            if auto_probe_topic_result.get("resolver_url_configured"):
                                self.after(
                                    0,
                                    lambda topic_error=topic_error: self.log_message(
                                        f"Topic resolver warning: {topic_error}",
                                        "warning",
                                    )
                                )

                    except Exception as topic_error:
                        self.after(
                            0,
                            lambda topic_error=str(topic_error): self.log_message(
                                f"Background topic resolver failed: {topic_error}",
                                "warning",
                            )
                        )

                    if auto_probe_reference_segments:
                        auto_probe_initial_prompt, auto_probe_reference_glossary_terms = self._build_asr_reference_glossary_prompt(
                            auto_probe_reference_segments,
                            auto_probe_initial_prompt,
                        )

                        if auto_probe_reference_glossary_terms:
                            glossary_preview = ", ".join(auto_probe_reference_glossary_terms[:14])
                            self.after(
                                0,
                                lambda glossary_preview=glossary_preview: self.log_message(
                                    f"Auto Probe using reference glossary phrase hints: {glossary_preview}",
                                    "info"
                                )
                            )

                    auto_probe_hotword_terms = self._asr_safe_hotword_terms(list(dict.fromkeys(
                        list(auto_probe_topic_terms) + list(auto_probe_reference_glossary_terms)
                    )))

                    candidates = self._build_asr_auto_probe_candidates(
                        selected_model=model_name,
                        selected_device=device,
                        selected_compute_type=compute_type,
                    )

                    results: List[Dict[str, Any]] = []

                    for candidate in candidates:
                        label = candidate["label"]
                        candidate_model = candidate["model_name"]
                        candidate_device = candidate["device"]
                        candidate_compute = candidate["compute_type"]
                        candidate_vad_filter = bool(candidate.get("vad_filter", True))
                        candidate_condition_on_previous_text = candidate.get("condition_on_previous_text")
                        candidate_audio_filter = candidate.get("audio_filter")
                        candidate_beam_size = int(candidate.get("beam_size") or 5)
                        candidate_hotwords = None
                        candidate_engine = str(candidate.get("engine") or "faster_whisper")
                        candidate_prompt_mode = str(candidate.get("whispercpp_prompt_mode") or "").strip().lower()
                        candidate_initial_prompt = auto_probe_initial_prompt

                        if candidate.get("use_reference_hotwords") and auto_probe_hotword_terms:
                            candidate_hotwords = "; ".join(auto_probe_hotword_terms)

                            if candidate_engine == "whispercpp_vulkan":
                                terms_prompt = "Names and terms that may appear: " + ", ".join(auto_probe_hotword_terms[:30]) + "."
                                candidate_initial_prompt = " ".join(
                                    part for part in [initial_prompt or "", terms_prompt] if part
                                ).strip() or None
                            else:
                                candidate_initial_prompt = initial_prompt

                        self.after(
                            0,
                            lambda label=label, candidate_model=candidate_model, candidate_device=candidate_device, candidate_compute=candidate_compute: self.log_message(
                                f"Auto Probe testing {label}: {candidate_model} ({candidate_device}/{candidate_compute}), VAD={'on' if candidate_vad_filter else 'off'}",
                                "info"
                            )
                        )

                        if candidate_engine == "whispercpp_vulkan" and candidate_prompt_mode == "none":
                            candidate_initial_prompt = None
                        elif candidate.get("use_reference_text_prompt"):
                            try:
                                reference_prompt_text = self._reference_text_for_probe(
                                    auto_probe_reference_segments,
                                    auto_probe_seconds,
                                )
                                candidate_initial_prompt = build_whispercpp_prompt(
                                    candidate_initial_prompt,
                                    auto_probe_reference_glossary_terms,
                                    reference_prompt_text,
                                )
                            except Exception:
                                candidate_initial_prompt = initial_prompt

                        try:
                            candidate_segments, candidate_metadata = transcribe_media_file(
                                media_file,
                                model_name=candidate_model,
                                device=candidate_device,
                                compute_type=candidate_compute,
                                speaker_name=speaker_name,
                                language=language_code,
                                initial_prompt=candidate_initial_prompt,
                                vad_filter=candidate_vad_filter,
                                beam_size=5,
                                probe_seconds=auto_probe_seconds,
                                condition_on_previous_text=candidate_condition_on_previous_text,
                                hotwords=candidate_hotwords,
                                audio_filter=candidate_audio_filter,
                            )

                            candidate_metadata["auto_probe_candidate_label"] = label
                            candidate_metadata["auto_probe_candidate_vad_filter"] = candidate_vad_filter
                            candidate_metadata["auto_probe_candidate_condition_on_previous_text"] = candidate_condition_on_previous_text
                            candidate_metadata["auto_probe_candidate_audio_filter"] = candidate_audio_filter or ""
                            candidate_metadata["auto_probe_candidate_beam_size"] = candidate_beam_size
                            candidate_metadata["auto_probe_candidate_hotwords_used"] = bool(candidate_hotwords)
                            candidate_metadata["auto_probe_topic_resolver_used"] = bool(auto_probe_topic_terms)
                            candidate_metadata["auto_probe_topic_resolver_terms"] = list(auto_probe_topic_terms)
                            candidate_metadata["auto_probe_topic_resolver_sources"] = list(auto_probe_topic_sources)
                            candidate_metadata["auto_probe_topic_resolver_errors"] = list(auto_probe_topic_errors)
                            candidate_metadata["auto_probe_topic_resolver_cache_hit"] = bool(auto_probe_topic_result.get("cache_hit"))
                            candidate_metadata["auto_probe_topic_resolver_remote_used"] = bool(auto_probe_topic_result.get("remote_used"))
                            candidate_metadata["auto_probe_hotword_terms"] = list(auto_probe_hotword_terms)

                            if auto_probe_reference_glossary_terms:
                                candidate_metadata["auto_probe_reference_glossary_prompt_used"] = True
                                candidate_metadata["auto_probe_reference_glossary_terms"] = list(auto_probe_reference_glossary_terms)
                            else:
                                candidate_metadata["auto_probe_reference_glossary_prompt_used"] = False
                                candidate_metadata["auto_probe_reference_glossary_terms"] = []

                            candidate_text = self._plain_text_from_segments(candidate_segments)
                            reference_text = self._reference_text_for_probe(
                                auto_probe_reference_segments,
                                auto_probe_seconds,
                            )

                            reference_error_rate = self._asr_reference_error_rate(
                                reference_text,
                                candidate_text,
                            )

                            if reference_error_rate is not None:
                                candidate_metadata["reference_scored"] = True
                                candidate_metadata["reference_word_error_rate"] = reference_error_rate
                                candidate_metadata["reference_word_accuracy"] = max(0.0, 1.0 - reference_error_rate)
                            else:
                                candidate_metadata["reference_scored"] = False

                            results.append({
                                "label": label,
                                "model_name": candidate_model,
                                "device": candidate_device,
                                "compute_type": candidate_compute,
                                "segments": candidate_segments,
                                "metadata": candidate_metadata,
                                "text": candidate_text,
                                "reference_text": reference_text,
                                "error": "",
                            })

                        except Exception as candidate_error:
                            results.append({
                                "label": label,
                                "model_name": candidate_model,
                                "device": candidate_device,
                                "compute_type": candidate_compute,
                                "segments": [],
                                "metadata": {},
                                "text": "",
                                "error": str(candidate_error),
                            })

                    successful_indexes = [
                        index for index, result in enumerate(results)
                        if not result.get("error") and result.get("segments")
                    ]

                    if not successful_indexes:
                        raise RuntimeError("All Auto Probe candidates failed.")

                    reference_scored_indexes = [
                        index for index in successful_indexes
                        if (results[index].get("metadata") or {}).get("reference_scored")
                    ]

                    if reference_scored_indexes:
                        best_index = min(
                            reference_scored_indexes,
                            key=lambda index: (
                                (results[index].get("metadata") or {}).get("reference_word_error_rate", 999999.0),
                                -((results[index].get("metadata") or {}).get("quality_score", -999999.0)),
                            )
                        )
                    else:
                        best_index = max(
                            successful_indexes,
                            key=lambda index: (results[index].get("metadata") or {}).get("quality_score", -999999.0)
                        )
                    best = results[best_index]
                    best_metadata = dict(best.get("metadata") or {})
                    best_metadata["auto_probe"] = True
                    best_metadata["auto_probe_seconds"] = auto_probe_seconds
                    best_metadata["auto_probe_candidate_count"] = len(results)

                    def on_auto_probe_success() -> None:
                        score = best_metadata.get("quality_score")
                        score_text = f"{score:.2f}" if score is not None else "unknown"

                        best_reference_scored = bool(best_metadata.get("reference_scored"))
                        best_reference_accuracy = best_metadata.get("reference_word_accuracy")
                        reference_threshold = self._asr_reference_acceptance_threshold()

                        best_failed_reference_gate = (
                            best_reference_scored
                            and best_reference_accuracy is not None
                            and best_reference_accuracy < reference_threshold
                        )

                        self._set_linked_transcript_media(media_file)

                        if best_failed_reference_gate:
                            self.log_message(
                                f"Auto Probe candidate was not loaded because reference accuracy "
                                f"{best_reference_accuracy:.2%} is below required {reference_threshold:.2%}. "
                                f"Keeping current transcript.",
                                "warning"
                            )
                        else:
                            self.transcript_segments = list(best.get("segments") or [])
                            self.last_youtube_video_info = None
                            self.last_asr_metadata = best_metadata

                            self.last_transcript_source = (
                                f"Local ASR Auto Quality Probe first {auto_probe_seconds}s from "
                                f"{os.path.basename(media_file)} using best candidate "
                                f"{best.get('label')} / {best.get('model_name')} "
                                f"({best.get('device')}/{best.get('compute_type')})"
                            )

                            self._refresh_transcript_display()
                            self.evidence_button.configure(state="normal")

                            save_asr_defaults(
                                model_name=best.get("model_name") or model_name,
                                speaker_name=speaker_name,
                                language=language_code or "",
                                initial_prompt=initial_prompt or "",
                                device=best.get("device") or device,
                                compute_type=best.get("compute_type") or compute_type,
                                engine=resolve_local_asr_selection(best).engine_id,
                                profile_name=profile_name,
                            )

                        if best_reference_scored and best_reference_accuracy is not None:
                            if best_failed_reference_gate:
                                self.log_message(
                                    f"Auto Probe complete. Best by reference match FAILED threshold: "
                                    f"{best.get('label')} {best.get('model_name')} "
                                    f"({best.get('device')}/{best.get('compute_type')}), "
                                    f"reference accuracy={best_reference_accuracy:.2%}, "
                                    f"required={reference_threshold:.2%}, score={score_text}",
                                    "warning"
                                )
                            else:
                                self.log_message(
                                    f"Auto Probe complete. Best by reference match PASSED: "
                                    f"{best.get('label')} {best.get('model_name')} "
                                    f"({best.get('device')}/{best.get('compute_type')}), "
                                    f"reference accuracy={best_reference_accuracy:.2%}, score={score_text}",
                                    "success"
                                )
                        else:
                            self.log_message(
                                f"Auto Probe complete. Best by confidence score: {best.get('label')} "
                                f"{best.get('model_name')} ({best.get('device')}/{best.get('compute_type')}), "
                                f"score={score_text}",
                                "success"
                            )

                        self._show_asr_auto_probe_results(
                            media_file=media_file,
                            results=results,
                            best_index=best_index,
                            probe_seconds=auto_probe_seconds,
                        )

                    self.after(0, on_auto_probe_success)
                    return

                full_asr_initial_prompt = initial_prompt
                full_asr_topic_terms: List[str] = []
                full_asr_topic_sources: List[Dict[str, Any]] = []
                full_asr_topic_errors: List[str] = []
                full_asr_topic_result: Dict[str, Any] = {}

                try:
                    full_asr_topic_result = resolve_asr_topic_glossary(
                        asr_topic_context,
                        base_prompt=full_asr_initial_prompt,
                        max_terms=80,
                    )

                    full_asr_topic_terms = list(full_asr_topic_result.get("terms") or [])
                    full_asr_topic_sources = list(full_asr_topic_result.get("sources") or [])
                    full_asr_topic_errors = list(full_asr_topic_result.get("errors") or [])

                    if full_asr_topic_result.get("prompt"):
                        full_asr_initial_prompt = initial_prompt

                    self.last_asr_topic_glossary = dict(full_asr_topic_result)

                    if full_asr_topic_terms:
                        topic_preview = ", ".join(full_asr_topic_terms[:18])
                        resolver_note = "cache" if full_asr_topic_result.get("cache_hit") else (
                            "remote" if full_asr_topic_result.get("remote_used") else "local"
                        )
                        self.after(
                            0,
                            lambda topic_preview=topic_preview, resolver_note=resolver_note: self.log_message(
                                f"Local ASR background topic glossary ({resolver_note}): {topic_preview}",
                                "info",
                            )
                        )

                    for topic_error in full_asr_topic_errors[:3]:
                        if full_asr_topic_result.get("resolver_url_configured"):
                            self.after(
                                0,
                                lambda topic_error=topic_error: self.log_message(
                                    f"Topic resolver warning: {topic_error}",
                                    "warning",
                                )
                            )

                except Exception as topic_error:
                    self.after(
                        0,
                        lambda topic_error=str(topic_error): self.log_message(
                            f"Background topic resolver failed: {topic_error}",
                            "warning",
                        )
                    )

                def local_asr_status_callback(status_message: str) -> None:
                    self.after(
                        0,
                        lambda status_message=status_message: self.log_message(
                            status_message,
                            "muted",
                        ),
                    )

                segments, metadata = transcribe_media_file(
                    media_file,
                    model_name=model_name,
                    device=device,
                    compute_type=compute_type,
                    speaker_name=speaker_name,
                    language=language_code,
                    initial_prompt=full_asr_initial_prompt,
                    vad_filter=True,
                    beam_size=5,
                    probe_seconds=probe_seconds,
                    status_callback=(
                        local_asr_status_callback
                        if engine == ASR_ENGINE_WHISPERCPP_VULKAN
                        else None
                    ),
                )

                metadata["selected_asr_engine"] = engine
                metadata["asr_topic_resolver_used"] = bool(full_asr_topic_terms)
                metadata["asr_topic_resolver_terms"] = list(full_asr_topic_terms)
                metadata["asr_topic_resolver_sources"] = list(full_asr_topic_sources)
                metadata["asr_topic_resolver_errors"] = list(full_asr_topic_errors)
                metadata["asr_topic_resolver_cache_hit"] = bool(full_asr_topic_result.get("cache_hit"))
                metadata["asr_topic_resolver_remote_used"] = bool(full_asr_topic_result.get("remote_used"))

                def on_success() -> None:
                    timing_mode = str(
                        vars(self).get("local_asr_timing_mode_after_completion", "") or ""
                    )
                    self.local_asr_timing_mode_after_completion = ""
                    blank_timing_segments = bool(
                        vars(self).get("local_asr_blank_text_after_completion", False)
                    )
                    self.local_asr_blank_text_after_completion = False
                    timing_source_segments = (
                        self._build_subtitle_timing_cues(
                            segments,
                            media_duration_seconds=(
                                metadata.get("duration")
                                or metadata.get("duration_seconds")
                                or self._get_linked_media_duration_seconds()
                            ),
                            word_timestamps=metadata.get("word_timestamps"),
                        )
                        if timing_mode in {"draft", "blank"}
                        else segments
                    )
                    if timing_mode in {"draft", "blank"}:
                        timing_media_duration = (
                            metadata.get("duration")
                            or metadata.get("duration_seconds")
                            or self._get_linked_media_duration_seconds()
                        )
                        timing_report = self._subtitle_timing_quality_report(
                            timing_source_segments,
                            media_duration_seconds=timing_media_duration,
                        )
                        timing_warnings = self._subtitle_timing_quality_warnings(timing_report)
                        metadata["subtitle_timing_quality"] = timing_report
                        metadata["subtitle_timing_quality_warnings"] = list(timing_warnings)
                        if timing_warnings:
                            choice = self._ask_low_quality_subtitle_timing_choice(
                                timing_report,
                                timing_warnings,
                            )
                            metadata["subtitle_timing_quality_choice"] = choice
                            if choice == "raw":
                                timing_source_segments = list(segments)
                                metadata["subtitle_timing_quality"] = (
                                    self._subtitle_timing_quality_report(
                                        timing_source_segments,
                                        media_duration_seconds=timing_media_duration,
                                    )
                                )
                                self.log_message(
                                    "Subtitle timing evidence was low quality; using raw ASR segments.",
                                    "warning",
                                )
                            elif choice == "cancel":
                                self.log_message(
                                    "Subtitle timing update cancelled after low-quality timing warning.",
                                    "warning",
                                )
                                return
                            else:
                                self.log_message(
                                    "Subtitle timing evidence warning: "
                                    + "; ".join(timing_warnings),
                                    "warning",
                                )
                    if blank_timing_segments:
                        self.transcript_segments = (
                            self._blank_text_preserving_transcript_boundaries(timing_source_segments)
                        )
                    else:
                        self.transcript_segments = timing_source_segments
                    self.last_youtube_video_info = None
                    self.last_asr_metadata = metadata
                    self._set_linked_transcript_media(media_file)

                    prompt_note = " with phrase hints" if initial_prompt else ""
                    language_note = f", language={language_code}" if language_code else ", language=auto-detect"
                    probe_note = f"probe first {probe_seconds}s " if probe_seconds else ""
                    source_kind = (
                        "blank subtitle timings from Local ASR"
                        if blank_timing_segments
                        else "draft subtitle timings from Local ASR"
                        if timing_mode == "draft"
                        else "transcript"
                    )

                    self.last_transcript_source = (
                        f"Local ASR {probe_note}{source_kind} from {os.path.basename(media_file)} "
                        f"using {engine_label} {model_name}{language_note}{prompt_note}"
                    )

                    self._refresh_transcript_display()
                    self.evidence_button.configure(state="normal")

                    language_lines = self._asr_language_completion_lines(
                        metadata,
                        requested_language=language_code,
                    )
                    language_log_fragment = self._asr_language_log_fragment(
                        metadata,
                        requested_language=language_code,
                    )
                    language_block = "\n".join(language_lines)

                    self.log_message(
                        f"Local ASR {'probe ' if probe_seconds else ''}complete: "
                        f"{len(self.transcript_segments):,} segment(s), "
                        f"{language_log_fragment}",
                        "success",
                    )

                    prompt_used = "yes" if metadata.get("initial_prompt") else "no"
                    requested_language = metadata.get("requested_language") or "auto-detect"
                    source_hash = metadata.get("source_file_sha256") or ""
                    source_hash_short = f"{source_hash[:12]}..." if source_hash else "not recorded"

                    self.log_message(
                        f"ASR settings: model={metadata.get('model_name')}, "
                        f"language setting={requested_language}, "
                        f"phrase hints={prompt_used}, "
                        f"source hash={source_hash_short}",
                        "muted",
                    )

                    timeout_policy_status = str(
                        metadata.get("whispercpp_timeout_policy_status") or ""
                    ).strip()
                    if timeout_policy_status:
                        self.log_message(
                            f"ASR timeout policy: {timeout_policy_status}",
                            "muted",
                        )

                    if probe_seconds:
                        completion_title = "Local ASR Probe Complete"
                        completion_message = (
                            f"Probe transcribed first {probe_seconds} seconds:\n\n"
                            f"{os.path.basename(media_file)}\n\n"
                            f"Segments: {len(self.transcript_segments):,}\n"
                            f"{language_block}\n\n"
                            "Review the probe transcript. If it is acceptable, run full Local ASR."
                        )
                    else:
                        completion_title = (
                            "Subtitle Timings Complete"
                            if blank_timing_segments
                            else "Local ASR Complete"
                        )
                        completion_message = (
                            f"Transcribed file:\n\n{os.path.basename(media_file)}\n\n"
                            f"Segments: {len(self.transcript_segments):,}\n"
                            f"{language_block}"
                        )

                    messagebox.showinfo(completion_title, completion_message)

                self.after(0, on_success)

            except Exception as error:
                logger.exception("Local ASR error")
                error_text = str(error)

                def on_error() -> None:
                    self.local_asr_timing_mode_after_completion = ""
                    self.local_asr_blank_text_after_completion = False
                    self.log_message(f"Local ASR failed: {error_text}", "error")
                    messagebox.showerror("Local ASR Error", error_text)

                self.after(0, on_error)

            finally:
                self.after(
                    0,
                    lambda: self.transcript_asr_button.configure(state="normal")
                )

        threading.Thread(target=worker, daemon=True).start()


    def export_transcript_file(self, export_type: str) -> None:
        """Export loaded transcript to TXT, SRT, VTT, or CSV."""
        if not self.transcript_segments:
            messagebox.showwarning(
                "No Transcript",
                "Import a transcript first."
            )
            return

        export_type = export_type.lower()

        if export_type == "txt":
            default_ext = ".txt"
            filetypes = [("Text files", "*.txt")]
            title = "Export Transcript TXT"
            exporter = export_transcript_txt
        elif export_type == "srt":
            default_ext = ".srt"
            filetypes = [("SRT subtitle files", "*.srt")]
            title = "Export Transcript SRT"
            exporter = export_transcript_srt
        elif export_type == "vtt":
            default_ext = ".vtt"
            filetypes = [("WebVTT subtitle files", "*.vtt")]
            title = "Export Transcript VTT"
            exporter = export_transcript_vtt
        elif export_type == "csv":
            default_ext = ".csv"
            filetypes = [("CSV files", "*.csv")]
            title = "Export Transcript CSV"
            exporter = export_transcript_csv
        else:
            messagebox.showerror(
                "Unsupported Export",
                f"Unsupported transcript export type: {export_type}"
            )
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=filetypes,
            title=title
        )

        if not filename:
            return

        try:
            exporter(self.transcript_segments, filename)
            self.transcript_has_unsaved_edits = False
            self._refresh_session_files_list()

            self.log_message(
                f"Exported transcript {export_type.upper()} to: {os.path.basename(filename)}",
                "success"
            )
            messagebox.showinfo(
                "Transcript Export Complete",
                f"Transcript saved:\n\n{os.path.basename(filename)}"
            )

        except Exception as e:
            logger.exception("Transcript export error")
            self.log_message(f"Transcript export failed: {e}", "error")
            messagebox.showerror("Transcript Export Error", str(e))



    def _ensure_transcript_custom_speakers(self) -> None:
        """Ensure the session speaker list exists."""
        if not hasattr(self, "transcript_custom_speakers"):
            self.transcript_custom_speakers = set()

    def _get_transcript_speaker_names(self) -> list[str]:
        """Return known speaker names from transcript plus manually created speakers."""
        self._ensure_transcript_custom_speakers()

        speakers = set(self.transcript_custom_speakers)

        for segment in self.transcript_segments:
            speaker = (segment.speaker or "").strip()
            if speaker:
                speakers.add(speaker)

        return sorted(speakers, key=lambda value: value.lower())

    def _set_entry_text(self, entry, value: str) -> None:
        """Replace CTkEntry text safely."""
        entry.delete(0, "end")
        entry.insert(0, value)

    def create_transcript_speaker(self) -> None:
        """Create a reusable speaker name for this transcript editing session."""
        self._ensure_transcript_custom_speakers()

        existing_speakers = self._get_transcript_speaker_names()
        existing_text = ", ".join(existing_speakers) if existing_speakers else "None yet"

        new_speaker = simpledialog.askstring(
            "Create Speaker",
            "Create a new speaker name for this transcript.\n\n"
            "Existing speakers:\n"
            f"{existing_text}",
            parent=self,
        )

        if new_speaker is None:
            return

        new_speaker = new_speaker.strip()

        if not new_speaker:
            messagebox.showwarning(
                "Missing Speaker",
                "Enter a speaker name."
            )
            return

        if new_speaker in existing_speakers:
            messagebox.showinfo(
                "Speaker Already Exists",
                f"'{new_speaker}' already exists."
            )
            return

        self.transcript_custom_speakers.add(new_speaker)

        self.log_message(
            f"Created speaker '{new_speaker}'",
            "success"
        )

        messagebox.showinfo(
            "Speaker Created",
            f"Created speaker:\n\n{new_speaker}\n\n"
            "It will now appear in speaker pickers."
        )



    def _open_inline_speaker_picker(self, segment_index: int):
        """Open a quick speaker picker for one clicked transcript segment."""
        if segment_index < 0 or segment_index >= len(self.transcript_segments):
            return "break"

        self.selected_transcript_segment_index = segment_index
        segment = self.transcript_segments[segment_index]
        current_speaker = segment.speaker or "Speaker"

        speaker_choices = self._get_transcript_speaker_names()
        if current_speaker not in speaker_choices:
            speaker_choices.append(current_speaker)
            speaker_choices = sorted(set(speaker_choices), key=lambda value: value.lower())

        dialog_width = 380
        dialog_height = min(420, 150 + (len(speaker_choices) * 42))

        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Segment Speaker")
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.configure(fg_color=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog_width) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{max(y, 20)}")

        container = ctk.CTkFrame(
            dialog,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        container.pack(fill="both", expand=True, padx=14, pady=14)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(2, weight=1)

        title = ctk.CTkLabel(
            container,
            text=f"Change speaker for segment {segment_index + 1:,}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))

        info = ctk.CTkLabel(
            container,
            text=(
                f"Current speaker: {current_speaker}\n"
                "Pick an existing speaker. Use Create Speaker to add new names."
            ),
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            justify="left"
        )
        info.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

        speaker_list = ctk.CTkScrollableFrame(
            container,
            height=210,
            fg_color=COLORS["bg_input"],
            corner_radius=8
        )
        speaker_list.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 12))

        def apply_speaker(new_speaker: str) -> str:
            old_speaker = segment.speaker or "Speaker"

            if new_speaker == old_speaker:
                dialog.destroy()
                return "break"

            self._end_transcript_text_edit_phase()
            self._push_transcript_undo_state("inline speaker change")
            segment.speaker = new_speaker
            self.selected_transcript_segment_index = segment_index
            self._refresh_transcript_display()

            self.log_message(
                f"Changed segment {segment_index + 1:,} speaker: '{old_speaker}' → '{new_speaker}'",
                "success"
            )

            if hasattr(self, "transcript_cursor_status_label"):
                self.transcript_cursor_status_label.configure(
                    text=(
                        f"Changed segment {segment_index + 1:,} speaker: "
                        f"{old_speaker} → {new_speaker}"
                    ),
                    text_color=COLORS["text_primary"]
                )

            dialog.destroy()
            return "break"

        for speaker in speaker_choices:
            is_current = speaker == current_speaker
            btn = ctk.CTkButton(
                speaker_list,
                text=speaker,
                command=lambda value=speaker: apply_speaker(value),
                height=34,
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold" if is_current else "normal"),
                fg_color=COLORS["accent_secondary"] if is_current else "transparent",
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"],
                corner_radius=6
            )
            btn.pack(fill="x", padx=6, pady=(4, 0))

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))

        edit_btn = ctk.CTkButton(
            button_row,
            text="Open Segment Editor",
            command=lambda: (dialog.destroy(), self.edit_transcript_segment_speaker()),
            width=150,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8
        )
        edit_btn.pack(side="left")

        close_btn = ctk.CTkButton(
            button_row,
            text="Close",
            command=dialog.destroy,
            width=80,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            corner_radius=8
        )
        close_btn.pack(side="right")

        dialog.bind("<Escape>", lambda _event: close_segment_editor())
        return "break"



    def merge_selected_transcript_segment_up(self) -> None:
        """Merge the selected transcript segment into the previous segment."""
        self._merge_selected_transcript_segment(direction="up")

    def merge_selected_transcript_segment_down(self) -> None:
        """Merge the selected transcript segment into the next segment."""
        self._merge_selected_transcript_segment(direction="down")

    def _merge_selected_transcript_segment(self, direction: str) -> None:
        """Merge the selected transcript segment up or down."""
        if not self.transcript_segments:
            messagebox.showwarning(
                "No Transcript",
                "Import a transcript first."
            )
            return

        selected_index = getattr(self, "selected_transcript_segment_index", None)

        if not isinstance(selected_index, int):
            messagebox.showwarning(
                "No Segment Selected",
                "Click inside a transcript segment first, then choose Merge Up or Merge Down."
            )
            return

        if selected_index < 0 or selected_index >= len(self.transcript_segments):
            messagebox.showwarning(
                "Invalid Selection",
                "The selected transcript segment is no longer valid."
            )
            return

        if direction == "up":
            if selected_index == 0:
                messagebox.showwarning(
                    "Cannot Merge Up",
                    "The selected segment is already the first segment."
                )
                return

            first_index = selected_index - 1
            second_index = selected_index
            result_index = first_index
            speaker_rule = "previous"

        elif direction == "down":
            if selected_index >= len(self.transcript_segments) - 1:
                messagebox.showwarning(
                    "Cannot Merge Down",
                    "The selected segment is already the last segment."
                )
                return

            first_index = selected_index
            second_index = selected_index + 1
            result_index = first_index
            speaker_rule = "selected"

        else:
            return

        first = self.transcript_segments[first_index]
        second = self.transcript_segments[second_index]

        first_speaker = first.speaker or "Speaker"
        second_speaker = second.speaker or "Speaker"

        if direction == "up":
            merged_speaker = first_speaker
            direction_label = "up"
            confirm_text = (
                "These two segments have different speakers:\n\n"
                f"Previous segment: {first_speaker}\n"
                f"Selected segment: {second_speaker}\n\n"
                f"Merge anyway using '{merged_speaker}' as the speaker?"
            )
        else:
            merged_speaker = first_speaker
            direction_label = "down"
            confirm_text = (
                "These two segments have different speakers:\n\n"
                f"Selected segment: {first_speaker}\n"
                f"Next segment: {second_speaker}\n\n"
                f"Merge anyway using '{merged_speaker}' as the speaker?"
            )

        if first_speaker != second_speaker:
            proceed = messagebox.askyesno(
                "Different Speakers",
                confirm_text
            )

            if not proceed:
                return

        first_text = (first.text or "").strip()
        second_text = (second.text or "").strip()

        if first_text and second_text:
            merged_text = f"{first_text} {second_text}"
        else:
            merged_text = first_text or second_text

        if hasattr(self, "_end_transcript_text_edit_phase"):
            self._end_transcript_text_edit_phase()

        self._push_transcript_undo_state(f"merge {direction_label} segment")

        merged_segment = TranscriptSegment(
            speaker=merged_speaker,
            start=first.start,
            end=second.end,
            text=merged_text,
        )

        self.transcript_segments[first_index:second_index + 1] = [merged_segment]
        self.selected_transcript_segment_index = result_index

        self._refresh_transcript_display()

        self.log_message(
            f"Merged segment {selected_index + 1:,} {direction_label}",
            "success"
        )

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=(
                    f"Merged segment {selected_index + 1:,} {direction_label}. "
                    f"New time: {merged_segment.start or 'no start'} → {merged_segment.end or 'no end'}"
                ),
                text_color=COLORS["text_primary"]
            )


    def edit_transcript_segment_speaker(self) -> None:
        """Edit the speaker label for one transcript segment only."""
        if not self.transcript_segments:
            messagebox.showwarning(
                "No Transcript",
                "Import a transcript first."
            )
            return

        dialog_width = 900
        dialog_height = 760

        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Segment")
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.configure(fg_color=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog_width) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{max(y, 20)}")

        container = ctk.CTkFrame(
            dialog,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        container.pack(fill="both", expand=True, padx=16, pady=16)
        container.grid_columnconfigure(0, weight=0)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(2, weight=1)

        title = ctk.CTkLabel(
            container,
            text="✏ Edit One Segment",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 2))

        help_text = ctk.CTkLabel(
            container,
            text="Search or scroll the segment list, then edit the speaker or timing for that one segment only.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            wraplength=820,
            justify="left"
        )
        help_text.grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 10))

        # Left side: searchable segment list
        list_panel = ctk.CTkFrame(container, fg_color="transparent")
        list_panel.grid(row=2, column=0, sticky="nsew", padx=(16, 8), pady=(0, 12))
        list_panel.grid_rowconfigure(3, weight=1)

        segment_label = ctk.CTkLabel(
            list_panel,
            text="Segments",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        segment_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

        search_var = ctk.StringVar(value="")
        segment_search_entry = ctk.CTkEntry(
            list_panel,
            textvariable=search_var,
            placeholder_text="Search segment text or speaker...",
            width=330,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6
        )
        segment_search_entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        segment_count_label = ctk.CTkLabel(
            list_panel,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        segment_count_label.grid(row=2, column=0, sticky="w", pady=(0, 6))

        segment_list_frame = ctk.CTkScrollableFrame(
            list_panel,
            width=340,
            height=395,
            fg_color=COLORS["bg_input"],
            corner_radius=8
        )
        segment_list_frame.grid(row=3, column=0, sticky="nsew")

        # Right side: selected segment details
        details_panel = ctk.CTkFrame(container, fg_color="transparent")
        details_panel.grid(row=2, column=1, sticky="nsew", padx=(8, 16), pady=(0, 12))
        details_panel.grid_columnconfigure(0, weight=1)
        details_panel.grid_rowconfigure(9, weight=1)

        selected_title_label = ctk.CTkLabel(
            details_panel,
            text="Selected segment",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        selected_title_label.grid(row=0, column=0, sticky="w", pady=(0, 6))

        selected_info_label = ctk.CTkLabel(
            details_panel,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            wraplength=480,
            justify="left"
        )
        selected_info_label.grid(row=1, column=0, sticky="w", pady=(0, 10))

        speaker_label = ctk.CTkLabel(
            details_panel,
            text="Speaker for this segment only",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        speaker_label.grid(row=2, column=0, sticky="w", pady=(0, 4))

        speaker_entry = ctk.CTkEntry(
            details_panel,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6
        )

        speaker_choices = self._get_transcript_speaker_names()
        if not speaker_choices:
            speaker_choices = ["Speaker"]

        def set_segment_speaker_from_picker(value: str) -> None:
            self._set_entry_text(speaker_entry, value)

        speaker_picker = ctk.CTkOptionMenu(
            details_panel,
            values=speaker_choices,
            command=set_segment_speaker_from_picker,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_secondary"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_secondary"],
            corner_radius=6
        )
        speaker_picker.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        speaker_entry.grid(row=4, column=0, sticky="ew", pady=(0, 10))

        timing_row = ctk.CTkFrame(details_panel, fg_color="transparent")
        timing_row.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        timing_row.grid_columnconfigure(0, weight=1)
        timing_row.grid_columnconfigure(1, weight=1)

        start_time_label = ctk.CTkLabel(
            timing_row,
            text="Start time",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        start_time_label.grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 4))

        end_time_label = ctk.CTkLabel(
            timing_row,
            text="End time",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        end_time_label.grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(0, 4))

        start_time_entry = ctk.CTkEntry(
            timing_row,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6,
            placeholder_text="00:00:00.000"
        )
        start_time_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))

        end_time_entry = ctk.CTkEntry(
            timing_row,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6,
            placeholder_text="00:00:00.000"
        )
        end_time_entry.grid(row=1, column=1, sticky="ew", padx=(6, 0))

        timing_help_label = ctk.CTkLabel(
            details_panel,
            text="Accepted: HH:MM:SS.mmm or MM:SS.mmm. Leave blank for no timestamp.",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        timing_help_label.grid(row=6, column=0, sticky="w", pady=(0, 8))

        preview_label = ctk.CTkLabel(
            details_panel,
            text="Preview",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        preview_label.grid(row=7, column=0, sticky="w", pady=(0, 4))

        preview_textbox = ctk.CTkTextbox(
            details_panel,
            height=135,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            wrap="word"
        )
        preview_textbox.grid(row=8, column=0, sticky="nsew", pady=(0, 12))

        button_row = ctk.CTkFrame(details_panel, fg_color="transparent")
        button_row.grid(row=9, column=0, sticky="ew", pady=(0, 4))

        selected_state = {
            "index": self.selected_transcript_segment_index
            if isinstance(getattr(self, "selected_transcript_segment_index", None), int)
            and 0 <= self.selected_transcript_segment_index < len(self.transcript_segments)
            else 0,
            "filtered": [],
            "search_after_id": None,
        }

        def format_segment_button_text(index: int) -> str:
            segment = self.transcript_segments[index]
            speaker = segment.speaker or "Speaker"
            start = segment.start or "no start"
            end = segment.end or "no end"
            text_preview = " ".join((segment.text or "").split())

            if len(text_preview) > 72:
                text_preview = text_preview[:69].rstrip() + "..."

            return f"{index + 1}. [{start} - {end}] {speaker}: {text_preview}"

        def segment_matches_query(index: int, query: str) -> bool:
            query = query.strip().lower()
            if not query:
                return True

            segment = self.transcript_segments[index]
            haystack = " ".join([
                str(index + 1),
                segment.speaker or "",
                segment.start or "",
                segment.end or "",
                segment.text or "",
            ]).lower()

            return query in haystack

        def load_selected_segment_details() -> None:
            index = selected_state["index"]
            segment = self.transcript_segments[index]
            speaker = segment.speaker or "Speaker"

            selected_info_label.configure(
                text=(
                    f"Segment {index + 1:,} of {len(self.transcript_segments):,}\n"
                    f"Time: {segment.start or 'no start'} → {segment.end or 'no end'}\n"
                    f"Current speaker: {speaker}"
                )
            )

            self._set_entry_text(speaker_entry, speaker)
            self._set_entry_text(start_time_entry, segment.start or "")
            self._set_entry_text(end_time_entry, segment.end or "")

            if speaker in speaker_choices:
                speaker_picker.set(speaker)

            preview_textbox.configure(state="normal")
            preview_textbox.delete("1.0", "end")
            preview_textbox.insert("1.0", segment.text or "")
            preview_textbox.configure(state="disabled")

        def select_segment(index: int) -> None:
            selected_state["index"] = index
            load_selected_segment_details()
            rebuild_segment_list()

        def scroll_segment_list_to_top() -> None:
            """Reset the segment list scroll position after filtering."""
            try:
                segment_list_frame._parent_canvas.yview_moveto(0)
            except Exception:
                pass

        def rebuild_segment_list(force_first_match: bool = False) -> None:
            query = search_var.get().strip()
            filtered = [
                i for i in range(len(self.transcript_segments))
                if segment_matches_query(i, query)
            ]
            selected_state["filtered"] = filtered

            for child in segment_list_frame.winfo_children():
                child.destroy()

            if not filtered:
                segment_count_label.configure(
                    text=f"0 matching segment(s) for: {query}" if query else "0 matching segment(s)"
                )
                no_results = ctk.CTkLabel(
                    segment_list_frame,
                    text="No matching segments.",
                    font=ctk.CTkFont(size=12),
                    text_color=COLORS["text_muted"]
                )
                no_results.pack(anchor="w", padx=8, pady=8)
                dialog.after_idle(scroll_segment_list_to_top)
                return

            if force_first_match or selected_state["index"] not in filtered:
                selected_state["index"] = filtered[0]
                load_selected_segment_details()

            if query:
                segment_count_label.configure(
                    text=f"{len(filtered):,} matching segment(s) for: {query}"
                )
            else:
                segment_count_label.configure(
                    text=f"{len(filtered):,} matching segment(s)"
                )

            for index in filtered:
                is_selected = index == selected_state["index"]
                button = ctk.CTkButton(
                    segment_list_frame,
                    text=format_segment_button_text(index),
                    command=lambda idx=index: select_segment(idx),
                    width=315,
                    height=32,
                    anchor="w",
                    font=ctk.CTkFont(size=11),
                    fg_color=COLORS["accent_secondary"] if is_selected else "transparent",
                    hover_color=COLORS["border"],
                    text_color=COLORS["text_primary"] if is_selected else COLORS["text_secondary"],
                    corner_radius=6
                )
                button.pack(fill="x", padx=6, pady=(4, 0))

            if force_first_match:
                dialog.after_idle(scroll_segment_list_to_top)

        def move_selection(delta: int) -> str:
            filtered = selected_state.get("filtered") or []

            if not filtered:
                return "break"

            current_index = selected_state["index"]

            if current_index in filtered:
                current_position = filtered.index(current_index)
            else:
                current_position = 0

            new_position = max(0, min(len(filtered) - 1, current_position + delta))
            select_segment(filtered[new_position])
            return "break"

        def export_segment_search_matches() -> None:
            """Export the currently filtered Segment editor matches to TXT."""
            query = search_var.get().strip()
            filtered = selected_state.get("filtered") or []

            if not filtered:
                messagebox.showwarning(
                    "No Matches",
                    "There are no matching segments to export."
                )
                return

            safe_query = "".join(
                ch if ch.isalnum() or ch in ("-", "_") else "_"
                for ch in (query or "all_segments")
            ).strip("_") or "all_segments"

            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                title="Export Segment Search Matches",
                initialfile=f"segment_matches_{safe_query}.txt"
            )

            if not filename:
                return

            try:
                with open(filename, "w", encoding="utf-8", newline="\n") as f:
                    f.write("Segment Search Matches\n")
                    f.write("=" * 80)
                    f.write("\n\n")
                    f.write(f"Query: {query or '(all segments)'}\n")
                    f.write(f"Matches: {len(filtered):,}\n\n")

                    for output_number, segment_index in enumerate(filtered, start=1):
                        segment = self.transcript_segments[segment_index]
                        speaker = segment.speaker or "Speaker"
                        start = segment.start or "no start"
                        end = segment.end or "no end"
                        text = " ".join((segment.text or "").split())

                        f.write(f"{output_number}. Segment {segment_index + 1:,}\n")
                        f.write(f"Speaker: {speaker}\n")
                        f.write(f"Time: {start} -> {end}\n")
                        f.write("Text:\n")
                        f.write(text)
                        f.write("\n\n")
                        f.write("-" * 80)
                        f.write("\n\n")

                self.log_message(
                    f"Exported {len(filtered):,} segment search match(es) to: {os.path.basename(filename)}",
                    "success"
                )
                messagebox.showinfo(
                    "Segment Matches Exported",
                    f"Saved {len(filtered):,} matching segment(s):\n\n{os.path.basename(filename)}"
                )

            except Exception as error:
                logger.exception("Segment search export error")
                self.log_message(f"Segment search export failed: {error}", "error")
                messagebox.showerror("Segment Search Export Error", str(error))

        def normalise_segment_time(raw_value: str, label: str) -> Optional[str]:
            """Normalise segment time input to HH:MM:SS.mmm, or blank."""
            value = (raw_value or "").strip().replace(",", ".")

            if not value:
                return ""

            if value.lower() in {"none", "no start", "no end"}:
                return ""

            parts = value.split(":")

            if len(parts) == 2:
                hours_text = "0"
                minutes_text, seconds_text = parts
            elif len(parts) == 3:
                hours_text, minutes_text, seconds_text = parts
            else:
                messagebox.showwarning(
                    "Invalid Time",
                    f"{label} must look like HH:MM:SS.mmm or MM:SS.mmm."
                )
                return None

            if "." in seconds_text:
                seconds_main, millis_text = seconds_text.split(".", 1)
            else:
                seconds_main = seconds_text
                millis_text = "000"

            if not (
                hours_text.strip().isdigit()
                and minutes_text.strip().isdigit()
                and seconds_main.strip().isdigit()
                and millis_text.strip().isdigit()
            ):
                messagebox.showwarning(
                    "Invalid Time",
                    f"{label} contains invalid characters."
                )
                return None

            hours = int(hours_text)
            minutes = int(minutes_text)
            seconds = int(seconds_main)

            if minutes > 59 or seconds > 59:
                messagebox.showwarning(
                    "Invalid Time",
                    f"{label} has minutes or seconds above 59."
                )
                return None

            millis = millis_text[:3].ljust(3, "0")

            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis}"

        def do_update() -> None:
            index = selected_state["index"]
            segment = self.transcript_segments[index]

            old_speaker = segment.speaker or "Speaker"
            old_start = segment.start or ""
            old_end = segment.end or ""

            new_speaker = speaker_entry.get().strip()
            new_start = normalise_segment_time(start_time_entry.get(), "Start time")
            new_end = normalise_segment_time(end_time_entry.get(), "End time")

            if new_start is None or new_end is None:
                return

            if not new_speaker:
                messagebox.showwarning(
                    "Missing Speaker",
                    "Enter a speaker name for this segment."
                )
                return

            if new_start and new_end:
                start_seconds = self._transcript_time_to_seconds(new_start)
                end_seconds = self._transcript_time_to_seconds(new_end)

                if (
                    start_seconds is not None
                    and end_seconds is not None
                    and end_seconds < start_seconds
                ):
                    messagebox.showwarning(
                        "Invalid Time Range",
                        "End time must be the same as or later than start time."
                    )
                    return

            speaker_changed = new_speaker != old_speaker
            timing_changed = new_start != old_start or new_end != old_end

            if not speaker_changed and not timing_changed:
                messagebox.showinfo(
                    "No Change",
                    "The speaker and timing are already the same for this segment."
                )
                return

            if hasattr(self, "_end_transcript_text_edit_phase"):
                self._end_transcript_text_edit_phase()

            self._push_transcript_undo_state("segment speaker/timing edit")

            if speaker_changed:
                self._ensure_transcript_custom_speakers()
                self.transcript_custom_speakers.add(new_speaker)
                segment.speaker = new_speaker

            if timing_changed:
                segment.start = new_start
                segment.end = new_end

            self.selected_transcript_segment_index = index
            self._refresh_transcript_display()

            # Queue the visual flash until the Segment editor closes.
            # Flashing immediately is mostly hidden behind the dialog.
            selected_state["flash_after_close_index"] = index

            load_selected_segment_details()
            rebuild_segment_list()

            changes = []

            if speaker_changed:
                changes.append(f"speaker: '{old_speaker}' → '{new_speaker}'")

            if timing_changed:
                changes.append(
                    f"time: {old_start or 'no start'} → {old_end or 'no end'} "
                    f"changed to {new_start or 'no start'} → {new_end or 'no end'}"
                )

            self.log_message(
                f"Updated segment {index + 1:,}: " + "; ".join(changes),
                "success"
            )

            if hasattr(self, "transcript_cursor_status_label"):
                self.transcript_cursor_status_label.configure(
                    text=f"Updated segment {index + 1:,}. Ctrl+Z undo, Ctrl+Y redo.",
                    text_color=COLORS["text_primary"]
                )


        def close_segment_editor() -> None:
            flash_index = selected_state.get("flash_after_close_index")

            # If no edit was applied, still flash the last selected segment.
            # This helps when the user only searched/selected inside the Segment editor.
            if not isinstance(flash_index, int):
                flash_index = selected_state.get(
                    "index",
                    getattr(self, "selected_transcript_segment_index", None)
                )

            dialog.destroy()

            if isinstance(flash_index, int):
                self.selected_transcript_segment_index = flash_index

                if hasattr(self, "_refresh_transcript_timeline"):
                    self._refresh_transcript_timeline()

                if hasattr(self, "_flash_transcript_segment_selection"):
                    self.after(
                        100,
                        lambda idx=flash_index: self._flash_transcript_segment_selection(
                            idx,
                            duration_ms=1000
                        )
                    )

        dialog.protocol("WM_DELETE_WINDOW", close_segment_editor)

        export_matches_btn = ctk.CTkButton(
            button_row,
            text="Export Matches",
            command=export_segment_search_matches,
            width=135,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            corner_radius=8
        )
        export_matches_btn.pack(side="left")

        close_btn = ctk.CTkButton(
            button_row,
            text="Close",
            command=close_segment_editor,
            width=90,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            corner_radius=8
        )
        close_btn.pack(side="right")

        update_btn = ctk.CTkButton(
            button_row,
            text="Update Segment",
            command=do_update,
            width=150,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#000000",
            corner_radius=8
        )
        update_btn.pack(side="right", padx=(0, 8))

        def on_search_changed(*_args) -> None:
            rebuild_segment_list(force_first_match=True)

        def schedule_segment_search_refresh(*_) -> None:
            """Debounce Segment editor search so typing does not rebuild the list every keypress."""
            existing_after_id = selected_state.get("search_after_id")
        
            if existing_after_id:
                try:
                    dialog.after_cancel(existing_after_id)
                except Exception:
                    pass
        
            def run_search_refresh() -> None:
                selected_state["search_after_id"] = None
                rebuild_segment_list(force_first_match=True)
        
            selected_state["search_after_id"] = dialog.after(180, run_search_refresh)
        
        search_var.trace_add("write", schedule_segment_search_refresh)
        segment_search_entry.bind("<Down>", lambda _event: move_selection(1))
        segment_search_entry.bind("<Up>", lambda _event: move_selection(-1))
        dialog.bind("<Down>", lambda _event: move_selection(1))
        dialog.bind("<Up>", lambda _event: move_selection(-1))
        dialog.bind("<Return>", lambda _event: do_update())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

        load_selected_segment_details()
        rebuild_segment_list()
        segment_search_entry.focus_set()

    def rename_transcript_speaker(self) -> None:
        """Rename one speaker label globally across all transcript segments."""
        if not self.transcript_segments:
            messagebox.showwarning(
                "No Transcript",
                "Import a transcript first."
            )
            return

        speaker_counts = {}
        for segment in self.transcript_segments:
            speaker = (segment.speaker or "").strip()
            if speaker:
                speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1

        speakers = sorted(speaker_counts)

        if not speakers:
            messagebox.showwarning(
                "No Speakers",
                "No speaker labels were found in the transcript."
            )
            return

        display_to_speaker = {
            f"{speaker} ({speaker_counts[speaker]:,} segment(s))": speaker
            for speaker in speakers
        }
        display_values = list(display_to_speaker.keys())

        dialog_width = 500
        dialog_height = 310

        dialog = ctk.CTkToplevel(self)
        dialog.title("Rename Speaker Globally")
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.configure(fg_color=COLORS["bg_dark"])
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog_width) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        container = ctk.CTkFrame(
            dialog,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        container.pack(fill="both", expand=True, padx=16, pady=16)

        title = ctk.CTkLabel(
            container,
            text="👤 Rename Speaker Globally",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(anchor="w", padx=16, pady=(14, 6))

        help_text = ctk.CTkLabel(
            container,
            text="This changes the selected speaker label everywhere it appears in the transcript.",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            wraplength=440,
            justify="left"
        )
        help_text.pack(anchor="w", padx=16, pady=(0, 12))

        old_label = ctk.CTkLabel(
            container,
            text="Speaker to rename",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        old_label.pack(anchor="w", padx=16)

        selected_display = ctk.StringVar(value=display_values[0])

        new_name_entry = ctk.CTkEntry(
            container,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6
        )

        count_label = ctk.CTkLabel(
            container,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )

        def get_selected_speaker() -> str:
            return display_to_speaker.get(selected_display.get(), speakers[0])

        def update_count_label() -> None:
            speaker = get_selected_speaker()
            count = speaker_counts.get(speaker, 0)
            count_label.configure(
                text=f"Will rename {count:,} segment(s) currently labelled: {speaker}"
            )

        def on_speaker_selected(value: str) -> None:
            speaker = display_to_speaker.get(value, speakers[0])
            new_name_entry.delete(0, "end")
            new_name_entry.insert(0, speaker)
            update_count_label()

        speaker_menu = ctk.CTkOptionMenu(
            container,
            values=display_values,
            variable=selected_display,
            command=on_speaker_selected,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            button_color=COLORS["accent_secondary"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            dropdown_hover_color=COLORS["accent_secondary"],
            corner_radius=6
        )
        speaker_menu.pack(fill="x", padx=16, pady=(4, 8))

        count_label.pack(anchor="w", padx=16, pady=(0, 10))

        new_label = ctk.CTkLabel(
            container,
            text="New speaker name",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        new_label.pack(anchor="w", padx=16)

        new_name_entry.pack(fill="x", padx=16, pady=(4, 12))
        new_name_entry.insert(0, speakers[0])
        new_name_entry.focus_set()
        new_name_entry.select_range(0, "end")
        update_count_label()

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.pack(fill="x", padx=16, pady=(0, 14))

        def do_rename() -> None:
            old_name = get_selected_speaker()
            new_name = new_name_entry.get().strip()

            if not new_name:
                messagebox.showwarning(
                    "Missing Name",
                    "Enter a new speaker name."
                )
                return

            if new_name == old_name:
                messagebox.showinfo(
                    "No Change",
                    "The new speaker name is the same as the current speaker name."
                )
                return

            changed = 0
            for segment in self.transcript_segments:
                if segment.speaker == old_name:
                    segment.speaker = new_name
                    changed += 1

            dialog.destroy()
            self._refresh_transcript_display()
            self.log_message(
                f"Renamed speaker globally: '{old_name}' → '{new_name}' in {changed:,} segment(s)",
                "success"
            )
            messagebox.showinfo(
                "Speaker Renamed",
                f"Renamed:\n\n{old_name}\n\nTo:\n\n{new_name}\n\nSegments changed: {changed:,}"
            )

        cancel_btn = ctk.CTkButton(
            button_row,
            text="Cancel",
            command=dialog.destroy,
            width=90,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            corner_radius=8
        )
        cancel_btn.pack(side="right")

        rename_btn = ctk.CTkButton(
            button_row,
            text="Rename All",
            command=do_rename,
            width=120,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#000000",
            corner_radius=8
        )
        rename_btn.pack(side="right", padx=(0, 8))

        dialog.bind("<Return>", lambda _event: do_rename())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def clear_transcript(self) -> None:
        """Clear imported transcript from the app."""
        if not self.transcript_segments:
            return

        answer = messagebox.askyesno(
            "Clear Transcript",
            "Remove the currently loaded transcript from the app?"
        )

        if not answer:
            return

        self.transcript_segments = []
        self.transcript_playhead_seconds = None
        self.selected_transcript_segment_index = None
        self.last_transcript_source = None
        self.transcript_has_unsaved_edits = False
        self.active_transcript_file_path = ""
        self._refresh_transcript_display()
        self._refresh_transcript_timeline()
        self._refresh_session_files_list()
        self.log_message("Transcript cleared.", "muted")

        with self._data_lock:
            has_comments = len(self.all_comments) > 0

        if not has_comments and not self.attached_screenshots:
            self.evidence_button.configure(state="disabled")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the application."""
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
