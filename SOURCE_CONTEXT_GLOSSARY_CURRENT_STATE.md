# Source Context / Glossary Current State

Date: 2026-07-14

Branch: `v2.6.0-asr-engines`

Latest known checkpoint:

```text
f709f8e Add explicit ASR connection test seam
```

## Purpose

This document is the local current-state handoff for the source URL, source adapter, source capture plan, provenance, context/glossary, evidence queue, Access & Keys metadata/catalog/window, row 2A credential architecture/audit, row 2B read-only credential status integration, row 2C1 secure credential-store infrastructure, row 2C2 masked cloud-ASR Save/Clear controls, secure YouTube credential migration/legacy cleanup, the local-only cloud-ASR credential-consumption prerequisite, the explicit injected-executor ASR provider-action seam, the explicit injected-tester ASR connection-test seam, and evidence database taxonomy skeletons.

It records what exists now, what is intentionally not implemented, how to verify the local helpers, and what safe future milestones look like.

## Hard Boundaries

The current source/context/glossary helpers are local planning and metadata helpers only.

They must not:

- fetch source URLs,
- download media,
- fetch comments, live chat, captions, transcripts, metadata, oEmbed, or webpage content,
- call ASR providers,
- call topic resolver, Common Crawl, Serper, Exa, archive services, or any network/API service,
- scrape pages,
- capture screenshots,
- store credentials, cookies, tokens, or sessions,
- inspect or extract ZIPs,
- persist or background-process evidence queue items,
- test/store credentials or integrate OAuth/browser profiles,
- scan database roots, classify evidence automatically, infer sensitive traits, or move files,
- add secret-bearing GUI/runtime wiring beyond the bounded Access & Keys presentation, read-only status overlay, row 2C1 store abstraction, row 2C2 masked cloud-ASR Save/Clear controls, committed secure YouTube credential migration/legacy cleanup, local-only trusted-callback cloud-ASR credential-consumption prerequisite, explicit injected-executor ASR provider-action seam, and explicit injected-tester ASR connection-test seam,
- change runtime extractor/export/ASR behavior.

Current helpers validate, normalize, classify, and assemble local metadata only.

## Current Local Helpers

| Area | Files | Purpose |
| --- | --- | --- |
| YouTube URL parsing | `youtube_url_utils.py`, `youtube_url_utils_test.py` | Strict local YouTube video-ID extraction/normalization. |
| Source adapter metadata | `source_adapters.py`, `source_adapters_test.py`, `source_adapters_registry_test.py` | Local adapter capability metadata, YouTube URL support, metadata-only News Website known-host URL support, `source_name` registry helpers, and name lookup. |
| Source adapter capability report | `source_adapter_capability_report.py`, `source_adapter_capability_report_test.py`, `source_adapter_capability_report_cli.py`, `source_adapter_capability_report_cli_test.py` | Local registered-adapter capability/credential/privacy/setup report rendering. |
| Source adapter gap analysis | `source_adapter_gap_analysis.py`, `source_adapter_gap_analysis_test.py`, `source_adapter_gap_analysis_cli.py`, `source_adapter_gap_analysis_cli_test.py` | Local current-vs-future adapter and preservation backend gap analysis. |
| Capture method metadata | `capture_method_metadata.py`, `capture_method_metadata_test.py` | Local metadata catalog for visible/full-page/container/stitched screenshots, selected/raw HTML, and manual evidence bundles; no capture execution. |
| Context/glossary skeleton | `context_glossary.py`, `context_glossary_test.py` | Local glossary normalization, deduplication, user-term handling, and context hint resolution. |
| Context glossary CLI | `context_glossary_cli.py`, `context_glossary_cli_test.py` | Explicit-output-only CLI for manually supplied context/glossary JSON normalization and reporting. |
| Source capture planning | `source_capture_plan.py`, `source_capture_plan_test.py` | Local source URL + adapter + capture option + context hint plan assembly. |
| Source capture plan CLI | `source_capture_plan_cli.py`, `source_capture_plan_cli_test.py` | Explicit-output-only inspection CLI for manually supplied source URL/context/glossary JSON. |
| Source plan provenance | `source_plan_provenance.py`, `source_plan_provenance_test.py` | Local provenance records derived from Source Capture Plans without fetch/capture behavior. |
| Evidence item queue schema | `evidence_item_queue.py`, `evidence_item_queue_test.py` | Immutable local queue-item/link/ASR-pairing metadata with explicit roles, lifecycle states, and Total Export include/exclude intent; no persistence, file operations, GUI, capture, ASR, archive, or export wiring. |
| Access & Keys metadata schema | `access_keys_metadata.py`, `access_keys_metadata_test.py` | Non-secret access/credential/test-status and provider/source/archive/browser-assisted-capture metadata with deterministic reports; no secret fields, credential tests, OAuth, provider calls, archive calls, or GUI wiring. |
| Access & Keys catalog | `access_keys_catalog.py`, `access_keys_catalog_test.py` | Complete planned non-secret services, ordered sections/subgroups, aliases, planned/implemented status, separate archive/browser placeholders, and deterministic validation; no credentials or external execution. |
| Access & Keys manager view model | `access_keys_view_model.py`, `access_keys_view_model_test.py` | GUI-independent platform sections plus search/filter/selection and safe status/capability presentation over the non-secret catalog; no widgets, credential values, connection execution, provider calls, persistence, or runtime wiring. |
| Access & Keys window | `access_keys_dialog.py`, `access_keys_dialog_test.py`, narrow `main.py` wiring | Separate `KEYS` button and reusable catalog window with ordered sections/subgroups, alias-aware search, full-width family selection, stable in-place selection/details, short-family scroll-reset behavior, empty/duplicate diagnostics, the row 2B safe status overlay, and row 2C2 masked cloud-ASR Save/Clear controls for supported cloud-ASR entries only; no provider/API/network execution. |
| Credential architecture/security audit | `credential_architecture.py`, `credential_architecture_test.py`, `CREDENTIAL_SECURITY_AUDIT.md` | Approved row 2A stable non-secret credential IDs, backend/migration/redaction/sink policy, safe presence labels, eight existing-code findings, deterministic reporting, and later approval boundaries; no credential lifecycle changes, provider tests, or network behavior. |
| Read-only credential runtime status | `credential_runtime_status.py`, `credential_runtime_status_test.py`, Access & Keys metadata/dialog, narrow `main.py` wiring | Approved row 2B configured/missing/backend-unavailable/error status plus safe provenance. YouTube status uses safe storage information without value exposure; cloud ASR uses named environment-variable presence only. No value rendering/retention, writes, connection tests, provider calls, OAuth, or network behavior. The later secure YouTube migration keeps stored credentials out of the UI field. |
| Secure credential store | `credential_store.py`, `credential_store_test.py` | Approved row 2C1 secure-store infrastructure for catalogued cloud-ASR credential IDs only. It provides deterministic non-secret keyring locators, explicit `youtube_data_api_key` rejection, a session-only in-memory test backend, a fail-closed injected/system-keyring backend, and fixed non-secret result statuses/diagnostics. Row 2C2 invokes it for explicit cloud-ASR Save/Clear and safe presence probing; the later YouTube migration uses the existing app settings/keyring path for secure-only YouTube storage. |
| Secure YouTube credential migration | `core/settings.py`, `youtube_credential_migration.py`, `youtube_credential_migration_test.py`, `settings_keyring_fallback_test.py`, `credential_runtime_status.py`, `credential_runtime_status_test.py`, `main.py`, `main_export_state_test.py`, `access_keys_dialog_test.py` | Approved secure YouTube credential migration/legacy cleanup. New/updated YouTube saves are secure-only with no plaintext fallback; legacy migration is explicit and user-controlled; Clear reports partial failures truthfully; stored credentials are never preloaded into the UI field; reveal/unmask controls are removed; existing extraction resolves configured credentials internally at action time. Cloud-ASR row 2C2 remains unchanged. |
| Cloud-ASR credential consumption prerequisite | `credential_consumption.py`, `credential_consumption_test.py`, `credential_runtime_status.py`, `credential_runtime_status_test.py`, `credential_store.py`, `credential_store_test.py` | Local-only explicit action-time credential resolution for trusted internal callbacks. Secure non-empty keyring values take precedence over environment values; genuinely absent secure values may fall back to non-empty environment values where supported; backend unavailable/error states preserve the established environment fallback; empty or whitespace-only secure values are invalid secure states that do not invoke callbacks and do not fall back. Public results contain only fixed non-secret status/provenance/diagnostic fields. No real provider consumes credentials, and no provider client, connection test, upload, API request, or network behavior exists. |
| Explicit ASR provider-action seam | `asr_provider_action.py`, `asr_provider_action_test.py` | Outcome B local-only coordinator seam because no safe tracked production cloud-provider runtime path existed. `ASRProviderActionCoordinator.dispatch_provider_action(...)` validates provider/action metadata, rejects unsupported actions, unknown/non-dispatchable providers, YouTube IDs, pattern-adjacent IDs, and missing executors before credential lookup, delegates credential resolution to `CloudASRCredentialConsumer`, and invokes only injected trusted executors. `elevenlabs_scribe` and `whisper_cpp_vulkan_large_v3_turbo` are dispatchable through an injected trusted executor only; this is not a production provider implementation and adds no connection test, SDK/client, API call, upload, network, GUI, or background behavior. |
| Explicit ASR connection-test seam | `asr_connection_test.py`, `asr_connection_test_test.py` | Outcome B local-only coordinator seam because no safe tracked production connection-test runtime path existed. `ASRConnectionTestCoordinator.test_provider_connection(...)` validates exact provider ID, rejects YouTube/non-ASR misuse, classifies local/cloud/not-test-dispatchable providers, rejects local/no-test-required providers, rejects non-test-dispatchable providers, and rejects missing testers before credential lookup; only then does it resolve credentials through `CloudASRCredentialConsumer` and invoke an injected trusted tester once. `tester_completed` means only that the injected tester returned normally; it does not prove credential validity, authentication, provider reachability, network connectivity, account/quota access, model availability, or production connection-test success. There is no production tester, GUI Test Connection button/caller, SDK/client, API request, upload, network behavior, background test, or provider-specific connection implementation. |
| Evidence database taxonomy schema | `evidence_database_taxonomy.py`, `evidence_database_taxonomy_test.py` | Read-only root/taxonomy/dimension/dry-run/history metadata with unknown-state and sensitive-classification safeguards; no scanning, automatic classification, persistence, reclassification execution, or file movement. |

## Current Verified State

The focused inspection before this file was added found these relevant files present:

```text
source_adapters.py
source_adapters_test.py
source_capture_plan.py
source_capture_plan_test.py
source_plan_provenance.py
source_plan_provenance_test.py
context_glossary.py
context_glossary_test.py
youtube_url_utils.py
youtube_url_utils_test.py
```

Local verification passed for:

- Source adapter self-test.
- Source capture plan self-test.
- Source plan provenance self-test.
- Context glossary self-test.
- YouTube URL utility self-test.

The later source-evidence skeleton milestones also passed their focused and adjacent local regression chains at these checkpoints:

- `7af8eea`: `evidence_item_queue_test.py`.
- `66871b6`: `access_keys_metadata_test.py`.
- `e63def4`: `evidence_database_taxonomy_test.py`.
- `8d11a4b`: `access_keys_view_model_test.py` plus adjacent source-adapter/ASR-provider metadata regressions.
- `1b57e74`: guarded-headless `access_keys_dialog_test.py` plus metadata, view-model, evidence-schema, queue, taxonomy, and source-adapter regressions.
- `0ff528d`: `access_keys_catalog_test.py`, `access_keys_view_model_test.py`, `access_keys_dialog_test.py`, metadata/schema/queue/taxonomy/source-adapter regressions, and `main_export_state_test.py`; manual acceptance confirmed restored hover, working family selection, and removal of the earlier selection/filter flash.
- `ee945fe`: focused `access_keys_dialog_test.py` short-family visibility regression plus the adjacent Access & Keys, ASR-provider, source-adapter, and `main_export_state_test.py` chain; manual acceptance confirmed ASR Providers and other short families appear immediately after switching from a long scrolled family.
- `ef92017`: `credential_architecture_test.py` plus Access & Keys metadata/catalog/view/dialog, ASR-provider, source-adapter, and `main_export_state_test.py` regressions; confirmed row 2A contains only non-secret descriptors/policies/redaction/status helpers and audit documentation with no existing runtime-file changes or credential/provider/network behavior.
- `7c1db2a`: `credential_runtime_status_test.py` plus credential architecture, Access & Keys metadata/catalog/view/dialog, ASR-provider, source-adapter, and `main_export_state_test.py` regressions; manual inspection confirmed safe YouTube/cloud-ASR status and provenance text with no credential values.
- `29af218`: `credential_store_test.py` plus credential architecture/runtime status, Access & Keys metadata/catalog/view/dialog, source-adapter, ASR-provider, and `main_export_state_test.py` regressions; confirmed row 2C1 adds only `credential_store.py` and `credential_store_test.py`, rejects the existing YouTube credential ID, uses injected/fake keyring tests, and exposes no credential values, fragments, lengths, hashes, exception text, tracebacks, or secret-bearing diagnostics.
- `97de48d`: `credential_store_test.py`, `credential_runtime_status_test.py`, `access_keys_dialog_test.py`, Access & Keys metadata/catalog/view tests, ASR-provider/source-adapter regressions, and `main_export_state_test.py`; confirmed row 2C2 adds masked cloud-ASR Save/Clear controls only for supported cloud-ASR entries, safe keyring/environment status refresh, fake/injected keyring coverage, no provider/API/network execution, and no changes to the existing YouTube credential workflow. The first manual row 2C2 test exposed an unmasked cloud credential field; the defect was fixed before commit, wrapper/internal-entry masking tests were added, and the corrected manual retest passed.
- `3abb49d`: `youtube_credential_migration_test.py`, `settings_keyring_fallback_test.py`, `credential_runtime_status_test.py`, `main_export_state_test.py`, and `access_keys_dialog_test.py` regressions; confirmed secure-only YouTube Save/Update, explicit legacy plaintext migration and cleanup, no plaintext fallback for new writes, truthful partial-failure states, malformed-settings protection, no reveal/copy/unmask path, no stored-key UI preload, and internal action-time credential resolution for existing extraction. Manual production verification used `python main.py` with the venv active and confirmed masked Save, configured status, empty field after restart, Access & Keys presence/provenance, and no credential value exposure.
- `a1cf07d`: `credential_consumption_test.py`, `credential_runtime_status_test.py`, and `credential_store_test.py` regressions; confirmed local-only cloud-ASR credential consumption through explicit trusted callbacks, secure-store/environment precedence aligned with safe status reporting, invalid empty/whitespace secure values treated as safe errors with no environment fallback, explicit rejection of YouTube/local/unknown IDs, non-secret public results, no import/construction lookup, no credential cache, and no provider client, connection test, upload, API request, or network behavior.
- `058af01`: `asr_provider_action_test.py` plus credential consumption/store/runtime/architecture, Access & Keys metadata/catalog/view/dialog, ASR provider metadata, YouTube credential migration/settings fallback, source adapter registry/report/gap, `youtube_url_utils_test.py`, `main_export_state_test.py`, compile, whitespace/final-newline, and `git diff --check` verification; confirmed Outcome B provider-action seam, exact provider mappings, validation-before-credential-lookup behavior, trusted injected-executor boundary, non-secret public result fields with no `credential_id`, no provider implementation, no connection test, no upload, no API/network behavior, no GUI wiring, and unchanged YouTube/cloud-ASR Save/Clear/status behavior. `asr_tools_test.py` is an interactive/manual harness that prompts for an audio/video path; it was compile-checked but intentionally not executed as an automated test.
- `f709f8e`: `asr_connection_test_test.py` plus provider-action, credential consumption/store/runtime/architecture, Access & Keys metadata/catalog/view/dialog, ASR-provider metadata, YouTube credential migration/settings fallback, source adapter registry/report/gap, `youtube_url_utils_test.py`, `main_export_state_test.py`, compile, whitespace/final-newline, and `git diff --check` verification; confirmed Outcome B connection-test seam, exact validation-before-credential-lookup ordering, `elevenlabs_scribe` test-dispatchable only through an injected trusted tester, local/non-testable/YouTube/unknown/pattern-adjacent providers rejected before lookup, ignored tester return values, fixed non-secret public result fields, narrow `tester_completed` completion semantics, no production tester, no GUI Test Connection button/caller, no SDK/client, no API request, no upload, no network behavior, no background test, and unchanged YouTube/cloud-ASR Save/Clear/status behavior. `asr_tools_test.py` remains compile-checked only and is not executed as an automated test because it is an interactive/manual harness.

The queue/taxonomy schemas and Access & Keys metadata/view-model remain data/reporting foundations. Commits `1b57e74`, `0ff528d`, and `ee945fe` add the bounded `KEYS` button/window, complete planned catalog, corrected local interactions, and short-family visibility behavior described above. Commit `ef92017` adds row 2A non-secret credential architecture/audit, `7c1db2a` adds the row 2B read-only safe status/provenance overlay, `29af218` adds row 2C1 secure-store infrastructure, `97de48d` adds row 2C2 masked cloud-ASR Save/Clear controls with safe presence/provenance refresh, `3abb49d` adds secure YouTube credential migration/legacy cleanup, `a1cf07d` adds the local-only trusted-callback cloud-ASR credential-consumption prerequisite, `058af01` adds the explicit injected-executor ASR provider-action seam, and `f709f8e` adds the explicit injected-tester ASR connection-test seam. No source fetching, production provider implementation, production/user-facing provider connection testing, database scanning, file movement, provider access, network behavior, or unrelated runtime behavior was added.

## Pipeline Position

The planned pipeline remains:

1. Source URL.
2. Source adapter capability check.
3. Local capture plan options.
4. Context hint and user glossary term normalization.
5. Candidate glossary/entity handling.
6. User review/edit before any ASR prompt/keyterm use.
7. Optional future provider-specific keyterms.
8. Term QA after transcription.

Only local planning, metadata, bounded Access & Keys presentation, row 2A credential architecture/audit, row 2B read-only safe status/provenance, row 2C1 secure-store infrastructure, row 2C2 masked cloud-ASR Save/Clear controls, secure YouTube credential migration/legacy cleanup, the local-only cloud-ASR credential-consumption prerequisite, the explicit injected-executor ASR provider-action seam, and the explicit injected-tester ASR connection-test seam exist here. The evidence queue can describe links among source URLs, local media, reference text, transcript/subtitle candidates, ASR results, archive/snapshot records, packages, and taxonomy suggestions, but it is not persisted or wired into this pipeline. The credential runtime layer reports only boolean presence, safe provenance, and fixed diagnostic categories; it does not render or retain values. Cloud-ASR secure-store usage includes explicit Save/Clear, safe presence probing, explicit trusted-callback resolution, explicit dispatch to injected trusted executors, and explicit dispatch to injected trusted connection testers only; no production provider implementation consumes stored credentials or performs a production/user-facing connection test. YouTube storage is secure-only for new/updated saves, explicit for legacy migration, and never preloads stored credentials into the UI field. Fetching, capture, ASR provider execution, provider keyterms, reveal/copy UI, production/user-facing credential connection tests, database scanning, file movement, and new persistence workflows are not implemented by this layer.

## Context / Glossary Policy

- Metadata/comments/context are for glossary discovery and QA only.
- They are not a replacement for transcription.
- External/background context is optional.
- External/background context must be strict-filtered.
- External/background context must never block local transcript/ASR work.
- External/background context must never be trusted as ground truth.
- The user must be able to review/edit glossary terms before they affect ASR prompts, provider keyterms, QA checks, or final transcript decisions.
- If a provider has no glossary/keyterm support, glossary terms can still feed Term QA after transcription.

## Scrollable Container Capture Notes

Social platforms can display comments inside nested scrollable containers or modals. A browser page screenshot or Page Up/Page Down workflow may only capture the visible portion of the comments container, not the full comment thread.

Future preservation/capture metadata should distinguish:

- visible screenshot only,
- full-page screenshot,
- scrollable-container screenshot,
- stitched/multi-image capture,
- selected-DOM or print-cleaned HTML,
- raw saved HTML,
- manually supplied evidence bundle.

Manual tools such as Print Edit WE, FireShot, GoFullPage, browser DevTools, or saved-page HTML can be useful evidence sources, but their outputs should be recorded with capture limitations. Do not treat any one visual/DOM capture method as a universal social-comment extractor. Future automation should be site-specific or site-family-specific, opt-in, and tested locally/mocked before any fetch/capture/browser behavior is added.

`capture_method_metadata.py` now formalizes these seven methods as local metadata with output kinds, current manual-only status, future-automation candidacy, limitations, and recommended next steps. It does not fetch, browse, capture screenshots, scrape, download, or wire into the GUI.

Preservation backend plans now also record media preservation intent as `none`, `select`, or explicit `all`. This local metadata neither discovers nor downloads media; any future automation must remain opt-in, site-specific, and locally/mocked tested.

The same preservation plan reports can now include multiple selected IDs from `capture_method_metadata.py`, with display names and limitations. Selection remains metadata only: no screenshot, DOM capture, scrolling, scraping, browser execution, or download occurs, and nested scrollable containers remain a known evidence limitation.

`preservation_evidence_bundle.py` and its stdout-only CLI now describe empty/planned or manual/external artifact bundles, fixed preservation formats, capture-method links, path hints, and limitations. They do not open, scan, hash, validate, create, upload, or capture files; nested scrollable-container completeness remains an explicit limitation.

Future webpage media preservation should also record whether media capture is `all` or `select`: `all` means every discovered image/video/media asset is intended for preservation, while `select` means the user chooses individual assets. Media download must remain opt-in and must not default to downloading everything from a webpage.

## Preservation Backend Plan CLI Usage

`preservation_backend_plan_cli.py` renders a local preservation backend plan for manually supplied source URLs, backend choices, and desired output formats.

```cmd
python preservation_backend_plan_cli.py
python preservation_backend_plan_cli.py --format text
python preservation_backend_plan_cli.py --format json
python preservation_backend_plan_cli.py --input preservation_plan.json --output PRESERVATION_BACKEND_PLAN.md --overwrite
```

Example input JSON:

```json
{
  "source_url": "https://www.telegraph.co.uk/news/example/",
  "selected_backend_ids": ["manual_local_files", "archivebox_self_hosted"],
  "selected_format_ids": ["html", "pdf", "warc", "json"],
  "notes": "User wants a local backup plan."
}
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network/archive services, test credentials, scrape pages, run ArchiveBox, capture screenshots, or wire into the GUI.

## Source Adapter Gap Analysis CLI Usage

`source_adapter_gap_analysis_cli.py` renders a local adapter and preservation gap analysis comparing the current adapter inventory with future platform/backend categories.

```cmd
python source_adapter_gap_analysis_cli.py
python source_adapter_gap_analysis_cli.py --format text
python source_adapter_gap_analysis_cli.py --format json
python source_adapter_gap_analysis_cli.py --output SOURCE_ADAPTER_GAP_ANALYSIS.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network/archive services, test credentials, scrape pages, run ArchiveBox, capture screenshots, or wire into the GUI.

## Source Adapter Capability Report CLI Usage

`source_adapter_capability_report_cli.py` renders local source adapter metadata from the registered adapter list as Markdown, text, or JSON.

```cmd
python source_adapter_capability_report_cli.py
python source_adapter_capability_report_cli.py --format text
python source_adapter_capability_report_cli.py --format json
python source_adapter_capability_report_cli.py --adapter youtube --output SOURCE_ADAPTER_CAPABILITIES.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network/archive services, test credentials, scrape pages, capture screenshots, or wire into the GUI.

## Context Glossary CLI Usage

`context_glossary_cli.py` reads a manually supplied JSON object and renders normalized context hints, deduped glossary terms, and phrase-prompt terms as Markdown, text, or JSON.

Example input shape:

```json
{
  "source_label": "YouTube clip",
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "Example title",
  "user_terms": ["Nyxara", "Freckelston"]
}
```

```cmd
python context_glossary_cli.py --input context_glossary_input.json
python context_glossary_cli.py --input context_glossary_input.json --format text
python context_glossary_cli.py --input context_glossary_input.json --format json
python context_glossary_cli.py --input context_glossary_input.json --output CONTEXT_GLOSSARY_REPORT.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network services, or feed ASR prompts/keyterms.

## Source Capture Plan CLI Usage

`source_capture_plan_cli.py` reads a manually supplied JSON object and renders a local Source Capture Plan as Markdown, text, or JSON.

Example input shape:

```json
{
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
  "source_label": "YouTube clip",
  "title": "Example title",
  "selected_capture_options": ["comments", "archive_check"],
  "user_terms": ["Nyxara", "Freckelston"]
}
```

```cmd
python source_capture_plan_cli.py --input source_capture_plan_input.json
python source_capture_plan_cli.py --input source_capture_plan_input.json --format text
python source_capture_plan_cli.py --input source_capture_plan_input.json --format json
python source_capture_plan_cli.py --input source_capture_plan_input.json --output SOURCE_CAPTURE_PLAN_REPORT.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything or call providers/network services.

## Verification

Run from Windows CMD with the project virtual environment active:

```cmd
python -m py_compile source_adapters.py source_adapters_test.py source_adapters_registry_test.py source_adapter_capability_report.py source_adapter_capability_report_test.py source_adapter_capability_report_cli.py source_adapter_capability_report_cli_test.py source_adapter_gap_analysis.py source_adapter_gap_analysis_test.py source_adapter_gap_analysis_cli.py source_adapter_gap_analysis_cli_test.py source_capture_plan.py source_capture_plan_test.py source_capture_plan_cli.py source_capture_plan_cli_test.py source_plan_provenance.py source_plan_provenance_test.py context_glossary.py context_glossary_test.py context_glossary_cli.py context_glossary_cli_test.py youtube_url_utils.py youtube_url_utils_test.py evidence_item_queue.py evidence_item_queue_test.py access_keys_metadata.py access_keys_metadata_test.py access_keys_catalog.py access_keys_catalog_test.py access_keys_view_model.py access_keys_view_model_test.py access_keys_dialog.py access_keys_dialog_test.py credential_architecture.py credential_architecture_test.py credential_runtime_status.py credential_runtime_status_test.py credential_store.py credential_store_test.py main.py evidence_database_taxonomy.py evidence_database_taxonomy_test.py evidence_schema.py evidence_schema_test.py & python source_adapters_test.py & python source_adapters_registry_test.py & python source_adapter_capability_report_test.py & python source_adapter_capability_report_cli_test.py & python source_adapter_gap_analysis_test.py & python source_adapter_gap_analysis_cli_test.py & python source_capture_plan_test.py & python source_capture_plan_cli_test.py & python source_plan_provenance_test.py & python context_glossary_test.py & python context_glossary_cli_test.py & python youtube_url_utils_test.py & python evidence_item_queue_test.py & python access_keys_metadata_test.py & python access_keys_catalog_test.py & python access_keys_view_model_test.py & python access_keys_dialog_test.py & python credential_architecture_test.py & python credential_runtime_status_test.py & python credential_store_test.py & python main_export_state_test.py & python evidence_database_taxonomy_test.py & python evidence_schema_test.py & git diff --check & git status --short
```

Expected result: all listed local self-tests pass and the working tree is clean after committed changes.

## Deferred GUI Performance Note

- The corrected Access & Keys interaction path, including short-family visibility after relayout, is accepted through `ee945fe`. Broader pauses while moving or closing application windows remain deferred to a later whole-application GUI responsiveness/performance audit.

## Safe Next Milestones

1. Ordered Access & Keys boundary:
   - row 1 bounded `KEYS` sidebar/window presentation is implemented,
   - row 2A non-secret credential architecture/audit is implemented at `ef92017`,
   - row 2B read-only non-secret presence/provenance status, safe diagnostic categories, and fail-closed behavior is implemented at `7c1db2a`,
   - row 2C1 backend-only secure credential-store infrastructure is implemented at `29af218`,
   - row 2C2 masked cloud-ASR credential-entry fields, explicit Save/Clear GUI actions, and safe presence/provenance refresh are implemented at `97de48d`,
   - secure YouTube credential migration, legacy plaintext cleanup, no plaintext fallback, no UI preload, and removal of reveal/unmask controls are implemented at `3abb49d`,
   - the local-only trusted-callback cloud-ASR credential-consumption prerequisite is implemented at `a1cf07d`,
   - the explicit injected-executor ASR provider-action seam is implemented at `058af01`,
   - the explicit injected-tester ASR connection-test seam is implemented at `f709f8e`,
   - the next separately approved credential boundary is the first real provider implementation and later explicit user-facing Test Connection wiring; the current roadmap does not define a precise row label for that boundary. Production/user-facing connection testing must be explicit/user-triggered, and real provider/API calls, cloud-ASR execution, OAuth/browser flows, uploads, network behavior, and any future reveal/copy/export behavior remain later boundaries.
2. Local-only compatibility/reporting:
   - defer explicit transforms or reports across queue, adapter, access-status, taxonomy, provenance, and Total Export metadata until the next ordered credential boundary is separately approved or intentionally deferred,
   - no background jobs, file operations, external calls, provider tests, or network behavior.
3. Future source adapters and runtime integration:
   - adapters should remain metadata/capability skeletons first, not a generic scraper,
   - site fetching, credential testing, database scanning, file movement, and GUI/runtime integration remain deferred until separately approved with local/mocked tests.

## Preservation Evidence Bundle Plan Integration

Preservation plans may include evidence bundle metadata for manual/planned/external artifacts. Path hints are descriptive labels only. The helpers do not open, scan, hash, create, upload, download, capture, scrape, or fetch files/URLs.


Evidence bundle item details can record role, origin, path hint labels, and notes in preservation plan reporting. Path hints are descriptive only and are not opened, scanned, hashed, or validated.


The preservation evidence bundle CLI can record item role, origin, path hint labels, and notes. These remain metadata strings only and do not trigger file inspection or capture behavior.


Evidence item detail parsing now uses shared preservation evidence bundle helpers across the local CLI entry points, keeping role/origin/path-hint/notes validation consistent without file or network operations.


Evidence item detail metadata now has local regression checks for malformed specs, duplicate details, and unknown artifact IDs across the shared helper and CLI entry points.


Preservation backend plan input JSON can include evidence bundle metadata for local reporting. The evidence bundle fields remain descriptive metadata and do not cause source fetching, file opening, capture, or network behavior.


Standalone preservation evidence bundle CLI can render explicit local JSON bundle metadata through `--input`; evidence path hints remain descriptive strings and do not trigger file inspection or capture behavior.


Evidence bundle CLI JSON input errors are covered for missing files and malformed JSON, with explicit local failures and no evidence path inspection.


Total Export preservation-plan explanations can render explicit evidence bundle JSON input. The JSON is local metadata only; path hints inside it are labels and do not trigger file inspection or capture behavior.


Total Export evidence bundle JSON input error handling is covered for malformed JSON and non-object roots, while continuing to avoid evidence path inspection.


Total Export evidence bundle JSON input is checked in JSON preservation-plan output so metadata fields remain stable for downstream tooling.


Evidence bundle JSON helper validation now has standalone coverage for malformed local metadata while keeping path hints descriptive only.


Preservation backend plan JSON input now verifies malformed nested evidence bundle metadata is rejected before reporting, without inspecting path hints or evidence files.


Total Export evidence bundle input now rejects malformed nested local metadata through CLI tests before any preservation-plan reporting occurs.


Standalone evidence bundle CLI JSON input now rejects malformed nested local metadata before rendering, without inspecting path hints or evidence files.


Evidence bundle regression coverage can now be run through a single aggregate local test runner spanning model, JSON helper, standalone CLI, backend plan CLI, and Total Export prepare CLI checks.


Evidence bundle JSON helper tests now verify that source and item metadata fields stay typed as strings, preserving path hints as descriptive labels only.


Evidence bundle JSON helper tests now cover optional `None` normalization for local metadata fields, preserving empty path hints as descriptive labels only.


Evidence bundle regression coverage can now be listed or selectively run through `preservation_evidence_bundle_regression_test.py --list` and `--only LABEL`.


The aggregate evidence bundle regression runner now has a focused local test for listing, targeted execution, and unknown label validation.


Evidence bundle local-only scope invariants now have a dedicated regression test covering no-open plus scan/hash/upload/capture/network wording and descriptive path hints.


The aggregate evidence bundle regression runner test now explicitly covers targeted execution of the local-only scope invariant group.


The aggregate evidence bundle regression runner test now covers repeatable `--only` usage for targeted multi-group execution.


Evidence bundle local-only scope invariants now include preservation backend plan CLI JSON output through `--format json`, keeping path hints descriptive and local-only.


The aggregate evidence bundle regression runner now includes its own behavior test group without circular imports; the behavior test exercises the runner through subprocess calls.


Evidence bundle local-only scope invariants now cover text and JSON output surfaces, checking path hints remain descriptive and no-open/scan/hash/upload/capture/network wording remains visible.


Evidence bundle local-only scope invariants now cover Markdown output for the standalone evidence bundle and backend preservation-plan CLIs, keeping path hints descriptive and local-only.


Evidence bundle local-only scope invariants now assert path hints remain descriptive only and are not materialized into temp capture files or directories during CLI checks.


Evidence bundle local-only scope invariants now verify successful CLI output checks produce no stderr noise across JSON, text, and Markdown surfaces.


Evidence bundle regression runner behavior coverage now checks duplicate `--only` labels run once, preserving deterministic targeted regression selection.


Evidence bundle regression runner behavior coverage now checks targeted selections preserve canonical regression order instead of depending on request order.


Evidence bundle regression runner behavior coverage now checks mixed known/unknown targeted selections produce clear unknown-label diagnostics.


Evidence bundle local-only scope invariants now explicitly check archive/download prohibition wording so preservation metadata stays descriptive and non-executing.


Evidence bundle local-only scope invariants now check rendered and structured CLI outputs do not leak temp input paths, so descriptive path hints remain non-resolved metadata.


Evidence bundle local-only scope invariants now reject structured file-state keys, keeping evidence items descriptive rather than measured, opened, validated, or materialized.


Evidence bundle local-only scope invariants now verify structured path hints stay relative and descriptive, not absolute, URL-like, or drive-qualified evidence paths.


Evidence bundle local-only scope invariants now include negative examples for path hints, rejecting URL-like, drive-qualified, root-relative, and absolute forms.


Evidence bundle local-only scope invariants now include negative file-state key examples, proving representative measured/opened/uploaded/validated state fields are rejected.


Evidence bundle local-only scope invariants now exercise the full forbidden file-state key set in negative tests, keeping the helper and forbidden-key list synchronized.


Evidence bundle local-only scope invariants now check CLI outputs do not leak temporary JSON input filenames, keeping rendered metadata detached from test input files.


Evidence bundle regression runner behavior coverage now checks unknown-label diagnostics include all expected regression labels.


Evidence bundle local-only scope invariants now reject rendered file-state field markers in text/Markdown output so rendered metadata does not expose measured evidence state.


Evidence bundle local-only scope invariants now check metadata-only execution wording when present in structured outputs and in rendered outputs so evidence items remain descriptive rather than executable artifacts.


Evidence bundle local-only scope invariants now reject parent-traversal path hints, so descriptive evidence hints cannot point outside their labeled relative context.


Evidence bundle local-only scope invariants now reject embedded parent-traversal path hints, not only traversal at the start of the hint.


Evidence bundle regression runner behavior coverage now checks mixed known/unknown selection errors include all expected regression labels.


Evidence bundle regression runner behavior coverage now checks `--list` does not run regression groups or emit pass output.


Evidence bundle local-only scope invariants now include negative temp-path leak examples for temp directories and temporary JSON input filenames.


Evidence bundle regression runner behavior coverage now verifies targeted `--only` output contains exactly the requested passed labels.


Evidence bundle regression runner behavior coverage now pins exact passed-label output for single and duplicate targeted selections.


Evidence bundle regression runner behavior coverage now pins exact passed-label output for multi-target and reverse-order selections.


Evidence bundle regression runner behavior coverage now rejects duplicate regression labels in the expected label set and list-mode output.


Evidence bundle regression runner behavior coverage now verifies successful targeted runs emit exactly one aggregate success banner.


Evidence bundle regression runner behavior coverage now actively applies the success-banner-once helper to each successful targeted runner subprocess.


Evidence bundle regression runner behavior coverage now verifies failure diagnostics do not include success banners or passed-output lines.


Evidence bundle regression runner behavior coverage now pins list-mode output shape to one raw label line per canonical regression label.


Evidence bundle regression runner behavior coverage now explicitly verifies list-mode output has zero parsed `: passed` labels.


Evidence bundle regression runner behavior coverage now treats blank list-mode lines as output-shape failures and requires a trailing newline.


Evidence bundle regression runner behavior coverage now exercises all non-self regression labels in one targeted invocation to validate canonical output without recursive self-selection.


Evidence bundle regression runner behavior coverage now pins the self-recursive runner behavior label to the final canonical position and checks non-self coverage against `EXPECTED_LABELS[:-1]`.

Evidence bundle regression runner behavior coverage now checks multiple unknown `--only` labels are reported together, with empty stdout, no success-output leakage, and every valid expected label retained in diagnostics.

Evidence bundle regression runner behavior coverage now centralizes the aggregate success banner and self-recursive label constants and documents why broad coverage remains a targeted non-self run.

Evidence bundle regression runner behavior coverage now verifies broad non-self arguments exclude the recursive runner label, include every intended non-self label, and contain one `--only` switch per selection.

Evidence bundle regression runner behavior coverage now shares deterministic repeatable `--only` tuple construction across multi-label, non-self, duplicate, and unknown-label subprocess checks.

Evidence bundle regression runner behavior coverage now shares successful targeted-result assertions while retaining exact passed-label, single-banner, return-code, and clean-stderr validation.

Evidence bundle regression runner behavior coverage now shares contains-based unknown-label failure assertions across single, multiple, and mixed targeted-selection diagnostics.

Evidence bundle regression runner behavior coverage now verifies an unknown label blocks execution even when a valid targeted label is duplicated in the same selection.

Evidence bundle regression runner behavior coverage now verifies argparse rejects a bare `--only` option without emitting regression pass or aggregate success output.

Evidence bundle regression runner behavior coverage now verifies whitespace-only `--only` labels are rejected as unknown before any targeted regression output appears.

Evidence bundle regression runner behavior coverage now shares malformed bare `--only` assertion checks through a helper while preserving diagnostic-only blank-label validation.

Evidence bundle regression runner behavior coverage now verifies unexpected positional arguments are rejected diagnostically before any targeted regression output appears.

Evidence bundle regression runner behavior coverage now shares argparse-style malformed argument assertions across bare `--only` and unexpected positional failures.

Evidence bundle regression runner behavior coverage now verifies `--help` documents `--list` and `--only` without emitting regression pass lines or the aggregate success banner.

Evidence bundle regression runner behavior coverage now shares no-regression-output assertions across `--list` and `--help` while preserving their mode-specific diagnostics.

Evidence bundle regression runner behavior coverage now verifies `--list` remains listing-only when combined with `--only`, with no targeted regression output.

Evidence bundle regression runner behavior coverage now verifies `--help` remains non-executing when combined with `--only` or `--list`.

Evidence bundle regression runner behavior coverage now verifies partial `--only` label text is rejected diagnostically rather than matched by substring or fuzziness.

Evidence bundle regression runner behavior coverage now includes unknown option rejection, suffix-only exact-match rejection, and non-executing list/help behavior when unknown `--only` labels are supplied.

Evidence bundle regression runner behavior coverage now has a final cleanup pass that centralizes list/help non-execution checks and keeps the recursion guard visible.

Evidence bundle scope invariant coverage now includes a batched cleanup pass for clean local command output, descriptive-only evidence metadata, and no temporary-path leakage.

Evidence bundle JSON input validation coverage now verifies operational file-state keys are discarded across helper and CLI metadata input paths before rendered or structured evidence output.

Standalone evidence bundle CLI coverage now includes a batched cleanup pass for consistent invalid-input diagnostics and descriptive-only evidence metadata semantics.

Preservation backend plan CLI coverage now includes a batched cleanup pass for consistent invalid-input diagnostics and descriptive-only preservation/evidence plan semantics.

Total Export prepare CLI coverage now includes a batched cleanup pass for consistent invalid-input diagnostics and descriptive-only export/evidence plan semantics.

Preservation planning CLI/report coverage now includes a batched cleanup pass for consistent invalid-input diagnostics and local-only preservation metadata semantics.

Source capture/context CLI coverage now includes a batched cleanup pass for consistent invalid-input diagnostics and local-only, non-fetch context/glossary semantics.

Total Export bundle index reconciliation CLI coverage now includes a batched cleanup pass for consistent invalid-input diagnostics and local-only ZIP/index semantics.

Total Export ZIP sidecar coverage now includes a batched cleanup pass for shared SHA256/inspection JSON write-state assertions and local-only ZIP sidecar semantics.

Total Export review bundle verification coverage now includes a batched cleanup pass for shared status assertions and local-only ZIP sidecar diagnostics.

Total Export review bundle folder verification coverage now includes a batched cleanup pass for shared folder count assertions and local-only ZIP sidecar diagnostics.

Total Export batch review bundle coverage now shares deterministic row/success/failure count checks across its main batch-result scenarios.

Total Export batch review reconciliation coverage now shares deterministic single-item status checks across its primary local result scenarios.

Total Export batch review plan coverage now shares deterministic row/error count checks across ready and invalid local planning scenarios.

Total Export package ZIP coverage now shares deterministic created/failure result checks while preserving local archive metadata and inspection diagnostics.

Total Export ZIP inspection coverage now shares deterministic status checks across valid and malformed local ZIP fixture scenarios.

Total Export package inspection coverage now shares deterministic status checks across valid and missing/invalid local package fixture scenarios.

Total Export validation coverage now shares deterministic exact error-code checks across malformed local manifest and asset fixture scenarios.
