# Current Dev State

Branch: v2.6.0-asr-engines

Current focus:
- Local ASR engine testing and Auto Quality selection.
- Accuracy is priority over speed.
- Clear/common speech should not be silently accepted if wrong.
- Weak ASR output should stay marked as draft or be rejected by threshold.

Important context:
- Python GUI already has Transcript tab, local ASR dialog, Auto Probe 30s, Self-Test 15s, linked media, waveform/timeline work, and ASR warning export.
- There is no separate asr_hardware.py file. Hardware/environment detection currently lives in asr_quality_policy.py.
- whisper.cpp Vulkan works on AMD RX 5700 through C:\whisper.cpp.
- Manual matrix result: large-v3 phrase prompt is best quality; large-v3-turbo is faster but weaker on important terms.
- Topic resolver / Common Crawl / Serper / Exa are later background glossary helpers only. They are not ASR engines and must be strict-filtered.

Next feature area: Source URL ingestion and context/glossary pipeline:
- Planning section originated as docs-only; later fetch/glossary/ASR phases are not implemented yet.
- Phase 1 code step completed: `youtube_url_utils.py` provides network-free YouTube URL validation/normalization and strict 11-character video ID extraction.
- Comment/livechat maintenance patch completed: `extractor.py` now uses the shared strict YouTube URL/video ID helper, and livechat unlimited pagination no longer stops after one page.
- Comment capture defaults were adjusted for full-capture workflows:
  - Spam separation is off by default and labeled as `Separate flagged spam`; flagged items still export separately when enabled.
  - Date/Newest is now the default sort for new/default settings so newer comments are less likely to be missed.
  - Max comments remains empty/unlimited by default, with UI copy noting that limits count comments + replies.
- Future generalized ingestion should use "Source URLs" / source adapters terminology, with YouTube as the first/currently supported adapter.
- Other websites will need site-specific source adapters; do not assume one generic scraper can reliably capture every comments section.
- Existing YouTube comments/livechat behavior must be preserved while source terminology generalizes.
- Source adapter skeleton added: `source_adapters.py` defines `SourceCapabilities`, a `SourceAdapter` protocol, and `YouTubeSourceAdapter`.
- `YouTubeSourceAdapter` delegates validation, normalization, and source ID extraction to the existing strict `youtube_url_utils.py` helper.
- A metadata-only News Website source adapter skeleton is implemented for URL recognition/normalization only; no metadata/comment/livechat/transcript/page fetching behavior changed.
- Source adapter metadata skeleton added for future Access & Keys UI; no credential storage, key testing, UI, or behavior changes were added.
- `SOURCE_EVIDENCE_ROADMAP.md` captures the docs-only roadmap for future source/comment adapters, web evidence capture, archive checks, optional media-download inspiration, capture options, and provenance fields.
- `SOURCE_EVIDENCE_ROADMAP.md` also plans a future "KEYS" / "Access & Keys" manager so credentials/access settings can scale beyond the current sidebar API key field.
- Local raw `reference_feature_notes/` files are ignored by git and must remain local reference material only.
- Evidence/provenance schema skeleton added in `evidence_schema.py`; it is not wired into existing fetch/export behavior yet.
- Future Total Export, archive, screenshot, and media-source-chain features should use the schema skeleton when implemented.
- Total Export manifest skeleton added in `total_export_manifest.py`; it is not wired into existing GUI/export behavior yet.
- Future Total Export should use the manifest to track selected outputs, assets, hashes, provenance, archive results, claim notes, and media source-chain notes.
- Total Export manifest JSON writer helper added; it remains explicit-call only and is not wired into existing GUI/export behavior yet.
- Total Export package naming and asset-type helper skeleton added; it does not create folders and is not wired into existing GUI/export behavior yet.
- Context/glossary skeleton added for future background topic resolver, ASR phrase prompts, and Term QA; it is not wired into ASR, GUI, network, or exports.
- ASR provider metadata skeleton added for future Access & Keys UI; it records non-secret benchmark/status notes only and does not test keys, store credentials, call providers, or change ASR behavior.
- `ASR_PROVIDER_LEADERBOARD_NOTES.md` records user-supplied ASR/STT leaderboard, Meta Seamless/Instagram-adjacent, Groq/VillFlowSTT, Witsy, Kolwrite, WebAssembly streaming, and benchmark leads for later local comparison planning; no provider calls or ASR integration are implemented.
- Added a local-only ASR comparison report skeleton for manually recording provider/model WER, cost, latency, reference accuracy, and keyterm hit/miss results without provider calls or ASR integration.
- Added local-only ASR manual results seed records for known project ASR results and external/user-supplied leaderboard leads, using the comparison report format without provider calls or transcription behavior.
- Added a local-only ASR comparison report CLI for rendering manual ASR result records as text, Markdown, or JSON without provider calls, transcription, network, or GUI integration.
- Capture option metadata skeleton added for future Total Export evidence checkboxes; it is not wired into GUI/export behavior and does not perform archive checks, screenshots, scraping, or media downloading.
- Capture option selection validation added for the Total Export package helper; it remains non-wired and performs no capture/network behavior.
- Total Export package builder helper added; it creates package folders/manifests only when explicitly called and is not wired into GUI/export/capture behavior.
- Total Export asset registration helpers added for already-created local files; they are explicit-call only and do not perform capture, scraping, archive checks, screenshots, media downloading, or GUI/export wiring.
- Total Export manifest JSON read/round-trip helpers added; asset registration can update existing manifest files explicitly without capture/network behavior.
- Source Capture Plan helper added for future Total Export/source evidence workflows; it validates source adapters, capture option selections, and context hints without fetching/capture/network/GUI behavior.
- Total Export package-from-plan helper added; it creates package manifests from Source Capture Plans only when explicitly called and performs no fetch/capture/network/GUI behavior.
- Source Capture Plan provenance helpers added; Total Export package-from-plan manifests now include explicit provenance records without fetch/capture/network/GUI behavior.
- Added `SOURCE_CONTEXT_GLOSSARY_CURRENT_STATE.md` as a docs-only handoff/index for local source URL, source adapter, capture plan, provenance, and context/glossary helpers, tests, boundaries, and safe next milestones.
- Added an explicit-output-only Source Capture Plan inspection CLI for manually supplied source URL/context/glossary JSON, rendering text, Markdown, or JSON without fetch/capture/network/provider/GUI behavior.
- Added an explicit-output-only context/glossary CLI for manually supplied source label, source URL, title, and user terms, rendering normalized hints and deduped glossary candidates as text, Markdown, or JSON without fetch/capture/network/provider/GUI behavior.
- Added source adapter registry helpers for adapter `source_name` listing/name lookup plus regression coverage that adapters do not expose a misleading `.name` attribute.
- Added a local-only source adapter capability report helper and explicit-output-only CLI for registered adapter metadata, rendering text, Markdown, or JSON without fetch/capture/network/archive/provider/credential-test/scraping/GUI behavior.
- Added a metadata-only News Website source adapter skeleton for known Telegraph/MSN-style host suffixes; it performs URL recognition/normalization only and does not fetch, scrape, capture, archive-check, download, bypass access controls, or wire into the GUI.
- Added a local-only source adapter/preservation gap analysis helper and explicit-output-only CLI covering current adapters plus future ExportComments-style platform categories, Substack/newsletter sites, review platforms, and ArchiveBox-style preservation backends without fetch/capture/network/archive execution/scraping/GUI behavior.
- Added a local-only preservation backend plan helper and explicit-output-only CLI for manual local files, ArchiveBox-style self-hosted stores, and desired output formats such as HTML, PDF, PNG, TXT, JSON, WARC, media, and SQLite metadata without fetch/capture/network/archive execution/scraping/GUI behavior.
- Total Export prepare CLI can list preservation backend/format metadata and explain preservation backend plans without package creation or fetch/capture/network/archive execution/scraping/GUI behavior.
- Future visual preservation planning should distinguish visible-page screenshots, full-page screenshots, scrollable-container captures, stitched/multi-image captures, selected-DOM/print-cleaned HTML, raw saved HTML, and manually supplied evidence bundles; social comment modals can hide comments inside nested scroll containers, so generic full-page capture must not be treated as complete evidence.
- Added a local-only capture method metadata catalog for those seven manual evidence methods, including output kinds, limitations, future-automation candidacy, and recommended next steps without fetch/capture/browser/screenshot/network/scraping/GUI behavior.
- Added local-only media preservation choice metadata (`none`, `select`, or explicit `all`) to preservation plans and CLI reporting; it does not discover or download media, and future automation must remain opt-in, site-specific, and locally/mocked tested.
- Preservation plan reporting now accepts multiple existing capture-method IDs and renders their display names and limitations as metadata only; it performs no screenshots, DOM capture, scrolling, scraping, downloads, or browser execution.
- Added local-only preservation evidence bundle metadata and a stdout-only CLI for describing planned/manual/external artifacts, formats, capture-method links, path hints, and limitations without opening, scanning, hashing, validating, creating, uploading, or capturing files.
- Total Export manifest validation helpers added for local package/asset consistency checks; they are explicit-call only and perform no fetch/capture/network/GUI behavior.
- Total Export workflow helper added for explicit source URL -> plan -> package -> validation preparation; it remains non-wired and performs no fetch/capture/network/GUI behavior.
- Total Export summary helpers added for human-readable package/plan/validation review text; they are explicit-call only and perform no fetch/capture/network/GUI behavior.
- Total Export summary-file helper added for explicit package review summaries; it can register the summary as a local manifest asset without fetch/capture/network/GUI behavior.
- Total Export asset registration now supports duplicate-safe manifest updates for repeated explicit summary/asset registration without fetch/capture/network/GUI behavior.
- Total Export prepare helper added for explicit source URL -> package shell -> validation -> summary-file preparation; it remains non-wired and performs no fetch/capture/network/GUI behavior.
- Total Export prepare CLI added for explicit local package-shell testing; it remains non-wired and performs no fetch/capture/network/GUI behavior.
- Total Export prepare CLI now supports deterministic JSON output for local/dev scripting without fetch/capture/network/GUI behavior.
- Total Export README/marker helper added for explicit package-folder explanation and duplicate-safe local manifest registration without fetch/capture/network/GUI behavior.
- Total Export prepare helper/CLI can optionally write/register the README marker file without changing default non-wired fetch/capture/network behavior.
- Total Export prepare helper/CLI now supports final local manifest validation after summary/README review-file registration without fetch/capture/network/GUI behavior.
- Total Export inventory helper added for local package file-vs-manifest review without fetch/capture/network/GUI behavior.
- Total Export prepare CLI can optionally print local package inventory data without writing/registering inventory reports or performing fetch/capture/network/GUI behavior.
- Total Export inventory report helper added for explicit local package inventory text reports and duplicate-safe manifest registration without fetch/capture/network/GUI behavior.
- Total Export prepare helper/CLI can optionally write/register the inventory report file without changing default non-wired fetch/capture/network behavior.
- Total Export prepare CLI developer examples documented for local-only package-shell usage without fetch/capture/network/GUI behavior.
- Total Export prepare CLI now supports a local-only `--review-files` shortcut for README, inventory report, and inventory output without fetch/capture/network/GUI behavior.
- Total Export prepare CLI can list supported capture options in text or JSON without preparing packages or performing fetch/capture/network/GUI behavior.
- Total Export prepare CLI can list source adapter and ASR provider metadata in text/JSON without package creation or fetch/capture/network/GUI behavior.
- Total Export prepare CLI can explain source capture plans without package creation or fetch/capture/network/GUI behavior.
- Total Export prepare helper/CLI can optionally write/register a local source-plan report without fetch/capture/network/GUI behavior.
- Total Export prepare CLI supports `--full-review-files` for README, source-plan report, inventory report, and inventory output without changing default behavior.
- Total Export prepare CLI can inspect existing local package folders in text/JSON without creating files or performing fetch/capture/network/GUI behavior.
- Total Export prepare CLI can create deterministic local ZIPs for existing inspected package folders without fetch/capture/network/GUI behavior or external archive submission.
- Total Export prepare CLI can inspect local Total Export ZIP files in text/JSON without extraction, fetch/capture/network/GUI behavior, or external archive access.
- Total Export prepare CLI can write local `.sha256` and `.inspection.json` sidecars for inspected ZIPs without extraction, fetch/capture/network/GUI behavior, or external archive access.
- Total Export prepare CLI can build a local review bundle in one command: package shell, full review files, package inspection, ZIP, ZIP inspection, and optional ZIP sidecars, without fetch/capture/network/GUI behavior or external archive access.
- Total Export prepare CLI can verify local review-bundle ZIPs against `.sha256` and `.inspection.json` sidecars without extraction, fetch/capture/network/GUI behavior, or external archive access.
- Total Export prepare CLI can verify folders of local review-bundle ZIPs against sidecars, optionally writing a local JSON report, without extraction, fetch/capture/network/GUI behavior, or external archive access.
- Total Export prepare CLI can build local review bundles from a UTF-8 batch source file and optionally verify/report the output folder, without fetch/capture/network/GUI behavior or external archive access.
- Total Export prepare CLI can dry-run local batch review-bundle inputs, deriving package/ZIP/sidecar paths and detecting duplicate/existing outputs without writing files or using fetch/capture/network/GUI behavior.
- Total Export prepare CLI can reconcile a local UTF-8 batch source file against expected review-bundle ZIPs and sidecars without writing by default, extraction, fetch/capture/network/GUI behavior, or external archive access.
- `SOURCE_PRESERVATION_ROADMAP.md` documents future local media registration and manual archive URL preservation phases while keeping downloading, archive checks/submission, screenshots, scraping, network/API calls, and GUI wiring out of scope.
- Added a local-only manual archive URL metadata skeleton for user-supplied archive links and user-entered archive statuses, without archive checks/submission, network, scraping, downloading, or GUI integration.
- Added a local-only media registration metadata skeleton for user-supplied local media files, local file size/hash notes, and extension-based media type reporting without downloads, fetching, transcription, network, archive checks, or GUI integration.
- Added a local-only media verification helper/report for re-checking user-supplied local file paths, size, and optional SHA-256 without downloads, fetching, transcription, network, archive checks, scraping, browser automation, or GUI integration.
- Added a local-only media verification CLI for rendering verification of user-supplied local media records as text, Markdown, or JSON without downloads, network, archive checks, transcription, scraping, or GUI integration.
- Added a local-only preservation plan report helper that compares source URLs with manual archive URL metadata and local media registration records to identify manual follow-up actions without archive checks, downloads, network, scraping, transcription, or GUI integration.
- Added a local-only preservation plan CLI for rendering user-supplied archive/media metadata as text, Markdown, or JSON without archive checks, downloads, network, scraping, transcription, or GUI integration.
- Added a local-only Total Export bundle index helper for existing review-bundle ZIPs and sidecars, reporting missing/mismatched local sidecars without ZIP extraction, network, archive checks, downloads, or GUI integration.
- Added a local-only Total Export bundle index CLI for rendering existing ZIP/sidecar indexes as text, Markdown, or JSON without ZIP extraction, network, archive checks, downloads, or GUI integration.
- Added a local-only bundle index reconciliation helper for comparing expected ZIP paths with local bundle index results, reporting missing, unexpected, and needs-review bundles without ZIP extraction, network, archive checks, downloads, or GUI integration.
- Added a local-only bundle index reconciliation CLI for comparing JSON/text expected ZIP lists with local bundle index results and rendering text, Markdown, or JSON without ZIP extraction, network, archive checks, downloads, or GUI integration.
- Added `SOURCE_PRESERVATION_CURRENT_STATE.md` as a docs-only handoff/index for local preservation helpers, CLIs, tests, boundaries, and safe next milestones.
- Added a local-only preservation metadata seed JSON and tests for manual archive/local media records and preservation-plan reporting without archive checks, downloads, network, scraping, transcription, or GUI integration.
- Added a local-only preservation metadata seed report generator for Markdown, text, or JSON with explicit-output-only writes and no network, archive, download, provider, ZIP extraction, or GUI behavior.
- Added a local-only evidence package manifest helper/report for aggregating preservation, media, verification, and bundle metadata without file copying, package building, ZIP extraction, network, archive checks, downloads, or GUI integration.
- Added a local-only evidence manifest CLI for rendering source, archive, media, verification, and bundle metadata as Markdown, text, or JSON with explicit-output-only writes and no file copying, package building, ZIP creation/extraction, network, archive checks, downloads, or GUI integration.
- Added `PROJECT_CURRENT_STATE_HANDOFF.md` as a docs-only cross-project handoff covering ASR comparison, Total Export, upstream parity, local preservation/evidence helpers, workflow boundaries, and safe next milestones.
- Added a local-only ASR decision summary report for accepted/candidate/rejected/blocked/external-lead counts, leading scored/local results, and safe next-action guidance without provider calls, transcription, downloads, network, or GUI integration.
- Added an explicit-output-only ASR decision summary CLI for rendering manually entered provider status/ranking records as Markdown, text, or JSON without provider calls, transcription, downloads, network, or GUI integration.
- Added `ASR_REPORTING_CURRENT_STATE.md` as a docs-only handoff/index for local ASR comparison, decision-summary, term-coverage helpers, CLIs, tests, boundaries, and safe next milestones.
- Added `ASR_PROVIDER_STATUS_NOTES.md` as a docs-only status clarification for accepted/candidate/rejected/blocked/needs-review ASR provider records, preserving AWS as blocked and ElevenLabs as a candidate without provider calls or runtime integration.
- Added an explicit-output-only combined ASR report CLI for rendering manual comparison, decision summary, and term coverage sections together as Markdown, text, or JSON without provider calls, transcription, downloads, network, or GUI integration.
- Polished `ASR_MANUAL_RESULTS_SEED.json` metadata with descriptive local reporting/status policy fields for the 95% gate, Term QA, accepted/candidate/blocked/external-lead handling, current leaders, and reporting CLIs without provider calls or runtime integration.
- Fixed the ASR manual seed blocked-status metadata wording so `asr_manual_results_seed_test.py` passes and blocked rows are explicitly described as not quality-rejected.
- Refreshed `PROJECT_CURRENT_STATE_HANDOFF.md` and `ASR_REPORTING_CURRENT_STATE.md` to the current `b59a052` checkpoint after ASR reporting/metadata cleanup.
- Added a local-only ASR term coverage/gap summary report for manually entered comparison records, showing key-term hit/miss patterns, known-phrase performance, and provider gaps without provider calls, transcription, downloads, network, or GUI integration.
- Added an explicit-output-only ASR term coverage summary CLI for rendering manually entered key-term hit/miss and provider-gap records as Markdown, text, or JSON without provider calls, transcription, downloads, network, or GUI integration.
- `UPSTREAM_V2_1_1_AUDIT.md` records a docs-only upstream/original-creator v2.1.1 parity audit and recommended local/mocked regression tests before porting behavior.
- Added local upstream v2.1.1 parity regression tests for testable extractor error handling, newest-sort/max-comment mapping, and spam false-positive areas; GUI export/fetch-state and campaign short-praise guards remain deferred pending helper extraction or a later behavior port.
- Added local upstream v2.1.1 behavior fixes for structured quota/daily-limit API error classification and short-praise campaign false-positive guarding, with local regression coverage and no network/GUI/provider behavior.
- Added local upstream v2.1.1 safety coverage/fixes for export blocking during active fetch/cancel states and keyring runtime fallback, using mocked/local tests without network, real credentials, or GUI launch.
- Local Total Export dev output folders are ignored to avoid committing generated package checks.
- Future source adapter pipeline:
  - Source URL.
  - Identify source type.
  - Route to matching adapter.
  - Adapter validates/normalizes URL.
  - Adapter fetches source-specific metadata/comments/livechat/transcripts where supported.
  - Normalize output into shared comment/transcript/evidence structures.
  - Export with existing evidence-friendly TXT/JSON structure.
- Conceptual adapter interface:
  - `source_name`
  - `can_handle(url)`
  - `normalize_url(url)`
  - `extract_source_id(url)`
  - `fetch_metadata()`
  - `fetch_comments()`
  - `fetch_replies()` if applicable.
  - `fetch_livechat()` if applicable.
  - `fetch_transcript_or_captions()` if applicable.
  - Capability flags:
    - `supports_comments`
    - `supports_replies`
    - `supports_livechat`
    - `supports_likes`
    - `supports_timestamps`
    - `supports_author_channel_ids`
    - `supports_transcripts`
- Initial adapters:
  - YouTube adapter:
    - Current implemented source.
    - Comments supported.
    - Replies supported.
    - Livechat supported where `activeLiveChatId` exists.
    - Transcripts/captions partly supported through the existing transcript downloader.
    - Likes supported for normal comments/replies.
  - News Website adapter:
    - Metadata-only known-host URL recognition/normalization for Telegraph/MSN-style news websites.
    - No fetching, scraping, archive checks, screenshots, media downloading, access bypass, credential storage, or GUI wiring.
  - Future adapters:
    - Reddit.
    - Additional site-specific or site-family website adapters.
    - Forums.
    - Other video platforms.
    - Each needs site-specific rules and should not be assumed trivial.
- Source adapter principles:
  - Full capture is preferred over filtering.
  - Filters should be opt-in/user-controlled.
  - Source-specific limitations must be visible to the user.
  - Never silently treat missing comments as proof that no comments exist.
  - Preserve raw/source metadata where useful for evidence export.
  - Keep YouTube path stable while generalizing terminology.
  - New adapters should start as metadata-only, site-specific or site-family skeletons before any capture/fetch behavior.
  - Network fetching should remain explicit/user-triggered.
  - External/background context remains optional, strict-filtered, non-blocking, and not ground truth.
- Target pipeline:
  - Source URL.
  - Validate/normalize URL.
  - Extract source ID. The current YouTube adapter uses an 11-character video ID.
  - Fetch metadata where available.
  - Fetch existing captions/transcripts where available.
  - Fetch comments/livechat where available and user-selected.
  - Collect contextual text from metadata/comments/transcripts.
  - Optionally collect external background context later.
  - Extract candidate glossary/entities.
  - Let user review/edit glossary.
  - Pass glossary/keyterms into ASR providers that support it.
  - Run ASR as draft.
  - Run Term QA/glossary checks.
  - User reviews/accepts/edits final transcript.
- Feature principles:
  - Existing captions/transcripts should be preferred when available and acceptable.
  - ASR should be used when no reliable transcript exists or when user requests it.
  - Metadata/comments/context are for glossary discovery and QA, not a replacement for transcription.
  - Metadata/comments/transcripts/external context are only used to propose glossary/entity candidates and QA warnings.
  - External/background context is optional.
  - External/background context must be strict-filtered.
  - External/background context must never block local transcript/ASR work.
  - External/background context must never be trusted as ground truth.
  - No silent auto-correction of transcript terms.
  - User must be able to review/edit glossary before it affects ASR or QA.
  - User review remains required before glossary candidates affect ASR prompts/keyterms or final transcript decisions.
  - Provider-specific glossary support should be optional:
    - ElevenLabs keyterms.
    - Deepgram keyterms.
    - Speechmatics custom dictionary.
    - Azure phrase list.
    - AWS custom vocabulary only if future access works.
    - whisper.cpp prompt/initial prompt.
  - If a provider has no glossary support, glossary still feeds Term QA after transcription.
  - Keep local/offline ASR available for privacy/no-cloud mode.
  - Keep cloud ASR opt-in because of cost/privacy/API-key concerns.
- Likely implementation phases:
  1. URL validation and source ID extraction. Current adapter-specific case: YouTube 11-character video ID.
  2. Metadata/transcript/comment fetch plumbing.
  3. Context-to-glossary resolver.
  4. Glossary review UI.
  5. Provider keyterm/prompt mapping.
  6. ASR run + Term QA review flow.
  7. Evidence/debug export for transcript decisions.

Command style preference:
- Do not put multiple separate CMD commands in one copy block.
- Avoid repeating cd/venv activation when already in the project venv.
- Prefer one large Python patch/update file over many manual code edits.

## 2026-07-07 Local ASR result: Parakeet rejected

Status:
- whisper.cpp Vulkan is working on AMD RX 5700.
- Built-in ASR Self-Test 15s passed with AMD GPU — whisper.cpp large-v3-turbo terms only.
- Real media Auto Probe 30s still failed the 95% reference threshold.
- Best real-media whisper.cpp candidate remained AMD GPU — whisper.cpp large-v3-turbo phrase prompt at about 74.19% reference word accuracy.
- The app correctly kept the imported reference transcript and did not load the failed ASR draft.

Parakeet test:
- `parakeet-cli.exe` exists in the whisper.cpp Vulkan build and runs on AMD Vulkan.
- Downloaded and tested:
  - `ggml-parakeet-tdt-0.6b-v3-q8_0.bin`
  - `ggml-parakeet-tdt-0.6b-v3-f16.bin`
- Parakeet q8_0 strict 30s score: 49.46% word accuracy.
- Parakeet f16 strict 30s score: 47.31% word accuracy.
- Both Parakeet outputs were very fast but missed critical wording/names:
  - `Shadowsmith` became `Shadow Smith`
  - `blindfold` became `blindfold plan thing` / `blind fault plant thing`
  - `I've cleared the Nicolas Cage event` became `that's really the Nicholas cage of it`
  - `Caltheris` became `Cal Ferris`

Decision:
- Do not integrate Parakeet into Auto Quality Probe yet.
- It is practical and fast on AMD Vulkan, but not accurate enough for this subtitle workflow.
- Keep Parakeet models installed for future comparison only.

## 2026-07-07 Local ASR result: DirectML / TorchCodec feasibility

Status:
- `onnxruntime-directml==1.24.4` is installed locally and ONNX Runtime reports `DmlExecutionProvider`.
- `optimum-onnx==0.1.0`, `optimum==2.1.0`, and `onnx==1.22.0` are installed locally.
- DirectML Whisper tiny.en ONNX export, load, and direct `ORTModelForSpeechSeq2Seq.generate()` completed successfully.
- The tiny.en DirectML probe was fast but scored about 49.46% strict 30s reference word accuracy, so it is only a runtime proof, not a quality verdict.
- The Transformers pipeline path initially failed because TorchCodec could not load FFmpeg DLLs.
- TorchCodec import and the Transformers pipeline path work after registering the FFmpeg 7 shared DLL folder before importing TorchCodec-related libraries.

Runtime note:
- The local FFmpeg 7 shared build used for TorchCodec is `C:\ffmpeg-7-shared\bin`.
- Experimental DirectML/TorchCodec scripts should call `os.add_dll_directory(r"C:\ffmpeg-7-shared\bin")` before TorchCodec imports, or use `asr_runtime_paths.add_ffmpeg7_shared_dll_directory()`.
- The helper also supports overriding that folder with `ASR_FFMPEG7_SHARED_BIN`.

Decision:
- Do not integrate DirectML into the main UI yet.
- Do not treat tiny.en as representative of final DirectML quality.
- Next DirectML work should remain an explicit experimental script using direct `AutoProcessor` plus `ORTModelForSpeechSeq2Seq.generate()` with larger models.

Manual runner:
- `RUN_DIRECTML_WHISPER_MATRIX.py` is available for manual local testing only.
- It compares `openai/whisper-base.en` and `openai/whisper-small.en` through ONNX Runtime DirectML on the same 30s reference probe.
- It is not wired into `main.py`, `asr_tools.py`, the UI, or Auto Quality Probe.
- It should be run manually from the project venv when DirectML testing is desired.

Manual DirectML matrix result:
- The runner completed after fixing generation config. These are manual matrix results, not final ASR quality results.
- Provider: `DmlExecutionProvider`.
- `openai/whisper-small.en`: 58.06% strict 30s reference accuracy, 41.94% WER, 65 candidate words, 11.37s elapsed.
- `openai/whisper-base.en`: 55.91% strict 30s reference accuracy, 44.09% WER, 63 candidate words, 12.97s elapsed.
- Important failures:
  - `Shadowsmith` became `Shousemith` / `chat's missing`.
  - `Caltheris` became `Kalfirisk` / `Calfare, Wisconsin`.
  - `I've cleared the Nicolas Cage event` was not recovered correctly.
  - base.en produced `Miyas`.

Decision:
- Reject DirectML base.en and small.en for Auto Quality Probe for now.
- DirectML is technically viable on AMD Windows, but current base/small ONNX quality is below whisper.cpp Vulkan on this clip.
- Do not test medium/large DirectML models yet unless explicitly approved later.

Manual scoring helper:
- `RUN_TRANSCRIPT_REFERENCE_SCORE.py` is available for manual provider-agnostic transcript comparison.
- It can score future offline or online transcript files against the same strict reference window without integrating any provider into the app.
- It writes `TRANSCRIPT_REFERENCE_SCORE_SUMMARY.txt`, which is a local ignored output.
- No new ASR/provider results have been recorded from this helper yet.

AssemblyAI manual API transcript results:
- Default/no-context:
  - `speech_model_used`: `universal-3-5-pro`.
  - Input: `directml_probe_30s.wav`.
  - Candidate file: `candidate_assemblyai.txt`.
  - Reference scoring window: strict first 30s.
  - Reference words: 93.
  - Candidate words: 74.
  - WER: 29.03%.
  - Reference accuracy: 70.97%.
  - Important terms:
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Caltheris`: MISSING.
  - Important failures:
    - `I've cleared the Nicolas Cage event` was rendered as `it's weird, the Nicolas Cage event`.
    - `Caltheris` was rendered as `Calpheon`.
- Prompted/keyterms:
  - `speech_model_used`: `universal-3-5-pro`.
  - `keyterms_prompt` accepted:
    - `Kingman`
    - `ZoneX`
    - `Shadowsmith`
    - `Nicolas Cage`
    - `Freckelston`
    - `Caltheris`
    - `Nyxara`
  - Candidate file: `candidate_assemblyai_prompted.txt`.
  - Reference scoring window: strict first 30s.
  - Reference words: 93.
  - Candidate words: 76.
  - WER: 29.03%.
  - Reference accuracy: 70.97%.
  - Important terms:
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Caltheris`: FOUND.
  - Important failures:
    - `I've cleared the Nicolas Cage event` was still rendered as `it's weird, the Nicolas Cage event`.
    - It added `Cool.` at the start.
  - Prompting fixed `Caltheris` but did not improve the overall WER/accuracy.

Decision:
- Reject AssemblyAI Universal-3.5 Pro default and prompted/keyterms results for integration for now.
- Both are below the 95% acceptance threshold.
- The prompted/keyterms run still does not beat the best local whisper.cpp Vulkan result on this clip.
- Keep provider comparison manual until a provider clearly beats the local options.

Deepgram Nova-3 keyterms manual transcript result:
- Provider: Deepgram Nova-3 prerecorded transcription with keyterm prompting.
- Keyterms used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Nicolas Cage`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
- Generated files, local only:
  - `TEMP_DEEPGRAM_TRANSCRIBE.py`
  - `candidate_deepgram_nova3_keyterms.txt`
  - `candidate_deepgram_nova3_keyterms.json`
- Score from `RUN_TRANSCRIPT_REFERENCE_SCORE.py` after correcting the reference line to `Oh, I've completed the Nicolas Cage event`:
  - Candidate: `candidate_deepgram_nova3_keyterms.txt`.
  - Reference words: 93.
  - Candidate words: 77.
  - WER: 33.33%.
  - Reference accuracy: 66.67%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: FOUND.
  - `Nicolas Cage`: FOUND.
  - `Freckelston`: MISSING.
  - `Caltheris`: FOUND.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cutscene, to be honest. I I think it's it's a lot of great content there. I think I think there's a there's a lot to digest in that cutscene. Yeah. But, like, you know, when the Shadowsmith is on screen. When she's not, you know, don't care. But I I understand the blindfold. It's all I'm saying. Mhmm. Fuck. We have Nicolas Cage event. Trying to insinuate. I just We need more Caltheris content.`

Decision:
- Reject Deepgram Nova-3 keyterms for integration for now.
- It found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`, but strict reference accuracy was only 66.67%.
- It does not beat AssemblyAI at 70.97%.
- It does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- It badly misrecognized the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `Fuck. We have Nicolas Cage event`, so it is not acceptable for this workflow.

Speechmatics enhanced custom dictionary manual transcript result:
- Provider: Speechmatics Batch API on EU1 endpoint.
- Model/config: enhanced model with custom dictionary / additional vocabulary.
- Notes:
  - An older key returned 401 Unauthorized.
  - A new key worked on EU1.
  - Initial config failed with HTTP 400 because `remove_disfluencies` is not allowed in the current Speechmatics job config.
  - Removing `remove_disfluencies` allowed the job to run.
- Custom dictionary terms / `sounds_like` hints included:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Nicolas Cage`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
- Generated files, local only:
  - `TEMP_SPEECHMATICS_TRANSCRIBE.py`
  - `candidate_speechmatics_enhanced_vocab.txt`
  - `candidate_speechmatics_enhanced_vocab.json`
  - `candidate_speechmatics_enhanced_vocab_job.json`
- Score from `RUN_TRANSCRIPT_REFERENCE_SCORE.py`:
  - Candidate: `candidate_speechmatics_enhanced_vocab.txt`.
  - Reference words: 93.
  - Candidate words: 71.
  - WER: 34.41%.
  - Reference accuracy: 65.59%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: FOUND.
  - `Nicolas Cage`: FOUND.
  - `Freckelston`: MISSING.
  - `Caltheris`: FOUND.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cut scene, to be honest. I think it's a lot of great content in there. I think there's a lot to digest in that cutscene. Yeah. But like, you know, when, uh, the Shadowsmith is on screen, when she's not, you know, don't care, but I understand the blindfold. That's all I'm saying. Mhm. I played the Nicolas Cage event. I just we need more Caltheris content. MM.`

Decision:
- Reject Speechmatics enhanced custom dictionary for integration for now.
- It found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`, but strict reference accuracy was only 65.59%.
- It does not beat Deepgram at 66.67%.
- It does not beat AssemblyAI at 70.97%.
- It does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- It misrecognized the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `I played the Nicolas Cage event`, so it is not acceptable for this workflow.

Google Speech-to-Text v1 phrase-hint manual transcript results:
- Provider: Google Speech-to-Text v1 synchronous recognize.
- Authentication: API key.
- Input file: `directml_probe_30s.wav`.
- WAV info: mono, 16000 Hz, 16-bit PCM.
- Phrase hints used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Shadowsmith's`
  - `Nicolas Cage`
  - `Nicolas Cage event`
  - `I've completed the Nicolas Cage event`
  - `Oh I've completed the Nicolas Cage event`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
  - `blindfold`
- Generated files, local only:
  - `TEMP_GOOGLE_STT_TRANSCRIBE.py`
  - `candidate_google_stt_latest_long_phrases.txt`
  - `candidate_google_stt_latest_long_phrases.json`
  - `candidate_google_stt_video_enhanced_phrases.txt`
  - `candidate_google_stt_video_enhanced_phrases.json`
- Run 1:
  - Model/config: `latest_long` with phrase hints.
  - Candidate: `candidate_google_stt_latest_long_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 66.
  - WER: 49.46%.
  - Reference accuracy: 50.54%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: MISSING.
    - `Nicolas Cage`: FOUND.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `Oh, it's a Great Cuts in me Oz. I think it's a lot of great content there. I mean, that's a lot to digest in that cutting. Yeah. Like, you know, when the child Smith is on screen when she's not, you know, don't care, but I understand the blindfold. So I'm saying. I've played the Nicolas Cage. I just we need more Calvin. Harris content.`
- Run 2:
  - Model/config: `video` with `useEnhanced=true` and phrase hints.
  - Candidate: `candidate_google_stt_video_enhanced_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 70.
  - WER: 38.71%.
  - Reference accuracy: 61.29%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: MISSING.
    - `Nicolas Cage`: MISSING.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `It's a great cutscene to be honest. I I think it's a long break content there. I think there's a lot to digest in that cut scene. Yeah. So like you know when uh, the Sha Smith's on screen when she's not, you know, don't care. But I I understand the blindfold. That's why I'm saying, mhm. Oh, I believe the Nicholas Cage. I just we need more cerus content.`

Decision:
- Reject Google Speech-to-Text v1 phrase-hint runs for integration for now.
- The best Google run was video enhanced at 61.29%, which is below Speechmatics at 65.59%, Deepgram at 66.67%, AssemblyAI at 70.97%, and the best local whisper.cpp Vulkan run at about 74.19%.
- Google `latest_long` performed worse at 50.54%.
- Google failed the critical phrase around `Oh, I've completed the Nicolas Cage event`.
- Google also failed key glossary terms, including `Shadowsmith` and `Caltheris`.
- Keep Google out of provider integration unless a clearly better Google configuration is tested later.

Azure Speech SDK phrase-list manual transcript results:
- Provider: Azure Speech SDK.
- Azure Speech resource: UK South.
- Python SDK installed in venv:
  - `azure-cognitiveservices-speech` 1.50.0.
  - `azure-core` 1.41.0.
- Input file: `directml_probe_30s.wav`.
- Phrase list used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Shadowsmith's`
  - `Nicolas Cage`
  - `Nicolas Cage event`
  - `I've completed the Nicolas Cage event`
  - `Oh I've completed the Nicolas Cage event`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
  - `blindfold`
  - `cut scene`
- Generated files, local only:
  - `TEMP_AZURE_SPEECH_TRANSCRIBE.py`
  - `candidate_azure_speech_en_us_phrases.txt`
  - `candidate_azure_speech_en_gb_phrases.txt`
- Run 1:
  - Model/config: Azure Speech SDK, language=`en-US`, phrase list.
  - Candidate: `candidate_azure_speech_en_us_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 68.
  - WER: 35.48%.
  - Reference accuracy: 64.52%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `It's a great cut scene. Be honest. I think it's a lot of great content there. I think there's a lot to digest in that cut scene, yeah. Like, you know, when the Shadowsmith is on screen, when she's not, you know, don't care. But I, I understand the blindfold, that's all I'm saying. I believe the Nicolas Cage event. I just we need more Cal fearless content.`
- Run 2:
  - Model/config: Azure Speech SDK, language=`en-GB`, phrase list.
  - Candidate: `candidate_azure_speech_en_gb_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 68.
  - WER: 35.48%.
  - Reference accuracy: 64.52%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `It's a great cut scene. Be honest. I think it's a lot of great content there. I think there's a lot to digest in that cut scene, yeah. Like, you know, when the Shadowsmith is on screen, when she's not, you know, don't care. But I, I understand the blindfold, that's all I'm saying. I believe the Nicolas Cage event. I just we need more Cal fearless content.`

Decision:
- Reject Azure Speech SDK phrase-list runs for integration for now.
- `en-US` and `en-GB` produced the same result.
- Strict reference accuracy was only 64.52%.
- Azure does not beat Speechmatics at 65.59%.
- Azure does not beat Deepgram at 66.67%.
- Azure does not beat AssemblyAI at 70.97%.
- Azure does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- Azure failed the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `I believe the Nicolas Cage event`.
- Azure also failed `Caltheris`, producing `Cal fearless`.
- Keep Azure out of provider integration unless a clearly better Azure configuration is tested later.

Cohere Transcribe manual transcript result:
- Provider: Cohere Transcribe API.
- Model/config: `cohere-transcribe-03-2026`.
- Endpoint/script used local temp script:
  - `TEMP_COHERE_TRANSCRIBE.py`
- Input file:
  - `directml_probe_30s.wav`
- Output files, local only:
  - `candidate_cohere_transcribe_03_2026.txt`
  - `candidate_cohere_transcribe_03_2026.json`
- The test was run twice and produced the same transcript preview/output.
- Score:
  - Candidate: `candidate_cohere_transcribe_03_2026.txt`.
  - Reference words: 93.
  - Candidate words: 74.
  - WER: 41.94%.
  - Reference accuracy: 58.06%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: MISSING.
  - `Nicolas Cage`: MISSING.
  - `Freckelston`: MISSING.
  - `Caltheris`: MISSING.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cutscene, to be honest. I think it's a lot of great content there. I think there's a lot to digest in that cutscene. Yeah. For, like, you know, when the Shouse Mist is on screen. When she's not, you know, don't care. I understand the blindfold. That's what I'm saying. I believe the Nicholas Cage event. I'm just trying to insinuate. I just. We need more Carl Fairis content. Hmm. Yeah.`

Decision:
- Reject Cohere Transcribe 03-2026 for integration for now.
- Strict reference accuracy was only 58.06%.
- Cohere does not beat Google STT video enhanced phrases at 61.29%.
- Cohere does not beat Azure Speech SDK phrase list at 64.52%.
- Cohere does not beat Speechmatics at 65.59%.
- Cohere does not beat Deepgram at 66.67%.
- Cohere does not beat AssemblyAI at 70.97%.
- Cohere does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- Cohere failed the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `I believe the Nicholas Cage event`.
- Cohere failed `Shadowsmith`, producing `Shouse Mist`.
- Cohere failed `Caltheris`, producing `Carl Fairis`.
- Cohere missed all tracked important terms.
- Keep Cohere out of provider integration unless a clearly better Cohere configuration is tested later.

AWS Transcribe custom vocabulary manual test status:
- Provider: AWS Transcribe batch transcription with custom vocabulary.
- Region attempted: `eu-west-2` / Europe London.
- IAM user/access key was created for a temporary local test.
- `AWS_SESSION_TOKEN` was intentionally cleared because normal IAM user access keys do not use a session token.
- Local temp script:
  - `TEMP_AWS_TRANSCRIBE_CUSTOM_VOCAB.py`
- Input file:
  - `directml_probe_30s.wav`
- Planned language/config:
  - `en-GB` with custom vocabulary.
  - `en-US` with custom vocabulary.
- Planned local output files:
  - `candidate_aws_transcribe_custom_vocab_en_gb.txt`
  - `candidate_aws_transcribe_custom_vocab_en_gb.json`
  - `candidate_aws_transcribe_custom_vocab_en_us.txt`
  - `candidate_aws_transcribe_custom_vocab_en_us.json`
- Observed run result:
  - S3 setup succeeded:
    - Temporary bucket was created.
    - Audio was uploaded to S3.
    - Vocabulary table was uploaded to S3.
  - AWS Transcribe failed before any transcription job could run.
  - Failure occurred on `CreateVocabulary`.
  - Error:
    - `SubscriptionRequiredException`
    - `The AWS Access Key Id needs a subscription for the service`
  - The AWS Console in Europe London showed the same service-subscription error.
  - Temporary S3 cleanup succeeded:
    - Vocabulary object deleted.
    - Audio object deleted.
    - Temporary bucket deleted.
  - No transcript candidate was produced.
  - No WER/reference-accuracy score was produced.

Decision:
- Mark AWS Transcribe custom vocabulary as BLOCKED, not rejected.
- Do not rank AWS against the tested ASR providers because no model-quality result exists.
- Cause appears to be AWS account/service subscription access under the current free-plan/account state, not local script failure.
- Do not upgrade to paid AWS solely for this test unless explicitly approved later.
- Keep AWS Transcribe as a possible future retest only if service access becomes available without unwanted billing risk.

ElevenLabs Scribe v2 keyterms manual transcript result:
- Provider: ElevenLabs Speech-to-Text API.
- Model/config: Scribe v2 with keyterms.
- Local temp script:
  - `TEMP_ELEVENLABS_SCRIBE_TRANSCRIBE.py`
- Input file:
  - `directml_probe_30s.wav`
- Output files, local only:
  - `candidate_elevenlabs_scribe_v2_keyterms.txt`
  - `candidate_elevenlabs_scribe_v2_keyterms.json`
- API key was cleared from the CMD session after the test.
- Keyterms used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Shadowsmith's`
  - `Nicolas Cage`
  - `Nicolas Cage event`
  - `completed Nicolas Cage event`
  - `Oh I've completed`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
  - `blindfold`
  - `cut scene`
  - `cutscene`
- Score:
  - Candidate: `candidate_elevenlabs_scribe_v2_keyterms.txt`.
  - Reference words: 93.
  - Candidate words: 85.
  - WER: 15.05%.
  - Reference accuracy: 84.95%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: FOUND.
  - `Nicolas Cage`: FOUND.
  - `Freckelston`: MISSING.
  - `Caltheris`: FOUND.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cut scene to be honest. I, I think it's a lot of great content in there Gotcha I think, I think there's a, there's a lot to digest in that cut scene, yeah. For like, you know, when, uh, the Shadowsmith's on screen. When she's not, you know, don't care, but- I, I understand the blindfold. That's all I'm saying Mm-hmm. Oh I've completed the Nicolas Cage event Like what you're trying to insinuate I just- We need more Caltheris content`

Decision:
- Mark ElevenLabs Scribe v2 with keyterms as the new best tested online ASR provider result so far.
- Reference accuracy was 84.95%, clearly above all previously tested providers and the previous best local whisper.cpp Vulkan run at about 74.19%.
- ElevenLabs correctly preserved the critical phrase around `Oh I've completed the Nicolas Cage event`.
- ElevenLabs correctly found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`.
- ElevenLabs still missed `Kingman`, `ZoneX`, `Freckelston`, and `Nyxara`, so ASR output must still be treated as draft text with Term QA/glossary review.
- Do not treat ElevenLabs as final truth; treat it as a leading integration candidate subject to cost, quota, API reliability, and user opt-in.
- Keep local whisper.cpp Vulkan as the best no-cloud/free local baseline.
- Current architecture decision remains: ASR draft + glossary/context QA + explicit user review.

## ASR hardware profile planning

Recommended offline/hardware profiles:
- AMD Windows, older Radeon such as RX 5700:
  - Recommended local path: whisper.cpp Vulkan.
  - Keep local whisper.cpp Vulkan as the best no-cloud/free local baseline.
  - Best tested local/no-cloud result remains whisper.cpp Vulkan large-v3-turbo with phrase prompt at about 74.19% reference accuracy.
  - CPU/quantized whisper.cpp is fallback only.
  - DirectML is experimental/low-return based on local tests.
  - ROCm/PyTorch is not a reliable Windows path for this RX 5700/RDNA1 setup.
- NVIDIA Windows/Linux:
  - Recommended GPU paths:
    - faster-whisper / CTranslate2 CUDA.
    - whisper.cpp CUDA.
  - Advanced Linux/NVIDIA users may test NeMo/Parakeet/Canary-style models separately.
  - Do not make this the default for the current AMD test machine.
- Intel CPU / iGPU / Arc:
  - Recommended path: OpenVINO Whisper / Distil-Whisper-style route.
  - CPU fallback remains available.
  - This is a profile for Intel users, not tested on the current AMD RX 5700 machine.
- CPU-only:
  - Recommended path: whisper.cpp quantized models.
  - Use strict draft-only mode.
  - Expect slower speed and no guarantee of better accuracy.

Architecture notes:
- ElevenLabs Scribe v2 with keyterms is the leading optional cloud integration candidate after the provider confidence pass, at 84.95% reference accuracy.
- AWS Transcribe custom vocabulary is BLOCKED, not rejected, because no score was produced.
- Local ASR and cloud ASR should both be treated as draft text unless a strict quality gate passes.
- Term QA/glossary review remains mandatory for names and lore terms.
- Keep local whisper.cpp Vulkan as the best free/local fallback.
- Hardware acceleration does not guarantee higher accuracy by itself. It mainly enables faster/larger model testing.
- Any NVIDIA, Intel, or CPU profile must pass the same strict reference scoring gate before being trusted.
- DirectML base/small are rejected for now; DirectML medium/large remain deferred unless explicitly approved later.
- Offline ASR is not fully exhausted globally, but the practical AMD paths tested so far are below the project acceptance threshold.

Next local-ASR branches:
1. Canary / other offline model feasibility if practical.
2. NVIDIA CUDA and Intel OpenVINO profile testing only on matching hardware.
3. DirectML medium/large only if explicitly approved later.

- Preservation evidence bundle metadata is now integrated into preservation plan reporting and Total Export prepare preservation explanations; it remains descriptive only and does not open, scan, hash, validate, create, upload, download, capture, scrape, or fetch evidence files/URLs.

- Evidence bundle plan reporting now exposes metadata-only item details for artifact role, origin, path hint labels, and item notes; path hints are not opened or checked.

- The standalone preservation evidence bundle CLI now accepts item role, origin, path hint label, and notes metadata; path hints remain labels only and are not opened or checked.

- Evidence item spec parsing is centralized in the preservation evidence bundle model and reused by the standalone CLI, preservation backend CLI, and Total Export prepare CLI to keep detail validation consistent.

- Added regression coverage that rejects malformed, duplicate, or unknown evidence item detail specs across the shared helper and CLI entry points.

- Preservation backend plan CLI input JSON can include an `evidence_bundle` object parsed as local descriptive metadata only; path hints remain labels and are not opened or checked.

- Standalone preservation evidence bundle CLI can read an explicit local JSON bundle metadata file with `--input`; it reads only that JSON file and does not inspect path hints inside it.

- Standalone evidence bundle CLI input handling has regression coverage for missing JSON files and malformed JSON, keeping failures local and explicit.

- Total Export preservation-plan explanations can read an explicit local evidence bundle JSON file via `--evidence-bundle-input`; this reads only that JSON file and does not inspect evidence path hints.

- Total Export evidence bundle JSON input handling has regression coverage for missing files, malformed JSON, non-object JSON roots, and override rejection.

- Total Export evidence bundle JSON input is now covered in both text and JSON preservation-plan explanations.

- Preservation evidence bundle JSON helpers have focused regression coverage for item object validation, string field types, catalog values, duplicate artifact IDs, and invalid capture-method IDs.

- Preservation backend plan CLI input JSON now has regression coverage for nested evidence bundle item validation errors, invalid capture-method IDs, and duplicate artifact IDs.

- Total Export evidence bundle input now has CLI-level regression coverage for malformed nested item metadata, invalid capture-method IDs, and duplicate artifact IDs.

- Standalone evidence bundle CLI JSON input now has regression coverage for malformed nested item metadata, invalid capture-method IDs, and duplicate artifact IDs.

- Added an aggregate preservation evidence bundle regression runner covering the model, JSON helper validation, standalone CLI, backend plan CLI integration, and Total Export prepare CLI integration.

- Evidence bundle JSON helper validation now includes explicit string-field type checks for source metadata and item-level capture method, path hint, notes, and limitations fields.

- Evidence bundle JSON helper validation now covers `None` normalization for optional source and item metadata fields while keeping required artifact fields strict.

- The aggregate preservation evidence bundle regression runner now supports `--list` and repeatable `--only LABEL` for targeted local checks.

- Added a focused regression runner behavior test covering `--list`, targeted `--only`, and unknown label errors for the evidence bundle aggregate runner.

- Added evidence bundle local-only scope invariant coverage across the model, standalone evidence bundle CLI JSON output, and Total Export preservation-plan JSON output.

- The evidence bundle regression runner behavior test now explicitly covers targeted `--only` execution for the local-only scope invariant group.

- The evidence bundle regression runner behavior test now covers repeatable `--only` selections for targeted multi-group local regression runs.

- Evidence bundle local-only scope invariant coverage now also checks preservation backend plan CLI JSON output via `--input ... --format json`.

- The regression runner behavior test no longer imports the aggregate runner directly, allowing the aggregate evidence bundle runner to include its behavior test without a circular import.

- Evidence bundle local-only scope invariant coverage now checks text output as well as JSON output for standalone evidence bundle CLI, preservation backend plan CLI, and Total Export preservation-plan explanations.

- Evidence bundle local-only scope invariant coverage now checks Markdown output for standalone evidence bundle CLI and preservation backend plan CLI in addition to text and JSON outputs.

- Evidence bundle local-only scope invariant coverage now also asserts that path hints are not materialized into temp evidence files or directories during JSON/text/Markdown CLI checks.

- Evidence bundle local-only scope invariant coverage now asserts successful subprocess checks leave stderr empty for JSON/text/Markdown output surfaces.

- The evidence bundle regression runner behavior test now verifies duplicate `--only` labels are de-duplicated and run once.

- The evidence bundle regression runner behavior test now verifies targeted `--only` selections are emitted in canonical regression order even when requested in reverse order.

- The evidence bundle regression runner behavior test now covers mixed known/unknown `--only` selections and verifies the error still reports the unknown label plus expected choices.

- Evidence bundle local-only scope invariant coverage now also asserts archive/download prohibition wording alongside scan/hash/upload/capture/network wording.

- Evidence bundle local-only scope invariant coverage now asserts CLI JSON/text/Markdown outputs do not leak the temp input directory path, keeping path hints descriptive rather than resolved.

- Evidence bundle local-only scope invariant coverage now rejects structured file-state keys such as hashes, sizes, existence, opened, created, uploaded, validated, or captured state in evidence bundle outputs.

- Evidence bundle local-only scope invariant coverage now asserts structured path hints stay relative/descriptive and are not absolute paths, URLs, or drive-qualified paths.

- Evidence bundle local-only scope invariant coverage now includes negative path-hint assertions for URL, drive-qualified, root-relative, and absolute examples.

- Evidence bundle local-only scope invariant coverage now includes negative assertions proving representative forbidden file-state keys are rejected.

- Evidence bundle local-only scope invariant coverage now runs negative rejection checks for every key in the forbidden file-state key set, not just a representative subset.

- Evidence bundle local-only scope invariant coverage now also asserts CLI outputs do not leak the temporary JSON input filenames.

- The evidence bundle regression runner behavior test now verifies unknown-label errors list every expected regression label.

- Evidence bundle local-only scope invariant coverage now rejects rendered file-state field markers such as checksum, file_size, mtime, sha256, and size_bytes in text/Markdown output surfaces.

- Evidence bundle local-only scope invariant coverage now asserts evidence item execution stays `metadata only` when present in structured outputs and in rendered text/Markdown surfaces.

- Evidence bundle local-only scope invariant coverage now rejects parent-traversal path hints such as `..\\captures\\comments.png` and `../captures/comments.png`.

- Evidence bundle local-only scope invariant coverage now also rejects embedded parent-traversal path hints such as `captures\\..\\comments.png` and `captures/../comments.png`.

- The evidence bundle regression runner behavior test now also verifies mixed known/unknown `--only` errors list every expected regression label without running partial selections.

- The evidence bundle regression runner behavior test now verifies `--list` stays listing-only and does not emit pass banners or per-test passed output.

- Evidence bundle local-only scope invariant coverage now includes negative checks proving temp directory paths and temporary JSON input filenames are rejected if rendered into CLI output.

- The evidence bundle regression runner behavior test now verifies targeted `--only` runs emit exactly the selected passed labels and no extra regression pass lines.
