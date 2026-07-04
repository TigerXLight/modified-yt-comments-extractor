"""
YouTube Comment Extractor - Desktop Application.

A modern GUI application for extracting, filtering, and analyzing
YouTube comments with advanced spam detection.
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
import webbrowser
from dataclasses import dataclass
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Dict, List, Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw

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
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
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
        self.last_transcript_source: Optional[str] = None
        self.last_youtube_video_info: Optional[Dict[str, Any]] = None
        self.last_asr_metadata: Optional[Dict[str, Any]] = None
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
            font=ctk.CTkFont(size=12),
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

        self.transcript_asr_button = ctk.CTkButton(
            button_row,
            text="🎙 Local ASR",
            command=self.local_asr_transcribe_clicked,
            width=110,
            fg_color="#7C3AED",
            hover_color="#6D28D9",
        )
        self.transcript_asr_button.pack(side="left", padx=3, pady=3)

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
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            wrap="word"
        )
        self.transcript_textbox.pack(fill="x", padx=15, pady=(0, 15))
        self.transcript_display_ranges = []
        self.selected_transcript_segment_index = None

        transcript_text_widget = self._get_transcript_text_widget()
        transcript_text_widget.configure(
            insertbackground="#FFFFFF",
            insertwidth=2,
            insertofftime=300,
            insertontime=600
        )
        transcript_text_widget.bind("<ButtonRelease-1>", self._on_transcript_preview_cursor_changed)
        transcript_text_widget.bind("<KeyPress>", self._on_transcript_preview_key_press)
        transcript_text_widget.bind("<KeyRelease>", self._on_transcript_preview_cursor_changed)

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

    def clear_log(self) -> None:
        """Clear the activity log."""
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
        color = LOG_COLORS.get(level, COLORS["text_secondary"])
        icon = LOG_ICONS.get(level, "→")

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

    def _refresh_transcript_display(self) -> None:
        """Refresh transcript preview, stats, and inline editor mapping."""
        has_transcript = len(self.transcript_segments) > 0
        state = "normal" if has_transcript else "disabled"

        self._set_transcript_buttons_state(state)

        if hasattr(self, "transcript_search_entry"):
            self.transcript_search_entry.configure(state=state)

        self.transcript_display_ranges = []
        self.selected_transcript_segment_index = None

        if hasattr(self, "transcript_cursor_status_label"):
            if has_transcript:
                self.transcript_cursor_status_label.configure(
                    text="Click inside the transcript to select a segment.",
                    text_color=COLORS["text_muted"]
                )
            else:
                self.transcript_cursor_status_label.configure(
                    text="No transcript segment selected.",
                    text_color=COLORS["text_muted"]
                )

        self.transcript_textbox.configure(state="normal")
        self.transcript_textbox.delete("1.0", "end")

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

        for segment_index, segment in enumerate(self.transcript_segments):
            if chars_written >= preview_char_limit:
                truncated = True
                break

            speaker = segment.speaker or "Speaker"
            start_time = segment.start or "no start"
            end_time = segment.end or "no end"
            text = segment.text or ""

            segment_start_index = self.transcript_textbox.index("end-1c")

            if show_speakers:
                self.transcript_textbox.insert("end", f"{speaker}\n")

            segment_text_start_index = self.transcript_textbox.index("end-1c")

            for paragraph in self._split_readable_text(text):
                remaining_chars = preview_char_limit - chars_written

                if remaining_chars <= 0:
                    truncated = True
                    break

                if len(paragraph) > remaining_chars:
                    self.transcript_textbox.insert("end", paragraph[:remaining_chars].rstrip())
                    self.transcript_textbox.insert("end", "...\n\n")
                    chars_written += remaining_chars
                    truncated = True
                    break

                self.transcript_textbox.insert("end", paragraph)
                self.transcript_textbox.insert("end", "\n\n")
                chars_written += len(paragraph)

            segment_text_end_index = self.transcript_textbox.index("end-1c")

            if show_timestamps:
                self.transcript_textbox.insert("end", f"[{start_time} - {end_time}]\n\n")

            segment_end_index = self.transcript_textbox.index("end-1c")

            self.transcript_display_ranges.append({
                "segment_index": segment_index,
                "start": segment_start_index,
                "end": segment_end_index,
                "text_start": segment_text_start_index,
                "text_end": segment_text_end_index,
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


    def _on_transcript_preview_key_press(self, event=None):
        """Keep transcript preview focusable while blocking accidental text edits."""
        if event is None:
            return None

        allowed_navigation_keys = {
            "Left", "Right", "Up", "Down",
            "Home", "End", "Prior", "Next",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Escape",
        }

        # Allow Ctrl+C / Ctrl+A style shortcuts.
        ctrl_pressed = bool(getattr(event, "state", 0) & 0x4)
        if ctrl_pressed:
            return None

        if getattr(event, "keysym", "") in allowed_navigation_keys:
            return None

        if getattr(event, "keysym", "") in {"Return", "KP_Enter"}:
            self._split_selected_transcript_segment_at_cursor()
            return "break"

        blocked_edit_keys = {
            "BackSpace", "Delete", "Tab",
        }

        if getattr(event, "keysym", "") in blocked_edit_keys:
            return "break"

        # Block normal printable typing so preview text is not accidentally changed.
        if getattr(event, "char", ""):
            return "break"

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
                f.write(f"Source: {self.last_transcript_source}\n\n")

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

    def local_asr_transcribe_clicked(self) -> None:
        """Transcribe a local audio/video file using faster-whisper."""
        media_file = filedialog.askopenfilename(
            title="Choose audio or video file for local ASR",
            filetypes=[
                ("Media files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.mp4 *.mkv *.webm *.mov *.avi"),
                ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
                ("Video files", "*.mp4 *.mkv *.webm *.mov *.avi"),
                ("All files", "*.*"),
            ],
        )

        if not media_file:
            return

        asr_defaults = load_asr_defaults()

        model_name = simpledialog.askstring(
            "ASR Model",
            "Choose faster-whisper model:\n\n"
            "tiny = fastest, weakest accuracy\n"
            "base = fast, basic accuracy\n"
            "small = better accuracy, slower\n"
            "medium = better again, much slower on CPU",
            initialvalue=asr_defaults.get("model_name", "small"),
            parent=self,
        )

        if model_name is None:
            return

        model_name = model_name.strip().lower() or "base"

        allowed_models = {"tiny", "base", "small", "medium"}
        if model_name not in allowed_models:
            messagebox.showerror(
                "Invalid ASR Model",
                "Please choose one of:\n\n"
                "tiny\nbase\nsmall\nmedium"
            )
            return

        speaker_name = simpledialog.askstring(
            "Speaker Label",
            "Speaker label to use for this ASR transcript:",
            initialvalue=asr_defaults.get("speaker_name", "Speaker 1"),
            parent=self,
        )

        if speaker_name is None:
            return

        speaker_name = speaker_name.strip() or "Speaker 1"

        language_code = simpledialog.askstring(
            "ASR Language",
            "Optional language code.\n\n"
            "Leave blank for auto-detect.\n"
            "Examples: en, ar, fr, de, es",
            initialvalue=asr_defaults.get("language", "en"),
            parent=self,
        )

        if language_code is None:
            return

        language_code = language_code.strip() or None

        initial_prompt = simpledialog.askstring(
            "ASR Known Words",
            "Optional known names/terms/context.\n\n"
            "This can improve unusual names, usernames, game terms, or repeated phrases.\n\n"
            "Example:\n"
            "Freckelston, Kingman, ZoneX, Nyxara, Caltheris, BLACKED, Nicolas Cage",
            initialvalue=asr_defaults.get("initial_prompt", ""),
            parent=self,
        )

        if initial_prompt is None:
            return

        initial_prompt = initial_prompt.strip() or None

        save_asr_defaults(
            model_name=model_name,
            speaker_name=speaker_name,
            language=language_code or "",
            initial_prompt=initial_prompt or "",
        )

        self.transcript_asr_button.configure(state="disabled")
        self.log_message(
            f"Starting local ASR with faster-whisper model: {model_name}",
            "info"
        )

        def worker() -> None:
            try:
                segments, metadata = transcribe_media_file(
                    media_file,
                    model_name=model_name,
                    device="cpu",
                    compute_type="int8",
                    speaker_name=speaker_name,
                    language=language_code,
                    initial_prompt=initial_prompt,
                    vad_filter=True,
                    beam_size=5,
                )

                def on_success() -> None:
                    self.transcript_segments = segments
                    self.last_youtube_video_info = None
                    self.last_asr_metadata = metadata
                    prompt_note = " with known-words prompt" if initial_prompt else ""
                    language_note = f", language={language_code}" if language_code else ", language=auto-detect"

                    self.last_transcript_source = (
                        f"Local ASR transcript from {os.path.basename(media_file)} "
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
                        f"Local ASR complete: {len(segments):,} segment(s), "
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
                        f"known words prompt={prompt_used}, "
                        f"source hash={source_hash_short}",
                        "muted",
                    )

                    messagebox.showinfo(
                        "Local ASR Complete",
                        f"Transcribed file:\n\n{os.path.basename(media_file)}\n\n"
                        f"Segments: {len(segments):,}\n"
                        f"Detected language: {language}\n"
                        f"Language confidence: {probability_text}",
                    )

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


    def edit_transcript_segment_speaker(self) -> None:
        """Edit the speaker label for one transcript segment only."""
        if not self.transcript_segments:
            messagebox.showwarning(
                "No Transcript",
                "Import a transcript first."
            )
            return

        dialog_width = 900
        dialog_height = 660

        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Segment Speaker")
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
            text="✏ Edit One Segment Speaker",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 2))

        help_text = ctk.CTkLabel(
            container,
            text="Search or scroll the segment list, then choose a speaker for that one segment only.",
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
        details_panel.grid_rowconfigure(6, weight=1)

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

        speaker_entry.grid(row=4, column=0, sticky="ew", pady=(0, 12))

        preview_label = ctk.CTkLabel(
            details_panel,
            text="Preview",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        preview_label.grid(row=5, column=0, sticky="w", pady=(0, 4))

        preview_textbox = ctk.CTkTextbox(
            details_panel,
            height=210,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_input"],
            border_color=COLORS["border"],
            border_width=1,
            corner_radius=8,
            wrap="word"
        )
        preview_textbox.grid(row=6, column=0, sticky="nsew", pady=(0, 12))

        button_row = ctk.CTkFrame(details_panel, fg_color="transparent")
        button_row.grid(row=7, column=0, sticky="ew")

        selected_state = {
            "index": self.selected_transcript_segment_index
            if isinstance(getattr(self, "selected_transcript_segment_index", None), int)
            and 0 <= self.selected_transcript_segment_index < len(self.transcript_segments)
            else 0,
            "filtered": [],
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

        def do_update() -> None:
            index = selected_state["index"]
            segment = self.transcript_segments[index]

            old_speaker = segment.speaker or "Speaker"
            new_speaker = speaker_entry.get().strip()

            if not new_speaker:
                messagebox.showwarning(
                    "Missing Speaker",
                    "Enter a speaker name for this segment."
                )
                return

            if new_speaker == old_speaker:
                messagebox.showinfo(
                    "No Change",
                    "The speaker name is already the same for this segment."
                )
                return

            self._ensure_transcript_custom_speakers()
            self.transcript_custom_speakers.add(new_speaker)

            segment.speaker = new_speaker

            self._refresh_transcript_display()
            load_selected_segment_details()
            rebuild_segment_list()

            self.log_message(
                f"Changed segment {index + 1:,} speaker: '{old_speaker}' → '{new_speaker}'",
                "success"
            )

        close_btn = ctk.CTkButton(
            button_row,
            text="Close",
            command=dialog.destroy,
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

        search_var.trace_add("write", on_search_changed)
        segment_search_entry.bind("<KeyRelease>", lambda _event: rebuild_segment_list(force_first_match=True))
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
        self.last_transcript_source = None
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
