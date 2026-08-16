# External Reference Source Coverage Audit V76N

Audit date: 2026-08-16

Audited app commit: `5af82d1 Document current project capabilities and functions`

External reference folders inspected:

- `external_reference_sources_20260814_234822`
- `external_reference_sources_20260816_article_extraction`

Both folders are `REFERENCE_ONLY` and `DO_NOT_VENDOR` unless a future patch explicitly imports a small, reviewed, licence-compatible idea into app code. This audit does not vendor third-party source, run web downloads, crawl the web, download media, or scan a real Profile/Media HOME folder.

Status tags used: `IMPLEMENTED`, `PARTIAL`, `CLI_ONLY`, `GUI_ONLY`, `TESTED`, `DOCUMENTED_ONLY`, `REFERENCE_ONLY`, `SUPERSEDED`, `NOT_IMPLEMENTED`, `UNSAFE_OUT_OF_SCOPE`, `BLOCKED_BY_DEPENDENCY`, `NEEDS_MANUAL_REVIEW`, `DO_NOT_VENDOR`, `DO_NOT_IMPLEMENT_WRITE_ACTION`.

## High-Level Coverage

| Area | Current coverage | Summary |
| --- | --- | --- |
| Screenshot/page/archive references | `IMPLEMENTED`, `PARTIAL`, `TESTED`, `NEEDS_MANUAL_REVIEW` | The app has its own local browser execution, screenshot models, WARC/WACZ helpers, MSN offline viewer, static replay views, archive provider request builders, and local viewer. It does not copy GoFullPage/PageCap/webshot code. |
| Twitter/X references | `IMPLEMENTED`, `PARTIAL`, `CLI_ONLY`, `TESTED`, `UNSAFE_OUT_OF_SCOPE` | The app has X/Twitter URL recognition, compact row state, browser capture strategy/runner, timeline cursor scheduling, HAR/network parsing, reference registries, and shared media backend. Account write actions, DMs, following, deleting, credential automation, and CAPTCHA bypass remain out of scope. |
| Video/download references | `IMPLEMENTED`, `PARTIAL`, `TESTED`, `REFERENCE_ONLY` | The app uses its own YouTube/JDownloader/media execution bridge stack with FFmpeg/yt-dlp wrappers. Browser extension/native-helper references are not vendored. |
| Article extraction references | `IMPLEMENTED`, `PARTIAL`, `BLOCKED_BY_DEPENDENCY`, `REFERENCE_ONLY` | V76L adapter parses supplied HTML/local files, optionally imports metadata_parser/trafilatura/newspaper4k, and falls back to stdlib. Full dependency/API parity is not implemented. |
| Profile/Media HOME/source workflow | `IMPLEMENTED`, `PARTIAL`, `TESTED`, `NOT_IMPLEMENTED` | HOME models, source criticism, claim-subject affiliation gap, guarded Save-to-HOME backend, and folder operation workflows exist. Full HOME source folder ingestion from `source.txt`/RTF/media/screenshot folders is not implemented. |

## Reference Coverage Matrix

| Reference name | Reference area | Useful functions found | Current app equivalent | Status tag | Implemented files/tests | Missing pieces | Safety/out-of-scope notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GoFullPage extension archive | Screenshot/page capture | browser extension full-page screenshot idea | app-owned capture models and Playwright/local fallback | `REFERENCE_ONLY`, `SUPERSEDED`, `PARTIAL` | `capture_browser.py`, `source_local_browser_execution.py`, tests | no extension parity; no copied extension code | `DO_NOT_VENDOR`; browser extension code not needed |
| PageCap extension archive | Screenshot/page capture | page screenshot extension reference | app-owned screenshot/page capture | `REFERENCE_ONLY`, `SUPERSEDED`, `PARTIAL` | `capture_snapshots.py`, `source_local_browser_execution.py`, tests | no extension UI parity | `DO_NOT_VENDOR` |
| `mrcoles__full-page-screen-capture-chrome-extension` | Screenshot/page capture | full-page Chrome extension logic | full-page screenshot support via local browser/capture modules | `REFERENCE_ONLY`, `PARTIAL` | `capture_browser.py`, `source_local_browser_execution.py` | extension-specific stitching not imported | `DO_NOT_VENDOR` |
| `kubahorak__pagecap` | Screenshot/page capture | pagecap service/tool reference | app-owned local capture and static replay outputs | `REFERENCE_ONLY`, `PARTIAL` | `source_local_browser_execution.py`, `source_replay_static_snapshot.py` | exact CLI/API parity not implemented | `DO_NOT_VENDOR` |
| `stratofax__pagecap` | Screenshot/page capture | pagecap service/tool reference | same as above | `REFERENCE_ONLY`, `PARTIAL` | same as above | exact parity not implemented | `DO_NOT_VENDOR` |
| `EverythingSuckz__webshot-api` | Screenshot/page API | URL-to-screenshot API style | no webshot service; local/browser capture only | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` | none equivalent as API service | web API server not implemented | do not add external screenshot API dependency without review |
| `sea-deep__link-to-screenshot` | Screenshot/page API | link-to-screenshot service pattern | local browser capture and viewer | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` | local modules only | public API service not implemented | no web-service dependency |
| `kdippan__SnapStream` | Screenshot/page API | Microlink-style screenshot app | local evidence viewer/static screenshots | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` | local capture modules only | Microlink/API integration not implemented | external API use would need opt-in |
| `copperline-labs__rendex-mcp` | Render/capture MCP | render/capture service concept | no MCP integration; local capture modules | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` | none direct | MCP tool bridge not implemented | plugin/tool integration would be separate |
| `myselfshravan__third-eye` | Browser/screenshot capture | browser capture reference | local capture modules | `REFERENCE_ONLY`, `PARTIAL` | `source_local_browser_execution.py` | exact reference architecture not implemented | `DO_NOT_VENDOR` |
| `carbogninalberto__fast-html-to-pdf-api` | HTML/PDF capture | HTML-to-PDF service | no equivalent production PDF capture in this audit | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` | none direct | PDF capture API not implemented | external service out of scope |
| Twitter Exporter extension archive | Twitter/X export | browser extension export reference | local importer/review and X browser capture stack | `REFERENCE_ONLY`, `PARTIAL` | `capture_twitter_exporter_import.py`, `twitter_browser_capture_runner.py`, tests | full extension export parity not implemented | extension code not vendored |
| `annismckenzie__x-article-exporter` | X article extraction/rendering | article ID parsing, extraction, rendering, PDF/HTML pipeline | V76L article adapter plus X capture modules | `REFERENCE_ONLY`, `PARTIAL` | `profile_media_article_extraction_adapter.py`, `twitter_browser_capture_runner.py` | X article renderer/PDF/Typst parity not implemented | translate/MCP/server pieces not imported |
| `Aston1690__baoyu-danger-x-to-markdown` | X thread markdown/export | tweet/thread Markdown, media localization | X capture/cursor stack; no full thread Markdown product parity | `REFERENCE_ONLY`, `PARTIAL` | `twitter_browser_capture_runner.py`, `twitter_timeline_cursor_scheduler.py` | post/thread Markdown rendering incomplete if not separately implemented | cookie/session handling must be gated |
| `d60__twikit` | X private API client | API client, login/session, timeline/post actions | no direct client; app uses browser/reference/fake-safe capture paths | `REFERENCE_ONLY`, `UNSAFE_OUT_OF_SCOPE` for write/auth pieces | none direct | full API client not implemented | `DO_NOT_IMPLEMENT_WRITE_ACTION`; no credential automation |
| `fa0311__twitter-openapi` | X internal API reference | endpoint/schema docs | query-name and cursor handling in app | `REFERENCE_ONLY`, `PARTIAL` | `twitter_browser_capture_runner.py`, `twitter_browser_timeline_pagination.py` | full API surface not implemented | read-only reference only |
| `fa0311__TwitterInternalAPIDocument` | X internal API docs | endpoint/schema docs | query-name mapping and HAR/cursor parsers | `REFERENCE_ONLY`, `PARTIAL` | Twitter capture modules | full API coverage not implemented | read-only reference only |
| `fawwazabrials__TwitterFetch` | X fetch reference | request/fetch ideas | no direct client; browser capture stack | `REFERENCE_ONLY`, `PARTIAL` | `twitter_browser_capture_runner.py` | full fetcher parity not implemented | avoid credential/header leakage |
| `prinsss__twitter-web-exporter` | X web exporter | web export architecture | importer/review and browser capture stack | `REFERENCE_ONLY`, `PARTIAL` | `capture_twitter_exporter_*`, `twitter_browser_capture_runner.py` | full account export parity missing | no extension code vendored |
| `Rishikant181__Rettiwt-Core` | X API/core library | API/timeline/client ideas | no direct Rettiwt client | `REFERENCE_ONLY`, `UNSAFE_OUT_OF_SCOPE` where write/auth present | none direct | full client not implemented | no credential automation/write actions |
| `rxliuli__twitter-openapi` | X openapi/schema | query names/schema | query name list and cursor parsing | `REFERENCE_ONLY`, `PARTIAL` | `twitter_browser_capture_runner.py`, `twitter_browser_timeline_pagination.py` | no full generated client | read-only reference |
| `rxliuli__xkit` | X toolkit | toolkit/extraction ideas | app-owned X capture modules | `REFERENCE_ONLY`, `PARTIAL` | Twitter modules/tests | toolkit parity not implemented | no vendor |
| `sportiz91__x-monitor` | X monitoring | monitor/watch concepts | scheduler/cooldown controller | `REFERENCE_ONLY`, `PARTIAL` | `twitter_timeline_cursor_scheduler.py`, rate-limit policy | production monitor UI not implemented | aggressive monitoring must stay gated |
| `yashiels__twitter-cli` | X CLI read/write | timeline/search/tweet/profile plus post/delete/like/follow | read-only ideas only; app does not embed CLI | `REFERENCE_ONLY`, `UNSAFE_OUT_OF_SCOPE` | none direct | CLI not integrated | `DO_NOT_IMPLEMENT_WRITE_ACTION`; cookie extraction/write actions out of scope |
| `sixsechszes-666__x-reply-bot` | X bot | reply bot/write automation | no equivalent | `UNSAFE_OUT_OF_SCOPE`, `DO_NOT_IMPLEMENT_WRITE_ACTION` | none | do not implement | bot/write automation excluded |
| `thesahibnanda-max__twitterAPIAutomation` | X automation | API automation | no equivalent | `UNSAFE_OUT_OF_SCOPE`, `DO_NOT_IMPLEMENT_WRITE_ACTION` | none | do not implement | automation/write risk |
| `sferik__twitter-ruby`, `Twitter4J__Twitter4J`, `python-twitter-tools__twitter` | Twitter clients | API clients including read/write | no direct SDK integration | `REFERENCE_ONLY`, `UNSAFE_OUT_OF_SCOPE` for writes | none direct | SDK parity not implemented | write/credential actions excluded |
| `aclap-dev__vdhcoapp` | Video DownloadHelper native helper | native helper, conversion, downloads | JDownloader/media execution bridge | `REFERENCE_ONLY`, `PARTIAL`, `SUPERSEDED` | `jdownloader_internal_*`, `source_media_execution_bridge.py`, tests | native helper parity not implemented | no vendor |
| `alasim__video-downloader-pro` | Video downloader | generic video detection/download | JDownloader/media backend | `REFERENCE_ONLY`, `PARTIAL` | `youtube_media_download_backend.py`, `source_media_execution_bridge.py` | browser extension parity missing | no vendor |
| Video Download Helper extension archive | Video downloader extension | media detection/download extension | app uses JDownloader/yt-dlp/FFmpeg wrappers | `REFERENCE_ONLY`, `SUPERSEDED`, `PARTIAL` | `jdownloader_internal_*`, `media_ffmpeg_mux.py`, `source_media_execution_bridge.py` | extension behavior not copied | no vendor |
| Video Downloader Professional extension archive | Video downloader extension | media detection/download extension | app media backend | `REFERENCE_ONLY`, `PARTIAL` | same | extension parity missing | no vendor |
| `temjoy__video-catch` | Video capture/download | media catch reference | app media bridge | `REFERENCE_ONLY`, `PARTIAL` | `source_media_execution_bridge.py` | full generic media catch not implemented | external sites gated |
| `zming-huang__X_twitter_video_downloader_Chrome` | X media downloader extension | X video download extension | shared Twitter media backend/JDownloader route | `REFERENCE_ONLY`, `PARTIAL` | `twitter_media_backend.py`, `source_media_execution_bridge.py` | extension parity not implemented | no standalone Twitter downloader stack |
| `rxliuli__ffmpeg-online`, `paulrouget__libav.js` | FFmpeg/libav browser/WASM | browser-side conversion | local subprocess wrapper/FFmpeg mux plan | `REFERENCE_ONLY`, `PARTIAL`, `SUPERSEDED` | `source_media_execution_bridge.py`, `media_ffmpeg_mux.py` | WASM/browser conversion not implemented | no vendor |
| `paulrouget__YouTube.js` | YouTube private API | InnerTube/private API reference | app uses YouTube URL/JDownloader/backend paths | `REFERENCE_ONLY`, `NOT_IMPLEMENTED` | no direct InnerTube client | private API parity absent | private API risk; keep reference only |
| `trafilatura` | Article extraction | rich extraction, metadata, dedupe, language/date | optional import in V76L | `REFERENCE_ONLY`, `PARTIAL`, `BLOCKED_BY_DEPENDENCY` | `profile_media_article_extraction_adapter.py`, tests | full trafilatura API not integrated | no fetch/crawl default |
| `newspaper4k` | Article extraction | article lifecycle, authors/date/top image/movies | optional import in V76L | `REFERENCE_ONLY`, `PARTIAL`, `BLOCKED_BY_DEPENDENCY` | V76L adapter/tests | full lifecycle/config/feed/source parity absent | no crawl default |
| `metadata_parser` | Article metadata | OpenGraph/Twitter/schema metadata | optional import in V76L | `REFERENCE_ONLY`, `PARTIAL`, `BLOCKED_BY_DEPENDENCY` | V76L adapter/tests | full API, URL normalization, redirect/history handling absent | no web fetch default |

## Cross-Cutting Gaps

- `NOT_IMPLEMENTED`: full reference-repo parity is not a goal for most references.
- `PARTIAL`: Twitter/X read-only capture is implemented in several modules, but full account export, GUI integration, interaction/follower graph capture, and polished post/thread Markdown exports remain incomplete.
- `PARTIAL`: screenshot/archive support is app-owned and tested, but ReplayWeb/WARC/WACZ visual success remains manual-review-only unless an explicit replay verifier is run.
- `PARTIAL`: Profile/Media HOME has controlled models and guarded write paths, but not full HOME source folder ingestion.
- `UNSAFE_OUT_OF_SCOPE`: posting, deleting, liking, reposting, following/unfollowing, DMs, blocking/muting, credential/cookie automation, CAPTCHA bypass, botting, aggressive scraping, and rate-limit bypass.

