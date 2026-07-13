# Project Current-State Handoff

Date: 2026-07-14

Checkpoint: `3abb49d Add secure YouTube credential migration`

Branch: `v2.6.0-asr-engines`

## Purpose

This document is the cross-project handoff for the current ASR comparison, Total Export, upstream v2.1.1 parity, source-preservation, local evidence-manifest, and source-evidence model-skeleton work.

It records the state needed for a future session to resume safely. It does not implement behavior and does not replace the detailed subsystem documents listed below.

## Repository And Workflow Snapshot

- The working tree was clean when this handoff milestone started. Reconfirm with `git status --short` before applying any new patch.
- Current branch: `v2.6.0-asr-engines`.
- Current checkpoint: `3abb49d Add secure YouTube credential migration`.
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
- Credential work beyond the approved row 2C2 masked cloud-ASR Save/Clear controls, safe presence/provenance refresh, and committed secure YouTube credential migration/legacy cleanup. Provider credential consumption, OAuth, browser-profile integration, provider/API calls, connection testing, network behavior, and future reveal/copy/export behavior remain separately approval-gated.
- Database-root scanning, automatic classification, sensitive-trait inference, reclassification execution, or file movement.
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

## Source Evidence Model Skeleton State

Three planned source-evidence areas now have standalone, local-only schema implementations with focused tests:

- `evidence_item_queue.py` and `evidence_item_queue_test.py` (`7af8eea`): immutable queue-item, link, ASR-pairing, role, lifecycle-status, and Total Export include/exclude metadata. Source URLs, local media, reference text, transcript/subtitle candidates, ASR results, screenshots/snapshots, archive URLs, packages, and taxonomy suggestions remain distinct roles. The model performs no file checks, deletion, persistence, GUI work, ASR execution, capture, archive access, or Total Export wiring.
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
- `evidence_database_taxonomy.py` and `evidence_database_taxonomy_test.py` (`e63def4`): read-only database-root/taxonomy metadata, arbitrary user-defined dimensions, valid unknown/not-identified states, dry-run reclassification and alias-normalization suggestions, sensitive-classification safeguards, review states, preserved history, and queue/package/source references. Paths are descriptive metadata only; the model performs no scanning, automatic classification, persistence, reclassification execution, or file movement.

The queue and taxonomy remain local-only schema/test foundations rather than implemented UI/runtime workflows. Access & Keys has the bounded catalog/view/window, row 2A credential architecture/audit, row 2B read-only non-secret status/provenance overlay, row 2C1 secure-store infrastructure, row 2C2 masked cloud-ASR Save/Clear controls, and committed secure YouTube credential migration/legacy cleanup described above. Cloud-ASR row 2C2 remains unchanged and no provider consumes stored credentials yet. Connection testing, provider credential consumption, provider access, OAuth, browser-profile access, future reveal/copy/export behavior, and new non-ASR credential persistence workflows remain unimplemented and separately approval-gated. `SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md` should continue to distinguish implemented secure storage/UI behavior from later credential-consumption and external-access gaps.

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
| `EVIDENCE_ITEM_QUEUE_UI_SPEC.md` | Future evidence queue UI/workflow contract; current implementation is schema-only. |
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
| Access & Keys metadata schema | `access_keys_metadata.py` | `access_keys_metadata_test.py` |
| Access & Keys catalog/view/window | `access_keys_catalog.py`, `access_keys_view_model.py`, `access_keys_dialog.py`, narrow `main.py` wiring | `access_keys_catalog_test.py`, `access_keys_view_model_test.py`, `access_keys_dialog_test.py`, `main_export_state_test.py`; includes short-family scroll-reset regression |
| Credential architecture/security audit | `credential_architecture.py`, `CREDENTIAL_SECURITY_AUDIT.md` | `credential_architecture_test.py`; stable non-secret descriptors/policies/redaction/status helpers |
| Read-only credential runtime status | `credential_runtime_status.py`, Access & Keys metadata/dialog, narrow `main.py` wiring | `credential_runtime_status_test.py`, Access & Keys regressions, `main_export_state_test.py`; safe presence/provenance only, with no values, writes, migration, tests, provider calls, or network access |
| Secure credential store and masked cloud-ASR controls | `credential_store.py`, `credential_runtime_status.py`, `access_keys_dialog.py`, narrow `main.py` wiring | `credential_store_test.py`, `credential_runtime_status_test.py`, `access_keys_dialog_test.py`, `main_export_state_test.py`; deterministic cloud-ASR keyring locators, explicit YouTube rejection, test-only/session-only memory backend, fail-closed injected/system-keyring backend, fixed non-secret result statuses, masked cloud-ASR Save/Clear controls, safe presence/provenance refresh, and no provider/API/network execution |
| Secure YouTube credential migration | `core/settings.py`, `youtube_credential_migration.py`, `credential_runtime_status.py`, narrow `main.py` wiring | `youtube_credential_migration_test.py`, `settings_keyring_fallback_test.py`, `credential_runtime_status_test.py`, `main_export_state_test.py`, `access_keys_dialog_test.py`; secure-only Save/Update, explicit legacy migration/cleanup, no plaintext fallback, no UI preload, no reveal/unmask path, truthful partial-failure states, and existing extraction compatibility through internal action-time resolution |
| Evidence database taxonomy schema | `evidence_database_taxonomy.py` | `evidence_database_taxonomy_test.py` |
| URL normalization | `youtube_url_utils.py` | `youtube_url_utils_test.py` |
| Upstream parity | Extractor/spam/settings/export-state code | Five local/mocked parity tests listed above |

## Latest Known Commit Chain

```
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
python -m py_compile evidence_item_queue.py evidence_item_queue_test.py access_keys_metadata.py access_keys_metadata_test.py access_keys_catalog.py access_keys_catalog_test.py access_keys_view_model.py access_keys_view_model_test.py access_keys_dialog.py access_keys_dialog_test.py credential_architecture.py credential_architecture_test.py credential_runtime_status.py credential_runtime_status_test.py credential_store.py credential_store_test.py main.py evidence_database_taxonomy.py evidence_database_taxonomy_test.py evidence_schema.py evidence_schema_test.py & python evidence_item_queue_test.py & python access_keys_metadata_test.py & python access_keys_catalog_test.py & python access_keys_view_model_test.py & python access_keys_dialog_test.py & python credential_architecture_test.py & python credential_runtime_status_test.py & python credential_store_test.py & python main_export_state_test.py & python evidence_database_taxonomy_test.py & python evidence_schema_test.py
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

## Deferred General GUI Responsiveness

- Access & Keys selection, filtering, hover, popup behavior, and short-family visibility passed focused tests and manual acceptance through `ee945fe`.
- The user still observed broader pauses while moving or closing application windows. Preserve this as a later whole-application GUI responsiveness/performance audit; do not treat it as unfinished row-1 catalog interaction or use it to bypass row 2.

## Safe Next Milestones

1. Row 2A non-secret credential architecture/audit is complete at `ef92017`, row 2B read-only local credential status integration is complete at `7c1db2a`, row 2C1 secure credential-store infrastructure is complete at `29af218`, row 2C2 masked cloud-ASR Save/Clear controls are complete at `97de48d`, and secure YouTube credential migration/legacy cleanup is complete at `3abb49d`.
2. The exact next ordered credential boundary is provider credential consumption and/or explicit connection testing for stored credentials. The current roadmap does not define a precise row label for that boundary, so treat it as separately approval-gated rather than inventing a row number.
3. Do not expand that boundary into provider calls, OAuth, cloud ASR execution, browser behavior, uploads, network access, or future reveal/copy/export behavior without explicit approval.
4. Do not begin later-row compatibility/reporting work by treating row 2C2 as approval for unresolved credential migration or provider/network layers.
5. Create the next full external session handoff before beginning a substantially different feature area.
6. Keep database scanning, automatic/sensitive classification, credential testing/provider access, archive/downloader/capture, and other networked behavior deferred until explicitly approved, opt-in where applicable, and covered by local/mocked tests.

## Do-Not-Do List

- Do not treat leaderboard leads as accepted providers.
- Do not treat ElevenLabs as accepted; it remains below the 95% gate.
- Do not classify AWS Transcribe as quality-rejected; no score exists.
- Do not silently replace transcript text or skip Term QA/user review.
- Do not add network/provider/archive/downloader behavior under a local-report milestone.
- Do not copy/build packages or extract ZIPs through preservation/evidence metadata helpers.
- Do not infer remote deletion or unavailability from missing local records.
- Do not expose or record secrets in docs, logs, manifests, reports, screenshots, or test fixtures.
- Do not describe the queue or database-taxonomy UI/persistence/runtime as implemented. The bounded Access & Keys catalog/view/window, row 2A architecture/audit, row 2B read-only safe status/provenance overlay, row 2C1 secure-store infrastructure, row 2C2 masked cloud-ASR Save/Clear UI, and secure YouTube credential migration/legacy cleanup are implemented, but provider credential consumption, connection testing, provider access, OAuth, browser-profile access, future reveal/copy/export behavior, and new persistence workflows remain unimplemented.
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
