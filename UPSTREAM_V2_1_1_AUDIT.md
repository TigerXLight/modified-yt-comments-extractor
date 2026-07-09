# Upstream v2.1.1 Parity Audit

Date: 2026-07-09

Scope: local repository inspection only. This audit does not introduce behavior changes, network calls, YouTube API calls, ASR provider calls, downloading, archive checks, screenshots, browser automation, scraping, ZIP extraction, credential storage, or network-dependent tests.

This document compares the current repo against upstream/original-creator v2.1.1 release-page ideas already captured in project handoff context. If a feature could not be found from local inspection, it is marked as not found rather than inferred.

## Priority Summary

High priority now:
- API quota error handling audit/tests.
- Newest sort and max-comments behavior audit/tests.
- Export hotkey/button fetch-state safety.
- Spam false-positive regression tests.

Medium priority:
- API key storage fallback audit.
- GUI close/cancel behavior audit.
- Campaign detection performance guard tests.

Low priority/later:
- Packaging entry point and package inclusion audit.
- Linux icon fallback.
- Docs/branding polish.

## 1. API Quota-Exceeded Typed Handling

Upstream issue/feature summary:
- Upstream v2.1.1 appears to call out friendlier, typed handling for YouTube API quota exhaustion instead of surfacing generic API errors.

Relevant local code:
- `extractor.py` defines `QuotaExceededError`, `CommentsDisabledError`, and `VideoNotFoundError`.
- `extractor.py` converts errors in `_raise_friendly_error()`, currently by scanning the lowercased exception text for terms such as `quota`.
- `main.py` catches `QuotaExceededError` in the background fetch thread and logs `API quota exceeded. Try again tomorrow.`

Current repo status: needs investigation.

Assessment:
- Relevant code exists, but the quota detection appears string-based rather than explicitly parsing `googleapiclient.errors.HttpError` JSON/error reasons such as `quotaExceeded`, `dailyLimitExceeded`, or related status fields.
- `HttpError` is imported in `extractor.py`, but local inspection did not find typed reason parsing.
- No dedicated quota regression test was found in the visible local test list.

Recommended next action:
- Add local mocked tests first, then consider replacing or supplementing string scanning with a small helper that extracts YouTube/Google API error reasons from `HttpError` payloads.

Suggested regression tests before any behavior port:
- Mock an `HttpError` whose payload reason is `quotaExceeded` and assert `QuotaExceededError`.
- Mock `dailyLimitExceeded` or equivalent quota reason and assert `QuotaExceededError`.
- Mock comments-disabled and not-found payloads and assert the existing typed errors still work.
- Mock a non-quota API error and assert it remains a generic runtime/API error.

Risk notes:
- Broad string matching can misclassify unrelated messages that contain `quota`.
- Overly narrow typed parsing can miss real-world Google API payload variants, so tests should cover both typed payload and fallback string detection.

## 2. API Key Storage Fallback / Keyring Runtime Failure Fallback

Upstream issue/feature summary:
- Upstream v2.1.1 appears to handle systems where keyring is missing or fails at runtime, falling back safely to file storage.

Relevant local code:
- `core/settings.py` imports `keyring` optionally and sets `KEYRING_AVAILABLE`.
- `SettingsManager._load_api_key()` catches keyring read exceptions and falls back to `settings.json`.
- `SettingsManager._save_api_key()` catches keyring write exceptions and falls through to file storage.
- `SettingsManager.save()` writes the API key into JSON only when `_use_keyring` is false.
- `requirements.txt` includes `keyring>=24.0.0`; `pyproject.toml` lists `keyring` as optional under `secure`.
- `main.py` displays a storage status label based on `SettingsManager.get_storage_info()`.

Current repo status: risky.

Assessment:
- Fallback code exists, but local inspection suggests a possible runtime-failure gap: if keyring is installed, `_use_keyring` remains true even after `set_password()` fails, and `save()` uses `include_api_key = not self._use_keyring`. That may prevent the fallback JSON save from actually including the API key after a runtime keyring failure.
- `_load_api_key()` can read from JSON fallback if a key is already present there.
- No dedicated settings/keyring fallback tests were found in the visible local test list.

Recommended next action:
- Add mocked `SettingsManager` tests before changing behavior. Verify save/load behavior when keyring import is missing, keyring write fails, keyring read fails, and delete fails.

Suggested regression tests before any behavior port:
- Simulate keyring unavailable and assert saved JSON includes `api_key`.
- Simulate keyring available but `set_password()` raises and assert saved JSON includes `api_key`.
- Simulate keyring available but `get_password()` raises and assert JSON fallback is read.
- Assert non-secret settings still save when keyring errors occur.
- Assert UI storage info does not misleadingly claim secure storage after runtime fallback.

Risk notes:
- Storing API keys in JSON is less secure; any fallback should be explicit in logs/UI and should avoid writing secrets into exports, manifests, screenshots, or diagnostics.

## 3. Packaging / pyproject / Console Entry Point Package Inclusion

Upstream issue/feature summary:
- Upstream v2.1.1 appears to include packaging metadata and console entry point cleanup.

Relevant local code:
- `pyproject.toml` defines project metadata and `[project.scripts] yt-comments = "main:main"`.
- `pyproject.toml` package discovery includes only `core*`.
- Top-level application modules such as `main.py`, `extractor.py`, and many helper modules live outside `core`.

Current repo status: needs investigation.

Assessment:
- A console script exists, but package inclusion may not match the current source layout. With `include = ["core*"]`, top-level modules may be omitted from wheel packaging depending on setuptools behavior and project layout.
- The project has accumulated many top-level helper modules for ASR, source evidence, and Total Export workflows that are unlikely to be covered by the current package discovery setting.

Recommended next action:
- Treat packaging as a separate low-priority audit/test task. Do not change packaging until behavior tests and expected distribution target are clear.

Suggested regression tests before any behavior port:
- Build an sdist/wheel locally in an isolated temp output and inspect included files.
- Install the wheel into a temporary venv and run `yt-comments --help` or a harmless startup/import check if available.
- Import representative top-level helper modules from the installed package.

Risk notes:
- Packaging changes can unintentionally include local-only dev files, generated artifacts, or credential-adjacent settings.
- This repo has many local dev CLI/test helpers; packaging policy should be explicit before inclusion is broadened.

## 4. Linux GUI Icon Startup Fallback

Upstream issue/feature summary:
- Upstream v2.1.1 appears to avoid GUI startup failure on Linux when `.ico` icon handling is unsupported.

Relevant local code:
- `main.py` sets `assets/logo.ico` with `self.iconbitmap(icon_path)` when the file exists.

Current repo status: likely missing.

Assessment:
- Local inspection found an existence check but did not find a try/except around `iconbitmap()`.
- On some Linux/Tk configurations, `.ico` icon loading can raise even when the file exists.

Recommended next action:
- Add a small guarded startup fallback later: catch icon setup errors, log/debug them, and continue without failing app startup.

Suggested regression tests before any behavior port:
- Unit-test an icon setup helper with a fake/root object whose `iconbitmap()` raises.
- Assert startup continues and no exception escapes.
- If a PNG fallback is added later, test missing/invalid icon paths without touching GUI behavior.

Risk notes:
- Direct GUI startup tests can be fragile on headless systems. Prefer a tiny helper function test or mocked widget.

## 5. Disable Export Hotkeys/Buttons During Fetch

Upstream issue/feature summary:
- Upstream v2.1.1 appears to avoid half-fetched exports by disabling export buttons/hotkeys while background fetch is running.

Relevant local code:
- `main.py` disables CSV, Excel, TXT, and evidence/package buttons when starting a fetch.
- `main.py` re-enables export buttons after fetch if comments exist.
- `main.py` binds `Ctrl+S`, `Ctrl+E`, and `Ctrl+T` directly to export methods.
- `export_txt()`, `export_csv()`, `export_excel()`, and `export_evidence_folder()` snapshot data under `_data_lock`, but local inspection did not find an early `fetch_state.is_fetching` guard inside those export methods.

Current repo status: risky.

Assessment:
- Button state is partly handled, but hotkeys can still call export methods unless Tk button state implicitly prevents only button clicks. The bound hotkeys call methods directly.
- The export methods check for available comments, not whether a fetch is in progress.
- Local inspection found no dedicated UI regression tests for export blocking during fetch.

Recommended next action:
- Add tests around a small export-allowed helper before changing UI. Then gate export methods and hotkeys while `fetch_state.is_fetching` is true.

Suggested regression tests before any behavior port:
- Simulate `fetch_state.is_fetching = True` and assert CSV/TXT/Excel/package export methods return before opening save dialogs.
- Assert export hotkey handlers respect the same guard.
- Assert exports remain enabled after completed fetch with data.
- Assert cancelled/failed fetch resets the UI state without enabling exports when no complete data exists.

Risk notes:
- Current export methods take data snapshots, which reduces race risk but does not solve "partial data looks complete" risk.
- A fetch-start path currently disables buttons before checking whether Comments/Livechat are selected; that path should be reviewed because an early return could leave fetch UI state inconsistent.

## 6. Window-Close / Cancel Behavior During Background Fetch

Upstream issue/feature summary:
- Upstream v2.1.1 appears to improve behavior when the user cancels or closes the window while a background fetch is active.

Relevant local code:
- `main.py` has `FetchState` with `is_fetching`, `cancel_event`, and `request_cancel()`.
- `cancel_fetching()` sets the cancel event and updates status/logging.
- `_on_closing()` requests cancellation, joins the fetch thread for up to two seconds, then destroys the window.
- `extractor.py` accepts `cancel_event` and checks it during comment, reply, and livechat loops.

Current repo status: needs investigation.

Assessment:
- Relevant cancellation code exists.
- Closing waits only briefly, then destroys the window while the daemon fetch thread may still be alive.
- Background code schedules UI updates via `after()`, so teardown races should be tested.
- Reply fetch errors are broadly swallowed to keep capture moving; cancellation behavior through that path should be confirmed.

Recommended next action:
- Add local mocked tests or an isolated state-machine test for cancel/close behavior before changing GUI code.

Suggested regression tests before any behavior port:
- Start a fake long-running fetch, call `cancel_fetching()`, and assert the cancel event is set.
- Simulate `_on_closing()` with a fake alive thread and assert it requests cancel before destroy.
- Verify extractor loops stop when `cancel_event` is set.
- Verify `_reset_fetch_ui()` clears fetch state after normal completion, cancellation, and exceptions.

Risk notes:
- Destroying Tk while background callbacks are queued can cause intermittent UI errors.
- Tests should avoid real network/API calls and should use fake request objects.

## 7. Spam False-Positive Fixes

Upstream issue/feature summary:
- Upstream v2.1.1 appears to reduce false positives, especially short organic praise and broad contact/adult/phone-number false positives.

Relevant local code:
- `spam_filter.py` contains multi-signal spam scoring, legitimacy bonuses, contact solicitation, phone, email, adult-content, URL, engagement bait, and structural spam logic.
- `spam_filter.py` includes a "Short harmless comment" legitimacy signal when text length is below 30 and no spam signals are present.
- `main.py` defaults spam separation off and labels it `Separate flagged spam`.
- `extractor.py` separates flagged spam into a separate export section when spam filtering is enabled.

Current repo status: needs investigation.

Assessment:
- Relevant spam logic exists and already appears designed around multi-signal scoring rather than single-keyword blocking.
- Broad contact, phone, and adult regexes remain high-risk for false positives and should be regression-tested against real organic comments before any upstream behavior is ported.
- No dedicated spam false-positive test file was found in the visible local test list.

Recommended next action:
- Add a spam regression test module first. Freeze examples of allowed short praise, normal contact-language discussion, phone-number context that is not solicitation, and adult-word context that is not spam.

Suggested regression tests before any behavior port:
- Assert short praise such as "Great video", "Loved this", and "This helped a lot" is not spam.
- Assert non-solicitation contact phrasing such as "contact support if it fails" is not spam unless paired with redirect/scam signals.
- Assert phone-number-like educational examples do not cross threshold without solicitation.
- Assert adult-word discussion context does not cross threshold without solicitation/URL signals.
- Assert obvious crypto/WhatsApp/Telegram scams still cross threshold.

Risk notes:
- Spam filtering changes can harm full-capture workflows if legitimate comments are separated or omitted.
- Since full capture is preferred, spam separation should remain opt-in/user-controlled.

## 8. Campaign Detection Performance Guard / Prefilters

Upstream issue/feature summary:
- Upstream v2.1.1 appears to guard duplicate/campaign detection performance with prefilters or other limits.

Relevant local code:
- `spam_filter.py` has `detect_spam_campaigns()` with exact grouping first, then pairwise `SequenceMatcher` comparisons over representatives.
- `filter_spam_batch()` defaults `detect_campaigns=True`.

Current repo status: needs investigation.

Assessment:
- Some performance reduction exists through exact grouping and representatives.
- Local inspection did not find an explicit large-input guard, max comparison cap, length/prefix prefilter, bucketing, or early opt-out for large unique comment sets.
- Campaign detection does not appear to be wired into the current `extractor.py` per-comment separation path, which uses local detector analysis through `apply_local_filters()`. It may be used only by direct batch helper callers.

Recommended next action:
- Add performance-oriented unit tests around `detect_spam_campaigns()` and decide whether a cap/prefilter is needed before changing defaults.

Suggested regression tests before any behavior port:
- Large list of unique comments completes under a local time budget.
- Exact duplicate cluster is detected without pairwise blow-up.
- Near-duplicate cluster is detected.
- Short generic comments are not falsely grouped as campaigns.
- Turning campaign detection off in `filter_spam_batch()` bypasses campaign logic.

Risk notes:
- Pairwise similarity can become expensive on large comment sets.
- Performance guards must not silently skip detection in ways that users interpret as proof that no campaign exists.

## 9. Newest Sort Behavior With Max-Comment Limits

Upstream issue/feature summary:
- Upstream v2.1.1 appears to address newer comments being missed when a max-comment limit is used with relevance/likes order.

Relevant local code:
- `core/constants.py` has `SortOption.DATE_NEWEST` and `SortOption.from_display_name()` defaults unknown display names to newest.
- `core/settings.py` defaults `sort_by` to `SortOption.DATE_NEWEST.value`.
- `main.py` initializes the sort dropdown to `Date (Newest)`.
- `extractor.py` direct caller default is `sort_by="time"`.
- `extractor.py.api_comment_order()` maps date/newest/oldest/time sort keys to YouTube API `order="time"`.
- `extractor.py` max limits count parent comments plus replies by checking and passing remaining capacity.
- `core/validators.py` treats empty max comments as unlimited.
- `main.py` UI copy says "Leave empty for all; limits count comments + replies".

Current repo status: already handled, but needs regression tests.

Assessment:
- The current code appears aligned with the full-capture default: Date/Newest is the GUI/settings/default fallback, direct extractor callers use API time order by default, and max-comment copy explains combined comment/reply limits.
- Edge cases still need tests, especially max limits with replies and API order mapping.

Recommended next action:
- Add mocked extractor tests for sort order and max limit behavior before any further sort/max changes.

Suggested regression tests before any behavior port:
- `process_video()` default `sort_by` sends commentThreads `order="time"`.
- UI/default settings resolve to Date/Newest.
- `SortOption.from_display_name()` unknown fallback is Date/Newest.
- Empty max comments parses as unlimited.
- Max comments limit counts parent comments plus replies.
- Date/Newest with a max limit does not fall back to likes/relevance order.

Risk notes:
- Even with newest order, applying date/min-likes/filter-word filters during fetch can reduce captured output. UI should keep those filters clearly user-controlled.
- API `order="time"` behavior should be verified with mocks only here; no quota-consuming test should be added.

## 10. Test-Suite Gap: Upstream-Style Regression Tests Before Porting Behavior

Upstream issue/feature summary:
- Before porting upstream v2.1.1 behavior, this repo should have local regression tests that describe the desired safety and parity behavior.

Relevant local code:
- The repo has many local tests for Total Export, URL utilities, source adapters, ASR helpers, and related skeletons.
- Visible test files did not include dedicated extractor quota tests, spam false-positive tests, settings/keyring fallback tests, or GUI fetch/export-state tests.

Current repo status: likely missing.

Assessment:
- The test suite is strong around recent Total Export/source-planning helpers, but upstream comment-extractor parity areas are not yet covered at the same level.
- Behavior changes should not be ported directly without tests, because these areas affect export integrity, credential handling, and full comment capture.

Recommended next action:
- Add a small upstream-parity regression test cluster before code changes:
  - `extractor_error_handling_test.py`
  - `extractor_sort_limit_test.py`
  - `spam_filter_regression_test.py`
  - `settings_keyring_fallback_test.py`
  - UI state tests only if they can be isolated/mocked without launching the full GUI.

Suggested regression tests before any behavior port:
- Cover all tests listed in sections 1, 2, 5, 7, 8, and 9.
- Keep tests local/mocked and free of YouTube API calls.
- Avoid network-dependent tests and avoid real credential storage.

Risk notes:
- Porting upstream behavior without tests could regress local full-capture priorities, especially reply capture, newest ordering, livechat pagination, spam separation, and export evidence structure.

## Cross-Cutting Boundaries for Future Work

- Do not introduce YouTube API calls in regression tests; use mocks/fakes.
- Do not add downloading, archive behavior, screenshots, browser automation, scraping, ZIP extraction, ASR provider calls, or credential storage as part of upstream parity work.
- Keep future behavior changes explicit, opt-in where user-facing, and locally testable.
- Preserve current YouTube comments/livechat behavior unless a scoped, tested parity patch explicitly changes it.
- Preserve full-capture defaults: spam separation off by default, Date/Newest by default, max comments empty/unlimited by default, and comments/replies/livechat clearly separated in exports.
