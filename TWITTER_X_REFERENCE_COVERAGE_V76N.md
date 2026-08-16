# Twitter X Reference Coverage V76N

Audit date: 2026-08-16

This file compares X/Twitter references to the app's current read-only capture/extraction direction.

## Current App Implementation

| Capability | Status | Implemented files/tests | Notes |
| --- | --- | --- | --- |
| URL/source adapter recognition | `IMPLEMENTED`, `TESTED` | `source_adapters.py`, `source_adapters_test.py` | `x.com` and `twitter.com` are recognized as `twitter_x`. |
| Compact row declaration UI state | `IMPLEMENTED`, `GUI_ONLY`, `TESTED` | `source_twitter_compact_row.py`, `source_twitter_compact_row_test.py`, `tools/assert_twitter_x_*.py` | Captures Post/Thread selection intent and settings state; live success not implied. |
| Single post/browser capture scaffolding | `IMPLEMENTED`, `CLI_ONLY`, `TESTED`, `PARTIAL` | `twitter_browser_capture_strategy.py`, `twitter_browser_capture_runner.py`, `tools/run_twitter_browser_capture_v71.py` | Requires operator/browser context for live use. |
| Rendered DOM fallback | `IMPLEMENTED`, `TESTED` | `twitter_browser_capture_runner.py`, `tools/assert_twitter_rendered_dom_fallback_v72d.py` | Preserves rendered DOM fallback status; not a guarantee of completeness. |
| Media URL capture / shared backend | `IMPLEMENTED`, `TESTED`, `PARTIAL` | `twitter_media_backend.py`, `tools/run_twitter_media_backend_v68.py`, `source_media_execution_bridge.py` | Shared backend path exists; not a separate Twitter-only downloader stack. |
| Replies/timeline cursor handling | `IMPLEMENTED`, `CLI_ONLY`, `TESTED`, `PARTIAL` | `twitter_browser_timeline_pagination.py`, `twitter_timeline_cursor_scheduler.py`, `tools/run_twitter_timeline_cursor_*.py` | Cursor/resume/rate-limit state exists; live session completeness remains manual. |
| Scheduler/cooldown controller | `IMPLEMENTED`, `TESTED` | `twitter_timeline_cursor_scheduler.py`, `twitter_rate_limit_policy.py` | Rate-limit headers/cooldown are modelled. |
| Archive-ready output | `PARTIAL`, `TESTED` | `twitter_browser_capture_runner.py`, source evidence/export modules | Manifests/sidecars exist; complete archive package parity remains partial. |
| No write actions | `IMPLEMENTED` as policy | no app write-action modules found/endorsed | The audit marks write/bot references out of scope. |

## Reference Mapping

| Reference | Useful read-only ideas | Current equivalent | Status | Missing |
| --- | --- | --- | --- | --- |
| Twitter Exporter extension archive | browser-side export shape | `capture_twitter_exporter_*`, `twitter_browser_capture_runner.py` | `REFERENCE_ONLY`, `PARTIAL` | full extension/account export parity |
| `annismckenzie__x-article-exporter` | X article extraction/rendering | V76L adapter, Twitter browser stack | `REFERENCE_ONLY`, `PARTIAL` | X article PDF/Typst/rendering pipeline |
| `Aston1690__baoyu-danger-x-to-markdown` | tweet/thread Markdown and media localization | cursor/browser capture modules | `REFERENCE_ONLY`, `PARTIAL` | polished post/thread Markdown rendering |
| `d60__twikit` | client/session/API patterns | no direct equivalent | `REFERENCE_ONLY`, `UNSAFE_OUT_OF_SCOPE` for write/auth | API client parity not implemented |
| `fa0311__twitter-openapi` | internal endpoint/schema docs | query name constants/cursor parsers | `REFERENCE_ONLY`, `PARTIAL` | full generated client |
| `fa0311__TwitterInternalAPIDocument` | endpoint docs | query/cursor handling | `REFERENCE_ONLY`, `PARTIAL` | full endpoint coverage |
| `fawwazabrials__TwitterFetch` | fetch client reference | browser capture runner | `REFERENCE_ONLY`, `PARTIAL` | direct fetcher not implemented |
| `prinsss__twitter-web-exporter` | web export architecture | importer/review/capture modules | `REFERENCE_ONLY`, `PARTIAL` | full account export parity |
| `Rishikant181__Rettiwt-Core` | API client/core | no direct equivalent | `REFERENCE_ONLY`, `UNSAFE_OUT_OF_SCOPE` for write/auth | SDK not implemented |
| `rxliuli__twitter-openapi` | query/schema reference | `TWITTER_API_QUERY_NAMES`, cursor handling | `REFERENCE_ONLY`, `PARTIAL` | full API surface |
| `rxliuli__xkit` | toolkit | app-owned capture modules | `REFERENCE_ONLY`, `PARTIAL` | toolkit parity |
| `sportiz91__x-monitor` | monitoring | cursor scheduler/rate limit policy | `REFERENCE_ONLY`, `PARTIAL` | production monitor UI |
| `yashiels__twitter-cli` | read/write CLI | none direct | `REFERENCE_ONLY`, `UNSAFE_OUT_OF_SCOPE` | CLI not integrated |

## Unsafe / Out-Of-Scope Reference Functions

The following functions are forbidden for product integration unless a separate safety review creates a narrow, explicit, user-approved exception:

- `DO_NOT_IMPLEMENT_WRITE_ACTION`: posting, replying, quote-posting, reposting, deleting.
- `DO_NOT_IMPLEMENT_WRITE_ACTION`: liking/unliking, bookmarking/unbookmarking.
- `DO_NOT_IMPLEMENT_WRITE_ACTION`: following/unfollowing, blocking/unblocking, muting/unmuting.
- `UNSAFE_OUT_OF_SCOPE`: DMs, account automation, bot/reply automation, follower graph automation where it requires credentials or aggressive scraping.
- `UNSAFE_OUT_OF_SCOPE`: CAPTCHA bypass, stealth/fingerprint spoofing, session-cookie extraction automation, credential store scraping.
- `UNSAFE_OUT_OF_SCOPE`: aggressive scraping, rate-limit bypass, hidden private API mutation calls.

## Missing Safe Pieces

- `NOT_IMPLEMENTED`: full account export parity with browser extensions.
- `PARTIAL`: GUI integration for full Twitter/X capture results beyond compact row state.
- `PARTIAL`: reusable social-media/video provenance model that bridges Twitter outputs into Profile/Media HOME.
- `PARTIAL`: post/thread Markdown rendering if no separate current module is selected.
- `NOT_IMPLEMENTED`: interaction/follower graph capture as a safe product feature.

