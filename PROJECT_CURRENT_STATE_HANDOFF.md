# Project Current-State Handoff

Date: 2026-07-10

Checkpoint: `b59a052 Fix ASR manual seed metadata test`

Branch: `v2.6.0-asr-engines`

## Purpose

This document is the cross-project handoff for the current ASR comparison, Total Export, upstream v2.1.1 parity, source-preservation, and local evidence-manifest work.

It records the state needed for a future session to resume safely. It does not implement behavior and does not replace the detailed subsystem documents listed below.

## Repository And Workflow Snapshot

- The working tree was clean when this handoff milestone started. Reconfirm with `git status --short` before applying any new patch.
- Current branch: `v2.6.0-asr-engines`.
- Current checkpoint: `b59a052 Fix ASR manual seed metadata test`.
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
- New runtime dependencies or hidden configuration for these milestones.

Existing YouTube comment/live-chat behavior, app exports, ASR runtime behavior, and Total Export package/review behavior must remain stable unless a separately approved milestone changes them with local/mocked coverage.

## ASR Comparison And Provider State

### Acceptance Policy

- The strict project reference acceptance threshold remains 95%.
- Machine ASR output remains draft text unless strict quality and term checks pass.
- Term QA/glossary review remains mandatory for names and lore terms.
- External leaderboard results are research leads only and cannot override project-specific reference scoring.
- `accepted` remains reserved for a future provider/model that passes the project gate.

### Current Project Results

- Best tested local/no-cloud result: whisper.cpp Vulkan large-v3-turbo with phrase prompt, about 74.19% strict 30-second reference accuracy.
- No tested local ASR path has met the 95% threshold.
- Leading tested cloud candidate: ElevenLabs Scribe v2 with keyterms, 84.95%.
  - It preserved the Nicolas Cage reference phrase and found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`.
  - It missed `Kingman`, `ZoneX`, `Freckelston`, and `Nyxara`.
  - It is a leading optional candidate, not accepted and not final truth.
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

## Total Export Local Package And Review State

The repository now has a broad local Total Export foundation:

- Source URL validation plus YouTube and metadata-only News Website source-adapter skeletons.
- `SOURCE_CONTEXT_GLOSSARY_CURRENT_STATE.md` records the current local source/context/glossary helper stack, verification commands, boundaries, and safe next milestones.
- `source_capture_plan_cli.py`: explicit-output-only local Source Capture Plan inspection CLI for manually supplied source URL/context/glossary JSON.
- `context_glossary_cli.py`: explicit-output-only local context/glossary inspection CLI for manually supplied source label, source URL, title, and user terms.
- `source_adapters.py`: local source adapter registry helpers use `source_name` for names/listing/lookup; adapters do not expose a `.name` attribute.
- `source_adapter_capability_report.py` and CLI: local registered-adapter capability/credential/privacy/setup metadata reports without fetch/capture/network/archive/provider/credential-test/scraping/GUI behavior.
- `NewsWebsiteSourceAdapter`: metadata-only known-host news website URL-recognition skeleton for Telegraph/MSN-style sources; no fetching, scraping, capture, archive checks, downloads, access bypass, or GUI wiring.
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
| `SOURCE_CONTEXT_GLOSSARY_CURRENT_STATE.md` | Current local source URL, adapter, capture plan, provenance, and context/glossary helper/test index. |
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
| URL normalization | `youtube_url_utils.py` | `youtube_url_utils_test.py` |
| Upstream parity | Extractor/spam/settings/export-state code | Five local/mocked parity tests listed above |

## Latest Known Commit Chain

```
b59a052 Fix ASR manual seed metadata test
975238e Polish ASR manual seed metadata
7821f7f Add combined ASR report CLI
7ff20d0 Add ASR provider status notes
39fe85b Add ASR reporting current-state handoff
a1d9d36 Add ASR decision summary CLI
2af464a Add ASR term coverage summary CLI
f30c7d5 Add ASR term coverage summary report
6cede20 Add ASR decision summary report
a5cfe85 Add cross-project current-state handoff
5ed8a69 Add local evidence manifest CLI
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

Upstream parity regressions:

```cmd
python -m py_compile extractor_error_handling_test.py extractor_sort_limit_test.py spam_filter_regression_test.py main_export_state_test.py settings_keyring_fallback_test.py extractor.py spam_filter.py core\settings.py & python extractor_error_handling_test.py & python extractor_sort_limit_test.py & python spam_filter_regression_test.py & python main_export_state_test.py & python settings_keyring_fallback_test.py
```

Final repository checks:

```cmd
git diff --check & git status --short
```

Do not add provider/API/network calls to these verification chains.

## Safe Next Milestones

1. Perform docs-only bundle/preservation index polish if names or boundaries drift.
2. Add a local-only ASR term coverage/gap summary over manual records, or polish comparison/decision report formatting without provider calls.
3. Review whether this phase has reached a useful stopping point and create an external session handoff for the user.
4. Keep any future networked provider/archive/downloader/capture behavior deferred until explicitly approved, opt-in, and covered by local/mocked tests. Any additional adapters should start as metadata-only, site-specific or site-family skeletons.

## Do-Not-Do List

- Do not treat leaderboard leads as accepted providers.
- Do not treat ElevenLabs as accepted; it remains below the 95% gate.
- Do not classify AWS Transcribe as quality-rejected; no score exists.
- Do not silently replace transcript text or skip Term QA/user review.
- Do not add network/provider/archive/downloader behavior under a local-report milestone.
- Do not copy/build packages or extract ZIPs through preservation/evidence metadata helpers.
- Do not infer remote deletion or unavailability from missing local records.
- Do not expose or record secrets in docs, logs, manifests, reports, screenshots, or test fixtures.
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
