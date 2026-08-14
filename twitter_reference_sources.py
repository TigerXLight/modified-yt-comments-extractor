from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


TWITTER_REFERENCE_SOURCES_SCHEMA_VERSION = "twitter_reference_sources.v68b"


@dataclass(frozen=True)
class TwitterReferenceSource:
    reference_id: str
    display_name: str
    source_kind: str
    reference_url: str = ""
    local_path: str = ""
    extension_id: str = ""
    version: str = ""
    implementation_area: str = ""
    implementation_use: str = ""
    reuse_status: str = "reference_and_reimplement_in_ytce"
    host_permissions: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    relevant_patterns: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class TwitterReferenceRegistry:
    schema_version: str
    references: tuple[TwitterReferenceSource, ...]

    @property
    def reference_count(self) -> int:
        return len(self.references)

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["reference_count"] = self.reference_count
        return data


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _read_json_file(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inspect_chromium_extension_manifest(extension_root: str | Path) -> dict[str, Any]:
    """Return manifest metadata for a local Chromium extension folder.

    The caller uses this for implementation reference and compatibility checks.
    It does not execute extension JavaScript, open a browser, or read profile cookies.
    """
    root = Path(extension_root)
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found under {root}")
    manifest = dict(_read_json_file(manifest_path))
    content_scripts = manifest.get("content_scripts") or ()
    return {
        "name": manifest.get("name", ""),
        "version": manifest.get("version", ""),
        "description": manifest.get("description", ""),
        "homepage_url": manifest.get("homepage_url", ""),
        "permissions": tuple(str(item) for item in manifest.get("permissions", ()) or ()),
        "optional_permissions": tuple(str(item) for item in manifest.get("optional_permissions", ()) or ()),
        "host_permissions": tuple(str(item) for item in manifest.get("host_permissions", ()) or ()),
        "content_script_matches": tuple(
            match
            for item in content_scripts
            for match in tuple(item.get("matches", ()) or ())
        ),
        "content_script_files": tuple(
            script
            for item in content_scripts
            for script in tuple(item.get("js", ()) or ())
        ),
        "background_service_worker": str((manifest.get("background") or {}).get("service_worker", "")),
        "default_popup": str((manifest.get("action") or {}).get("default_popup", "")),
        "default_title": str((manifest.get("action") or {}).get("default_title", "")),
    }


def twitter_reference_sources() -> tuple[TwitterReferenceSource, ...]:
    """Reference map for building YTCE-owned X/Twitter capture/media implementation.

    These entries are deliberately implementation-oriented: they identify which
    source is useful for route discovery, media detection, exporter shape,
    browser automation, local storage capture, post-processing, or UI behaviour.
    """
    return (
        TwitterReferenceSource(
            reference_id="twitter_exporter_rxliuli_chromium_extension",
            display_name="Twitter Exporter",
            source_kind="local_chromium_extension_and_store_listing",
            reference_url="https://chromewebstore.google.com/detail/twitter-exporter/lnklhjfbeicncichppfbhjijodjgaejm",
            local_path=r"C:\Users\fahad\AppData\Local\Microsoft\Edge\User Data\Default\Extensions\lnklhjfbeicncichppfbhjijodjgaejm\0.8.58\_0",
            extension_id="lnklhjfbeicncichppfbhjijodjgaejm",
            version="0.8.58",
            implementation_area="twitter_export_graphql_and_media_fields",
            implementation_use=(
                "Reference for X/Twitter export task shapes, GraphQL endpoint naming, background processing, "
                "rate-limit handling, record flattening, media_url/video_info extraction, and local export output shapes."
            ),
            host_permissions=("https://x.com/**", "https://api.x.com/**", "https://ton.x.com/**"),
            permissions=("cookies", "notifications", "alarms", "idle", "declarativeNetRequest", "activeTab", "scripting"),
            relevant_patterns=("TweetDetail", "UserTweets", "UserMedia", "SearchTimeline", "Bookmarks", "media_url_https", "video_info", "x-csrf-token", "ct0"),
            notes="Primary local source for reverse-engineering YTCE-owned Twitter/X export and media-field handling.",
        ),
        TwitterReferenceSource(
            reference_id="twitter_filter_skills_rxliuli",
            display_name="twitter-filter-skills / twitter-filter-rules",
            source_kind="github_and_prompt_reference",
            reference_url="https://github.com/rxliuli/twitter-filter-skills",
            implementation_area="browser_automation_rule_generation",
            implementation_use=(
                "Reference for Claude/browser-assisted inspection of tweet/profile URLs, extracting account stats and reply patterns, "
                "and generating deterministic filter/review rules from examples."
            ),
            relevant_patterns=("twitter-filter-rules", "Claude", "logged-in browser", "account stats", "reply patterns", "filter rules"),
            notes="Useful for later rule-generation and review triage, not the media-download core.",
        ),
        TwitterReferenceSource(
            reference_id="twitter_filter_rxliuli_store",
            display_name="Twitter Filter",
            source_kind="store_and_extension_reference",
            reference_url="https://store.rxliuli.com/extensions/twitter-filter/",
            implementation_area="api_response_interception_and_rule_engine",
            implementation_use=(
                "Reference for intercepting Twitter/X API responses, extracting tweet/user data, evaluating expression rules, "
                "and applying mark/hide/block style local actions."
            ),
            relevant_patterns=("intercepts Twitter API responses", "tweet fields", "user fields", "expression language", "mark", "hide", "block", "community rules"),
        ),
        TwitterReferenceSource(
            reference_id="clean_twitter_rxliuli_store",
            display_name="Clean Twitter",
            source_kind="store_and_extension_reference",
            reference_url="https://store.rxliuli.com/extensions/clean-twitter/",
            implementation_area="dom_cleanup_for_capture_and_review",
            implementation_use=(
                "Reference for DOM/UI cleanup before screenshot/review capture: remove sidebars, promotions, navigation clutter, "
                "Grok buttons, recommendations, ads, and other non-evidence chrome."
            ),
            relevant_patterns=("remove sidebar", "hide ads", "hide recommendations", "hide Grok", "text mode", "navigation cleanup"),
        ),
        TwitterReferenceSource(
            reference_id="xkit_rxliuli",
            display_name="xkit",
            source_kind="github_and_site_reference",
            reference_url="https://github.com/rxliuli/xkit",
            implementation_area="twitter_network_analysis",
            implementation_use="Reference for X/Twitter network interaction analysis, interaction circles, and later source-context analytics.",
            relevant_patterns=("interaction circle", "network interaction", "sentiment", "topic trend", "influence"),
        ),
        TwitterReferenceSource(
            reference_id="twitter_openapi_rxliuli_or_fa0311",
            display_name="twitter-openapi",
            source_kind="github_reference",
            reference_url="https://github.com/rxliuli/twitter-openapi",
            implementation_area="twitter_internal_api_schema",
            implementation_use="Reference for X/Twitter internal GraphQL/OpenAPI route naming and response model structure.",
            relevant_patterns=("TweetDetail", "UserTweets", "UserMedia", "UserTweetsAndReplies", "SearchTimeline", "OpenAPI", "Swagger", "graphql"),
        ),
        TwitterReferenceSource(
            reference_id="ffmpeg_online_rxliuli",
            display_name="ffmpeg-online",
            source_kind="github_reference",
            reference_url="https://github.com/rxliuli/ffmpeg-online",
            implementation_area="browser_media_post_processing_reference",
            implementation_use="Reference for browser/WASM ffmpeg UX and conversion flow; desktop YTCE can keep native ffmpeg for actual post-processing.",
            relevant_patterns=("ffmpeg.wasm", "audio", "video", "convert", "browser"),
        ),
        TwitterReferenceSource(
            reference_id="webdatamaster_rxliuli",
            display_name="WebDataMaster",
            source_kind="github_and_store_reference",
            reference_url="https://github.com/rxliuli/WebDataMaster",
            implementation_area="browser_storage_export_import",
            implementation_use=(
                "Reference for exporting/importing local website data such as cookies, localStorage, sessionStorage and IndexedDB. "
                "Useful for optional browser-state diagnostics/import tooling with explicit user control."
            ),
            relevant_patterns=("Cookies", "localStorage", "sessionStorage", "IndexedDB", "import", "export"),
        ),
        TwitterReferenceSource(
            reference_id="google_translate_api_free_rxliuli",
            display_name="google-translate-api-free",
            source_kind="github_reference",
            reference_url="https://github.com/rxliuli/google-translate-api-free",
            implementation_area="optional_translation_reference",
            implementation_use="Reference for later optional translation helpers for captured tweets/articles; not part of media download.",
            relevant_patterns=("translate", "Google Translate", "text"),
        ),
        TwitterReferenceSource(
            reference_id="twitter_web_exporter_prinsss",
            display_name="twitter-web-exporter",
            source_kind="github_reference",
            reference_url="https://github.com/prinsss/twitter-web-exporter",
            implementation_area="web_exporter_capture_storage",
            implementation_use="Reference for browser-based export of tweets, bookmarks, lists, users, media fields, storage and export formats.",
            relevant_patterns=("tweets", "bookmarks", "lists", "users", "media", "export", "database"),
        ),
        TwitterReferenceSource(
            reference_id="web_exporter_eight04",
            display_name="web-exporter",
            source_kind="github_reference",
            reference_url="https://github.com/eight04/web-exporter",
            implementation_area="generic_webextension_export_framework",
            implementation_use="Reference for adapting a twitter-web-exporter style webextension to multiple sites and media/data exports.",
            relevant_patterns=("webextension", "export data", "media", "websites", "adapters"),
        ),
        TwitterReferenceSource(
            reference_id="x_article_exporter_annismckenzie",
            display_name="x-article-exporter",
            source_kind="github_reference",
            reference_url="https://github.com/annismckenzie/x-article-exporter",
            implementation_area="x_article_pdf_http_mcp_export",
            implementation_use="Reference for X/Twitter long-form article extraction/export, PDF rendering, optional translation, HTTP API, and MCP server shape.",
            relevant_patterns=("article", "PDF", "translation", "dark mode", "HTTP API", "MCP server"),
        ),
        TwitterReferenceSource(
            reference_id="video_download_helper_chromium_extension",
            display_name="Video Download Helper",
            source_kind="local_chromium_extension_and_store_listing",
            reference_url="https://chromewebstore.google.com/detail/video-download-helper/lmjnegcaeklhafolokijcfjliaokphfk",
            local_path=r"C:\Users\fahad\AppData\Local\Google\Chrome\User Data\Profile 1\Extensions\lmjnegcaeklhafolokijcfjliaokphfk\10.5.24.2\_0",
            extension_id="lmjnegcaeklhafolokijcfjliaokphfk",
            version="10.5.24.2",
            implementation_area="browser_media_discovery_and_download_worker",
            implementation_use=(
                "Reference for browser media discovery structure: site-specific injected scripts, isolated/main-world split, "
                "webRequest/webNavigation observation, download worker, libav/ffmpeg worker, and external helper boundary."
            ),
            host_permissions=("<all_urls>",),
            permissions=("tabs", "offscreen", "downloads", "sidePanel", "webRequest", "webNavigation", "scripting", "declarativeNetRequest", "storage", "notifications", "contextMenus", "unlimitedStorage"),
            relevant_patterns=("content_scripts", "webRequest", "webNavigation", "m3u8", "mpd", "download_worker", "libav", "ffmpeg"),
        ),
        TwitterReferenceSource(
            reference_id="vdhcoapp_aclap",
            display_name="DownloadHelper CoApp",
            source_kind="github_reference",
            reference_url="https://github.com/aclap-dev/vdhcoapp/",
            implementation_area="native_helper_file_writer_ffmpeg_boundary",
            implementation_use="Reference for a native messaging companion app that provides file writing, default-player launching and ffmpeg conversion outside the browser sandbox.",
            relevant_patterns=("native messaging", "file writing API", "ffmpeg", "coapp", "helper"),
        ),
        TwitterReferenceSource(
            reference_id="vdhcoapp_releases_aclap",
            display_name="DownloadHelper CoApp releases",
            source_kind="github_release_reference",
            reference_url="https://github.com/aclap-dev/vdhcoapp/releases",
            implementation_area="native_helper_distribution_reference",
            implementation_use="Reference for installer/release packaging of a browser-helper companion application.",
            relevant_patterns=("installer", "release", "Windows", "Mac", "Linux", "native helper"),
        ),
        TwitterReferenceSource(
            reference_id="aclap_dev_org",
            display_name="aclap-dev organization",
            source_kind="github_org_reference",
            reference_url="https://github.com/aclap-dev",
            implementation_area="video_downloadhelper_project_family",
            implementation_use="Reference index for Video DownloadHelper related repositories; vdhcoapp is the current useful implementation target.",
            relevant_patterns=("Video DownloadHelper", "coapp", "native messaging"),
        ),
        TwitterReferenceSource(
            reference_id="video_downloader_professional_chromium_extension",
            display_name="Video Downloader Professional",
            source_kind="local_chromium_extension_and_store_listing",
            reference_url="https://chromewebstore.google.com/detail/video-downloader-professi/elicpjhcidhpjomhibiffojpinpmmpil",
            local_path=r"C:\Users\fahad\AppData\Local\Google\Chrome\User Data\Profile 1\Extensions\elicpjhcidhpjomhibiffojpinpmmpil\2.1.7\_0",
            extension_id="elicpjhcidhpjomhibiffojpinpmmpil",
            version="2.1.7",
            implementation_area="lightweight_media_sniffer_reference",
            implementation_use="Reference for a lighter content-script plus webRequest/downloads media discovery path.",
            host_permissions=("https://*/*",),
            permissions=("sidePanel", "webRequest", "downloads", "tabs", "storage"),
            relevant_patterns=("content.js", "webRequest", "m3u8", "downloads", "sidePanel"),
        ),
        TwitterReferenceSource(
            reference_id="video_downloader_pro_alasim",
            display_name="video-downloader-pro",
            source_kind="github_or_npm_reference",
            reference_url="https://github.com/alasim/video-downloader-pro",
            implementation_area="generic_media_download_library_reference",
            implementation_use="Reference for generic media-download package structure and site/backend routing ideas.",
            relevant_patterns=("download any media", "npm", "media content", "website"),
        ),
        TwitterReferenceSource(
            reference_id="seal_android_video_downloader",
            display_name="Seal Android video downloader",
            source_kind="fdroid_reference",
            reference_url="https://f-droid.org/packages/com.junkfood.seal/",
            implementation_area="downloader_ux_backend_reference",
            implementation_use="Reference for downloader UX, queueing and backend-routing ideas outside desktop Chrome/Edge.",
            relevant_patterns=("Android", "media download", "yt-dlp", "queue"),
        ),
        TwitterReferenceSource(
            reference_id="youtube_js_paulrouget",
            display_name="YouTube.js / InnerTube client",
            source_kind="github_reference",
            reference_url="https://github.com/paulrouget/YouTube.js",
            implementation_area="youtube_private_api_reference",
            implementation_use="Reference for YouTube InnerTube client patterns; not a Twitter/X media route, but relevant to YTCE's YouTube source adapter architecture.",
            relevant_patterns=("InnerTube", "videos", "comments", "live chats", "streaming data"),
        ),
        TwitterReferenceSource(
            reference_id="libav_js_paulrouget",
            display_name="libav.js",
            source_kind="github_reference",
            reference_url="https://github.com/paulrouget/libav.js",
            implementation_area="media_processing_wasm_reference",
            implementation_use="Reference for FFmpeg/libav libraries compiled to WebAssembly/asm.js and licensing-aware media processing.",
            relevant_patterns=("libavformat", "libavcodec", "libavfilter", "ffmpeg", "ffprobe", "WebAssembly", "licensing"),
        ),
        TwitterReferenceSource(
            reference_id="webcc_paulrouget",
            display_name="WebCC",
            source_kind="github_reference_low_priority",
            reference_url="https://github.com/paulrouget/webcc",
            implementation_area="wasm_ui_toolchain_reference_low_priority",
            implementation_use="Low-priority reference for C++/WASM bridge ideas; not needed for immediate Twitter/X backend path.",
            relevant_patterns=("C++", "WebAssembly", "DOM", "Canvas", "WebGL", "WebGPU", "Audio"),
        ),
        TwitterReferenceSource(
            reference_id="console_gui_tools_paulrouget",
            display_name="console-gui-tools",
            source_kind="github_reference_low_priority",
            reference_url="https://github.com/paulrouget/console-gui-tools",
            implementation_area="cli_wizard_reference_low_priority",
            implementation_use="Low-priority reference for CLI wizard UI patterns; potentially useful for future dev tools, not media capture.",
            relevant_patterns=("console", "wizard", "keypressed", "popup selector"),
        ),
        TwitterReferenceSource(
            reference_id="pathfinder_paulrouget",
            display_name="Pathfinder",
            source_kind="github_reference_low_priority",
            reference_url="https://github.com/paulrouget/pathfinder",
            implementation_area="graphics_reference_low_priority",
            implementation_use="Low-priority graphics/rasterizer reference; not currently useful for Twitter/X media capture.",
            relevant_patterns=("GPU", "rasterizer", "fonts", "vector graphics", "OpenGL"),
        ),
        TwitterReferenceSource(
            reference_id="jocly_aclap",
            display_name="jocly",
            source_kind="github_reference_low_priority",
            reference_url="https://github.com/aclap-dev/jocly",
            implementation_area="not_currently_relevant",
            implementation_use="Not currently useful for Twitter/X media capture; recorded only because it was part of the supplied reference list.",
            relevant_patterns=("board games", "2D", "3D", "VR"),
        ),
    )


def build_twitter_reference_registry(
    *,
    include_local_manifest_status: bool = False,
    local_roots: Iterable[str | Path] = (),
) -> TwitterReferenceRegistry:
    references = list(twitter_reference_sources())
    if include_local_manifest_status:
        by_path = {str(source.local_path).lower(): source for source in references if source.local_path}
        for local_root in local_roots:
            root = Path(local_root)
            try:
                manifest = inspect_chromium_extension_manifest(root)
            except OSError:
                continue
            key = str(root).lower()
            existing = by_path.get(key)
            if existing:
                references.append(
                    TwitterReferenceSource(
                        reference_id=f"{existing.reference_id}_inspected_manifest",
                        display_name=f"{existing.display_name} inspected manifest",
                        source_kind="local_manifest_inspection",
                        local_path=str(root),
                        version=str(manifest.get("version", "")),
                        implementation_area=f"{existing.implementation_area}_manifest_verification",
                        implementation_use="Read-only local manifest inspection result for implementation verification.",
                        host_permissions=tuple(manifest.get("host_permissions", ()) or ()),
                        permissions=tuple(manifest.get("permissions", ()) or ()),
                        relevant_patterns=tuple(manifest.get("content_script_files", ()) or ()),
                        notes=str(manifest.get("description", "")),
                    )
                )
    return TwitterReferenceRegistry(
        schema_version=TWITTER_REFERENCE_SOURCES_SCHEMA_VERSION,
        references=tuple(references),
    )


def write_twitter_reference_registry(path: str | Path, **kwargs: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    registry = build_twitter_reference_registry(**kwargs)
    output.write_text(json.dumps(registry.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return output
