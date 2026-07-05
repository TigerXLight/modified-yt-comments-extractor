"""
YouTube Comment Extractor - Desktop Application.

A modern GUI application for extracting, filtering, and analyzing
YouTube comments with advanced spam detection.
"""

from __future__ import annotations

import logging
import os
import sys
import array
import subprocess
import random
import threading
import time
import webbrowser
from dataclasses import dataclass
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Dict, List, Optional, Tuple

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

from youtube_transcript_downloader import (
    download_youtube_transcript,
    merge_transcript_segments,
)
from youtube_video_metadata import fetch_youtube_video_metadata
from asr_tools import transcribe_media_file
from asr_defaults import load_asr_defaults, save_asr_defaults
from asr_settings_dialog import ask_asr_settings

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


# =============================================================================
# MAIN APPLICATION CLASS
# =============================================================================

class App(ctk.CTk):
    """Main application window."""

    SIDEBAR_WIDTH = 280

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
        self.transcript_text_edit_phase_segment_index: Optional[int] = None
        self.last_transcript_source: Optional[str] = None
        self.last_youtube_video_info: Optional[Dict[str, Any]] = None
        self.last_asr_metadata: Optional[Dict[str, Any]] = None
        self.linked_transcript_media_path: Optional[str] = None
        self.transcript_waveform_peaks: List[float] = []
        self.transcript_waveform_source_path: Optional[str] = None
        self.last_package_dir: Optional[str] = None

        self.transcript_show_speakers_var = ctk.BooleanVar(value=True)
        self.transcript_show_timestamps_var = ctk.BooleanVar(value=True)

        # Custom filter patterns
        self._blacklist_patterns: str = ""
        self._whitelist_patterns: str = ""

        # Thread reference for clean shutdown
        self._fetch_thread_ref: Optional[threading.Thread] = None

        # Build UI
        self._create_header()
        self._create_sidebar()
        self._create_main_content()

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
        """Create the top header with app name and description."""
        self.header_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=0,
            height=95
        )
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.header_frame.grid_propagate(False)

        # Header content
        header_content = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=30, pady=15)

        # App title with play button icon
        self._play_icon = self._create_play_icon()
        title_label = ctk.CTkLabel(
            header_content,
            text=f"  {APP_NAME}",
            image=self._play_icon,
            compound="left",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title_label.pack(anchor="w")

        # Brand attribution
        brand_label = ctk.CTkLabel(
            header_content,
            text="by Creator Intelligence",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["accent"]
        )
        brand_label.pack(anchor="w", pady=(1, 0))

        # Tagline
        subtitle_label = ctk.CTkLabel(
            header_content,
            text=f"{APP_DESCRIPTION}",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"]
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

    # =========================================================================
    # SIDEBAR CREATION
    # =========================================================================

    def _create_sidebar(self) -> None:
        """Create the left sidebar with all settings."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=self.SIDEBAR_WIDTH,
            fg_color=COLORS["bg_card"],
            corner_radius=0
        )
        self.sidebar.grid(row=1, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Sidebar scrollable content
        self.sidebar_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_secondary"]
        )
        self.sidebar_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # API Key section
        self._create_api_section()

        # Filters section
        self._create_filters_section()

        # Date Range section
        self._create_date_section()

        # Custom Filters section
        self._create_custom_filters_section()

        # Version at bottom
        self._create_sidebar_footer()

    def _create_section_label(self, parent: ctk.CTkFrame, text: str, first: bool = False) -> None:
        """Create a section label with divider."""
        if not first:
            divider = ctk.CTkFrame(parent, fg_color=COLORS["border"], height=1)
            divider.pack(fill="x", padx=20, pady=(15, 10))

        label = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        label.pack(anchor="w", padx=20, pady=(15 if first else 0, 10))

    def _create_api_section(self) -> None:
        """Create API key input section in sidebar."""
        self._create_section_label(self.sidebar_scroll, "API KEY", first=True)

        api_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        api_frame.pack(fill="x", padx=20)

        # API key entry with toggle button
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

        self.api_key_visible = False
        self.toggle_api_key_button = ctk.CTkButton(
            entry_frame,
            text="👁",
            width=36,
            height=36,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            corner_radius=6,
            command=self._toggle_api_key_visibility
        )
        self.toggle_api_key_button.grid(row=0, column=1, padx=(6, 0))

        # Storage info
        storage_info = self.settings_manager.get_storage_info()
        info_text = "🔒 Secure" if "keyring" in storage_info else "⚠️ File"
        self.storage_label = ctk.CTkLabel(
            api_frame,
            text=info_text,
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        self.storage_label.pack(anchor="w", pady=(4, 0))

    def _create_filters_section(self) -> None:
        """Create filters section in sidebar."""
        self._create_section_label(self.sidebar_scroll, "FILTERS")

        filters_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        filters_frame.pack(fill="x", padx=20)

        # Spam filter toggle
        spam_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        spam_row.pack(fill="x", pady=(0, 8))

        self.spam_filter_var = ctk.BooleanVar(value=True)
        self.spam_filter_checkbox = ctk.CTkSwitch(
            spam_row,
            text="Filter Spam",
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
        self.min_likes_entry.insert(0, "0")

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

        max_comments_hint = ctk.CTkLabel(
            filters_frame,
            text="Per video, leave empty for all",
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

        self.sort_var = ctk.StringVar(value="Likes")
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

    def _create_date_section(self) -> None:
        """Create date range section in sidebar."""
        self._create_section_label(self.sidebar_scroll, "DATE RANGE")

        date_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        date_frame.pack(fill="x", padx=20)

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

        # Hint
        hint_label = ctk.CTkLabel(
            date_frame,
            text="Leave empty for no limit",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        hint_label.pack(anchor="w", pady=(6, 0))

    def _create_custom_filters_section(self) -> None:
        """Create custom filters (blacklist/whitelist) section in sidebar."""
        self._create_section_label(self.sidebar_scroll, "CUSTOM FILTERS")

        custom_frame = ctk.CTkFrame(self.sidebar_scroll, fg_color="transparent")
        custom_frame.pack(fill="x", padx=20)

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
        self.main_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["border"],
            scrollbar_button_hover_color=COLORS["accent_secondary"]
        )
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=0)

        self._create_url_section()
        self._create_progress_section()
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
        url_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        url_card.grid_columnconfigure(0, weight=1)

        # URL input area
        url_frame = ctk.CTkFrame(url_card, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=(20, 6))

        url_label = ctk.CTkLabel(
            url_frame,
            text="📺 Video URLs",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        url_label.pack(anchor="w", pady=(0, 10))

        self.url_entry = ctk.CTkTextbox(
            url_frame,
            height=70,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8
        )
        self.url_entry.pack(fill="x")

        # Placeholder handling
        self._url_placeholder = "Paste YouTube URLs here (one per line)...\n\nSupported formats:\n• youtube.com/watch?v=...\n• youtu.be/...\n• youtube.com/shorts/..."
        self.url_entry.insert("1.0", self._url_placeholder)
        self.url_entry.configure(text_color=COLORS["text_muted"])
        self.url_entry.bind("<FocusIn>", self._on_url_focus_in)
        self.url_entry.bind("<FocusOut>", self._on_url_focus_out)
        self.url_entry.bind("<KeyRelease>", self._validate_urls_live)

        # URL status
        self.url_status = ctk.CTkLabel(
            url_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.url_status.pack(anchor="e", pady=(2, 0))

        # Filter words section
        filter_words_frame = ctk.CTkFrame(url_card, fg_color="transparent")
        filter_words_frame.pack(fill="x", padx=20, pady=(0, 10))

        filter_words_header = ctk.CTkFrame(filter_words_frame, fg_color="transparent")
        filter_words_header.pack(fill="x")

        filter_words_label = ctk.CTkLabel(
            filter_words_header,
            text="🔍 Only fetch comments with these words",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        filter_words_label.pack(side="left")

        filter_words_hint = ctk.CTkLabel(
            filter_words_header,
            text="Comma-separated, matches any word",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        filter_words_hint.pack(side="right")

        self.filter_words_entry = ctk.CTkEntry(
            filter_words_frame,
            height=36,
            placeholder_text="e.g., python, tutorial, beginner",
            font=ctk.CTkFont(size=13),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            corner_radius=6
        )
        self.filter_words_entry.pack(fill="x", pady=(8, 0))

        # Action buttons area
        action_area = ctk.CTkFrame(url_card, fg_color="transparent")
        action_area.pack(fill="x", padx=20, pady=(0, 20))

        # Main row: Go / Comments / Livechat / exports
        action_frame = ctk.CTkFrame(action_area, fg_color="transparent")
        action_frame.pack(fill="x")

        # Go button
        self.fetch_button = ctk.CTkButton(
            action_frame,
            text="▶ Go",
            command=self.start_fetching,
            width=100,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#000000",
            corner_radius=8
        )
        self.fetch_button.pack(side="left")

        # Extraction choice checkboxes
        mode_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        mode_frame.pack(side="left", padx=(14, 0))

        self.extract_comments_var = ctk.BooleanVar(value=True)
        self.extract_live_chat_var = ctk.BooleanVar(value=False)

        self.comments_checkbox = ctk.CTkCheckBox(
            mode_frame,
            text="Comments",
            variable=self.extract_comments_var,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000"
        )
        self.comments_checkbox.pack(side="left", padx=(0, 10))

        self.live_chat_checkbox = ctk.CTkCheckBox(
            mode_frame,
            text="Livechat",
            variable=self.extract_live_chat_var,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["border"],
            checkmark_color="#000000"
        )
        self.live_chat_checkbox.pack(side="left")

        # Cancel button hidden by default
        self.cancel_button = ctk.CTkButton(
            action_frame,
            text="⏹ Cancel",
            command=self.cancel_fetching,
            width=100,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["error"],
            hover_color=COLORS["accent_hover"],
            corner_radius=8
        )
        # Do not pack yet

        # Export buttons
        self.export_excel_button = ctk.CTkButton(
            action_frame,
            text="📊 Excel",
            command=self.export_excel,
            width=90,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.export_excel_button.pack(side="right")

        self.export_button = ctk.CTkButton(
            action_frame,
            text="📥 CSV",
            command=self.export_csv,
            width=90,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.export_button.pack(side="right", padx=(0, 10))

        self.export_txt_button = ctk.CTkButton(
            action_frame,
            text="📝 TXT",
            command=self.export_txt,
            width=90,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.export_txt_button.pack(side="right", padx=(0, 10))

        # Second row: screenshot/package/update tools
        tools_frame = ctk.CTkFrame(action_area, fg_color="transparent")
        tools_frame.pack(fill="x", pady=(10, 0))

        tools_hint = ctk.CTkLabel(
            tools_frame,
            text="Attach screenshots, then create an export package",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        tools_hint.pack(side="left")

        self.update_button = ctk.CTkButton(
            tools_frame,
            text="🔄 Updates",
            command=self.check_for_updates_clicked,
            width=105,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8
        )
        self.update_button.pack(side="right")

        self.evidence_button = ctk.CTkButton(
            tools_frame,
            text="📁 Package",
            command=self.export_evidence_folder,
            width=105,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.evidence_button.pack(side="right", padx=(0, 10))

        self.screenshot_button = ctk.CTkButton(
            tools_frame,
            text="🖼 Attach",
            command=self.attach_screenshots,
            width=105,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8
        )
        self.screenshot_button.pack(side="right", padx=(0, 10))

        # Extra package helper row
        package_tools_frame = ctk.CTkFrame(action_area, fg_color="transparent")
        package_tools_frame.pack(fill="x", pady=(8, 0))

        package_tools_hint = ctk.CTkLabel(
            package_tools_frame,
            text="Package tools",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        package_tools_hint.pack(side="left")

        self.open_last_package_button = ctk.CTkButton(
            package_tools_frame,
            text="📂 Open Last",
            command=self.open_last_package,
            width=105,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8,
            state="disabled"
        )
        self.open_last_package_button.pack(side="right")

        self.clear_screenshots_button = ctk.CTkButton(
            package_tools_frame,
            text="🧹 Clear Attach",
            command=self.clear_attached_screenshots,
            width=115,
            height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="transparent",
            hover_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            corner_radius=8,
            state="disabled"
        )
        self.clear_screenshots_button.pack(side="right", padx=(0, 10))

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

    def _create_transcript_section(self) -> None:
        """Create transcript import/export section."""
        self.transcript_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.transcript_card.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        self.transcript_card.grid_columnconfigure(0, weight=1)

        # Header row
        header = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 8))

        title = ctk.CTkLabel(
            header,
            text="🗣 Transcript",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(side="left")

        self.transcript_stats_label = ctk.CTkLabel(
            header,
            text="No transcript loaded",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.transcript_stats_label.pack(side="left", padx=(12, 0))

        # Button row
        button_row = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        button_row.pack(fill="x", padx=15, pady=(0, 8))

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
            text="⬇ YouTube",
            command=self.download_youtube_transcript_clicked,
            width=105,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent_secondary"],
            hover_color=COLORS["border"],
            corner_radius=8
        )
        self.transcript_youtube_button.pack(side="left", padx=(8, 0))

        self.transcript_asr_button_wrap = ctk.CTkFrame(
            button_row,
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


        self.transcript_media_button = ctk.CTkButton(
            button_row,
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

        self.transcript_media_status_label = ctk.CTkLabel(
            button_row,
            text="No media",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        self.transcript_media_status_label.pack(side="left", padx=(8, 0))

        self.transcript_media_clear_button = ctk.CTkButton(
            button_row,
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
        transcript_edit_row = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        transcript_edit_row.pack(fill="x", padx=15, pady=(0, 8))

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

        self.transcript_merge_up_button = ctk.CTkButton(
            self.transcript_edit_segment_button.master,
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
            self.transcript_edit_segment_button.master,
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
            transcript_edit_row,
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
        transcript_export_row = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        transcript_export_row.pack(fill="x", padx=15, pady=(2, 8))

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
        transcript_options_row = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        transcript_options_row.pack(fill="x", padx=15, pady=(0, 8))

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

        transcript_search_row = ctk.CTkFrame(self.transcript_card, fg_color="transparent")
        transcript_search_row.pack(fill="x", padx=15, pady=(0, 8))

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
        self.transcript_playhead_seconds: Optional[float] = None
        self.transcript_playback_process = None
        self.transcript_playback_after_id = None
        self.transcript_playback_start_seconds: Optional[float] = None
        self.transcript_playback_start_wall_time: Optional[float] = None
        self.transcript_playback_latency_offset_seconds = 0.0
        self.transcript_playback_active_segment_index: Optional[int] = None
        self.transcript_playback_tick_ms = 30
        self.transcript_playback_requested_start_seconds: Optional[float] = None
        self.transcript_vlc_clock_anchor_seconds: Optional[float] = None
        self.transcript_vlc_clock_anchor_wall_time: Optional[float] = None
        self.transcript_vlc_last_reported_seconds: Optional[float] = None
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

        self.transcript_timeline_pan_slider = ctk.CTkSlider(
            timeline_zoom_row,
            from_=0,
            to=100,
            number_of_steps=2000,
            command=self._on_transcript_timeline_pan_changed,
            height=16
        )
        self.transcript_timeline_pan_slider.grid(
            row=1,
            column=1,
            columnspan=4,
            sticky="ew",
            pady=(6, 0)
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

        self._refresh_transcript_display()

    def _create_log_section(self) -> None:
        """Create the activity log section."""
        self.log_card = ctk.CTkFrame(
            self.main_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )
        self.log_card.grid(row=3, column=0, sticky="ew")
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
            height=90,
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

        self.pattern_count_label.configure(text=" • ".join(parts) if parts else "")

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _on_closing(self) -> None:
        """Handle window close event - cancel any running operations."""
        if self.fetch_state.is_fetching:
            self.fetch_state.request_cancel()
            if self._fetch_thread_ref and self._fetch_thread_ref.is_alive():
                self._fetch_thread_ref.join(timeout=2.0)
        self.destroy()

    def _toggle_api_key_visibility(self) -> None:
        """Toggle API key visibility."""
        self.api_key_visible = not self.api_key_visible
        if self.api_key_visible:
            self.api_key_entry.configure(show="")
            self.toggle_api_key_button.configure(text="🔒")
        else:
            self.api_key_entry.configure(show="*")
            self.toggle_api_key_button.configure(text="👁")

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

        valid_count, invalid_count, status_msg = URLValidator.get_validation_summary(current_text)

        if valid_count == 0:
            color = COLORS["warning"]
        elif invalid_count == 0:
            color = COLORS["success"]
        else:
            color = COLORS["warning"]

        self.url_status.configure(text=status_msg, text_color=color)

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
            settings = self.settings_manager.load()

            if settings.api_key:
                self.api_key_entry.insert(0, settings.api_key)

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

            sort_option = SortOption(settings.sort_by) if settings.sort_by else SortOption.LIKES
            self.sort_var.set(sort_option.display_name)

            # Load filter words
            if settings.filter_words:
                self.filter_words_entry.delete(0, "end")
                self.filter_words_entry.insert(0, settings.filter_words)

            self._blacklist_patterns = settings.blacklist_patterns or ""
            self._whitelist_patterns = settings.whitelist_patterns or ""
            self._update_filter_counts()

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def _save_settings(self) -> None:
        """Save current settings."""
        try:
            settings = AppSettings(
                api_key=self.api_key_entry.get().strip(),
                filter_spam=self.spam_filter_var.get(),
                spam_threshold=self.spam_threshold_var.get(),
                exclude_creator=self.exclude_creator_var.get(),
                min_likes=self._get_min_likes(),
                max_comments=self._get_max_comments(),
                filter_words=self.filter_words_entry.get().strip(),
                sort_by=SortOption.from_display_name(self.sort_var.get()).value,
                blacklist_patterns=self._blacklist_patterns,
                whitelist_patterns=self._whitelist_patterns,
            )
            self.settings_manager.save(settings)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self.log_message(f"Error saving settings: {e}", "error")

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
            self.status_label.configure(text="Cancelling...", text_color=COLORS["warning"])
            self.log_message("Cancellation requested...", "warning")

    def start_fetching(self) -> None:
        """Start the comment fetching process."""
        if self.fetch_state.is_fetching:
            return

        # Get and validate inputs
        api_key = self.api_key_entry.get().strip()

        current_text = self.url_entry.get("1.0", "end").strip()
        if current_text == self._url_placeholder.strip():
            current_text = ""

        valid_urls, _ = URLValidator.parse_url_list(current_text)

        # Validate API key
        api_result = APIKeyValidator.validate(api_key)
        if not api_result:
            messagebox.showerror("Invalid API Key", api_result.error_message)
            return

        # Validate URLs
        if not valid_urls:
            messagebox.showerror(
                "Missing URLs",
                "Please enter at least one valid YouTube video URL.\n\n"
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
        self.fetch_button.pack_forget()
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

        # Start fetch thread
        extract_comments = self.extract_comments_var.get()
        extract_live_chat = self.extract_live_chat_var.get()

        if not extract_comments and not extract_live_chat:
            messagebox.showerror(
                "Selection Required",
                "Please tick Comments, Livechat, or both before pressing Go."
            )
            return

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
        self.cancel_button.pack_forget()
        self.fetch_button.pack(side="left")

    def export_txt(self) -> None:
        """Export data to a readable TXT file for Notepad."""
        with self._data_lock:
            if not self.all_comments:
                messagebox.showwarning("No Data", "No comments to export. Fetch comments first.")
                return
            metadata = list(self.all_metadata)
            comments = list(self.all_comments)
            spam = list(self.all_spam)

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
            if not self.all_comments:
                messagebox.showwarning("No Data", "No comments to export. Fetch comments first.")
                return
            metadata = list(self.all_metadata)
            comments = list(self.all_comments)
            spam = list(self.all_spam)

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
            if not self.all_comments:
                messagebox.showwarning("No Data", "No comments to export. Fetch comments first.")
                return
            metadata = list(self.all_metadata)
            comments = list(self.all_comments)
            spam = list(self.all_spam)

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

        if not comments and not self.attached_screenshots and not self.transcript_segments:
            messagebox.showwarning(
                "Nothing to Package",
                "Fetch comments, attach screenshots, or import a transcript first."
            )
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
                self.update_button.configure(state="normal", text="🔄 Updates")

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
        return "break"


    def _refresh_transcript_display(self) -> None:
        """Refresh transcript preview, stats, and inline editor mapping."""
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
                    text="No transcript segment selected.",
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
                "Import an SRT, VTT, or TXT transcript file here.\n\n"
                "v2.4.0 supports local import/export, YouTube transcript download, and Local ASR transcription.\n"
                "Use Local ASR to transcribe local audio/video files with faster-whisper."
            )
            self.transcript_textbox.configure(state="disabled")
            if hasattr(self, "transcript_search_count_label"):
                self._update_transcript_search_matches(reset_index=True)
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
        """Let mouse wheel scroll the main app even after sync controls are focused."""
        try:
            canvas = self.main_frame._parent_canvas
        except Exception:
            return "break"

        delta = getattr(event, "delta", 0)

        if delta:
            units = -1 * int(delta / 120)
        else:
            # Linux/X11 fallback if ever used.
            button_number = getattr(event, "num", None)
            units = -1 if button_number == 4 else 1

        if units == 0:
            units = -1 if delta > 0 else 1

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
        self.transcript_playback_requested_start_seconds = media_start_seconds
        self.transcript_playback_start_seconds = media_start_seconds
        self.transcript_playback_start_wall_time = time.monotonic()
        self.transcript_vlc_clock_anchor_seconds = media_start_seconds
        self.transcript_vlc_clock_anchor_wall_time = time.monotonic()
        self.transcript_vlc_last_reported_seconds = None
        self.transcript_playhead_seconds = visual_start_seconds
        self.transcript_playback_active_segment_index = None

        if hasattr(self, "_center_transcript_timeline_pan_on_time"):
            self._center_transcript_timeline_pan_on_time(visual_start_seconds)

        self._sync_transcript_selection_to_playback_time(visual_start_seconds)
        self._refresh_transcript_timeline()

        self._update_transcript_playback_buttons(True)
        self._tick_transcript_timeline_playback()


    def pause_transcript_timeline(self) -> None:
        """Pause transcript timeline playback at the current marker."""
        current_seconds = self._update_transcript_playhead_from_playback_clock()

        if current_seconds is not None:
            self._sync_transcript_selection_to_playback_time(current_seconds)

        after_id = getattr(self, "transcript_playback_after_id", None)

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
        self._refresh_transcript_timeline()


    def _update_transcript_playhead_from_playback_clock(self) -> Optional[float]:
        """Update playhead from VLC's media clock, with sync offset and monotonic smoothing."""
        backend = getattr(self, "transcript_playback_backend", None)

        if backend not in {"vlc", "vlc_paused"}:
            return None

        player = getattr(self, "transcript_vlc_player", None)

        if player is None:
            return None

        now = time.monotonic()

        try:
            raw_ms = player.get_time()
        except Exception:
            raw_ms = -1

        raw_media_seconds = None

        if raw_ms is not None and raw_ms >= 0:
            raw_media_seconds = raw_ms / 1000.0

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
            media_seconds = float(anchor_media_seconds) + max(0.0, now - float(anchor_wall))
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

        if hasattr(self, "transcript_cursor_status_label"):
            self.transcript_cursor_status_label.configure(
                text=f"Playing: {self._format_timeline_time(current_seconds)}",
                text_color=COLORS["accent"]
            )

        return current_seconds


    def _tick_transcript_timeline_playback(self) -> None:
        """Move playhead marker smoothly while VLC is playing."""
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

                if zoom_level > 1.05 and hasattr(self, "_center_transcript_timeline_pan_on_time"):
                    self._center_transcript_timeline_pan_on_time(current_seconds)

            self._refresh_transcript_timeline()

            self.transcript_playback_after_id = self.after(
                25,
                self._tick_transcript_timeline_playback
            )
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

        sync_offset = self._get_transcript_audio_sync_offset_seconds()
        media_seconds = max(0.0, seconds - sync_offset)
        self.transcript_vlc_clock_anchor_seconds = media_seconds
        self.transcript_vlc_clock_anchor_wall_time = time.monotonic()
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
        """Move playhead marker when the timeline background is clicked."""
        seconds = self._timeline_canvas_event_to_seconds(event)

        if seconds is None:
            return

        self._set_transcript_playhead_time(seconds, refresh=True)

    def _on_transcript_timeline_canvas_drag(self, event) -> None:
        """Scrub playhead marker while dragging over the timeline."""
        seconds = self._timeline_canvas_event_to_seconds(event)

        if seconds is None:
            return

        self._set_transcript_playhead_time(seconds, refresh=True)

    def _on_transcript_timeline_canvas_release(self, event) -> None:
        """Finalize playhead marker position after dragging."""
        seconds = self._timeline_canvas_event_to_seconds(event)

        if seconds is None:
            return

        self._set_transcript_playhead_time(seconds, refresh=True)


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

        full_duration = max(1.0, full_max_time - full_min_time)
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
            peak_position = int(
                ((time_at_x - full_min_time) / full_duration)
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


    def _get_transcript_timeline_bounds(self):
        """Return min/max seconds for transcript timeline drawing."""
        times = []

        for segment in self.transcript_segments:
            start_seconds = self._transcript_time_to_seconds(segment.start)
            end_seconds = self._transcript_time_to_seconds(segment.end)

            if start_seconds is not None:
                times.append(start_seconds)

            if end_seconds is not None:
                times.append(end_seconds)

        if not times:
            return None, None

        min_time = min(times)
        max_time = max(times)

        if max_time <= min_time:
            max_time = min_time + 1.0

        return min_time, max_time

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



    def _set_transcript_timeline_pan_slider(self, fraction: float) -> None:
        """Update pan slider without causing a second redraw loop."""
        fraction = max(0.0, min(1.0, float(fraction)))
        self.transcript_timeline_pan_fraction = fraction

        if not hasattr(self, "transcript_timeline_pan_slider"):
            return

        try:
            self._updating_transcript_timeline_pan_slider = True
            self.transcript_timeline_pan_slider.set(fraction * 100.0)
        finally:
            self._updating_transcript_timeline_pan_slider = False


    def _center_transcript_timeline_pan_on_time(self, center_time: float) -> None:
        """Center the zoomed timeline view around a specific time."""
        min_time, max_time = self._get_transcript_timeline_bounds()

        if min_time is None or max_time is None:
            self._set_transcript_timeline_pan_slider(0.0)
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
            self._set_transcript_timeline_pan_slider(0.0)
            return

        visible_duration = max(1.0, full_duration / zoom_level)
        max_pan_seconds = max(0.0, full_duration - visible_duration)

        if max_pan_seconds <= 0:
            self._set_transcript_timeline_pan_slider(0.0)
            return

        center_time = max(min_time, min(max_time, center_time))
        visible_min = center_time - visible_duration / 2
        fraction = (visible_min - min_time) / max_pan_seconds

        self._set_transcript_timeline_pan_slider(fraction)

    def _keep_transcript_playhead_visible(self, seconds: float) -> None:
        """Auto-pan during playback so the blue marker stays visible without hard jumps."""
        view = getattr(self, "_transcript_timeline_view", None)

        if not view:
            self._center_transcript_timeline_pan_on_time(seconds)
            return

        try:
            seconds = float(seconds)
            visible_min = float(view.get("min_time"))
            visible_max = float(view.get("max_time"))
        except Exception:
            return

        visible_duration = max(0.001, visible_max - visible_min)
        right_guard = visible_min + visible_duration * 0.72
        left_guard = visible_min + visible_duration * 0.18

        # When playing forward, pan ahead only when the marker approaches the right side.
        if seconds > right_guard:
            target_center = seconds + visible_duration * 0.18
            self._center_transcript_timeline_pan_on_time(target_center)
        elif seconds < left_guard:
            target_center = seconds - visible_duration * 0.18
            self._center_transcript_timeline_pan_on_time(target_center)


    def _center_transcript_timeline_pan_on_selected(self) -> None:
        """Set pan fraction so the selected segment is near the middle when zooming."""
        min_time, max_time = self._get_transcript_timeline_bounds()

        if min_time is None or max_time is None:
            self._set_transcript_timeline_pan_slider(0.0)
            return

        full_duration = max(1.0, max_time - min_time)

        try:
            zoom_level = float(getattr(self, "transcript_timeline_zoom_level", 1.0))
        except Exception:
            zoom_level = 1.0

        zoom_level = max(1.0, min(10.0, zoom_level))

        if zoom_level <= 1.05:
            self._set_transcript_timeline_pan_slider(0.0)
            return

        playhead_seconds = getattr(self, "transcript_playhead_seconds", None)

        if isinstance(playhead_seconds, (int, float)):
            self._center_transcript_timeline_pan_on_time(float(playhead_seconds))
            return

        visible_duration = max(1.0, full_duration / zoom_level)
        max_pan_seconds = max(0.0, full_duration - visible_duration)

        if max_pan_seconds <= 0:
            self._set_transcript_timeline_pan_slider(0.0)
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
        self._set_transcript_timeline_pan_slider(fraction)

    def _on_transcript_timeline_pan_changed(self, value) -> None:
        """Pan the zoomed transcript timeline left/right."""
        if getattr(self, "_updating_transcript_timeline_pan_slider", False):
            return

        try:
            fraction = float(value) / 100.0
        except Exception:
            fraction = 0.0

        self.transcript_timeline_pan_fraction = max(0.0, min(1.0, fraction))
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
            self._set_transcript_timeline_pan_slider(0.0)

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
        self._set_transcript_timeline_pan_slider(0.0)

        if hasattr(self, "transcript_timeline_zoom_slider"):
            self.transcript_timeline_zoom_slider.set(1.0)

        if hasattr(self, "transcript_timeline_zoom_value_label"):
            self.transcript_timeline_zoom_value_label.configure(text="Zoom: Full")

        self._refresh_transcript_timeline()


    def _refresh_transcript_timeline(self) -> None:
        """Draw a simple timestamp-based transcript timeline."""
        if not hasattr(self, "transcript_timeline_canvas"):
            return

        canvas = self.transcript_timeline_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 300)

        if not self.transcript_segments:
            canvas.configure(height=70)
            canvas.create_text(
                14,
                34,
                text="Import a transcript to show timeline blocks.",
                anchor="w",
                fill=COLORS["text_muted"],
                font=("Cascadia Mono", 10)
            )
            return

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
            max_pan_seconds = max(0.0, full_duration - visible_duration)

            try:
                pan_fraction = float(getattr(self, "transcript_timeline_pan_fraction", 0.0))
            except Exception:
                pan_fraction = 0.0

            pan_fraction = max(0.0, min(1.0, pan_fraction))
            visible_min = full_min_time + max_pan_seconds * pan_fraction
            visible_max = visible_min + visible_duration

            min_time = max(full_min_time, visible_min)
            max_time = min(full_max_time, visible_max)

            if hasattr(self, "transcript_timeline_pan_label"):
                self.transcript_timeline_pan_label.configure(
                    text=f"Position: {pan_fraction * 100:.0f}%"
                )
        else:
            if hasattr(self, "transcript_timeline_pan_label"):
                self.transcript_timeline_pan_label.configure(text="Position: Full")

        speakers = self._get_timeline_speakers()
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
            "left_margin": left_margin,
            "right_margin": right_margin,
            "top_margin": top_margin,
            "bottom_margin": bottom_margin,
            "timeline_width": timeline_width,
            "canvas_height": canvas_height,
            "width": width,
            "duration": duration,
        }
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

        # Speaker lanes
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
            outline = "#FFFFFF" if is_selected else color
            outline_width = 2 if is_selected else 1

            tag = f"timeline_segment_{segment_index}"

            canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                outline=outline,
                width=outline_width,
                tags=(tag,)
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

        self.linked_transcript_media_path = new_media_path
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
            self._set_linked_transcript_media(None)
            self._refresh_transcript_display()
            self.evidence_button.configure(state="normal")

            self.log_message(
                f"Imported transcript: {len(segments):,} segment(s) from {os.path.basename(filename)}",
                "success"
            )

        except Exception as e:
            logger.exception("Transcript import error")
            self.log_message(f"Transcript import failed: {e}", "error")
            messagebox.showerror("Transcript Import Error", str(e))

    def download_youtube_transcript_clicked(self) -> None:
        """Download YouTube captions/transcript for the first URL in the Video URLs box."""
        urls = self._get_current_source_urls()

        if not urls:
            messagebox.showwarning(
                "No YouTube URL",
                "Paste a YouTube video URL into the Video URLs box first."
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

                api_key = self.api_key_entry.get().strip()

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
                        text="⬇ YouTube"
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
        )

        self.log_message(
            "Saved Local ASR defaults: "
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


    def local_asr_transcribe_clicked(self) -> None:
        """Transcribe a local audio/video file using faster-whisper."""
        asr_defaults = load_asr_defaults()

        asr_settings = ask_asr_settings(
            self,
            asr_defaults,
            title="Local ASR",
            action_label="Start ASR",
        )

        if not asr_settings:
            return

        model_name = asr_settings.get("model_name", "small").strip().lower() or "small"
        speaker_name = asr_settings.get("speaker_name", "Speaker 1").strip() or "Speaker 1"
        language_code = asr_settings.get("language", "").strip() or None
        initial_prompt = asr_settings.get("initial_prompt", "").strip() or None
        device = asr_settings.get("device", "cpu").strip().lower() or "cpu"
        compute_type = asr_settings.get("compute_type", "int8").strip() or "int8"

        try:
            probe_seconds = int(asr_settings.get("probe_seconds") or 0)
        except Exception:
            probe_seconds = 0

        asr_mode_label = f"probe first {probe_seconds}s" if probe_seconds else "full transcription"

        linked_media_file = getattr(self, "linked_transcript_media_path", None)

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

            media_file = filedialog.askopenfilename(
                title=f"Choose audio or video file for Local ASR {asr_mode_label}",
                filetypes=[
                    ("Media files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.mp4 *.mkv *.webm *.mov *.avi"),
                    ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                    ("Video files", "*.mp4 *.mkv *.webm *.mov *.avi"),
                    ("All files", "*.*"),
                ],
            )

        if not media_file:
            return

        save_asr_defaults(
            model_name=model_name,
            speaker_name=speaker_name,
            language=language_code or "",
            initial_prompt=initial_prompt or "",
            device=device,
            compute_type=compute_type,
        )

        self.transcript_asr_button.configure(state="disabled")
        self.log_message(
            f"Starting local ASR {asr_mode_label} with faster-whisper model: {model_name} "
            f"({device}/{compute_type})",
            "info"
        )

        def worker() -> None:
            try:
                segments, metadata = transcribe_media_file(
                    media_file,
                    model_name=model_name,
                    device=device,
                    compute_type=compute_type,
                    speaker_name=speaker_name,
                    language=language_code,
                    initial_prompt=initial_prompt,
                    vad_filter=True,
                    beam_size=5,
                    probe_seconds=probe_seconds,
                )

                def on_success() -> None:
                    self.transcript_segments = segments
                    self.last_youtube_video_info = None
                    self.last_asr_metadata = metadata
                    self._set_linked_transcript_media(media_file)

                    prompt_note = " with phrase hints" if initial_prompt else ""
                    language_note = f", language={language_code}" if language_code else ", language=auto-detect"
                    probe_note = f"probe first {probe_seconds}s " if probe_seconds else ""

                    self.last_transcript_source = (
                        f"Local ASR {probe_note}transcript from {os.path.basename(media_file)} "
                        f"using faster-whisper {model_name}{language_note}{prompt_note}"
                    )

                    self._refresh_transcript_display()
                    self.evidence_button.configure(state="normal")

                    language = metadata.get("language") or "unknown"
                    probability = metadata.get("language_probability")

                    if probability is not None:
                        probability_text = f"{probability:.2%}"
                    else:
                        probability_text = "unknown"

                    self.log_message(
                        f"Local ASR {'probe ' if probe_seconds else ''}complete: {len(segments):,} segment(s), "
                        f"language={language}, confidence={probability_text}",
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

                    if probe_seconds:
                        completion_title = "Local ASR Probe Complete"
                        completion_message = (
                            f"Probe transcribed first {probe_seconds} seconds:\n\n"
                            f"{os.path.basename(media_file)}\n\n"
                            f"Segments: {len(segments):,}\n"
                            f"Detected language: {language}\n"
                            f"Language confidence: {probability_text}\n\n"
                            "Review the probe transcript. If it is acceptable, run full Local ASR."
                        )
                    else:
                        completion_title = "Local ASR Complete"
                        completion_message = (
                            f"Transcribed file:\n\n{os.path.basename(media_file)}\n\n"
                            f"Segments: {len(segments):,}\n"
                            f"Detected language: {language}\n"
                            f"Language confidence: {probability_text}"
                        )

                    messagebox.showinfo(completion_title, completion_message)

                self.after(0, on_success)

            except Exception as error:
                logger.exception("Local ASR error")
                error_text = str(error)

                def on_error() -> None:
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
            if export_type == "txt":
                self._export_readable_transcript_txt(self.transcript_segments, filename)
            else:
                exporter(self.transcript_segments, filename)

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

        self._stop_transcript_playback_process()
        self._update_transcript_playback_buttons(False)
        self.transcript_segments = []
        self.transcript_playhead_seconds = None
        self.last_transcript_source = None
        self._set_linked_transcript_media(None)
        self._refresh_transcript_display()
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
