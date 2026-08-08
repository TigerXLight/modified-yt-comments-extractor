# Project Current-State Handoff

Date: 2026-07-16

Checkpoint: `Wire operational site capture UI` milestone

Branch: `v2.6.0-asr-engines`

## Purpose

This document is the cross-project handoff for the current ASR comparison, Total Export, upstream v2.1.1 parity, source-preservation, local evidence-manifest, and source-evidence model-skeleton work.

It records the state needed for a future session to resume safely. It does not implement behavior and does not replace the detailed subsystem documents listed below.

## Repository And Workflow Snapshot

- The working tree was clean when this handoff milestone started. Reconfirm with `git status --short` before applying any new patch.
- Current branch: `v2.6.0-asr-engines`.
- Current checkpoint: `48daf04 Wire operational site capture UI`.
- The user performs final local checks, commits, and pushes after reviewing each patch.
- Codex should not commit unless the user explicitly changes that instruction.
- Keep one milestone per patch.
- Start each milestone with `git status --short` and the relevant recent commit history.
- If a prompt requires a clean checkpoint and the tree is dirty, stop and report status instead of layering work.
- Prefer complete milestone prompts as downloadable Markdown so scope, boundaries, checks, and commit guidance remain together.
- Use local or mocked tests. Current local-only milestones do not need broad network or sandbox access.
- Windows CMD preference: put one command in each copy block. Use `&` in verification chains so later checks still run; use `&&` in commit/push chains so later state changes require earlier success.

## Hard Boundaries

Unless a later milestone is explicitly approved, do not add:

- Media or YouTube downloading.
- Source, comment, reply, live-chat, caption, transcript, or page fetching.
- YouTube, archive, ASR-provider, HTTP, or other network/API calls.
- Archive checks or archive submission.
- Browser automation, scraping, or screenshots.
- Provider transcription or other ASR calls.
- Credential, secret, cookie, or browser-session storage in reports/packages.
- ZIP extraction or reading files from inside ZIPs.
- Login, paywall, private-content, anti-copy, or DRM bypass behavior.
- GUI wiring for the local-only preservation/evidence/report helpers.
- Evidence queue persistence, background processing, or file operations.
- Credential/provider work beyond the approved row 2C2 masked cloud-ASR Save/Clear controls, safe presence/provenance refresh, committed secure YouTube credential migration/legacy cleanup, local-only cloud-ASR credential-consumption prerequisite, explicit local ASR provider-action coordinator seam, local-only ASR connection-test coordinator seam, ElevenLabs Scribe v2 fake-transport-tested provider adapter, production-capable official SDK transport, one-call live verification, and explicit user-facing Online ASR action wiring. User-facing Test Connection wiring, OAuth, browser-profile integration, broader provider/API calls, automatic/background checks, account/quota/model calls, uploads beyond explicit selected-file transcription, network behavior beyond approved explicit provider actions, and future reveal/copy/export behavior remain separately approval-gated.
- Operational source-resource work beyond the local fixture/mock scaffolds. The current REV4 operational site-capture work adds local contracts, action logs, dependency audit metadata, localhost fixtures, lazy browser-runner wrappers, supplied-HTML capture helpers, localhost-only media-download tests, rendered-citation metadata/fixture manifests, ArchiveBox command planning, and source UI capture-plan preview wiring only; live HTTP/API retrieval, browser/DevTools/shadow-root execution against real sites, scraping, live comments, live resource enumeration, external downloads, real screen recording, webpage/comment screenshots, archive checks/submissions, ArchiveBox execution, credentials, and provider/network behavior remain separately approval-gated.
- Database-root scanning, automatic classification, sensitive-trait inference, reclassification execution, or file movement.
- New runtime dependencies or hidden configuration for these milestones.

Existing YouTube comment/live-chat behavior, app exports, ASR runtime behavior, and Total Export package/review behavior must remain stable unless a separately approved milestone changes them with local/mocked coverage.

## Source Adapter Audit Readiness

- `source_adapter_audit_registry.py` now provides a durable METADATA_ONLY / LOCAL_ONLY / USER_REVIEW_REQUIRED audit registry for current and required source-adapter methods.
- The registry covers MSN, X/Twitter public post/archive, X/Twitter reply thread/archive, YouTube media/transcript, YouTube comments, generic article HTML, generic article comments, manual local import, and archive-only import.
- Each audit entry records source type, capture method, required artifacts, archive strategy, comment/transcript/media support, credential requirement without credential values, live/manual mode, Evidence Database mapping, Total Export mapping, operator approval requirements, method-specific audit metadata, audit status, and execution status.
- The Source Adapter Audit Resolution pass resolved the five previous row-level gaps as `metadata_audit_ready` while keeping every row `not_yet_executed`: X/Twitter public post/archive, X/Twitter reply thread/archive, generic article HTML, generic article comments, and archive-only import. Generic article comments still records nested `site_specific_selector_status=audit_required` because selectors/pagination/login/challenge behavior must be audited per site before live execution.
- Grabbed-source records now expose typed article, comment, media, transcript, archive URL, screenshot, snapshot, manual-observation, and provider-receipt reference buckets. The operational capture controller derives those references from planned artifact metadata only.
- Evidence Database review/update support now includes a review-needed scan helper and rejects protected/sensitive classification dimension edits before update receipt creation. Safe edits still return deterministic audit receipts and perform no file reads, broad scans, moves, live execution, or automatic classification.
- The Source Evidence workflow review bundle now writes `source_adapter_audit_registry.json` alongside the existing workflow state, review manifest, queue review store, release readiness/action plan, grabbed-source record, database scan result, and access/provider gate sidecars. The Total Export/review manifest includes an explicit pathless Source Adapter audit registry metadata sidecar entry.
- This is audit readiness only. It performs no live site access, browser automation, network/API/provider call, archive submission, ASR job, upload, broad folder scan, file move, file-existence claim, protected-attribute inference, completed-evidence claim, or automatic classification.

## ASR Comparison And Provider State

### Acceptance Policy

- The strict project reference acceptance threshold remains 95%.
- Machine ASR output remains draft text unless strict quality and term checks pass.
- Term QA/glossary review remains mandatory for names and lore terms.
- External leaderboard results are research leads only and cannot override project-specific reference scoring.
- `accepted` remains reserved for a future provider/model that passes the project gate.

### Current Project Results

- Best tested local/no-cloud result: whisper.cpp Vulkan large-v3-turbo with phrase prompt, about 74.19% strict 30-second reference accuracy.
- Local ASR timeout hardening now scales whisper.cpp Vulkan subprocess timeout from normalized audio duration for long media, exposes `ASR_WHISPERCPP_TIMEOUT`, `ASR_WHISPERCPP_TIMEOUT_REALTIME_MULTIPLIER`, and `ASR_WHISPERCPP_MAX_TIMEOUT` as local operator controls, surfaces effective timeout/progress status for long runs, and keeps `whisper.cpp / Vulkan / large-v3` as the benchmark-backed local profile rather than recommending a downgrade after long-file timeout. Failed-run temp hygiene is bounded to the current invocation's generated WAV and exact whisper.cpp output prefix: empty stubs are cleaned, non-empty partial outputs are preserved as `user_review_required`, cleanup metadata/errors are recorded, source media is preserved, and no broad temp scan is performed.
- No tested local ASR path has met the 95% threshold.
- Leading tested cloud candidate: ElevenLabs Scribe v2 with keyterms, 84.95%.
  - It preserved the Nicolas Cage reference phrase and found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`.
  - It missed `Kingman`, `ZoneX`, `Freckelston`, and `Nyxara`.
  - It is a leading optional candidate, not accepted, not final truth, and not a production-integrated provider implementation.
- AWS Transcribe custom vocabulary is `blocked`, not rejected.
  - `SubscriptionRequiredException` prevented transcription and scoring in `eu-west-2`.
  - It must not be ranked against scored providers.

Rejected/lower-ranked project runs currently recorded:

| Provider/configuration | Strict reference accuracy | Current state |
| --- | ---: | --- |
| AssemblyAI Universal-3.5 Pro default/prompted | 70.97% | Rejected for integration for now. |
| Deepgram Nova-3 keyterms | 66.67% | Rejected for integration for now. |
| Speechmatics enhanced custom dictionary | 65.59% | Rejected for integration for now. |
| Azure Speech SDK phrase list | 64.52% | Rejected for integration for now. |
| Google STT video enhanced phrases | 61.29% | Rejected for integration for now. |
| Cohere Transcribe 03-2026 | 58.06% | Rejected for integration for now. |
| Google STT `latest_long` phrases | 50.54% | Rejected for integration for now. |

DirectML base/small are rejected for Auto Quality Probe for now. DirectML medium/large remain deferred unless explicitly approved. Offline ASR is not globally exhausted, but the practical AMD RX 5700 paths tested so far remain below threshold.

### ASR Reporting Tools

- `asr_comparison_report.py`: local/manual comparison records, deterministic ranking, text, Markdown, and JSON-ready output.
- `asr_comparison_report_cli.py`: reads manually entered JSON, renders text/Markdown/JSON, and writes only with explicit `--output`.
- `ASR_MANUAL_RESULTS_SEED.json`: local seed for known project results, blocked status, rejected results, external leads, and descriptive manual reporting/status metadata.
- `ASR_PROVIDER_LEADERBOARD_NOTES.md`: user-supplied external research leads; not independent verification.
- `asr_decision_summary.py` and `asr_decision_summary_cli.py`: local/manual decision summary for threshold, status counts, leading scored/local results, blocked items, external leads, and safe next-action guidance with Markdown/text/JSON rendering.
- `asr_term_coverage_summary.py` and `asr_term_coverage_summary_cli.py`: local/manual key-term hit/miss and provider-gap summary with Markdown/text/JSON rendering; no provider calls, transcription, downloads, network, credentials, or GUI behavior.
- `asr_combined_report_cli.py`: local/manual combined comparison, decision, and term coverage report renderer with explicit-output-only writes.
- `ASR_MANUAL_RESULTS_SEED.json` metadata was corrected after `975238e` by `b59a052` so `asr_manual_results_seed_test.py` passes; the blocked-status policy now explicitly includes `not quality-rejected`.

These tools do not call providers, run transcription, fetch media, or store credentials.

### Explicit Provider-Action Seam

- `058af01 Add explicit ASR provider action seam` added `asr_provider_action.py` and `asr_provider_action_test.py`.
- Outcome B applied: no tracked safe production cloud-provider runtime path existed, and the tracked ASR runtime remained local `faster-whisper` / `whisper.cpp`. The milestone therefore added only a local coordinator seam with injected trusted executors.
- The explicit entry point is `ASRProviderActionCoordinator.dispatch_provider_action(...)`.
- Credential lookup and executor dispatch occur only after that explicit method call. There is no lookup or dispatch at import, coordinator construction, startup, provider listing/search/filter, Access & Keys open, status refresh, Save/Clear, shutdown, or background time.
- The coordinator validates provider/action metadata, distinguishes local and cloud seams, delegates cloud credential resolution to `CloudASRCredentialConsumer`, invokes only an injected trusted executor, and returns a fixed non-secret action result.
- `elevenlabs_scribe` is dispatchable through an injected trusted executor with `elevenlabs_scribe_api_key`; this is not a production ElevenLabs implementation. `whisper_cpp_vulkan_large_v3_turbo` is dispatchable through an injected trusted executor without a cloud credential. AssemblyAI, Deepgram, Speechmatics, Azure, Google STT, Cohere, AWS, unknown IDs, pattern-adjacent IDs such as `elevenlabs_scribe_extra`, YouTube IDs, unsupported actions such as `connection_test`, and missing executors are rejected before credential lookup.
- The coordinator delegates unchanged credential semantics to `CloudASRCredentialConsumer`: non-empty secure values win, secure `None` permits environment fallback, empty/whitespace secure values are invalid and block environment fallback, backend unavailable/error may use the established non-empty environment fallback, and YouTube credential IDs are not accepted.
- Injected executors are trusted internal provider/action code, not a security sandbox. A malicious executor could retain or exfiltrate a supplied credential through side effects; the coordinator guarantee is limited to its own state, public result, repr, diagnostics, and tests.
- Public action results contain only `provider_id`, `action_kind`, `status`, `safe_diagnostic`, `credential_status`, `credential_provenance`, `executor_invoked`, `action_succeeded`, and `scope`. They exclude credential identifiers, credential values, fragments, prefixes/suffixes, lengths, hashes, executor returns, provider responses, transcripts, raw exceptions, tracebacks, request payloads, headers, and audio path/content.
- Ordinary executor exceptions become fixed non-secret failures; `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` are re-raised.
- No connection test, provider SDK/client, credential validation probe, list-model/account/quota call, live API request, audio open/upload, network behavior, GUI wiring, background action, credential write/delete, environment write, YouTube behavior change, cloud-ASR Save/Clear/status behavior change, or source/export behavior change was added.
- `asr_tools_test.py` is an interactive/manual harness that prompts for an audio/video path. It was compile-checked during the final chain but intentionally not executed as an automated self-test.

### Explicit Connection-Test Seam

- `f709f8e Add explicit ASR connection test seam` added `asr_connection_test.py` and `asr_connection_test_test.py`.
- Outcome B applied: no tracked safe connection-test runtime path existed. The milestone therefore added only a local coordinator seam with injected trusted testers; it did not add any production provider-specific tester.
- The explicit entry point is `ASRConnectionTestCoordinator.test_provider_connection(...)`.
- No credential lookup or tester invocation occurs at import, coordinator construction, provider listing/search/filter, app startup, `App` construction, Access & Keys open, status refresh, Save/Clear, shutdown, or background time. Only an explicit method call can trigger validation, credential resolution, and trusted tester invocation.
- Validation happens before credential lookup: exact provider ID is checked, YouTube/non-ASR misuse is rejected, local/cloud/not-test-dispatchable classification is determined, local/no-test-required and non-test-dispatchable providers are rejected, missing testers are rejected, and only then does the coordinator resolve credentials and invoke the trusted tester once.
- `elevenlabs_scribe` is test-dispatchable only through an injected trusted tester with `elevenlabs_scribe_api_key`; this is not a production ElevenLabs connection test. `whisper_cpp_vulkan_large_v3_turbo` is local/no test required. AssemblyAI, Deepgram, Speechmatics, Azure, Google STT, Cohere, AWS, unknown IDs, pattern-adjacent IDs such as `elevenlabs_scribe_extra`, YouTube IDs, and missing testers are rejected before credential lookup.
- The coordinator delegates unchanged credential semantics to `CloudASRCredentialConsumer`: non-empty secure values win, secure `None` permits environment fallback, empty/whitespace secure values are invalid and block environment fallback, backend unavailable/error may use the established non-empty environment fallback, empty/whitespace environment values are missing, and YouTube credential IDs are rejected.
- Injected testers are trusted internal provider-specific code, not a security sandbox. A malicious tester could retain or exfiltrate a supplied credential through side effects; the coordinator guarantee is limited to its own state, public result, repr, diagnostics, and tests.
- Public connection-test results contain only `provider_id`, `status`, `safe_diagnostic`, `credential_status`, `credential_provenance`, `tester_invoked`, `tester_completed`, and `scope`. They exclude credential IDs, credential values, fragments, prefixes/suffixes, lengths, hashes, tester returns, provider responses/bodies, account details, quota, model lists, raw exceptions, tracebacks, request payloads, and headers.
- `tester_completed=True` means only that the injected trusted tester returned normally without raising. It does not prove credential validity, authentication success, provider reachability, network connectivity, account access, quota access, model availability, or production connection-test success. Tester return values are ignored, including `True`, `False`, sentinel-like strings, and provider-like dictionaries.
- Ordinary tester exceptions become fixed non-secret failures; `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` are re-raised.
- No GUI Test Connection button/caller, production caller, provider SDK/client, credential-validation endpoint, authentication probe, list-model/account/quota call, health check, live API request, audio open/upload, network behavior, OAuth/browser access, background test, credential write/delete, environment write, YouTube behavior change, cloud-ASR Save/Clear/status behavior change, or source/export behavior change was added.
- `asr_tools_test.py` remains an interactive/manual harness that prompts for an audio/video path. It was compile-checked during the final chain but intentionally not executed as an automated self-test.

### ElevenLabs Scribe v2 Provider Adapter

- `f21e578 Add ElevenLabs Scribe v2 provider adapter` added `elevenlabs_scribe_provider.py` and `elevenlabs_scribe_provider_test.py`.
- This is an ElevenLabs Scribe v2 provider-specific adapter and fake-transport-tested executor, not a production-live ElevenLabs integration. It uses provider ID `elevenlabs_scribe`, credential ID `elevenlabs_scribe_api_key`, and model `scribe_v2`.
- Scope is intentionally narrow: local-file synchronous batch transcription request preparation, local validation, action-time credential flow through the existing `ASRProviderActionCoordinator`/`CloudASRCredentialConsumer` seams, injected trusted transport dispatch, response normalization, structured fake-error mapping, and safe non-secret public results.
- Request validation rejects unsupported options before credential/transport use where possible, requires an existing regular local file, enforces size strictly below `5_000_000_000` bytes, rejects booleans where numeric fields are expected, supports conservative language syntax, speaker counts from 1 through 32, supported timestamp granularities, optional diarization/audio-event settings, and optional keyterms.
- Keyterm policy is conservative and local: at most 1000 terms, at most five words by local whitespace normalization, first-occurrence dedupe, delimiter rejection, whitespace-only rejection, Unicode `len()` codepoint counting, and a 49-character term limit. The 49-character value is a conservative endpoint-compatible policy because official ElevenLabs wording conflicts: the endpoint reference says less than 50 characters while the guide says 50 characters. The local word/term normalization does not claim exact equivalence with provider-side normalization.
- Privacy and leakage protections are explicit. The request object is intentionally not a dataclass, and safe representations avoid full file paths, filenames, language values, keyterm values, exact speaker counts, credentials, headers, media content, raw provider responses, raw exceptions, and tracebacks. Credentials are resolved only at explicit action time and may reach only the injected trusted transport; trusted transport is internal code, not a sandbox.
- The adapter normalizes supported transcript text, optional language code/probability, word/audio-event items, start/end timestamps, speaker IDs, and item types. It safely rejects malformed, unsupported multichannel/webhook/async, negative/nonfinite/reversed timestamp, bool numeric, and raw-response-retaining shapes before public result creation. The current error taxonomy is tested only against structured fake-transport errors and is not yet verified against live ElevenLabs errors.
- File handles close after success, ordinary transport failure, response normalization failure, and `KeyboardInterrupt`/`SystemExit`/`GeneratorExit`. The adapter does not copy, move, delete, modify, retry, or cache media files.
- No live API request, real credential use, media upload, realtime mode, webhook/async retrieval, remote source URL submission, YouTube/TikTok URL submission, multichannel mode, account/quota/model API call, GUI transcription action, Test Connection wiring, background action, or network behavior exists in the adapter milestone itself.

### ElevenLabs Scribe v2 SDK Transport

- `38aee73 Add ElevenLabs Scribe v2 SDK transport` added `elevenlabs_scribe_transport.py`, `elevenlabs_scribe_transport_test.py`, provider category mapping in `elevenlabs_scribe_provider.py`, and the official dependency declaration `elevenlabs>=2.58.0,<3` in both `requirements.txt` and `pyproject.toml`.
- This is production-capable SDK transport code, fake-tested only, no live provider call. No package was installed during implementation, and no live ElevenLabs request, real API key, or media upload occurred.
- The transport lazily imports `elevenlabs.client` only during explicit provider execution. Normal app startup, provider listing, Access & Keys open/search/status refresh, Save/Clear, shutdown, and background time construct no SDK client and perform no credential lookup.
- During explicit action execution, the already-resolved credential is passed directly to a short-lived `ElevenLabs(api_key=..., timeout=240)` client. There is no implicit SDK environment-key fallback, no global client cache, and no credential cache. The official SDK/client is trusted third-party provider code, not a sandbox; project code keeps credentials out of its own public state/results/diagnostics, but a malicious or compromised SDK/client could retain or exfiltrate credentials or media through its own side effects.
- The exact batch call is `client.speech_to_text.convert(...)` with model `scribe_v2`, the already-open binary file object, and only the committed optional parameters: language code, audio-event tagging, diarization, speaker count, timestamp granularity, and keyterms. Unsupported and unset options are omitted; no webhook, multichannel, source URL, account/quota/model, connection-test, GUI, startup, or background call is added.
- Official SDK v2.58.0 source was inspected for constructor, `speech_to_text.convert`, `RequestOptions`, retry logic, timeout handling, `ApiError`, and response models. The SDK recognizes retryable HTTP statuses including 408/409/429/5xx, and `max_retries=0` was verified against source and fakes as one total request attempt. There is no application retry layer and no retry follows timeout, rate-limit, or service errors. The 240-second timeout is a local deterministic transport policy, not official ElevenLabs guidance.
- Lazy import handling distinguishes a missing top-level `elevenlabs` package from missing transitive dependencies and arbitrary SDK import exceptions. Only the missing top-level package maps to fixed `dependency_unavailable`; transitive/import failures are not hidden as missing SDK.
- Provider adapter code retains local path validation and file-handle ownership. The transport receives an already-open file object, does not reopen by path, does not close it, does not copy/move/delete media, and creates no temp files. Provider code closes the handle after success, SDK error, response conversion failure, provider normalization failure, `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit`.
- SDK response conversion accepts supported synchronous single-channel responses through documented model serialization or compatible mappings, preserves only text, language code, language probability, word/audio-event text, start/end, item type, and speaker ID, supports enum/plain-value normalization, and rejects multichannel/webhook/async variants. Structured error mapping uses safe `status_code` and structured body/detail fields only; it does not parse `str(exc)` or arbitrary human messages and does not retain raw body/header/request ID/account/billing data, credentials, paths, keyterms, request payloads, or media content.
- Verification for `38aee73` covered dependency declaration/TOML validation, compile checks for changed and adjacent modules/tests including compile-only `asr_tools_test.py`, `elevenlabs_scribe_transport_test.py`, `elevenlabs_scribe_provider_test.py`, provider-action and connection-test tests, credential tests, Access & Keys tests, ASR-provider metadata tests, YouTube migration/settings fallback tests, source adapter/report/gap tests and CLIs, `youtube_url_utils_test.py`, `main_export_state_test.py`, whitespace/final-newline checks, and `git diff --check`. Expected safe keyring fallback messages appeared while tests still exited successfully. `asr_tools_test.py` remains an interactive/manual harness and was not executed as an automated test.

### Online ASR User-Facing Action

- A separately approved one-call live verification after `9be4ea8` succeeded for the narrow ElevenLabs Scribe v2 local-file explicit-action path: secure keyring credential resolution, one request, `max_retries=0`, local 240-second timeout, provider/model `elevenlabs_scribe` / `scribe_v2`, action success, normalized provider success, no credential/raw-response output, and clean repository afterward. Exact-phrase accuracy was not confirmed by the synthetic sample.
- The main transcript toolbar now has `Online ASR` immediately beside `Local ASR`. The new control uses the same orange Local-ASR-style dimensions, typography, cog asset, transparent cog treatment, spacing, corner radius, hover behavior, and pressed/focus family rather than introducing a different button family. The existing Local ASR block remains visually unchanged.
- The Online ASR body opens a local-file workflow only. Opening the workflow, selecting a file, or clicking the cog/Access & Keys path performs no provider request. Dispatch occurs only after the explicit `Transcribe` action.
- The dispatch path is the committed production seam: UI action -> validated `ElevenLabsScribeRequest` -> `ASRProviderActionCoordinator` -> secure credential consumption -> ElevenLabs provider adapter -> SDK transport. UI code does not instantiate `ElevenLabs(...)`, does not duplicate credential lookup, and does not add a retry layer.
- The first user-facing slice is deliberately narrow: ElevenLabs Scribe v2, local file only, word timestamps, diarization off, audio-event tagging off, no keyterms by default, busy/duplicate-click prevention, thread-safe UI callback scheduling, safe fixed diagnostics, and existing transcript display/result routing. It adds no Test Connection UI, account/quota/model request, provider catalog redesign, OAuth/browser behavior, source URL support, multichannel/webhook mode, package installation, or automatic/background provider call.

## Total Export Local Package And Review State

The repository now has a broad local Total Export foundation:

- Source URL validation plus YouTube and metadata-only News Website source-adapter skeletons.
- `SOURCE_CONTEXT_GLOSSARY_CURRENT_STATE.md` records the current local source/context/glossary helper stack, verification commands, boundaries, and safe next milestones.
- `source_capture_plan_cli.py`: explicit-output-only local Source Capture Plan inspection CLI for manually supplied source URL/context/glossary JSON.
- `context_glossary_cli.py`: explicit-output-only local context/glossary inspection CLI for manually supplied source label, source URL, title, and user terms.
- `source_adapters.py`: local source adapter registry helpers use `source_name` for names/listing/lookup; adapters do not expose a `.name` attribute.
- `source_adapter_capability_report.py` and CLI: local registered-adapter capability/credential/privacy/setup metadata reports without fetch/capture/network/archive/provider/credential-test/scraping/GUI behavior.
- `NewsWebsiteSourceAdapter`: metadata-only known-host news website URL-recognition skeleton for Telegraph-style sources; no fetching, scraping, capture, archive checks, downloads, access bypass, or GUI wiring.
- `MsnSourceAdapter` plus `source_resource_state.py` and narrow `main.py` wiring (`2bb9340`): local-only MSN source-resource/archive/discussion UI scaffold. It adds Enter-driven multi-URL intake, Shift+Enter newline, canonical visible-source dedupe, removable session source rows, clean title/hostname display, fixture image and video/audio resource windows, dry-run-only Download, fixture/mock Wayback and archive.ph status display, ArchiveBox local-software scaffold/icon, source archive auto-check preference state, selected-source discussion dropdown, Webpage/Comments/Livechat controls with independent Screenshot intent state, Transcript `Get` label preserving the previous callback, sidebar order `UPDATES`, `KEYS/ACCOUNTS`, `EXPORT`, `FILES`, and main-page wheel routing. It performs no live MSN fetching, resource discovery from live pages, actual downloads, screenshots, browser automation, Wayback/archive.ph checks or submissions, ArchiveBox execution, credentials, provider calls, or network/API behavior.
- Operational site-capture REV4 local implementation through backend fixture coverage plus GUI/controller preview, export/queue metadata connection, and live/manual smoke planning scaffold: `capture_status.py`, `capture_contracts.py`, `capture_action_log.py`, `capture_dependency_audit.py`, `capture_fixture_server.py`, `capture_browser.py`, `capture_article.py`, `capture_page_outline.py`, `capture_snapshots.py`, `capture_comments.py`, `capture_livechat.py`, `capture_media_discovery.py`, `capture_media_download.py`, `capture_rendered_citation.py`, `capture_archive_providers.py`, `capture_archive_wayback.py`, `capture_archive_today.py`, `capture_archivebox.py`, `capture_warc_wacz.py`, `capture_controller.py`, `capture_export_queue.py`, `capture_live_smoke_plan.py`, and narrow `main.py` wiring provide deterministic capture status/contract/action-log metadata, a standard-library localhost fixture server, optional lazy browser-runner wrappers with fake-runner coverage, supplied-HTML article/page/snapshot/comment/livechat/media helpers, localhost-only explicit media-download tests, MODEL_ONLY / MOCK_CAPTURE_TESTED rendered-citation metadata and fixture segment manifests, MOCK_PROVIDER_TESTED Wayback/archive.today check/list/submit-plan/mock-result helpers, CHALLENGE_HANDOFF_ONLY archive.today manual challenge metadata, MOCK_COMMAND_TESTED ArchiveBox command planning for Windows Docker Compose, WSL2 CLI/Docker, remote, and native Unix modes, MODEL_ONLY / LOCALHOST_FIXTURE_TESTED / MOCK_PACKAGE_TESTED WARC/WACZ metadata with SECRET_REDACTION_TESTED header sanitization and deterministic manifest/file hashes, plus EXPORT_METADATA_ONLY / QUEUE_METADATA_ONLY converters. The source UI can produce a local scaffold plan for selected source/mode/screenshot preferences; controller results include deterministic in-memory `ACTION_LOG` artifact metadata, chained action events, sanitized JSONL hashes, and planned webpage/screenshot/comments/livechat/media/rendered-citation/archive/WARC/WACZ artifact declarations. The `Go` scaffold preview exposes plain-language selected scopes, screenshot intents, artifact counts/types, action-log event/hash-chain summary, fixture/model-only status, unsupported-live-execution wording, MANUAL_LIVE_SITE_SMOKE_PENDING warnings, and explicit manual live-smoke approval-required wording. The export/queue converter preserves planned artifact IDs, hashes, source URL, scope, action-log references, fixture/mock/model labels, and manual-live-smoke-pending status as Evidence Item Queue items, Total Export manifest assets/archive-result metadata, and unknown/user-review-required Evidence Database preview records without writing or moving files. `capture_live_smoke_plan.py` records candidate site labels, source URL placeholders, source adapter family, APPROVAL_REQUIRED / MANUAL_OPERATOR_ONLY statuses, manual checklist items, expected artifact declaration types, and safety prohibitions as MODEL_ONLY / USER_REVIEW_REQUIRED metadata; it emits no execution commands and cannot mark normal helper-created plans as completed manually. The MSN manual smoke metadata path is fixed to site label `MSN`, URL `https://www.msn.com/en-gb/news/uknews/twelve-arrested-over-terror-threat-at-islamic-festival/ar-AA27OIhw?`, adapter `msn`, and the four approved manual scopes `webpage_manual_review`, `comments_manual_review`, `media_manual_review`, and `export_queue_metadata_review`; imported manual observations remain USER_REVIEW_REQUIRED metadata and reject non-MSN, unapproved-scope, automation, archive submission, download, credential/cookie/account, and completion claims. Article/page helpers now exclude comments/chrome/ads from semantic article text, expose outline lines separately from article text, model raw/final/MHTML/DOM/accessibility snapshot artifacts, and separate faithful versus derived screenshot metadata. Comments/livechat helpers cover localhost/supplied fixtures for static, pagination/load-more/cursor/infinite, iframe/shadow/nested/virtualized/deleted/encoded/login/challenge comment shapes and bounded/deduped/reconnect/removal livechat event shapes, while treating livechat screenshot frames as supporting metadata only. Media helpers cover supplied DOM/poster/srcset/frame resources, HLS/DASH manifest references, supplied request/playback-event logs, blob/MediaSource non-downloadable states, signed/expiring URL metadata, explicit-selected localhost fixture downloads with hashes, and FFmpeg/yt-dlp command plans without execution. Rendered-citation helpers model user-mediated display-capture intent, browser `getDisplayMedia` preference, OS/window fallback metadata, purpose/time-range/source-label fields, fixture segment SHA-256 manifests, and PROTECTED_OUTPUT_BLOCKED mocked protected/black-output states. Archive helpers keep check/list separate from submit intent and command plans separate from execution. WARC/WACZ helpers model synthetic records, page/resource/index/component manifests, and fixture file hashes only. This does not execute live capture, real WARC capture, WACZ packaging, real screen recording, archive checks/submissions, ArchiveBox commands, action-log file writes, Total Export package writes, queue persistence, evidence database root scans, automatic classification, or file moves. No real external website access, real browser profile/cookie access, scraping, screenshots, OCR, external media downloads, real FFmpeg/yt-dlp execution, live comments/livechat capture, live archive checks/submissions, ArchiveBox process/server execution, credentials/cookies/auth headers, provider calls, or real evidence-database work was added.
- `capture_msn_extraction_fields.py` now links the approved MSN manual observation/import metadata to the MSN extraction-field/review bundle and converts that bundle to deterministic export/evidence queue review metadata. Metadata-only observations do not become extracted article/comment content; article/comment fields remain unavailable/needs-manual-source-content until local supplied HTML/text/comment records are passed. Article, comments, media observation, and export-review metadata remain separate, MANUAL_OPERATOR_ONLY, and USER_REVIEW_REQUIRED, with no artifact file, file-existence, live-verification, automation, network, archive, download, screenshot/OCR, credential, or automatic-classification claim.
- `capture_twitter_exporter_import.py` imports user-supplied local Twitter/X exporter outputs (TXT, JSON, JSONL, CSV, TSV, and ZIP containing those formats) into deterministic review bundles and Evidence Queue review metadata; `capture_twitter_exporter_import_cli.py` exposes safe explicit-file preview, JSON, batch, and queue-metadata modes; `capture_twitter_exporter_source_import.py` exposes source-workflow/source-row review summaries and summary-only queue draft handoff metadata for explicit local paths; `capture_twitter_exporter_manifest_report.py` projects queue drafts into export manifest/report review metadata; `capture_twitter_exporter_action_receipt.py` builds deterministic `CaptureActionLogEvent`-backed action-log/provenance receipt metadata; `capture_twitter_exporter_review_flow.py` composes those local-only pieces into an end-to-end source review -> queue draft -> manifest/report -> receipt summary; `capture_twitter_exporter_review_flow_cli.py` exposes that complete flow through a deterministic plain-text/JSON CLI full-summary entry point; and `main.py` now has minimal explicit local-file UI review, Add Review Draft, and Review Flow Summary actions. It records local file/member names, hashes, sizes, parsed counts, skipped unsupported members, warnings, and stable record IDs while preserving USER_REVIEW_REQUIRED / USER_SUPPLIED_LOCAL_EXPORT provenance. Sanitized synthetic compatibility fixtures cover nested `rows`/`list`/`users` JSON payloads, camelCase TXT/CSV fields, list-member metadata, and separator-delimited text blocks; no raw user export content is committed. UI/source-row summaries, queue draft notes, manifest/report entries, action receipts, end-to-end flow summaries, review-flow CLI output, and the UI Review Flow Summary dialog/log/status are metadata/counts-only and do not dump tweet text, raw record payloads, full local paths, or claim completed evidence files. ZIP import is bounded and rejects traversal, absolute, drive-letter, and symlink entries. This is local-file import only: no X/Twitter API, Chrome Web Store fetch, browser or extension automation, extension-code copying, credentials/cookies/accounts, media download, archive call, screenshot/OCR, live verification, evidence file movement/completion, or automatic classification is added.
- `evidence_item_queue.py` now bridges the source-role / claim-level roadmap into queue/export review metadata with `SourceRoleReviewMetadata`, `queue_source_role_reviews_to_claim_notes(...)`, `queue_source_role_reviews_to_ui_rows(...)`, `build_source_role_review_ui_summary(...)`, `source_role_review_receipt_id(...)`, `queue_source_role_reviews_to_action_log_events(...)`, and `build_source_role_review_flow_summary(...)`. Queue items can carry review-required scoped source-role claims, primary-source/currentness status, temporal/source-chain limitations, evidence basis, and safeguards that keep automatic classification false and sensitive inference prohibited; the export helper maps them into existing `ClaimEvidenceNote` records for Total Export manifests in deterministic queue order, the UI helper emits safe metadata-only rows/status summaries, the receipt helper emits deterministic `CaptureActionLogEvent` provenance metadata with only safe counts/flags/role/status rows, and the flow helper composes claim-note/UI-row/receipt counts into summary-only review metadata. `build_closed_loop_source_chain_review_summary(...)` adds a deterministic review-required summary of explicit propagated-source, source-chain-gap, and closed-loop flags already recorded on those queue items. This remains metadata-only and local-tested. It does not include raw claim/evidence payloads or full local paths, add visible editor UI, execute classification, infer sensitive attributes, scan folders, move files, call providers/network, claim completed evidence, perform duplicate reporting detection, or run automated source-chain analysis.
- `source_reference_intake.py` records the REV4 preparation pack and supplied browser-extension ZIP references as MODEL_ONLY architecture/licensing/security metadata only. It stores basenames, expected hashes, entry counts, inspected surfaces, high-level architecture patterns, and explicit reference-only/prohibited-use flags. It does not copy proprietary/minified code, bundle assets, port vendor internals, execute extension code, access browser profiles/cookies/credentials, or call live services. `evidence_item_queue.py` now also projects explicit Evidence Item Queue review summaries into deterministic `CaptureActionLogEvent` receipts, `BehaviorActivityRecord` rows, and summary/counts-only activity/provenance flow metadata while preserving USER_REVIEW_REQUIRED status and no-file/no-runtime/no-completion/no-classification flags.
- `ExistingYouTubeOutputReviewMetadata`, `build_youtube_evidence_queue_from_existing_outputs(...)`, `build_youtube_evidence_workflow_review_summary(...)`, `youtube_evidence_queue_metadata_to_action_log_events(...)`, and `build_youtube_evidence_queue_review_flow_summary(...)` in `evidence_item_queue.py` add a local metadata-only bridge, deterministic action-log/provenance receipt projection, and end-to-end review summary from explicitly supplied existing YouTube output status/counts into review-required Evidence Item Queue items. The bridge/receipt/flow records source URL/video-ID presence, output kinds/counts, safe queue item IDs, workflow summary IDs, receipt IDs/event hashes, USER_REVIEW_REQUIRED status, and DERIVED_FROM_EXISTING_YOUTUBE_RUNTIME provenance. It does not call the YouTube runtime, alter existing YouTube behavior, display raw comment/livechat/transcript payloads, record full local paths, claim file artifact/existence, perform live/API/browser execution, run automatic classification, or claim final-evidence state. Runtime wiring from the existing YouTube extractor/export UI remains future.
- `ManualMediaSourceChainLink` in `evidence_item_queue.py` adds local manual media source-chain link metadata before any fingerprinting or automated matching layer: operator-supplied links can record safe queue/source item IDs, relation kind, direction, review-required status, manual provenance, and note-presence/category metadata. `manual_media_source_chain_links_to_ui_rows(...)` and `build_manual_media_source_chain_review_summary(...)` emit deterministic metadata-only review rows/summaries, `manual_media_source_chain_links_to_action_log_events(...)` projects them into deterministic `CaptureActionLogEvent` provenance receipts with safe row metadata and manual link IDs, and `build_manual_media_source_chain_review_flow_summary(...)` composes links, rows, summary, and receipts into a summary/counts-only end-to-end review flow. `ManualPublisherFramingCorrectionNote`, `manual_publisher_framing_corrections_to_ui_rows(...)`, `build_manual_publisher_framing_correction_review_summary(...)`, `manual_publisher_framing_corrections_to_action_log_events(...)`, and `build_manual_publisher_framing_correction_review_flow_summary(...)` add deterministic metadata-only disputed-framing/source-author correction note rows, summaries, action-log/provenance receipts, and end-to-end summary/counts-only review flow metadata with safe queue/related item IDs, correction kind, recorded-source/correction presence flags, correction note IDs, manual provenance, and USER_REVIEW_REQUIRED status. Automated source-author detection, automated publisher-framing analysis, automated correction, automated matching, fingerprint matching, duplicate detection, automatic classification, sensitive inference, raw correction/media/evidence payloads, full local paths, live/API/browser/archive/download/OCR claims, and completed/verified evidence claims remain false or absent; no visible editor or correction-text import/display workflow is added.
- `source_capture_contract.py`: local-only capture-option contract records adapter support, execution mode, provenance, completeness status, and warnings for selected options; it does not fetch, scrape, capture screenshots, call archives/providers, download media, handle credentials, or wire into the GUI.
- `source_adapter_gap_analysis.py` and CLI: local-only gap analysis over current adapters and future platform/preservation categories, including Substack/newsletter, review platforms, ExportComments-style social categories, and ArchiveBox-style preservation backends.
- `preservation_backend_plan.py` and CLI: local-only preservation backend planning for manual local files, ArchiveBox-style self-hosted stores, and desired formats such as HTML, PDF, PNG, TXT, JSON, WARC, media, and SQLite metadata; no ArchiveBox execution, fetch/capture/network/archive calls, scraping, credential work, or GUI wiring.
- `total_export_prepare_cli.py`: local-only preservation metadata listing and preservation-plan explanation modes for the same backend/format metadata; no package creation is required for those modes.
- Visual preservation note: Facebook/social comment modals may use nested scroll containers, so Page Up/Page Down or full-page screenshot tools can capture only the visible container viewport unless the container itself is focused/scrolled. Future capture metadata should distinguish visible screenshot, full-page screenshot, scrollable-container screenshot, stitched/multi-image capture, selected-DOM/print-cleaned HTML, raw saved HTML, and manual evidence bundles.
- `capture_method_metadata.py`: local metadata catalog for those seven manual capture/evidence methods, with output kinds, limitations, and future-automation candidacy only; it performs no capture or browser behavior.
- Media preservation note: future webpage media capture should expose an explicit `all` versus `select` choice so users can decide whether to download every discovered image/video/media asset or only chosen assets; it must be opt-in and never default to downloading all media.
- Preservation backend plans now record local-only media intent as `none`, `select`, or explicit `all`; this metadata performs no discovery/download and does not authorize capture automation.
- Preservation backend plans now also represent multiple selected manual/planned capture methods from `capture_method_metadata.py`, including known nested-container limitations, without executing capture or browser behavior.
- `preservation_evidence_bundle.py` and its CLI describe planned, manually supplied, or external evidence artifacts and capture-method limitations without touching files or performing capture/network/browser/archive behavior.
- Capture-option metadata and deterministic selection validation.
- Source capture plans and local provenance records.
- Package IDs/folders, manifest read/write/round-trip, asset registration, and duplicate-safe updates.
- Package-shell preparation, final local validation, summaries, README markers, source-plan reports, and inventory reports.
- Human-readable and JSON developer output through `total_export_prepare_cli.py`.
- Metadata listing and source-plan explanation modes that do not create packages.
- Existing-package inspection and deterministic ZIP creation for explicitly selected local package folders.
- ZIP inspection with unsafe-entry checks and no extraction.
- Explicit `.sha256` and `.inspection.json` sidecar generation.
- Review-bundle build, verification, folder verification, batch planning/building, and batch reconciliation.
- Local bundle indexing and expected-bundle reconciliation, each with text/Markdown/JSON CLIs.

Important boundaries:

- Total Export package and review helpers operate on explicit local inputs.
- ZIP inspection does not extract files.
- Network/archive/source capture is not performed by these local package/review helpers.
- `total_export_prepare_cli.py` remains a local developer CLI and is not GUI wiring.
- Generated output folders are ignored where documented; tests use temporary directories.
- The mature existing YouTube comments/live-chat/export flow is separate and must be preserved.

See `TOTAL_EXPORT_DEV_CLI_EXAMPLES.md` for CMD-friendly prepare, review, inspect, ZIP, sidecar, verification, and batch examples.

## Source Evidence Model Skeleton State

Three planned source-evidence areas now have standalone, local-only schema implementations with focused tests:

- `evidence_item_queue.py` and `evidence_item_queue_test.py` (`7af8eea` plus later review-summary hardening): immutable queue-item, link, ASR-pairing, role, lifecycle-status, Total Export include/exclude metadata, and deterministic `build_evidence_item_queue_review_summary(...)` output over explicit queue records. Source URLs, local media, reference text, transcript/subtitle candidates, ASR results, screenshots/snapshots, archive URLs, packages, and taxonomy suggestions remain distinct roles. The review summary reports only safe IDs/counts/presence flags and performs no file checks, deletion, persistence, GUI work, ASR execution, capture, archive access, Total Export wiring, full-path display, automatic classification, or final-evidence claim.
- `access_keys_metadata.py` and `access_keys_metadata_test.py` (`66871b6`): non-secret access-mode, credential-status, connection-test-status, provider/source/archive/browser-assisted-capture metadata, deterministic serialization, and text/Markdown/JSON rendering. It stores no key, token, password, cookie, session, authorization header, or browser-profile path and performs no credential test, OAuth, provider call, archive call, source fetch, or GUI wiring.
- `access_keys_view_model.py` and `access_keys_view_model_test.py` (`8d11a4b`): GUI-independent searchable/filterable platform sections, selected-entry state, safe capability/status presentation, empty/duplicate diagnostics, and deterministic dictionary output over the existing non-secret catalog. It creates no widgets, stores no credential values, performs no connection test or external call, and does not wire into the sidebar/runtime.
- `access_keys_dialog.py`, `access_keys_dialog_test.py`, and narrow `main.py` wiring (`1b57e74`): preserve the existing masked YouTube API-key entry and add a separate `KEYS` button plus single reusable `Access & Keys` window. The window renders existing non-secret ASR-provider/source-adapter metadata with search, family filters, selection details, empty states, and duplicate diagnostics; it adds no credential-value widgets/actions, storage, migration, connection execution, provider/network/browser/archive behavior, or unrelated runtime changes.
- `access_keys_catalog.py` and `access_keys_catalog_test.py` (`0ff528d`): complete planned non-secret service catalog with deterministic top-level sections/subgroups, aliases, planned-versus-implemented status, separate archive check/submit entries, browser-assisted-capture placeholders, and no credential or external execution.
- The same `0ff528d` interaction pass replaces the partially clickable family control with a full-width selector, keeps list/detail containers stable, updates selection/details in place, removes the synchronous blank/loading flash, restores hover feedback, and preserves existing API-key, YouTube, ASR, and export behavior.
- `ee945fe` fixes the remaining short-family visibility defect by resetting the catalog scroll position before relayout and once after idle, coalescing/cancelling pending callbacks, and adding a deterministic regression. Manual testing confirmed ASR Providers, News Websites, Archive Services, and Browser-Assisted Capture appear immediately after switching from a long scrolled family.
- `credential_architecture.py`, `credential_architecture_test.py`, and `CREDENTIAL_SECURITY_AUDIT.md` (`ef92017`) implement approved row 2A as a non-secret architecture and existing-code audit: stable credential IDs for YouTube and catalogued cloud ASR providers, backend/migration/redaction/sink policy, safe presence labels, eight findings, deterministic serialization/rendering, and explicit row 2B/2C/later-network boundaries. They perform no credential reads/writes, storage, migration, clearing, GUI secret handling, provider testing, OAuth, browser access, or network activity and change no existing runtime file.
- `credential_runtime_status.py`, `credential_runtime_status_test.py`, metadata/test updates, and narrow `access_keys_dialog.py`/`main.py` wiring (`7c1db2a`) implement approved row 2B. The Access & Keys window receives only read-only configured/missing/backend-unavailable/error states and safe provenance. YouTube presence comes from the API key already loaded into the masked sidebar field plus safe storage information; cloud ASR checks named environment-variable presence only. No value is rendered or retained, and no save, clear, migration, connection test, provider call, OAuth, browser, or network behavior was added.
- `credential_store.py` and `credential_store_test.py` (`29af218`) implement approved row 2C1 as secure-store infrastructure for the already-catalogued cloud-ASR credential IDs. It provides deterministic non-secret keyring locators, explicit `youtube_data_api_key` rejection, a session-only in-memory test backend, an injected/system-keyring backend that fails closed, explicit save/overwrite/clear result statuses, and fixed non-secret diagnostics. At the row 2C1 checkpoint it had no production caller; row 2C2 later invokes it only for explicit cloud-ASR Save/Clear and safe presence probing. It does not change settings, provider logic, existing YouTube workflow, connection testing, OAuth, browser access, or network behavior.
- `access_keys_dialog.py`, `access_keys_dialog_test.py`, `credential_runtime_status.py`, `credential_runtime_status_test.py`, `credential_store.py`, `credential_store_test.py`, and narrow `main.py` wiring (`97de48d`) implement approved row 2C2. Access & Keys now shows masked cloud-ASR credential Save/Clear controls only for supported catalogued cloud-ASR entries. The field is masked from widget creation onward, has no reveal/copy control, never preloads stored values, clears after successful Save and Clear paths, stays empty after close/reopen, and reports only fixed non-secret outcomes. The secure store is invoked only for explicit cloud-ASR Save/Clear and safe presence probing; no provider execution path consumes stored credentials.
- Row 2C2 also refreshes safe configured/missing/unavailable/error status and provenance after actions, preserves read-only environment-variable presence reporting, and handles deterministic keyring/environment precedence so clearing secure-store state does not falsely report missing when an environment credential is still configured. Tests use fake/injected keyring behavior and do not access the user's real keyring.
- Manual row 2C2 verification found an initial plaintext cloud credential rendering defect. The masking defect was fixed before `97de48d`, automated tests were strengthened to verify effective wrapper and internal-entry masking, and the corrected manual retest passed for masked input, Save, configured status, close/reopen without value preload, Clear, missing status, local entries without controls, existing YouTube field remaining masked/unchanged, and no obvious destructive pane rebuild regression.
- `core/settings.py`, `youtube_credential_migration.py`, `youtube_credential_migration_test.py`, `settings_keyring_fallback_test.py`, `credential_runtime_status.py`, `credential_runtime_status_test.py`, `main.py`, `main_export_state_test.py`, and `access_keys_dialog_test.py` (`3abb49d`) implement the approved secure YouTube credential migration and legacy-cleanup boundary. New/updated YouTube saves are secure-only with no plaintext fallback; legacy plaintext migration is explicit and user-controlled; cleanup removes legacy plaintext only after secure save plus safe non-secret presence verification; Clear reports secure-only, legacy-only, both-copy, missing, backend-unavailable/error, malformed-settings, and partial-failure states truthfully.
- The YouTube API-key field is permanently masked, has no reveal/copy/unmask control, and never preloads stored credentials. After startup, reopen, status refresh, migration, and Clear, configured status can persist while the field remains empty. Existing extraction compatibility is preserved by resolving configured credentials internally at action time without inserting them into the widget; typed draft input still wins, and legacy-only credentials remain internally usable before explicit migration.
- Final YouTube security corrections before `3abb49d` removed the obsolete reveal/unmask path, removed stored-key UI preload, preserved legacy plaintext on secure-delete failure, refused destructive Clear for malformed settings, and avoided downgrading keyring read failures to false missing states. Manual production verification used `python main.py` with the venv active; an explicit equivalent is `.\venv\Scripts\python.exe main.py`. The corrected manual pass confirmed masked Save, configured status, empty field after restart, Access & Keys presence/provenance, no settings-root plaintext key, and no credential value exposure.
- `credential_consumption.py`, `credential_consumption_test.py`, `credential_runtime_status.py`, `credential_runtime_status_test.py`, `credential_store.py`, and `credential_store_test.py` (`a1cf07d`) implement the local-only cloud-ASR credential-consumption prerequisite. It resolves a credential only during an explicit trusted internal callback action, rejects YouTube/local/unknown credential IDs, never returns credential values or callback results in public dataclasses/dicts, performs no lookup at import or construction, and caches no secret. Public result fields are fixed and non-secret: `credential_id`, `status`, `provenance`, `safe_diagnostic`, `provider_id`, `callback_invoked`, `action_succeeded`, and `scope`.
- Cloud-ASR action-time consumption now matches safe status precedence: a present non-empty secure keyring value wins over environment values; a genuinely absent secure value may fall back to a non-empty environment value where supported; backend unavailable/error states can still use the established environment fallback; an empty or whitespace-only secure value is an invalid secure state that does not invoke the callback and does not fall back to environment. The callback is trusted internal code, not a security sandbox. No real provider currently consumes credentials, and no provider client, connection test, API request, upload, or network behavior was added.
- `asr_provider_action.py` and `asr_provider_action_test.py` (`058af01`) implement the explicit provider-action seam described above.
- `asr_connection_test.py` and `asr_connection_test_test.py` (`f709f8e`) implement the explicit connection-test seam described above. The seam is test-dispatchable through injected trusted testers only; it does not add or imply a production provider connection test.
- `elevenlabs_scribe_provider.py` and `elevenlabs_scribe_provider_test.py` (`f21e578`) implement the ElevenLabs Scribe v2 provider-specific fake-transport-tested adapter described above. It does not add production HTTP transport, SDK/client, live API request, real credential use, media upload, GUI action, Test Connection wiring, or network behavior.
- `evidence_database_taxonomy.py` and `evidence_database_taxonomy_test.py` (`e63def4`): read-only database-root/taxonomy metadata, arbitrary user-defined dimensions, valid unknown/not-identified states, dry-run reclassification and alias-normalization suggestions, sensitive-classification safeguards, review states, preserved history, and queue/package/source references. Paths are descriptive metadata only; the model performs no scanning, automatic classification, persistence, reclassification execution, or file movement.
- `evidence_database_index.py`, `evidence_database_index_test.py`, and `EVIDENCE_DATABASE_PHASE1_AUDIT.md` (`fbfd0d` through `4cf2e98`): Evidence Database Phase 1 local foundations. This adds deterministic JSON/dict contracts for registered roots, taxonomy versions, stable item identities, path history, classification state, evidence basis, placement/reclassification proposals, index records, and manifests; an atomic JSON index store using temp-file plus replace semantics; dry-run placement/classification proposal builders; fixture-path hierarchy recognition for renamed/nested/missing/unknown folders; and converters from existing evidence queue, source-resource row, and Total Export manifest metadata. This is model/local-fixture tested only: no broad folder scan, no UI workflow, no automatic classification, no file move, no live capture, no archive/provider call, no credential access, and no sensitive-attribute inference.
- `evidence_database_review.py`, `evidence_database_review_test.py`, and `EVIDENCE_DATABASE_PHASE2_REVIEW_AUDIT.md` (`bc0b633` through `58864e6`): Evidence Database Phase 2 review/controller foundations. This adds deterministic review session, root-registration draft/result, preview request/result/row, review decision, apply-plan entry, non-executing apply plan, and dry-run apply result contracts; temp-directory-tested root registration review; explicit-record-only preview grouping; and decision/apply-plan helpers that preserve old/new path history while executing no classification changes and no file moves. EDUI4 found no clean current UI hook that would avoid broader layout/runtime work, so the UI/window remains deferred. This is controller/local-fixture tested only: no broad folder scan, no real indexing, no UI workflow, no automatic classification execution, no file move, no live capture, no archive/provider call, no credential access, and no sensitive-attribute inference.
- `EVIDENCE_DATABASE_UI_HOOK_AUDIT.md`, `evidence_database_review_ui.py`, and `evidence_database_review_ui_test.py` (`3f245b4` through `3c015e1`): Evidence Database Phase 3 deferred UI hook resolution. The audit identifies the standalone review scaffold as the smallest safe hook and defers visible `main.py` placement because the current UPDATES, KEYS/ACCOUNTS, EXPORT, FILES sidebar and FILES/EXPORT workflows are already protected. The scaffold is UI_SCAFFOLD_ONLY and LOCAL_FIXTURE_TESTED through pure state/controller/text helpers plus an optional Tk window factory. It exposes registered-root counts, preview counts by state, decision/apply-plan summaries, dry-run warnings, and destructive-action-not-implemented status. It performs no broad scan, real indexing, file move, automatic classification execution, credential access, live capture, archive/provider call, or sensitive-attribute inference.
- `EVIDENCE_DATABASE_DEMO_IMPORT_EXPORT_AUDIT.md`, `evidence_database_demo_fixture.py`, `evidence_database_review_io.py`, and focused tests (`e74c994` through `4bf4c51`): Evidence Database Phase 4 synthetic demo/import-export support. This adds SYNTHETIC_FIXTURE_ONLY records for `unknown`, `not_evidenced`, `proposed`, `user_confirmed`, `rejected`, and `superseded`; deterministic JSON review-session export with payload hashes; import validation for schema, hashes, dry-run flags, supplied-records-only flags, non-executing apply plans, and secret/destructive-looking keys; and standalone scaffold helpers for demo/export/import controllers. Imports reconstruct review objects only; they do not execute decisions, scan folders, move files, apply classification changes, access credentials, call providers/network, or infer sensitive attributes.
- `EVIDENCE_DATABASE_PHASE5_HARDENING_AUDIT.md` plus focused evidence/UI/workflow tests (`fb848a8` through `55e5328`): Evidence Database Phase 5 regression hardening. Import/export tests now cover schema mismatches, missing/incorrect hashes, compatible unknown top-level fields, malformed record payloads, destructive-looking flags, and nested secret-like keys. Scaffold tests cover empty sessions, duplicate record IDs, missing root metadata, sparse classification groups, rejected/superseded apply-plan target summaries, and persistent dry-run warnings. `main_source_resource_ui_test.py` now guards that no visible Evidence Database hook/import/callback was added to `main.py` while preserving the UPDATES, KEYS/ACCOUNTS, EXPORT, FILES order. This is REGRESSION_HARDENED / LOCAL_FIXTURE_TESTED only and adds no runtime evidence-management workflow.

The queue, taxonomy, evidence database index, and evidence database review layers remain local-only schema/index/controller/UI-scaffold/demo/import-export/regression-hardened foundations rather than implemented runtime evidence-management workflows. Access & Keys has the bounded catalog/view/window, row 2A credential architecture/audit, row 2B read-only non-secret status/provenance overlay, row 2C1 secure-store infrastructure, row 2C2 masked cloud-ASR Save/Clear controls, committed secure YouTube credential migration/legacy cleanup, local-only cloud-ASR credential-consumption prerequisite, explicit provider-action coordinator seam, local-only connection-test coordinator seam, ElevenLabs Scribe v2 fake-transport-tested provider adapter, production-capable official SDK transport, one-call live verification, and explicit user-facing Online ASR action wiring described above. Cloud-ASR row 2C2 Save/Clear/status behavior remains unchanged. No GUI Test Connection wiring, account/quota/model request, provider catalog redesign, OAuth, browser-profile access, future reveal/copy/export behavior, new non-ASR credential persistence workflow, evidence database visible main-window hook, broad evidence database scan, classification execution, or file movement exists. User-facing Test Connection wiring, broader provider access, and evidence database runtime operations remain unimplemented and separately approval-gated. `SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md` should continue to distinguish implemented secure storage/UI/consumption/action/connection-test/fake-transport adapter/SDK-transport/Online-ASR behavior from later Test Connection and external-access gaps.

## Upstream v2.1.1 Parity State

`UPSTREAM_V2_1_1_AUDIT.md` is the original local parity audit and should be read as the baseline before the later regression/fix commits.

Completed follow-up work recorded after the audit:

- `daf47fd`: local regression tests for extractor error handling, newest-sort/max-comment behavior, and spam false positives.
- `494f5fa`: structured quota/daily-limit error classification and a short-organic-praise campaign false-positive guard.
- `f06f181`: export blocking during active fetch/cancel states and keyring runtime fallback, with mocked/local tests.

Relevant tests:

- `extractor_error_handling_test.py`
- `extractor_sort_limit_test.py`
- `spam_filter_regression_test.py`
- `main_export_state_test.py`
- `settings_keyring_fallback_test.py`

Items still requiring targeted investigation before any future port include packaging/console-entry-point coverage, Linux icon fallback, full window-close/background-fetch behavior, and campaign performance guards. Reinspect current code and tests before relying on the audit's older status labels.

## Source Preservation And Local Evidence State

All preservation/evidence work is local metadata/reporting only:

- Manual archive URL records store user-supplied archive metadata and user-entered statuses. They do not check or submit archives.
- Local media records reference files already on disk; registration/verification is explicit and local.
- Local media verification reports path, size, and optional hash consistency without downloading media.
- Preservation plans compare source URLs with archive/media metadata and produce manual follow-up actions.
- `PRESERVATION_METADATA_SEED.json` and its report generator provide deterministic local fixtures and text/Markdown/JSON output.
- Bundle index/reconciliation helpers report local ZIP and sidecar state without ZIP extraction.
- The evidence manifest helper aggregates source, archive, media, verification, and bundle metadata without copying or building packages.
- `total_export_evidence_manifest_cli.py` reads local JSON and renders Markdown/text/JSON with explicit-output-only writes.

Missing metadata/files are uncertainty and manual follow-up signals, not proof of remote deletion, nonexistence, or unavailability.

See `SOURCE_PRESERVATION_CURRENT_STATE.md` for the detailed preservation helper/CLI/test index and `SOURCE_PRESERVATION_ROADMAP.md` for phase boundaries.

## Important Documentation Index

| Document | Purpose |
| --- | --- |
| `CURRENT_DEV_STATE.md` | Detailed cumulative project state and decisions. |
| `ASR_TEST_PLAN.md` | ASR acceptance policy, hardware paths, manual provider results, and decisions. |
| `ASR_PROVIDER_LEADERBOARD_NOTES.md` | External/user-supplied ASR research leads and local snapshot. |
| `ASR_PROVIDER_STATUS_NOTES.md` | Local/manual accepted/candidate/rejected/blocked/needs-review semantics and current provider status handling. |
| `ASR_COMPARISON_REPORT_FORMAT.md` | Local ASR comparison schema, statuses, ranking, and CLI usage. |
| `ASR_REPORTING_CURRENT_STATE.md` | Current local ASR reporting helper/CLI/test index and safe next milestones. |
| `ASR_MANUAL_RESULTS_SEED.md` | Scope and policy for checked-in manual ASR result records. |
| `ASR_DECISION_SUMMARY.md` | Local/manual ASR threshold and provider-status decision summary semantics. |
| `TOTAL_EXPORT_DEV_CLI_EXAMPLES.md` | CMD-friendly Total Export developer CLI examples. |
| `TOTAL_EXPORT_BUNDLE_INDEX.md` | Local ZIP/sidecar index semantics and CLI. |
| `TOTAL_EXPORT_BUNDLE_INDEX_RECONCILIATION.md` | Expected bundle reconciliation semantics and CLI. |
| `SOURCE_PRESERVATION_CURRENT_STATE.md` | Detailed local preservation/evidence handoff and test index. |
| `SOURCE_PRESERVATION_ROADMAP.md` | Preservation phase boundaries and deferred behavior. |
| `SOURCE_CONTEXT_GLOSSARY_CURRENT_STATE.md` | Current local source URL, adapter, capture plan, provenance, context/glossary, and source-evidence model/test index. |
| `SOURCE_EVIDENCE_ROADMAP.md` | Cross-source evidence, capture, access, queue, taxonomy, and preservation roadmap. |
| `SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md` | Requirement-to-document/implementation coverage and next-gap audit. |
| `EVIDENCE_ITEM_QUEUE_UI_SPEC.md` | Future evidence queue UI/workflow contract; current implementation is local schema plus deterministic review-summary metadata only. |
| `ACCESS_KEYS_MANAGER_SPEC.md` | Access & Keys UI/workflow contract; current implementation includes bounded metadata/catalog/view/window presentation plus row 2C2 masked cloud-ASR Save/Clear controls only for supported cloud-ASR entries. |
| `CREDENTIAL_SECURITY_AUDIT.md` | Approved row 2A audit of the existing YouTube settings/keyring/plaintext path plus stable non-secret credential architecture, findings, storage/migration/redaction rules, and later approval boundaries; no runtime credential handling. |
| `EVIDENCE_DATABASE_TAXONOMY_SPEC.md` | Future database taxonomy/index/reclassification contract; current implementation is read-only schema/dry-run metadata only. |
| `PRESERVATION_METADATA_SEED.md` | Local preservation fixture and report-generator usage. |
| `EVIDENCE_PACKAGE_MANIFEST.md` | Local evidence manifest helper and CLI semantics. |
| `UPSTREAM_V2_1_1_AUDIT.md` | Historical upstream parity audit and recommended regression areas. |

## Important Helper, CLI, And Test Index

| Area | Helpers/CLIs | Primary tests |
| --- | --- | --- |
| ASR comparison/decision/terms | `asr_comparison_report.py`, `asr_comparison_report_cli.py`, `asr_decision_summary.py`, `asr_decision_summary_cli.py`, `asr_term_coverage_summary.py`, `asr_term_coverage_summary_cli.py`, `asr_combined_report_cli.py` | `asr_comparison_report_test.py`, `asr_comparison_report_cli_test.py`, `asr_manual_results_seed_test.py`, `asr_decision_summary_test.py`, `asr_decision_summary_cli_test.py`, `asr_term_coverage_summary_test.py`, `asr_term_coverage_summary_cli_test.py`, `asr_combined_report_cli_test.py` |
| Source/context/glossary | `youtube_url_utils.py`, `source_adapters.py`, `source_adapter_capability_report.py`, `source_adapter_capability_report_cli.py`, `source_adapter_gap_analysis.py`, `source_adapter_gap_analysis_cli.py`, `source_capture_plan.py`, `source_capture_plan_cli.py`, `source_plan_provenance.py`, `context_glossary.py`, `context_glossary_cli.py` | `youtube_url_utils_test.py`, `source_adapters_test.py`, `source_adapters_registry_test.py`, `source_adapter_capability_report_test.py`, `source_adapter_capability_report_cli_test.py`, `source_adapter_gap_analysis_test.py`, `source_adapter_gap_analysis_cli_test.py`, `source_capture_plan_test.py`, `source_capture_plan_cli_test.py`, `source_plan_provenance_test.py`, `context_glossary_test.py`, `context_glossary_cli_test.py` |
| Total Export package shell | `total_export_prepare_cli.py`, manifest/package/workflow/validation/summary/inventory modules | `total_export_prepare_cli_test.py` and focused `total_export_*_test.py` files |
| Review bundles and ZIPs | `total_export_review_bundle.py`, verification/folder verification, `total_export_zip_inspect.py`, `total_export_zip_sidecar.py` | Review-bundle, ZIP-inspection, sidecar, folder, and batch tests |
| Bundle index/reconciliation | `total_export_bundle_index.py`, both local CLIs, `total_export_bundle_index_reconcile.py` | Bundle index/reconciliation helper and CLI tests |
| Manual archive/local media | `total_export_manual_archive.py`, `total_export_local_media.py`, `total_export_local_media_verify.py` and verification CLI | Manual archive, local media, and verification helper/CLI tests |
| Preservation plans/seeds | `total_export_preservation_plan.py`, plan CLI, `preservation_metadata_seed_report.py` | Plan helper/CLI, seed, and seed-report tests |
| Evidence manifest | `total_export_evidence_manifest.py`, `total_export_evidence_manifest_cli.py` | Evidence manifest helper and CLI tests |
| Evidence item queue schema | `evidence_item_queue.py` | `evidence_item_queue_test.py` |
| Behavior/activity log schema | `evidence_activity_log.py` | `evidence_activity_log_test.py`; MODEL_ONLY deterministic review-required activity metadata, privacy policy defaults, stable summaries, and no runtime logging, telemetry, persistence, file reads/checks/moves, raw payloads, full local paths, classification, or completion claims |
| Access & Keys metadata schema | `access_keys_metadata.py` | `access_keys_metadata_test.py` |
| Access & Keys catalog/view/window | `access_keys_catalog.py`, `access_keys_view_model.py`, `access_keys_dialog.py`, narrow `main.py` wiring | `access_keys_catalog_test.py`, `access_keys_view_model_test.py`, `access_keys_dialog_test.py`, `main_export_state_test.py`; includes short-family scroll-reset regression |
| Credential architecture/security audit | `credential_architecture.py`, `CREDENTIAL_SECURITY_AUDIT.md` | `credential_architecture_test.py`; stable non-secret descriptors/policies/redaction/status helpers |
| Read-only credential runtime status | `credential_runtime_status.py`, Access & Keys metadata/dialog, narrow `main.py` wiring | `credential_runtime_status_test.py`, Access & Keys regressions, `main_export_state_test.py`; safe presence/provenance only, with no values, writes, migration, tests, provider calls, or network access |
| Secure credential store and masked cloud-ASR controls | `credential_store.py`, `credential_runtime_status.py`, `access_keys_dialog.py`, narrow `main.py` wiring | `credential_store_test.py`, `credential_runtime_status_test.py`, `access_keys_dialog_test.py`, `main_export_state_test.py`; deterministic cloud-ASR keyring locators, explicit YouTube rejection, test-only/session-only memory backend, fail-closed injected/system-keyring backend, fixed non-secret result statuses, masked cloud-ASR Save/Clear controls, safe presence/provenance refresh, and no provider/API/network execution |
| Secure YouTube credential migration | `core/settings.py`, `youtube_credential_migration.py`, `credential_runtime_status.py`, narrow `main.py` wiring | `youtube_credential_migration_test.py`, `settings_keyring_fallback_test.py`, `credential_runtime_status_test.py`, `main_export_state_test.py`, `access_keys_dialog_test.py`; secure-only Save/Update, explicit legacy migration/cleanup, no plaintext fallback, no UI preload, no reveal/unmask path, truthful partial-failure states, and existing extraction compatibility through internal action-time resolution |
| Cloud-ASR credential consumption prerequisite | `credential_consumption.py`, `credential_runtime_status.py`, `credential_store.py` | `credential_consumption_test.py`, `credential_runtime_status_test.py`, `credential_store_test.py`; explicit trusted-callback credential resolution, secure-store/environment precedence aligned with safe status, invalid empty/whitespace secure-value blocking, no secret-bearing public results, no provider client, no upload, and no network behavior |
| Explicit ASR provider-action and connection-test seams | `asr_provider_action.py`, `asr_connection_test.py` | `asr_provider_action_test.py`, `asr_connection_test_test.py`; explicit injected-executor/injected-tester seams, validation-before-credential-lookup, no production provider implementation, no production connection tester, no GUI caller, no API/network/upload behavior, and no secret-bearing public results |
| ElevenLabs Scribe v2 provider adapter, SDK transport, and Online ASR action | `elevenlabs_scribe_provider.py`, `elevenlabs_scribe_transport.py`, `main.py` | `elevenlabs_scribe_provider_test.py`, `elevenlabs_scribe_transport_test.py`, `online_asr_ui_test.py`; provider-specific fake-transport-tested executor plus production-capable official SDK transport and an explicit local-file Online ASR UI action. The UI dispatches only after `Transcribe`, uses `ASRProviderActionCoordinator` and secure credential consumption, routes results to the existing transcript display path, blocks duplicate starts while busy, and adds no GUI Test Connection, account/quota/model request, provider catalog redesign, startup/background call, package installation, or unrelated provider behavior |
| Evidence database taxonomy schema | `evidence_database_taxonomy.py` | `evidence_database_taxonomy_test.py` |
| Evidence database index foundations | `evidence_database_index.py`, `EVIDENCE_DATABASE_PHASE1_AUDIT.md` | `evidence_database_index_test.py`; deterministic contracts, atomic JSON store, dry-run proposals, fixture hierarchy recognition, and queue/source-resource/Total Export converters only |
| Evidence database review controller foundations | `evidence_database_review.py`, `EVIDENCE_DATABASE_PHASE2_REVIEW_AUDIT.md` | `evidence_database_review_test.py`; deterministic review/session/root/preview/decision/apply-plan contracts, temp-root registration review, explicit-record preview grouping, and non-executing apply plans only |
| URL normalization | `youtube_url_utils.py` | `youtube_url_utils_test.py` |
| Upstream parity | Extractor/spam/settings/export-state code | Five local/mocked parity tests listed above |

## Latest Known Commit Chain

```
38aee73 Add ElevenLabs Scribe v2 SDK transport
f21e578 Add ElevenLabs Scribe v2 provider adapter
f709f8e Add explicit ASR connection test seam
058af01 Add explicit ASR provider action seam
a1cf07d Add cloud ASR credential consumption
ea94263 Close secure YouTube credential migration milestone
3abb49d Add secure YouTube credential migration
5bd23c3 Close cloud ASR credential controls milestone
97de48d Add cloud ASR credential controls
2dfbb4d Close secure credential store backend milestone
29af218 Add secure credential store backend
7c1db2a Add read-only credential status integration
d610ddf Close credential architecture audit milestone
ef92017 Add credential architecture and security audit
447f031 Close Access Keys presentation milestone
ee945fe Fix Access Keys short-family visibility
```


## Local Verification Commands

Run from Windows CMD with the project virtual environment active. These checks are local-only.

ASR comparison reports and seed:

```cmd
python -m py_compile asr_comparison_report.py asr_comparison_report_test.py asr_comparison_report_cli.py asr_comparison_report_cli_test.py asr_manual_results_seed_test.py & python asr_comparison_report_test.py & python asr_comparison_report_cli_test.py & python asr_manual_results_seed_test.py
```

Preservation and evidence manifest:

```cmd
python -m py_compile total_export_evidence_manifest.py total_export_evidence_manifest_test.py total_export_evidence_manifest_cli.py total_export_evidence_manifest_cli_test.py total_export_manual_archive.py total_export_manual_archive_test.py total_export_local_media.py total_export_local_media_test.py total_export_local_media_verify.py total_export_local_media_verify_test.py total_export_local_media_verify_cli.py total_export_local_media_verify_cli_test.py total_export_preservation_plan.py total_export_preservation_plan_test.py total_export_preservation_plan_cli.py total_export_preservation_plan_cli_test.py preservation_metadata_seed_report.py preservation_metadata_seed_report_test.py preservation_metadata_seed_test.py & python total_export_evidence_manifest_test.py & python total_export_evidence_manifest_cli_test.py & python total_export_manual_archive_test.py & python total_export_local_media_test.py & python total_export_local_media_verify_test.py & python total_export_local_media_verify_cli_test.py & python total_export_preservation_plan_test.py & python total_export_preservation_plan_cli_test.py & python preservation_metadata_seed_report_test.py & python preservation_metadata_seed_test.py
```

Bundle index and reconciliation:

```cmd
python -m py_compile total_export_bundle_index.py total_export_bundle_index_test.py total_export_bundle_index_cli.py total_export_bundle_index_cli_test.py total_export_bundle_index_reconcile.py total_export_bundle_index_reconcile_test.py total_export_bundle_index_reconcile_cli.py total_export_bundle_index_reconcile_cli_test.py youtube_url_utils.py youtube_url_utils_test.py & python total_export_bundle_index_test.py & python total_export_bundle_index_cli_test.py & python total_export_bundle_index_reconcile_test.py & python total_export_bundle_index_reconcile_cli_test.py & python youtube_url_utils_test.py
```

Source-evidence model skeletons:

```cmd
python -m py_compile evidence_item_queue.py evidence_item_queue_test.py access_keys_metadata.py access_keys_metadata_test.py access_keys_catalog.py access_keys_catalog_test.py access_keys_view_model.py access_keys_view_model_test.py access_keys_dialog.py access_keys_dialog_test.py credential_architecture.py credential_architecture_test.py credential_runtime_status.py credential_runtime_status_test.py credential_store.py credential_store_test.py main.py evidence_database_taxonomy.py evidence_database_taxonomy_test.py evidence_database_index.py evidence_database_index_test.py evidence_schema.py evidence_schema_test.py & python evidence_item_queue_test.py & python access_keys_metadata_test.py & python access_keys_catalog_test.py & python access_keys_view_model_test.py & python access_keys_dialog_test.py & python credential_architecture_test.py & python credential_runtime_status_test.py & python credential_store_test.py & python main_export_state_test.py & python evidence_database_taxonomy_test.py & python evidence_database_index_test.py & python evidence_schema_test.py
```

Upstream parity regressions:

```cmd
python -m py_compile extractor_error_handling_test.py extractor_sort_limit_test.py spam_filter_regression_test.py main_export_state_test.py settings_keyring_fallback_test.py extractor.py spam_filter.py core\settings.py & python extractor_error_handling_test.py & python extractor_sort_limit_test.py & python spam_filter_regression_test.py & python main_export_state_test.py & python settings_keyring_fallback_test.py
```

Final repository checks:

```cmd
git diff --check & git status --short
```

Do not add provider/API/network calls to these verification chains.


## Online ASR KEYS/ACCOUNTS Review-Release Section Closeout

Current committed checkpoint: `635b3a1 Add Online ASR Keys Accounts release section closeout` on `v2.6.0-asr-engines`.

This closes the metadata-only Online ASR KEYS/ACCOUNTS review-release section. The added chain covers safe provider/catalogue state, app-state review projection, workflow/package/activity persistence, smoke fixtures, closeout, verifier, next-session handoff, handoff verifier, safety audit, release gate, release-gate persistence, release-gate store CLI, release-section closeout, release-section closeout store, and release-section closeout store CLI.

Boundary preserved across the chain:

- `KEYS/ACCOUNTS` is the main sidebar label; `Access & Keys` remains the dedicated window title.
- `KEYS/ACCOUNTS` lists added providers/accounts only; `Add a provider` is the searchable full catalogue.
- All generated/persisted review outputs are local-only, metadata-only, user-review-required, and execution-gated.
- Safe persistence reports expose filenames, hashes, byte counts, and directory roles, not full local paths.
- CLI readers reject secret-like input fields.
- No credential values are read, revealed, copied, exported, or stored in plaintext by this review chain.
- No provider/API calls, background key tests, media uploads, raw media serialization, live transcription runs, archive/network behavior, browser automation, or completed/verified transcription claims are added.

Working instruction for the next session: continue in roadmap order using larger section-level mega patches that bundle implementation, persistence, CLI, verifier/audit, tests, and documentation where practical. Avoid returning to long sequences of tiny two-file slices unless a failure needs an isolated corrective patch.

## Deferred General GUI Responsiveness

- Access & Keys selection, filtering, hover, popup behavior, and short-family visibility passed focused tests and manual acceptance through `ee945fe`.
- The user still observed broader pauses while moving or closing application windows. Preserve this as a later whole-application GUI responsiveness/performance audit; do not treat it as unfinished row-1 catalog interaction or use it to bypass row 2.

## Safe Next Milestones

1. Row 2A non-secret credential architecture/audit is complete at `ef92017`, row 2B read-only local credential status integration is complete at `7c1db2a`, row 2C1 secure credential-store infrastructure is complete at `29af218`, row 2C2 masked cloud-ASR Save/Clear controls are complete at `97de48d`, secure YouTube credential migration/legacy cleanup is complete at `3abb49d`, the local-only cloud-ASR credential-consumption prerequisite is complete at `a1cf07d`, the explicit provider-action coordinator seam is complete at `058af01`, the local-only connection-test coordinator seam is complete at `f709f8e`, the ElevenLabs Scribe v2 provider-specific fake-transport adapter is complete at `f21e578`, the production-capable official SDK transport is complete at `38aee73`, one-call live verification succeeded, explicit user-facing Online ASR action wiring is complete, the local MSN/source-resource/archive/discussion UI scaffold is complete at `2bb9340`, and the REV4 operational site-capture local/mocked scaffolds now include UI_SCAFFOLD_ONLY operational capture plan preview integration plus EXPORT_METADATA_ONLY / QUEUE_METADATA_ONLY Total Export/evidence queue conversion.
2. REV4 full local regression/documentation closeout is complete for the fixture/model/UI/export metadata stack through Batch 6, and a MODEL_ONLY live/manual site-smoke planning scaffold now records APPROVAL_REQUIRED / MANUAL_OPERATOR_ONLY checklist metadata. Named-site template validation requires explicit site label, non-placeholder source URL, adapter family, named manual action/scope IDs, approver metadata placeholder, and safety-boundary acknowledgement; no real site is approved by this template path, and approval remains manual-operator-only rather than executable. The exact remaining REV4 boundary is any separately approved live/manual site-smoke execution by site/action plus later production hardening. It must not silently expand from the local/mock/planning scaffolds into real HTTP/API retrieval, browser/DevTools/shadow-root execution against live sites, scraping, live comments, live resource enumeration, downloads, real WARC capture/WACZ packaging, real screen recording, webpage/comment screenshots, archive checks/submissions, ArchiveBox execution, credentials, provider/network behavior, protected-output bypass, or evidence-database implementation.
3. Provider work beyond explicit Online ASR transcription and explicit key validation remains separately approval-gated: user-facing Test Connection wiring, automatic/background provider checks, account/quota/model calls, broader provider/API behavior, OAuth/browser access, uploads beyond explicit selected-file transcription, and credential reveal/copy/export behavior are not implied by the source-resource milestone.
4. Do not begin later-row compatibility/reporting work by treating row 2C2 as approval for unresolved credential migration or provider/network layers.
5. Create the next full external session handoff before beginning a substantially different feature area.
6. Keep database scanning, automatic/sensitive classification, credential testing/provider access, archive/downloader/capture, and other networked behavior deferred until explicitly approved, opt-in where applicable, and covered by local/mocked tests.

## Do-Not-Do List

- Do not treat leaderboard leads as accepted providers.
- Do not treat ElevenLabs as accepted; the manual Scribe v2 run remains below the 95% gate, and the SDK transport is production-capable but fake-tested/source-verified only, not live-verified.
- Do not classify AWS Transcribe as quality-rejected; no score exists.
- Do not silently replace transcript text or skip Term QA/user review.
- Do not add network/provider/archive/downloader/source-capture behavior under a local-report or local-scaffold milestone.
- Do not copy/build packages or extract ZIPs through preservation/evidence metadata helpers.
- Do not infer remote deletion or unavailability from missing local records.
- Do not expose or record secrets in docs, logs, manifests, reports, screenshots, or test fixtures.
- Do not describe the queue or database-taxonomy UI/persistence/runtime as implemented. The bounded Access & Keys catalog/view/window, row 2A architecture/audit, row 2B read-only safe status/provenance overlay, row 2C1 secure-store infrastructure, row 2C2 masked cloud-ASR Save/Clear UI, secure YouTube credential migration/legacy cleanup, local-only trusted-callback cloud-ASR credential-consumption prerequisite, explicit injected-executor ASR provider-action seam, local-only injected-tester ASR connection-test seam, ElevenLabs Scribe v2 fake-transport-tested provider adapter, production-capable official SDK transport, one-call live verification, and explicit user-facing Online ASR action wiring are implemented, but user-facing Test Connection wiring, provider access beyond explicit Online ASR transcription, OAuth, browser-profile access, future reveal/copy/export behavior, and new persistence workflows remain unimplemented.
- Do not infer sensitive classifications from weak clues or turn dry-run taxonomy suggestions into automatic file operations.
- Do not modify mature YouTube comment/live-chat/export behavior during unrelated milestones.
- Do not commit before the user has reviewed the patch and local checks.

## Preservation Evidence Bundle Plan Integration

Evidence bundle metadata can now be included in preservation plan reporting and Total Export prepare preservation explanations. This records planned/manual/external artifact IDs, formats, capture-method links, and limitations as local metadata only; it does not inspect files or perform capture/network behavior.


Evidence bundle plan integration now supports item-level role, origin, path hint, and notes metadata. These fields remain labels/metadata only and do not inspect paths or evidence files.


The standalone preservation evidence bundle CLI now supports item-level role, origin, path hint, and notes metadata, matching the preservation-plan integration while remaining stdout/local metadata only.


Evidence item detail parsing/validation is centralized in `preservation_evidence_bundle.py` and reused by all current evidence bundle CLI entry points. This is a local metadata refactor only.


Evidence item detail parsing now has focused regression coverage for malformed `artifact_id=value` specs, duplicate detail entries, and detail metadata that references unknown artifact IDs across the helper and CLI entry points.


Preservation backend plan JSON input may include an `evidence_bundle` object with metadata-only items, roles, origins, path hints, notes, and capture-method IDs. The CLI still only reads the explicit JSON input file and does not inspect referenced evidence paths.


Standalone preservation evidence bundle CLI supports `--input` for explicit local JSON bundle metadata. It rejects combining input JSON with metadata override flags and does not inspect referenced path hints.


Standalone evidence bundle CLI `--input` handling now has regression coverage for missing input files and malformed JSON, in addition to metadata override rejection.


Total Export prepare `--explain-preservation-plan` supports `--evidence-bundle-input` for explicit local evidence bundle JSON metadata. It rejects combining this with evidence-item override flags and keeps path hints descriptive only.


Total Export evidence bundle JSON input coverage now includes missing files, malformed JSON, non-object JSON roots, and rejection of combined metadata override flags.


Total Export evidence bundle input coverage now verifies both text output and `--json` preservation-plan output for item details and local-only scope.


Preservation evidence bundle JSON helper validation is now covered by a focused self-test for malformed items, non-string fields, invalid catalog values, duplicate IDs, and invalid capture-method IDs.


Preservation backend plan CLI input JSON coverage now includes nested evidence bundle item-list validation, item object validation, invalid capture-method IDs, and duplicate artifact IDs.


Total Export `--evidence-bundle-input` coverage now includes nested item-list validation, item object validation, invalid capture-method IDs, and duplicate artifact IDs at the CLI level.


Standalone evidence bundle CLI `--input` coverage now includes nested item-list validation, item object validation, invalid capture-method IDs, and duplicate artifact IDs.


An aggregate `preservation_evidence_bundle_regression_test.py` runner now executes the evidence bundle model, JSON helper validation, standalone CLI, backend plan CLI, and Total Export prepare CLI regression tests together.


Evidence bundle JSON helper validation now covers non-string source metadata fields and non-string item metadata fields such as capture method, path hint, notes, and limitations.


Evidence bundle JSON helper validation now confirms optional `None` source/item metadata normalizes to empty/default metadata while required artifact fields remain strict.


The aggregate `preservation_evidence_bundle_regression_test.py` runner now supports `--list` and repeatable `--only LABEL`, so future sessions can run the whole evidence-bundle suite or a targeted subset without editing code.


`preservation_evidence_bundle_regression_runner_test.py` now verifies the aggregate runner's `--list`, targeted `--only`, and unknown-label error behavior.


`preservation_evidence_bundle_scope_invariant_test.py` now verifies local-only scope wording and path-hint preservation across model serialization, standalone evidence bundle CLI JSON output, and Total Export preservation-plan JSON output. The aggregate regression runner includes this group.


`preservation_evidence_bundle_regression_runner_test.py` now explicitly verifies targeted `--only "evidence bundle local-only scope invariants"` execution.


`preservation_evidence_bundle_regression_runner_test.py` now verifies repeatable `--only` selections so targeted multi-group evidence-bundle regression runs are covered.


The evidence bundle scope invariant test now also verifies preservation backend plan CLI JSON output via `--input ... --format json`, alongside model serialization, standalone evidence bundle CLI JSON output, and Total Export preservation-plan JSON output.


The aggregate `preservation_evidence_bundle_regression_test.py` suite now includes `evidence bundle regression runner behavior`. The behavior test uses subprocess calls instead of importing the aggregate runner, avoiding the earlier circular import issue.


`preservation_evidence_bundle_scope_invariant_test.py` now checks text output and JSON output for local-only evidence scope wording and path hints across standalone evidence bundle CLI, preservation backend plan CLI, and Total Export preservation-plan explanations.


`preservation_evidence_bundle_scope_invariant_test.py` now checks Markdown output for standalone evidence bundle CLI and preservation backend plan CLI local-only scope wording and path hints, alongside existing text and JSON checks.


`preservation_evidence_bundle_scope_invariant_test.py` now also checks that evidence path hints are not materialized into temp files or directories; only the explicit JSON input files may appear in the temp test directory.


`preservation_evidence_bundle_scope_invariant_test.py` now also asserts that successful JSON/text/Markdown subprocess checks leave stderr empty, so hidden warnings do not pass unnoticed.


`preservation_evidence_bundle_regression_runner_test.py` now verifies duplicate `--only` labels are de-duplicated, so repeated selections do not execute the same regression group twice.


`preservation_evidence_bundle_regression_runner_test.py` now verifies targeted `--only` selections keep canonical regression order even when the labels are requested in reverse order.


`preservation_evidence_bundle_regression_runner_test.py` now verifies mixed known/unknown `--only` selections fail cleanly, with the unknown label and expected choices reported in stderr.


`preservation_evidence_bundle_scope_invariant_test.py` now also asserts archive/download prohibition wording in local-only evidence scope output, alongside scan/hash/upload/capture/network checks.


`preservation_evidence_bundle_scope_invariant_test.py` now asserts JSON/text/Markdown CLI outputs do not leak the temp input directory path or temp folder name, reinforcing that path hints are not resolved to local evidence paths.


`preservation_evidence_bundle_scope_invariant_test.py` now rejects structured file-state keys in evidence bundle outputs, preventing local-only metadata from growing hash/size/existence/opened/created/uploaded/validated/captured state fields.


`preservation_evidence_bundle_scope_invariant_test.py` now asserts structured evidence path hints remain relative/descriptive metadata rather than URLs, absolute paths, or drive-qualified local paths.


`preservation_evidence_bundle_scope_invariant_test.py` now includes negative descriptive path-hint checks for URL, drive-qualified, root-relative, and absolute examples so the helper cannot silently weaken.


`preservation_evidence_bundle_scope_invariant_test.py` now includes negative checks proving representative forbidden file-state keys such as captured, exists, hash, opened, sha256, size_bytes, uploaded, and validated are rejected.


`preservation_evidence_bundle_scope_invariant_test.py` now iterates over the full `FORBIDDEN_FILE_STATE_KEYS` set for negative checks, so every forbidden file-state key must be rejected by the invariant helper.


`preservation_evidence_bundle_scope_invariant_test.py` now asserts JSON/text/Markdown CLI outputs do not leak the temporary input filenames (`evidence_bundle.json` or `backend_plan.json`) in addition to temp directory paths.


`preservation_evidence_bundle_regression_runner_test.py` now verifies unknown-label errors include the `expected one of` choices and every current regression label.


`preservation_evidence_bundle_scope_invariant_test.py` now rejects rendered file-state field markers (`checksum`, `file_size`, `mtime`, `sha256`, `size_bytes`) in text/Markdown outputs, while still allowing prohibition wording like scan/hash/upload.


`preservation_evidence_bundle_scope_invariant_test.py` now asserts evidence items keep `execution=metadata only` semantics when present in structured outputs and in rendered text/Markdown output surfaces.


`preservation_evidence_bundle_scope_invariant_test.py` now rejects parent-traversal path hints in addition to URL, drive-qualified, root-relative, and absolute examples, keeping evidence hints relative and non-resolving.


`preservation_evidence_bundle_scope_invariant_test.py` now covers embedded parent-traversal path hints as well as leading traversal examples, rejecting both Windows-style and POSIX-style `captures/../...` forms.


`preservation_evidence_bundle_regression_runner_test.py` now verifies mixed known/unknown `--only` failures include the `expected one of` choices and every current regression label, matching the single-unknown diagnostic coverage.


`preservation_evidence_bundle_regression_runner_test.py` now verifies `--list` is listing-only by rejecting pass banners and per-test `passed` output in list mode.


`preservation_evidence_bundle_scope_invariant_test.py` now includes negative checks for temp path leaks, proving temp directory paths plus `evidence_bundle.json` and `backend_plan.json` input filenames are rejected if rendered into CLI output.


`preservation_evidence_bundle_regression_runner_test.py` now parses `: passed` lines and asserts targeted `--only` runs emit exactly the selected regression labels, preventing accidental extra group execution.


`preservation_evidence_bundle_regression_runner_test.py` now keeps exact passed-label assertions beside the matching targeted run checks and also asserts duplicate `--only` selections emit one canonical passed label.


`preservation_evidence_bundle_regression_runner_test.py` now asserts multi-target and reverse-order `--only` runs emit exactly the canonical passed-label pair, preventing extra output and preserving runner ordering.


`preservation_evidence_bundle_regression_runner_test.py` now guards against duplicate regression labels by checking both the canonical `EXPECTED_LABELS` tuple and parsed `--list` output.


`preservation_evidence_bundle_regression_runner_test.py` now asserts successful targeted runner subprocesses emit the aggregate success banner exactly once, preventing duplicate or missing completion banners.


`preservation_evidence_bundle_regression_runner_test.py` now wires `_assert_success_banner_once(...)` into each successful targeted runner subprocess check, so the previously added helper actively verifies one completion banner per successful targeted invocation.


`preservation_evidence_bundle_regression_runner_test.py` now asserts unknown-label and mixed known/unknown failures keep stdout empty and do not leak success banners or `: passed` output in stderr.


`preservation_evidence_bundle_regression_runner_test.py` now asserts `--list` output shape exactly matches one raw `LABEL` line for each canonical regression label, with no headers, bullets, or extra lines.


`preservation_evidence_bundle_regression_runner_test.py` now explicitly parses `--list` output with `_passed_labels(...)` and asserts it yields an empty tuple, reinforcing that list mode never emits pass-result lines.


`preservation_evidence_bundle_regression_runner_test.py` now tightens `--list` output shape by comparing all split lines directly to `EXPECTED_LABELS`, so blank lines fail, and by requiring the normal trailing newline.


`preservation_evidence_bundle_regression_runner_test.py` now verifies a repeatable `--only` invocation containing every label except `evidence bundle regression runner behavior`, proving canonical output for the non-self suite without recursively invoking the runner behavior test.

Source Evidence execution-gate and review-projection closeout: `capture_execution_gate.py` / `capture_execution_gate_cli.py` add LOCAL_ONLY / APPROVAL_REQUIRED plan metadata for gated live/manual/destructive boundaries, including live site capture, browser automation, archive checks/submissions, downloads, rendered recording, WARC/WACZ, ArchiveBox, ASR provider calls, broad folder scans, and evidence file moves. `source_adapters.py` now carries local source-method profiles for MSN article/comments, X/Twitter archive/manual fallback, YouTube media/transcript/comments, generic article/comments, and manual/local import; X/Twitter is a registered local/import/archive-fallback metadata adapter, not a live/API/browser adapter. `evidence_database_index.py` adds explicit-record-only scan/filter rows and metadata-only patch/update audit receipts, and `source_grabbed_record.py` records durable grabbed-source metadata for controller plans. `evidence_item_queue_store.py` adds atomic JSON persistence for summary/counts-only queue review stores, and `source_evidence_review_export.py` projects queue review, execution-gate, source-reference, and release-readiness metadata into Total Export manifests. `source_evidence_release_readiness.py`, `source_evidence_release_plan.py`, `access_provider_gate.py`, `source_evidence_workflow_state.py`, and `source_evidence_workflow_store.py` now wire the app-facing Source Evidence workflow state to saved sidecars for release readiness, release-action receipts, grabbed-source records, database scan results, and KEYS/ACCOUNTS provider-gate summaries. These helpers remain metadata-only, USER_REVIEW_REQUIRED, APPROVAL_REQUIRED / RELEASE_APPROVAL_REQUIRED, and explicit-record-only; they emit no commands, perform no runtime execution, credential lookup, provider call, broad scan, or file move, and make no raw-payload, full-local-path, file-existence, completed-evidence, completed-release, release-upload, file-library mutation, operator-signoff, provider/network, automatic-classification, or sensitive-inference claims.


`preservation_evidence_bundle_regression_runner_test.py` now asserts `evidence bundle regression runner behavior` remains the final canonical label and that all-non-self targeted coverage exactly equals `EXPECTED_LABELS[:-1]`, preventing accidental recursive self-selection changes.

`preservation_evidence_bundle_regression_runner_test.py` now verifies repeated unknown `--only` labels fail cleanly together: stdout stays empty, no success output leaks, both missing labels are named, and valid expected choices remain listed.

`preservation_evidence_bundle_regression_runner_test.py` now centralizes the aggregate success banner and self-recursive runner behavior label as constants and documents why broad coverage uses targeted non-self selection rather than a no-filter aggregate runner call.

`preservation_evidence_bundle_regression_runner_test.py` now verifies the broad non-self targeted argument list excludes `RUNNER_BEHAVIOR_LABEL` while containing each non-self label with one `--only` switch per selection.

`preservation_evidence_bundle_regression_runner_test.py` now centralizes repeatable `--only` argument tuple construction in a helper, preserving deterministic targeted subprocess coverage without no-filter recursive runner calls.

`preservation_evidence_bundle_regression_runner_test.py` now centralizes successful targeted subprocess result assertions in a helper, preserving return-code, success-banner, exact passed-label, and clean-stderr checks across targeted runner coverage.

`preservation_evidence_bundle_regression_runner_test.py` now centralizes unknown-label failure assertions in a helper, preserving return-code, empty-stdout, no-success-output, missing-label, expected-choice, and valid-label diagnostic checks.

`preservation_evidence_bundle_regression_runner_test.py` now covers a duplicated valid `--only` selection mixed with an unknown label, asserting validation fails diagnostically before the valid regression group can run.

`preservation_evidence_bundle_regression_runner_test.py` now covers malformed `--only` usage with no label value, asserting diagnostic-only failure output before any regression group can run.

`preservation_evidence_bundle_regression_runner_test.py` now covers blank/whitespace-only `--only` labels and asserts diagnostic-only failure output before any regression group can run.

`preservation_evidence_bundle_regression_runner_test.py` now centralizes malformed bare `--only` assertion checks in a helper, preserving diagnostic-only failure behavior for malformed and blank targeted selections.

`preservation_evidence_bundle_regression_runner_test.py` now covers unexpected positional runner arguments and asserts diagnostic-only argparse failure before any regression group can run.

`preservation_evidence_bundle_regression_runner_test.py` now centralizes argparse-style malformed runner argument assertions, reusing the same diagnostic-only helper for bare `--only` and unexpected positional failures.

`preservation_evidence_bundle_regression_runner_test.py` now covers aggregate runner `--help` output, asserting argparse help lists `--list` and `--only` while emitting no regression pass lines or success banner.

`preservation_evidence_bundle_regression_runner_test.py` now centralizes no-regression-output checks for `--list` and `--help`, preserving exact list/help assertions while ensuring neither mode emits pass lines or the aggregate success banner.

`preservation_evidence_bundle_regression_runner_test.py` now covers `--list` combined with `--only`, asserting the runner still prints the canonical list and emits no regression pass output.

`preservation_evidence_bundle_regression_runner_test.py` now covers `--help` combined with `--only` and `--list`, asserting argparse help remains diagnostic-only and emits no regression pass output.

`preservation_evidence_bundle_regression_runner_test.py` now covers partial `--only` label text, asserting substring/fuzzy matches are rejected as unknown labels before any regression group runs.

`preservation_evidence_bundle_regression_runner_test.py` now covers final aggregate runner CLI edges for unknown options, suffix-only labels, and `--list`/`--help` combined with unknown `--only` labels, preserving diagnostic-only or non-executing behavior as appropriate.

`preservation_evidence_bundle_regression_runner_test.py` now completes a final runner-behavior cleanup by sharing list/help non-execution assertions while retaining the existing no-unfiltered-aggregate-run recursion guard.

`preservation_evidence_bundle_scope_invariant_test.py` now has a batched local-only scope cleanup that shares successful-command, clean-stderr, and no-temp-path checks while preserving the rule that evidence metadata never operates on user evidence files.

Evidence bundle JSON input validation now has a batched helper/CLI audit proving unknown operational fields such as upload state and hashes cannot survive normalization into standalone, backend-plan, or Total Export evidence output.

`preservation_evidence_bundle_cli_test.py` now has a batched standalone CLI cleanup that centralizes failed-command assertions while preserving metadata-only rendering and evidence-file non-operation boundaries.

`preservation_backend_plan_cli_test.py` now has a batched backend-plan CLI cleanup that centralizes failed-command assertions while preserving metadata-only preservation planning and backend/evidence non-operation boundaries.

`total_export_prepare_cli_test.py` now has a batched Total Export CLI cleanup that centralizes failed-command assertions while preserving metadata-only export preparation and backend/evidence non-operation boundaries.

`total_export_preservation_plan_cli_test.py` and `preservation_metadata_seed_report_test.py` now share invalid-command assertion helpers for preservation planning CLI/report coverage while preserving local-only, non-network semantics.

`source_capture_plan_cli_test.py` and `context_glossary_cli_test.py` now share invalid-command assertion helpers for source/context CLI coverage while preserving local-only, non-fetch semantics.

`total_export_bundle_index_reconcile_cli_test.py` now shares invalid-command assertion helpers for local bundle index reconciliation CLI coverage.

`total_export_zip_sidecar_test.py` now shares ZIP sidecar write-state assertions for SHA256 and inspection JSON outputs while preserving local-only review-bundle semantics.

`total_export_review_bundle_verify_test.py` now shares review-bundle verification status assertions while preserving sidecar, hash, size, entry-count, and unsafe-ZIP diagnostic coverage.

`total_export_review_bundle_folder_verify_test.py` now shares review-bundle folder count assertions while preserving missing-sidecar, mismatch, recursion, report-output, and empty-folder coverage.

`total_export_batch_review_bundle_test.py` now centralizes repeated batch row/success/failure count assertions while preserving scenario-specific ZIP, folder verification, warning, and error checks.

`total_export_batch_review_reconcile_test.py` now centralizes one-row item status assertions while preserving missing-ZIP, invalid-row, verification, missing-sidecar, report, and warning diagnostics.

`total_export_batch_review_plan_test.py` now centralizes repeated row/error count assertions while preserving ready, duplicate, warning, existing-output, item, and path diagnostics.

`total_export_package_zip_test.py` now centralizes successful and failed ZIP result-state assertions while preserving path, hash, size, file-count, archive-entry, inspection-status, and exact diagnostic checks.

`total_export_zip_inspect_test.py` now centralizes ZIP inspection status assertions while preserving found/readable flags, traversal and backslash safety, duplicate entries, manifest diagnostics, entry ordering, and hash coverage.

`total_export_package_inspect_test.py` now centralizes package inspection status assertions while preserving manifest discovery, validity, inventory, standard-file, warning, and missing-asset diagnostics.

`total_export_validation_test.py` now centralizes exact validation error-code assertions while preserving valid, informational, relative-path, missing-asset, size/hash mismatch, and manifest-read coverage.
- Local ASR whisper.cpp/Vulkan timeout handling now includes duration-scaled execution plus UI/log-friendly status metadata, clearer long-media retry guidance, and bounded failed-run temp cleanup that preserves source media and marks non-empty partial outputs as `user_review_required`; `large-v3` remains the benchmark-backed local recommendation.

## Source Adapter Runtime Queue Closeout Audit Handoff

The latest source-adapter runtime queue section is closed locally at `SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_AUDIT_BUILT`. It follows the promoted priority fixture regression queue and regression queue runtime wiring work. The closeout audits 20 local dry-run runner rows, 20 expanded controller/provider bindings, at least 4 GUI/controller call-site wiring rows, 20 local acceptance receipts, and 5 named-site smoke gates.

Current handoff status: `SOURCE_ADAPTER_RUNTIME_QUEUE_CLOSEOUT_READY_FOR_OPERATOR_APPROVED_NAMED_SITE_SELECTION`.

The next stage is operator named-site selection and approval-packet capture only. It must remain explicit and gated. This is not approval for live smoke execution, browser automation, network calls, API calls, archive provider submission, release upload, file-library mutation, credential storage, or GUI mutation. Preserve `KEYS/ACCOUNTS` wording and redacted credential-reference hashes in all future receipt metadata.

## Source Adapter implementation bundle checkpoint - 2026-08-08

The implementation bundle advances from operator-approved execution runtime into executable provider backend interfaces and GUI/controller execution bridge wiring. It adds:

- `SOURCE_ADAPTER_PROVIDER_BACKEND_INTERFACES_BUILT` with 25 provider backend request/receipt rows.
- `SOURCE_ADAPTER_GUI_CONTROLLER_EXECUTION_BRIDGE_BUILT` with four registered GUI/controller routes and five dispatch receipts.
- `KEYS/ACCOUNTS` credential-reference handling with redacted hashes.
- Explicit hygiene for generated operator receipt folders.

Next implementation work should bind the concrete GUI buttons, including the Online ASR button requirement where relevant, and replace local provider backend handlers with provider-specific browser/archive/release/file-library implementations.

### Source Adapter implementation execution bundle handoff

Use `SOURCE_ADAPTER_IMPLEMENTATION_EXECUTION_BUNDLE_CLOSEOUT.md` as the latest
implementation bundle checkpoint.  Next work should continue with provider-
specific command configs, GUI live-smoke action binding, and evidence database /
Total Export release import wiring against the provider command runtime,
named-site smoke execution, and smoke receipt review integration modules.

### Source Adapter release pipeline bundle handoff

Use `SOURCE_ADAPTER_RELEASE_PIPELINE_BUNDLE_CLOSEOUT.md` as the latest implementation checkpoint after `SOURCE_ADAPTER_IMPLEMENTATION_EXECUTION_BUNDLE_CLOSEOUT.md`.

The latest runtime path now reaches release/evidence delivery closeout:

1. smoke receipt review integration,
2. evidence/export runtime bridge,
3. release/archive delivery runtime,
4. operator delivery receipt closeout,
5. release-section completion handoff.

Next implementation work should bind these delivered artifacts into the concrete release-section UI/controller imports, evidence database acceptance, and final Total Export/release completion surfaces while preserving `KEYS/ACCOUNTS` and redacted credential-reference hashes.

## Source Adapter Full Execution Integration Bundle Closeout

- Status: `SOURCE_ADAPTER_FULL_EXECUTION_INTEGRATION_BUNDLE_CLOSEOUT_RECORDED`
- Added live provider profile runtime, browser capture backend, archive submission backend, release/file-library delivery backend, KEYS/ACCOUNTS credential reference runtime, end-to-end operator execution orchestrator, and GUI live execution panel wiring.
- Next: provider-specific adapter binding and concrete GUI installation against the implemented execution surfaces.


## Source Adapter Provider Integration Bundle Closeout (57105f1 follow-up)

- Provider configuration resolver, browser driver bindings, archive/release policies, provider receipt ledger, evidence sync, Total Export finalization, GUI operator run history, release review acceptance, and operator dashboard runtime are now represented as one connected implementation chain.
- `KEYS/ACCOUNTS` remains the credential-reference surface and receipts keep redacted hashes only.
- Next operational stage: connect real provider configuration values and run operator-selected named-site execution through the dashboard/review flow.


## Source Adapter Production Runtime Bundle Closeout
<!-- SOURCE_ADAPTER_PRODUCTION_RUNTIME_BUNDLE_CLOSEOUT_RECORDED -->

- Added production-runtime closeout coverage after the archive closeout runtime patch chain.
- Confirms the completed local implementation chain for provider secret boundaries, live-run permission capture, operator session execution, provider receipt persistence, evidence database writeback, Total Export handoff commit, release reconciliation, operator signoff, GUI completion state, release lock, and archive closeout.
- Preserves `KEYS/ACCOUNTS` as the credential-reference surface. Receipts and ledgers carry credential references, redacted hashes, and non-secret metadata only.
- Live/provider execution remains explicit operator-run workflow: named site inputs, operator approval metadata, provider configuration references, receipts, review, and signoff are recorded through deterministic runtime modules and CLI/test surfaces.
- Status marker: `SOURCE_ADAPTER_PRODUCTION_RUNTIME_BUNDLE_CLOSEOUT_BUILT`.
## Source Adapter execution policy bundle handoff

- Status: SOURCE_ADAPTER_EXECUTION_POLICY_BUNDLE_CLOSEOUT_RECORDED
- Current implementation chain is ready for the next large runtime bundle after execution-policy closeout.
- Continue with multi-patch ZIP bundles, commit-after-each-patch, and push-once-at-end.
- Preserve operator approval, named-site inputs, receipt review, and KEYS/ACCOUNTS redacted credential-reference rules.

<!-- SOURCE_ADAPTER_OPERATIONAL_RUNTIME_BUNDLE_CLOSEOUT_RECORDED -->

## Source Adapter Operational Runtime Bundle Closeout

- Status: SOURCE_ADAPTER_OPERATIONAL_RUNTIME_BUNDLE_CLOSEOUT_RECORDED
- Bundle head target: 473f4c8 runtime chain continuation
- Coverage: provider execution manifest, capability registry, browser session profiles, archive queues/results, artifact normalization, evidence materialization, Total Export package assembly, release target/receipt runtime, KEYS/ACCOUNTS redaction, operator approvals, runbook export, live smoke readiness, provider healthcheck, failure triage, GUI action state, audit replay, source pipeline completion, and operational closeout.
- KEYS/ACCOUNTS remains the preserved user-facing label.
- Secret material remains outside committed artifacts; only redacted reference hashes are recorded.
## Source Adapter Operator Runtime Handoff Bundle Closeout

- Status: SOURCE_ADAPTER_OPERATOR_RUNTIME_HANDOFF_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: provider contract execution, named-site browser binding, archive execution/verification, capture artifact store, evidence queue/review gates, Total Export assembly/release bridge, release upload/file-library publish, KEYS/ACCOUNTS audit and added-provider runtime, GUI execution/result import, operator receipt import, live smoke receipt, provider health/retry, archive poll merge, release index publish, runbook script materialization, manual/live smoke closeout, and operator runtime handoff closeout.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.
## Source Adapter Site Capture Mega Bundle Closeout

- Status: SOURCE_ADAPTER_SITE_CAPTURE_MEGA_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: source authority resolution, page/comment/media capture recipes, archive normalization/provider adapter execution, release bundle storage, evidence source links/taxonomy, Total Export artifact inventory, source receipt chains, action-log hash chains, operator approval ledger, GUI provider picker/named-site run wizard, KEYS/ACCOUNTS added-provider search and add-provider wizard, credential redaction verification, live smoke command runner, manual observation importer, archive result review, release audit report, source package verification, export queue dispatch, runtime metrics, provider capability documentation, and final operator handoff.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.
## Source Adapter Capture Delivery Mega Bundle Closeout

- Status: SOURCE_ADAPTER_CAPTURE_DELIVERY_MEGA_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: capture profile resolution, browser context launch, scroll capture, shadow-DOM comments, media metadata, transcript source binding, archive routing/polling/import, artifact digests, evidence claim materialization, review decision writing, evidence database commit, Total Export source/release manifesting, release package/publish/file-library delivery, provider/account binding, KEYS/ACCOUNTS added-provider registry/catalog filter, secret reference hashes, operator approval workflow, live run state machine, receipt chain validation, failure recovery, GUI execution/review panels, operator runbook packaging, manual smoke import closeout, and source/release acceptance.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.
## Source Adapter Execution Closure Mega Bundle Closeout

- Status: SOURCE_ADAPTER_EXECUTION_CLOSURE_MEGA_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: source coordination, article/comment/media capture runners, archive submission and poll/import runners, evidence commit runners, Total Export/release delivery, file-library publish runners, KEYS/ACCOUNTS runtime routing, secret scope boundaries, operator command/receipt gates, live smoke planning, manual observation review, capture/archive/evidence/release quality gates, GUI provider/archive/release/KEYS panels, MSN/X/YouTube/article/comments/transcript profiles, end-to-end manifests/verifiers, handoff reports, and operator acceptance checklists.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.
## Source Adapter Final Delivery Closure Bundle Closeout

- Status: SOURCE_ADAPTER_FINAL_DELIVERY_CLOSURE_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: production capture executors, browser automation command writers, article/comment/media/transcript stores, archive command/receipt/fallback runners, evidence package/database/queue gates, Total Export source/archive/release bridges, release uploader/file-library/acceptance receipts, KEYS/ACCOUNTS onboarding and credential aliases, provider capability/execution/error receipt gates, operator live approval/session/signoff surfaces, GUI ASR button adjacency state, GUI source/evidence/release panels, MSN/X/YouTube/article-comment profile verifiers, reproducibility verifiers, export readiness, and runtime acceptance summaries.
- Local ASR and Online ASR adjacency remains an explicit GUI state requirement; Online ASR must visually match the Local ASR control when wired to the concrete UI.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.
## Source Adapter Provider Site Roadmap Bundle Closeout

- Status: SOURCE_ADAPTER_PROVIDER_SITE_ROADMAP_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: live site selection, capture intent routing, browser command/session receipts, scroll/comment/shadow DOM materialization, media/ASR/transcript normalization, archive policy/result/manual import ledgers, source observation and evidence review gates, evidence database commit reports, queue GUI bridges, Total Export source manifests/closeout, release/file-library delivery acceptance, KEYS/ACCOUNTS provider state/search/credential boundaries, provider dispatch/receipt/failure escalation, operator session/handoff packets, GUI live/archive/export/KEYS/ACCOUNTS/Online ASR panels, MSN/X/YouTube/article-comment profile delivery, end-to-end receipt/release verification, runtime gap report, operator acceptance, and source-release traceability matrix.
- Online ASR remains adjacent to Local ASR and must visually match the Local ASR button when wired to concrete UI widgets.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.
## Source Adapter Ultimate Delivery Bundle Closeout

- Status: SOURCE_ADAPTER_ULTIMATE_DELIVERY_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: runbook launchers, browser/comment/media receipt mappers, archive execution/manual validation, source/evidence review and commit bridges, Total Export source/release indexing, release/file-library gates, KEYS/ACCOUNTS visible/catalogue/add-flow/search split surfaces, Online ASR adjacency/provider flow, local ASR benchmark guard, MSN/X/YouTube/article-comment profile executors, operator live-run preflight/import/closeout, GUI capture/archive/export/KEYS/ACCOUNTS/Online ASR states, provider backend/receipt/failure matrices, evidence-release/source-lineage matrices, final readiness reports, acceptance packets, runtime index, traceability register, operator delivery packet, and roadmap acceptance.
- Online ASR remains adjacent to Local ASR and must visually match the Local ASR button when wired to concrete UI widgets.
- Local ASR recommendation remains whisper.cpp large-v3 Vulkan on AMD RX 5700.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.
## Source Adapter Master Delivery Acceptance Bundle Closeout

- Status: SOURCE_ADAPTER_MASTER_DELIVERY_ACCEPTANCE_BUNDLE_CLOSEOUT_RECORDED
- Commit scope: runbook launchers, browser/comment/media receipt mappers, archive execution/manual validation, source/evidence review and commit bridges, Total Export source/release indexing, release/file-library gates, KEYS/ACCOUNTS visible/catalogue/add-flow/search split surfaces, Online ASR adjacency/provider flow, local ASR benchmark guard, MSN/X/YouTube/article-comment profile executors, operator live-run preflight/import/closeout, GUI capture/archive/export/KEYS/ACCOUNTS/Online ASR states, provider backend/receipt/failure matrices, evidence-release/source-lineage matrices, final readiness reports, acceptance packets, runtime index, traceability register, operator delivery packet, and roadmap acceptance.
- Online ASR remains adjacent to Local ASR and must visually match the Local ASR button when wired to concrete UI widgets.
- Local ASR recommendation remains whisper.cpp large-v3 Vulkan on AMD RX 5700.
- KEYS/ACCOUNTS remains the canonical label for credential/account surfaces.
- Credential material remains represented only by references and redacted hashes in receipts and ledgers.

<!-- source-adapter-absolute-delivery-acceptance-bundle-closeout -->
## Source Adapter Absolute Delivery Acceptance Bundle Closeout

- Added final acceptance records for source capture, archive, evidence, Total Export, release, KEYS/ACCOUNTS, Online ASR, local ASR, named-site profiles, provider acceptance, GUI acceptance, readiness crosschecks, traceability crosschecks, and operator handoff acceptance.
- Keeps all live/manual smoke and provider execution paths behind explicit operator approval, named-site inputs, receipt capture, and redacted credential references.
- Preserves the Local ASR benchmark lock: large-v3 with Vulkan acceleration on the AMD RX 5700 workflow, while keeping Online ASR as a separate provider flow.
- Preserves the KEYS/ACCOUNTS split between added visible providers and the searchable add-provider catalogue.

## Site-Specific Source Method Audit Handoff

The latest local-only pass adds the site-specific source method audit layer above the resolved row-level adapter audit. `source_site_method_audit_registry.py` records named site/method rows for MSN article, MSN shadow-DOM comments, X/Twitter public post archive/manual import, X/Twitter reply-thread archive/manual import, YouTube media/transcript, YouTube comments, generic article HTML, generic comments manual/import, generic comments site-specific selector, generic comments archive-only import, and archive-only import. The generic article-comments caveat is now a concrete `generic_comments_site_specific_selector` row with `selector_audit_required` and `live_approved_only` status; universal comment selector support is not claimed.

Database review/update coverage now converts site/method audit rows into explicit Evidence Database records, scans them through the existing review helpers, and records safe update receipts for status, operator review note, selector audit note, and archive/manual fallback note changes. It rejects protected/sensitive classification dimensions, completed-evidence claims, live-execution claims, file-move claims, and credential/cookie/account material. Grabbed source records now support selector-audit reference IDs.

Source Evidence workflow bundles write a `source_site_method_audit_registry.json` sidecar and include pathless Source site/method audit metadata in the Total Export/review manifest. This remains metadata-only, USER_REVIEW_REQUIRED, and not live-executed.

| Site/method | Current state | Remaining boundary |
| --- | --- | --- |
| MSN article | metadata_audit_ready | Named-site live/manual smoke requires separate approval. |
| MSN shadow-DOM comments | metadata_audit_ready | Live selector execution requires separate approval. |
| X/Twitter public post archive/manual import | metadata_audit_ready | No live X/Twitter/API/browser execution approved. |
| X/Twitter reply-thread archive/manual import | metadata_audit_ready | Reply thread live/manual audit remains approval-gated. |
| YouTube media/transcript | metadata_audit_ready | Existing-output metadata only; no runtime/API call. |
| YouTube comments | metadata_audit_ready | Existing-output status/count metadata only. |
| Generic article HTML | metadata_audit_ready | Site-specific live capture still approval-gated. |
| Generic comments manual/import | metadata_audit_ready | Manual/local import and archive review only. |
| Generic comments site-specific selector | selector_audit_required / live_approved_only | Named-site selector audit before any live comment capture. |
| Generic comments archive-only import | metadata_audit_ready | Operator-supplied archive metadata only. |
| Archive-only import | metadata_audit_ready | Review/signoff metadata only. |

No live site access, browser automation, MSN/X/Twitter/YouTube/API/archive/provider calls, credential use, evidence file movement, completed-evidence claim, or protected-attribute inference occurred in this pass.

## Source Adapter Audit Readiness Big-Scope Handoff

- Current status: SOURCE_ADAPTER_AUDIT_READINESS_BIG_SCOPE_BUILT.
- Implementation added real integration paths for named-site selector audit packs, Evidence Database scan/edit/update receipts, grabbed-source database/release receipt references, controller-populated selector audit references, workflow/store/export audit sidecars, an adapter audit report, and a named-site priority plan.
- New sidecars in Source Evidence workflow review bundles:
  - `source_adapter_audit_report.json`
  - `source_named_site_priority_plan.json`
- The big-scope path remains MODEL_ONLY / LOCAL_FIXTURE_TESTED / UI_SCAFFOLD_ONLY / USER_REVIEW_REQUIRED / APPROVAL_REQUIRED. It does not claim live capture, completed evidence, file existence, or provider execution.
- Remaining next boundary: operator-approved named-site selector/live smoke execution, with explicit source URLs, allowed scopes, provider configuration references, and review/signoff before any live/browser/archive/provider/destructive action.

## Database Review UI + Source Method Audit Workflow Handoff

- Current status: DATABASE_REVIEW_UI_SOURCE_METHOD_AUDIT_WORKFLOW_BUILT.
- New implementation commits: `d6d9542`, `9817a5e`, `19dd410`, `2d16059`, and `75463c1`; documentation is recorded separately after those implementation commits.
- Source Evidence workflow review bundles now include:
  - `source_database_review_workflow.json`
  - `source_record_review_workflow.json`
  - `source_selector_approval_packets.json`
  - existing `source_adapter_audit_report.json` and `source_named_site_priority_plan.json` now summarize these workflows.
- The database review view-model is GUI-callable/headless-testable and includes scan/review-needed/audit/source-record/queue rows, pending safe edits, rejected unsafe edits, receipt summaries, filters, selected row state, and preview-before-apply state.
- Safe metadata edits create preview receipts for operator notes, selector audit notes, manual observation notes, archive fallback notes, review-state transitions, queue assignment notes, source-record cross-reference notes, and Total Export inclusion notes. Unsafe completed-evidence, live-execution, file movement, raw payload, full local path, credential/cookie/account/API-key material, protected/sensitive classification, and automatic-classification claims are rejected.
- Source-record review summarizes typed article, comment, media, transcript, archive, screenshot, snapshot, manual-observation, provider-receipt, selector-audit, database-review-receipt, and release-action references, plus selector cross-links.
- Selector approval packets group current selector-audit-required rows, generate manual smoke checklist rows, and emit `not_live_executed` receipts. Generic comments site-specific selector remains `selector_audit_required` / `live_approved_only`.
- Existing main/source UI tests verify the app save/preview path exposes database review, source-record review, and selector approval counts through the real workflow state without layout churn.
- Boundary remains unchanged: no live site access, browser automation, MSN/X/Twitter/YouTube/archive/API/provider/ASR calls, credentials/cookies/accounts, evidence file moves, completed-evidence claims, protected-attribute inference, or automatic classification.

## Named-Site Source Method Pack Handoff

- Current status: NAMED_SITE_SOURCE_METHOD_PACKS_BUILT.
- Implementation commits: `18d3e90`, `c1c2e17`, `6859149`, `3a9b2d3`, `8209f69`, and `b3cd8f8`; documentation is recorded separately after those implementation commits.
- New module and tests: `source_named_site_method_packs.py`, `source_named_site_method_packs_test.py`.
- New Source Evidence workflow review sidecar: `source_named_site_method_packs.json`.
- Workflow/store/export integration:
  - Evidence Database review scans include named-site method pack index records.
  - Database review view-model includes named-site method pack rows and selector-audit-required counts.
  - Source-record review includes pack reference-bucket summaries.
  - Selector approval packet collection links pack summary metadata.
  - Adapter audit report and named-site priority plan include named-site pack summaries.
  - Total Export/review manifest includes a pathless Named-site source method pack metadata asset.
  - Existing main/source UI save-preview path reports pack counts and saves the new sidecar.

| Pack group | Count | State |
| --- | ---: | --- |
| MSN article/comments | 2 | metadata_audit_ready / not_live_executed |
| X/Twitter public/reply archive-manual | 2 | metadata_audit_ready / not_live_executed |
| YouTube media-transcript/comments | 2 | metadata_audit_ready / not_live_executed |
| Generic/archive methods | 5 | four metadata_audit_ready, one selector_audit_required / live_approved_only |

- Remaining selector/live boundary: `generic_comments_site_specific_selector` remains selector_audit_required / live_approved_only; named-site selector audit and live/manual smoke require separate operator approval, exact source inputs, and later receipts.
- Boundaries confirmed: no live site, browser automation, MSN/X/Twitter/YouTube/API/archive/provider/ASR calls, credentials/cookies/accounts, evidence file movement, completed-evidence claims, automatic classification, or protected-attribute inference.

## Source Audit Operator Workflow Bridge Handoff

- Current status: SOURCE_AUDIT_OPERATOR_WORKFLOW_BRIDGE_BUILT.
- Implementation commits in this pass: `9b0bb3f`, `c6bc762`, `47acf08`, `8393823`, `775f048`, `deee7fc`, and `82dedd0`; documentation is recorded separately after those implementation commits.
- New modules and tests: `source_review_panel_state.py`, `source_operator_command_packs.py`, `source_manual_smoke_checklists.py`, and `access_online_asr_bridge.py` with focused tests for each.
- Source Evidence workflow review bundles now include `source_operator_command_packs.json`, `source_manual_smoke_checklists.json`, and `source_audit_dashboard_state.json`; existing database review, source-record review, selector approval, named-site pack, adapter audit report, and named-site priority sidecars remain wired.
- App-facing bridge coverage includes database review counts, review-needed rows, pending safe edits, rejected unsafe edits, receipt summaries, source-record reference summaries, selector approval packet summaries, named-site method pack counts, and a no-live-execution dashboard state through the real main/source save-preview path.
- Operator command packs and manual smoke checklists are approval-gated and metadata-only for MSN, X/Twitter, YouTube, generic article/comment, and archive-only workflows. They do not launch browsers, providers, ASR, archive tools, downloads, file moves, or live capture.
- Access/KEYS/Online ASR summary keeps credential/provider state non-secret: added-provider and catalogue summaries are separate, Online ASR calls remain approval-required, and Local ASR stays guarded to the benchmarked whisper.cpp / Vulkan / large-v3 profile.

| Handoff area | Done | Not done |
| --- | --- | --- |
| GUI/app-facing panel state bridge | Done | No full new GUI layout in this pass. |
| Database review/edit/update summary | Done | Real accepted edits remain operator-reviewed and receipt-backed. |
| Source record review expansion | Done | No completed evidence or raw payload claims. |
| Operator command packs | Done | Commands are generated only, not executed. |
| Manual smoke checklist packs | Done | Manual live smoke remains separately approval-gated. |
| Workflow/store/export sidecars | Done | Metadata-only sidecars only. |
| Access/KEYS/Online ASR bridge | Done | No credential read/provider call/ASR run. |
| Generic comments live selector | Not done | `selector_audit_required` / `live_approved_only`. |

- Boundary remains unchanged: no live site access, browser automation, network/archive/API/provider/ASR calls, credentials/cookies/accounts, evidence file movement, completed-evidence claims, protected-attribute inference, or automatic classification occurred.

## Final Non-Live Operational Layer Handoff

- Current status: FINAL_NON_LIVE_OPERATIONAL_LAYER_BUILT.
- Implementation commits in this pass: `91364eb`, `4870fe7`, `cfbcb5e`, `1b31f26`, `e8cf9c4`, `4bb324a`, `316a9d2`, and `84af2e8`; documentation is recorded separately after those implementation commits.
- Operational capture runtime/result models now record session ID, source/canonical URL, access mode, capture method, selected methods, approval state, timestamps, status, artifact/receipt refs, completeness/warning flags, no-live flag, and hash-chain refs.
- Fixture capture results now cover article text, visible page outline, screenshot fidelity boundaries, comments, virtualized/deleted comments, encoded/page-decoded payload metadata, challenge pause/resume states, and text-first livechat.
- Media/archive runtime planning now covers image/video/audio discovery, mux command construction, rendered citation metadata, protected/black-output blocked results, mocked Wayback/archive.today statuses, ArchiveBox command plans, and app-native offline bundle planning.
- Evidence movement now has approval-gated temp-fixture-tested preview and receipt logic with hash-before/hash-after verification and completed-evidence receipts only after verified artifact presence. Real user evidence movement remains not performed.
- Source URL/FILES bridge preserves entered URL rows, resource rows, archive icons, selected-download vs injection separation, FILES hierarchy rows, and editor/transcript/media preservation guarantees.
- Workflow/store/export now writes the operational sidecars and includes pathless Total Export metadata assets. Main/source UI tests continue to exercise the real save/preview path.
- Access/Online ASR bridge preservation report proves non-secret provider summary state, Add Provider vs added-provider split, no provider call, no ASR run, and the preferred local benchmark profile whisper.cpp / Vulkan / large-v3.

Remaining live/manual-only boundary: real websites, external archive/provider calls, browser automation, real screenshots/OCR, downloads, FFmpeg/yt-dlp, ArchiveBox/Docker/WSL execution, ASR jobs, credentials, real evidence file movement, release uploads, and completed real-evidence verification still require explicit operator approval and later receipts.

## Source Evidence Execution Bridge Closeout - 2026-08-08

Starting from `f26f1cd`, the final execution-bridge pass converted the remaining safe plan-only areas into callable local/mocked execution adapters while preserving all live/operator boundaries. The implementation commits are `1ade13d` local browser execution bridge, `d2f7934` media execution bridge, `eaa4e8f` archive execution bridge, `683165a` offline evidence bundle writer, `c69e0f4` evidence movement executor hardening, `d7ca21c` Source URL/FILES bridge actions, and `375a763` execution bridge workflow sidecars.

Implemented modules and sidecars:
- `source_local_browser_execution.py`: local fixture/file/localhost browser-style execution bridge, rendered DOM writing, PNG screenshot artifacts, parser execution, progress/cancel/block states.
- `source_media_execution_bridge.py`: selected local media copy/download queue receipts plus approval-gated FFmpeg/yt-dlp subprocess wrappers with dry-run, missing-dependency, timeout, and failure states.
- `source_archive_execution_bridge.py`: Wayback/archive.today request builders, explicit submit gate, fake-HTTP execution client, challenge handoff/DNS diagnostics, and approval-gated ArchiveBox subprocess wrapper.
- `source_offline_bundle_writer.py`: real compressed ZIP bundle writer for supplied local/temp content and metadata.
- `evidence_movement_approval.py`: app-facing approved-root evidence movement executor with approval token, copy/move, hash verification, collision handling, rollback/failure receipts, and completed-evidence receipt generation only after verification.
- `source_url_files_bridge.py`: Enter-driven URL intake and FILES/source-row state transitions for download ticks, injection, pinned rows, editor clear/replace preservation, and audio-without-transcript status.
- `source_execution_bridge_results.json`: new workflow/review/export sidecar recording pathless execution-bridge capability and local/fake/mocked test summaries.

Local-only test status:
- Browser/screenshot/article/comments/livechat bridge: LOCAL_FIXTURE_TESTED.
- Media local copy/download and mux command wrappers: LOCAL_FIXTURE_TESTED / MOCKED_SUBPROCESS_TESTED.
- Archive provider clients and ArchiveBox wrapper: FAKE_HTTP_TESTED / MOCKED_SUBPROCESS_TESTED.
- Offline bundle writer and evidence movement executor: TEMP_FIXTURE_TESTED.
- Source URL/FILES bridge and workflow/store/export integration: APP_FACING_STATE_TESTED.

Remaining boundary: live external websites, named-site live selectors, real archive provider calls/submissions, real ArchiveBox/Docker/WSL execution, external downloads, real FFmpeg/yt-dlp, real browser automation against live sites, screenshots/OCR from live pages, ASR jobs/provider calls, credentials/cookies/accounts, broad scans, release uploads, and movement of user evidence files still require explicit operator approval and receipt import. No such live/external/destructive execution occurred in this pass.

## Source Evidence Operator Workflow Bridge - 2026-08-08

Starting from `29680e7`, Step 2 wired the execution bridges into real app/operator-facing workflows while keeping Codex tests local, temp, fake-client, or mocked-subprocess only. Implementation commits are `7bdba9c`, `e863384`, `d19cb1d`, `28b7dbc`, `51c023b`, `6ed7031`, and `2f70da6`.

Implemented:
- `source_operator_approval_gateway.py`: shared execution approval gateway for browser/local capture, screenshot/article/comments/livechat, media copy, FFmpeg, yt-dlp, archive check/submit, ArchiveBox, offline bundle, evidence copy/move, completed receipt creation, and ASR readiness. Real external/user-evidence/subprocess/archive-submit/ASR actions require scoped tokens.
- `source_unified_execution_runner.py`: approved local/temp job runner that calls the existing bridge modules and records progress, artifacts, hashes, behavior labels, cancellation, and failure receipts.
- `source_url_files_bridge.py`: app-facing Source URL/FILES workflow state for Enter intake, icon states, comments/livechat selectors and screenshot ticks, media download/inject ticks, pinned FILES rows, sort metadata, transcript clear/replace preservation, audio-without-transcript, and waveform/speech interval future state.
- `source_local_e2e_export.py`: local fixture Total Export package writer exercising the execution bridges and writing a temp package with manifest, article/outline/DOM/screenshot/comments/livechat/media/archive/offline bundle/provenance/movement sidecars.
- `evidence_database_operator_workflow.py`: temp-fixture scan/recognition, taxonomy migration preview, approval-token copy/move, collision handling, old/new path history, failure receipts, and completed receipt after hash verification.
- `source_live_smoke_runner.py`: dry-run operator live-smoke runner for MSN, X/Twitter, YouTube, generic, and archive-only method packs; approved live plans remain not executed by helper paths.
- `source_operator_workflow_sidecars.py`: workflow sidecar bundle persisted through Source Evidence store/export and Total Export metadata.

New persisted sidecars:
- `source_operator_approval_gateway.json`
- `source_unified_execution_jobs.json`
- `source_local_e2e_total_export.json`
- `source_live_smoke_runner.json`
- `source_database_movement_operator_workflow.json`

Remaining boundary: live/manual execution is still approval-only and was not run. No external sites, real archive providers, credentials/cookies/accounts, ASR jobs, external downloads, real FFmpeg/yt-dlp, real ArchiveBox/Docker/WSL, broad scans, release uploads, or user evidence file movement occurred.
## Source roadmap consolidation pointer — source methods, claims, URL UI, archives and database recognition

Marker: SOURCE ROADMAP CONSOLIDATION 9DDC226 PATCH BUNDLE

Added roadmap/model coverage for source website/method catalogue, claim-level source-role hierarchy, media source-chain tracking, Source URL/media UI contract, archive/offline preservation choices, rendered citation boundary, database recognition/reclassification previews, and behaviour/provenance logging. These are metadata/roadmap contracts; real evidence file movement, destructive migration, live capture, archive submission, media download, ASR execution and completed-evidence claims remain approval-gated.
