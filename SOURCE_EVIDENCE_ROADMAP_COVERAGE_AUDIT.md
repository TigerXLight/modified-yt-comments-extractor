# Source Evidence Roadmap Coverage Audit

Date: 2026-07-14

Checkpoint: `3abb49d Add secure YouTube credential migration`

Branch: `v2.6.0-asr-engines`

## Purpose

This document records the current roadmap coverage audit for the larger source-evidence, Access & Keys, Total Export, Add Media queue, database taxonomy, public-media evidence, behavior logging, and source-crediting plans.

It is a checklist for future sessions so completed roadmap coverage is not duplicated and roadmap-only items are not mistaken for implemented behavior.

This is documentation only. It does not implement adapters, capture, downloads, archive checks, archive submission, browser automation, scraping, credential storage, GUI behavior, database scanning, file movement, or provider/API calls.

## Coverage Audit

| User requirement | Covered? | Where covered | Current state | Gap / next milestone | Do not duplicate? |
| --- | --- | --- | --- | --- | --- |
| KEYS / Access & Keys manager window | Implemented bounded GUI presentation | `ACCESS_KEYS_MANAGER_SPEC.md`; `access_keys_catalog.py`; Access & Keys metadata/view model/dialog; `main.py` | Sidebar `KEYS` button and single reusable `Access & Keys` window render the complete planned non-secret catalog with ordered user-facing sections/subgroups, alias-aware search, full-width family selection, stable in-place selection/details, immediate short-family visibility after filtering, diagnostics, and limitations; the existing API-key entry remains unchanged | Row-1 presentation layer is complete; credential values/storage/testing and provider-specific operations belong to row 2 and require separate approval | Yes; extend existing models/spec |
| API/cloud ASR provider credentials | Rows 2A, 2B, 2C1, 2C2, and the approved YouTube credential-migration boundary are implemented within bounded boundaries | `ACCESS_KEYS_MANAGER_SPEC.md`; `CREDENTIAL_SECURITY_AUDIT.md`; `credential_architecture.py`; `credential_runtime_status.py`; `credential_store.py`; `youtube_credential_migration.py`; focused tests; Access & Keys metadata/dialog; narrow `main.py` wiring | Stable credential IDs and security policy are implemented together with read-only runtime status overlays, a secure credential-store abstraction for catalogued cloud-ASR credential IDs, masked cloud-ASR Save/Clear controls, and explicit secure YouTube credential migration/legacy cleanup. YouTube new/updated saves are secure-only with no plaintext fallback; legacy plaintext migration is explicit/user-controlled, uses preserve-before-delete ordering, and removes legacy plaintext only after secure save plus non-secret presence verification. Clear handles missing, secure-only, legacy-only, both-copy, unavailable/error, malformed settings, and partial-failure states truthfully. The YouTube entry is permanently masked, has no reveal/copy control, never preloads stored credentials, remains empty after startup/reopen/status refresh/migration/Clear, and resolves configured credentials internally only at existing action time. Row 2C2 still invokes the secure store only for explicit cloud-ASR Save/Clear and safe presence probing; no cloud-ASR provider consumes stored credentials. Environment-variable presence reporting remains supported. The initial plaintext cloud-ASR field defect and later YouTube reveal/preload/partial-clear/security defects were corrected before their commits. | Remaining credential work is unresolved and separately approval-gated: provider credential consumption, connection testing, OAuth/browser flows, provider/API calls, cloud ASR execution, uploads, network behavior, and any future reveal/copy/export behavior | Yes; extend the existing row 2 credential architecture rather than bypassing it |
| Platform/source access families beyond one API key | Implemented local metadata and presentation | `SOURCE_EVIDENCE_ROADMAP.md`; `ACCESS_KEYS_MANAGER_SPEC.md`; `access_keys_catalog.py`; Access & Keys modules | The complete planned non-secret service catalog is represented in deterministic sections/subgroups with aliases and explicit planned-versus-implemented status; no real authentication or adapter execution is added | Real platform authentication/access remains deferred behind row 2 and later source-specific approvals | Yes |
| Multi-source / website comment capture | Partly covered | `SOURCE_EVIDENCE_ROADMAP.md`, Track A and Mixed-Access Websites | YouTube works; News Website adapter is metadata/URL recognition only | Add one site-specific adapter with mocked/local tests after explicit approval | Yes; avoid generic scraper |
| Post capture | Partly covered | `SOURCE_EVIDENCE_ROADMAP.md`, Capture Checkbox Roadmap | Roadmap checkbox only | Define adapter capabilities/provenance/completeness warnings | Yes |
| Comments/replies/live chat capture | Implemented existing runtime for YouTube | Existing YouTube extractor flow; `SOURCE_EVIDENCE_ROADMAP.md` YouTube note | YouTube comments/replies/live chat exist; other sources do not | Preserve YouTube while adding adapters one by one | Yes |
| Visible page text | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Web Evidence Capture | No extraction runtime | Define explicit user-triggered capture contract | Yes |
| Readable/article text only when selected | Covered in roadmap | Mixed-Access Websites; Web Evidence Capture | Not implemented | Specify selection UX and access-state handling | Yes |
| Full-page screenshot | Covered in roadmap | Web Evidence Capture; capture method metadata notes | Metadata/planning only; no screenshot execution | Site-aware capture spec and mocked tests first | Yes |
| Scrollable-container/modal limitation | Implemented local-only metadata/planning | `CURRENT_DEV_STATE.md`; capture method metadata; handoff notes | Limitation represented as metadata; no capture execution | Future browser/capture design must target nested containers explicitly | Yes |
| HTML snapshot | Covered in roadmap | Web Evidence Capture; capture checkboxes | Planning/metadata only | Define raw versus selected/cleaned HTML provenance | Yes |
| Images/media evidence | Partly covered | `SOURCE_EVIDENCE_ROADMAP.md`; `SOURCE_PRESERVATION_ROADMAP.md`; local media registration helpers | User-supplied local media metadata/verification exist; no discovery/download | Specify selectable asset inventory and provenance | Yes |
| Video/media evidence | Covered in roadmap | Public media evidence policy; YouTube planning; optional media inspiration | Future selectable option; not current behavior | Keep opt-in/access-aware with mocked design before runtime | Yes |
| No/selected/all/defined-count media choice | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`; media evidence logging/spec notes | `none`, `select`, `all`, and defined count/amount are planned; no acquisition | Add implementation only after source-aware selection design | Yes |
| Wayback/archive.org check | Covered in roadmap | Archive track; `ACCESS_KEYS_MANAGER_SPEC.md` archive services | No external checks; manual archive URL metadata only | Explicit read-only adapter design with mocked tests | Yes |
| archive.ph/archive.today-style check | Covered in roadmap | Archive track; Access & Keys archive services | Separate optional service planned; not implemented | Treat as independent optional service | Yes |
| Explicit archive submit/save | Covered in roadmap | Archive track; UI wording; Access & Keys archive services | Explicit user-selection rule documented; no submission | Separate check and submit permissions/actions | Yes |
| Local ArchiveBox-style archiving | Partly covered | Preservation backend plan helpers; `SOURCE_PRESERVATION_ROADMAP.md`; `ACCESS_KEYS_MANAGER_SPEC.md` | Local-only metadata/planning; ArchiveBox never executed | Define local process boundary, paths, failure states, and opt-in controls | Yes |
| Primary/secondary/tertiary source roles | Covered in roadmap | Source-Role / Evidence Hierarchy | Detailed taxonomy and schema foundations; no full workflow UI | Map roles into queue/editor/export review | Yes |
| Claim-level source-role scope | Covered in roadmap | Source-role rules; claim-level planning | Exact-claim scoping documented | Add claim-review UI only when evidence workflow is implemented | Yes |
| Temporal/currentness source scope | Covered in roadmap | Claim-Level And Temporal Source-Role Planning | Current/historical/unknown/reposted/undated fields planned | Surface temporal limitations during review | Yes |
| Closed-loop reporting / propagated claims | Covered in roadmap | Tertiary role; claim-level planning | Flag concepts documented | Future duplicate/source-chain analysis not implemented | Yes |
| Media source-chain tracking | Covered in roadmap | Media Source-Chain And Disputed-Framing Tracking | Detailed fields and schema skeleton; no automated matching | Start with manual linking before fingerprints | Yes |
| Disputed publisher framing/source-author corrections | Covered in roadmap | Media source-chain; capture checkboxes | Correction/competing-claim fields planned | Add manual notes/import workflow before automation | Yes |
| Public YouTube evidence workflow | Covered in roadmap | YouTube-specific planning note | Comments/replies/live chat exist; broader evidence package incomplete | Connect existing YouTube outputs to explicit evidence items | Yes |
| Preserve current YouTube behavior | Implemented existing runtime and guarded in docs | Track A; YouTube note; `CURRENT_DEV_STATE.md` | Existing flow remains separate and must be preserved | Add regression coverage when future adapter wiring begins | Yes |
| Add Media / evidence item queue | Implemented local-only schema | `EVIDENCE_ITEM_QUEUE_UI_SPEC.md`; `evidence_item_queue.py`; `evidence_item_queue_test.py` | Immutable roles, statuses, links, ASR pairings, and Total Export include/exclude metadata exist; no UI, persistence, or runtime wiring | Queue UI/storage remains a later explicit milestone after earlier ordered rows | Yes |
| Old ASR reference workflow compatibility | Implemented local-only schema | `EVIDENCE_ITEM_QUEUE_UI_SPEC.md`; `ASRPairingMetadata` in `evidence_item_queue.py` | Media/reference/subtitle/transcript/engine/scoring metadata can be represented without running ASR | Runtime mapping into the existing ASR workflow remains deferred | Yes |
| Evidence database taxonomy/repository recognition | Implemented local-only schema | `EVIDENCE_DATABASE_TAXONOMY_SPEC.md`; `evidence_database_taxonomy.py`; focused test | Read-only root/taxonomy/item/dry-run metadata exists; paths are labels only | Real or temporary-fixture indexing/scanning is not implemented and remains behind earlier rows | Yes |
| Unknown-to-known reclassification | Implemented local-only schema | Taxonomy spec; reclassification suggestion/history/dry-run records | Reviewable unknown-to-known suggestions and history can be represented; nothing is applied | Conflict detection over supplied/indexed records remains a later layer | Yes |
| Sensitive classification safeguards | Implemented local-only schema | Taxonomy spec; classification/suggestion safeguards and tests | Unknown remains valid; weak-clue inference is prohibited; explicit evidence/review state is represented | Runtime enforcement, permissions, persistence, and classification execution remain unimplemented | Yes |
| Public-media download/capture for open public media | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Public Media Download / Evidence Capture Policy | Future explicit capability target; not implemented | Source-aware media selection/capture spec before runtime | Yes |
| Behavior/activity log | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Behavior / Activity Log And Research Metrics | Future local logging only; not telemetry; not implemented | Define local event schema and privacy controls before implementation | Yes |
| Compression/external archive-tool guidance | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Compression / External Archive Tool Guidance | Planning only; no compression execution/dependency | Define provenance fields and optional user-triggered tool workflow | Yes |
| Source crediting/witness/access-actor accounting | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Source Crediting / Witness And Access-Actor Accounting | Planning only; no UI/workflow | Map actors to claim/source-role records and queue items | Yes |
| Total Export folder/package of selected outputs | Implemented local-only | Total Export helpers; `TOTAL_EXPORT_DEV_CLI_EXAMPLES.md`; current-state docs | Local package shell, manifest, assets, review files, ZIP, sidecars, batch/index/reconcile exist | GUI integration and actual capture outputs remain absent | Yes |
| Current Total Export local capabilities | Implemented local-only | `PROJECT_CURRENT_STATE_HANDOFF.md`; `CURRENT_DEV_STATE.md`; Total Export docs | Plan/package/manifest, validation, inventory, summaries, ZIP, sidecars, verification, batch, index, reconciliation | Consolidate into GUI only after deliberate UX milestone | Yes |
| Remaining roadmap-only work | Roadmap-only | Roadmap/spec docs | Credential lifecycle UI, non-YouTube adapters, page capture, screenshots, archives, media acquisition, queue UI, and database indexing/reclassification are not implemented | Keep each operational area separately approved and locally/mocked | Yes |
| Most important next milestone | Gap remains after `3abb49d` | Next unresolved credential-consumption/testing boundary; `CREDENTIAL_SECURITY_AUDIT.md`; `credential_architecture.py`; `credential_runtime_status.py`; `credential_store.py`; `youtube_credential_migration.py` | Rows 2A, 2B, 2C1, 2C2, and the approved secure YouTube migration/legacy-cleanup boundary are implemented. Stored cloud-ASR credentials are still not consumed by providers, and no connection tests/provider calls exist. YouTube credential storage now saves securely only, supports explicit legacy migration/cleanup, keeps the GUI field empty on reopen, and preserves existing extraction through internal action-time credential resolution. | Obtain separate explicit security approval before provider credential consumption, connection testing, provider/API calls, OAuth/browser flows, cloud ASR execution, uploads, network behavior, or any future reveal/copy/export behavior | Do not treat the YouTube migration closeout as approval for provider execution, connection tests, or later roadmap rows |

## Already Covered And Should Not Be Duplicated

Do not duplicate these sections unless correcting an actual error:

- Access & Keys platform/access families.
- Mixed-access website rules.
- Archive check/submit separation.
- Source roles and claim-level source-role scope.
- Temporal/currentness source limitations.
- Media source-chain/disputed framing.
- YouTube evidence planning.
- Capture checkboxes.
- Public media evidence policy.
- Add Media/evidence queue roadmap/spec.
- Database taxonomy/reclassification roadmap/spec.
- Behavior/activity logging.
- Source crediting/witness/access-actor accounting.
- Total Export terminology and local-only boundaries.
- Preservation safety boundaries.

Future work should extend the relevant spec rather than re-adding the same roadmap content.

## Recently Added Roadmap/Spec Commits

- `6f2449e Plan evidence queue and database taxonomy`
  - Added future Add Media/evidence item queue planning.
  - Added user-defined evidence database taxonomy/reclassification planning.
- `9aab238 Plan media evidence logging and source crediting`
  - Added explicit public-media evidence download/capture policy.
  - Added behavior/activity log planning.
  - Added compression/external archive-tool guidance.
  - Added source crediting/witness/access-actor accounting.
- `e2456b6 Document evidence item queue UI flow`
  - Added focused queue UI/data-flow spec.
- `e4c195d Document evidence database taxonomy flow`
  - Added focused database taxonomy/reclassification spec.
- `65cf20f Document access keys manager flow`
  - Added focused Access & Keys UI/security/access metadata spec.
- `7af8eea Add evidence item queue model skeleton`
  - Added immutable local queue roles, states, links, ASR pairings, and Total Export selection metadata.
- `66871b6 Add access keys metadata model skeleton`
  - Added non-secret access/credential/test-status catalog and report structures.
- `e63def4 Add evidence database taxonomy schema skeleton`
  - Added read-only taxonomy, dry-run, review, safeguard, and history structures.
- `8d11a4b Add Access Keys manager view model`
  - Added GUI-independent searchable/filterable platform sections, selection state, safe entry presentation, and deterministic serialization.
- `1b57e74 Wire Access Keys manager window`
  - Added the separate `KEYS` sidebar control and reusable non-secret `Access & Keys` window while preserving the existing API-key field and behavior.
- `191ee21 Update Access Keys roadmap state`
  - Checkpointed the bounded non-secret window and retained row 2 as the first secret-bearing approval boundary.
- `0ff528d Complete Access Keys catalog and interactions`
  - Added the complete planned non-secret service catalog and ordered sections/subgroups, corrected full-width family selection, removed the earlier selection/filter pane flash, restored hover feedback, and added focused catalog/interaction regressions.
- `ee945fe Fix Access Keys short-family visibility`
  - Reset and coalesced the catalog scroll position during family/search relayout so short families such as ASR Providers, News Websites, Archive Services, and Browser-Assisted Capture appear immediately after switching from a long scrolled family; added the deterministic regression and passed manual acceptance.
- `447f031 Close Access Keys presentation milestone`
  - Closed row 1 documentation while preserving the deferred whole-application GUI responsiveness note and retaining row 2 as a separate approval boundary.
- `ef92017 Add credential architecture and security audit`
  - Added row 2A stable non-secret credential descriptors, backend/migration/redaction/sink policies, safe status helpers, eight existing-code security findings, focused validation, and explicit row 2B/2C/later-network boundaries without changing runtime credential behavior.
- `d610ddf Close credential architecture audit milestone`
  - Closed row 2A documentation and retained row 2B as a separately approved read-only runtime-status boundary.
- `7c1db2a Add read-only credential status integration`
  - Added row 2B local read-only credential status/provenance overlays for the already-loaded YouTube key and named cloud-ASR environment variables, fail-closed safe diagnostics, metadata/dialog integration, and focused regressions without exposing values or adding writes, migration, provider tests, calls, OAuth, or network behavior.
- `29af218 Add secure credential store backend`
  - Added row 2C1 backend-only secure credential-store infrastructure for catalogued cloud-ASR credential IDs, with deterministic non-secret keyring locators, a session-only in-memory test backend, a fail-closed injected/system-keyring backend, fixed non-secret result statuses, explicit YouTube credential rejection, and focused leakage/error regressions. At that checkpoint no production caller, GUI credential field, settings migration, legacy cleanup, provider test/call, OAuth, browser, or network behavior was added; row 2C2 later added only explicit cloud-ASR Save/Clear and safe presence probing.
- `97de48d Add cloud ASR credential controls`
  - Added row 2C2 masked cloud-ASR credential Save/Clear controls for supported catalogued cloud-ASR entries, safe secure-store presence/provenance refresh, deterministic keyring/environment precedence, and focused tests using fake/injected keyring behavior. The initial plaintext masking defect was corrected before commit and the corrected manual retest passed. Existing YouTube credential workflow, provider consumption, connection tests, OAuth/browser flows, uploads, and network behavior remain unchanged and separately gated.
- `3abb49d Add secure YouTube credential migration`
  - Added secure-only YouTube credential saving/updating, explicit legacy plaintext migration and cleanup, truthful Clear/partial-failure handling, no plaintext fallback for new writes, removal of reveal/unmask controls, no stored-key preload into the UI field, and existing extraction compatibility through internal action-time credential resolution. Manual production verification used `python main.py` with the active venv and confirmed masked Save, configured status, empty field after restart, Access & Keys presence/provenance, and no credential value exposure.

## Ordered Audit Progress At `3abb49d`

- Row 1 is complete for its approved bounded presentation layer: spec, non-secret metadata, complete planned catalog, view model, sidebar control, reusable window, full-width family selector, in-place selection/detail updates, and short-family scroll-reset behavior are implemented and tested.
- Row 2A is complete as a non-secret architecture and existing-code audit. It defines stable credential IDs, storage/migration/redaction/sink policy, safe presence labels, and security findings without changing credential lifecycle behavior.
- Row 2B is complete within its approved read-only boundary. It reports only non-secret presence/provenance and fixed safe diagnostic categories, derived YouTube presence from the then-existing masked field/storage state, inspected only named cloud-ASR environment-variable presence, and added no secret values, writes, clearing, migration, connection tests, provider calls, OAuth, or network behavior. The later `3abb49d` YouTube migration removed stored-key preload into the UI field.
- Row 2C1 is complete within its approved backend-only boundary. It adds deterministic cloud-ASR keyring locators, explicit `youtube_data_api_key` rejection, session-only in-memory testing, injected/system-keyring operations, fail-closed status results, and no plaintext/settings/env/file fallback.
- Row 2C2 is complete within its approved masked cloud-ASR UI boundary. The Access & Keys window exposes Save/Clear only for supported cloud-ASR entries, masks the credential field from widget creation onward, never preloads stored values, clears the entry after Save/Clear paths, refreshes safe status/provenance, preserves environment-variable reporting, and keeps local/non-cloud ASR entries without controls. Tests use fake/injected keyring behavior and do not access the user's real keyring. Manual GUI verification confirmed masked input, Save, configured status, close/reopen without value preload, Clear, missing status, local entries without controls, unchanged masked YouTube field behavior, and no obvious destructive pane rebuild regression.
- The approved YouTube credential migration/legacy-cleanup boundary is complete at `3abb49d`. New/updated YouTube credentials are secure-only with no plaintext fallback; legacy plaintext migration is explicit and user-controlled; legacy cleanup happens only after secure save plus safe presence verification; Clear handles secure-only, legacy-only, both-copy, missing, backend-unavailable/error, malformed-settings, and partial-failure states truthfully. Stored YouTube credentials are never preloaded into the GUI entry, the reveal/unmask path was removed entirely, and existing extraction resolves configured credentials internally at action time without inserting values into the widget.
- Remaining credential work after `3abb49d` is separately approval-gated: provider credential consumption, connection testing, OAuth/browser flows, provider/API calls, cloud ASR execution, uploads, network behavior, and any future reveal/copy/export behavior.
- Row 3 retains verified non-secret metadata and GUI presentation only; it does not claim real platform authentication.
- Rows 4 through 39 were reviewed for ordering only and were not implemented in this session. Existing completed schema layers at rows 27 through 31 were recognised and not duplicated.

## What Is Implemented Now

Implemented existing runtime:

- Current YouTube comments/replies/live chat/export workflow.
- Existing ASR/local reference workflows described in current-state docs.

Implemented local-only helper/CLI/test infrastructure:

- Source adapter metadata skeletons and capability/gap reports.
- Capture option metadata.
- Capture method metadata.
- Evidence/provenance schema skeletons.
- Total Export package/manifest/review/ZIP/sidecar/batch/index/reconcile helpers and tests.
- Manual archive URL metadata.
- User-supplied local media registration and verification helpers.
- Preservation plan/report helpers.
- ASR comparison/reporting/manual seed tooling.
- Evidence item queue schema with links, ASR pairing metadata, and explicit Total Export selection intent.
- Non-secret Access & Keys catalog/report metadata and GUI-independent manager presentation state.
- Bounded `KEYS` sidebar/window presentation over non-secret metadata and the complete planned catalog, with ordered sections/subgroups, alias-aware search, full-width family filtering, stable in-place selection/details, empty states, and diagnostics.
- Row 2A credential architecture/audit metadata: stable non-secret provider credential IDs, backend and migration policy, prohibited secret-sink rules, exact-value redaction helpers, safe presence labels, eight findings, deterministic serialization/rendering, and focused validation.
- Row 2B read-only runtime credential status: `credential_runtime_status.py` plus focused tests and narrow Access & Keys wiring report configured/missing/backend-unavailable/error states and safe provenance without rendering or retaining values; YouTube status uses safe storage information without value exposure, while cloud ASR uses named environment-variable presence only. The later secure YouTube migration keeps stored credentials out of the UI field.
- Row 2C1 secure credential store: `credential_store.py` plus focused tests provide deterministic non-secret locators for catalogued cloud-ASR credentials, explicit save/overwrite/clear/presence result statuses, a test-only/session-only memory backend, and a fail-closed injected/system-keyring backend. It deliberately excludes the existing YouTube credential workflow.
- Row 2C2 masked cloud-ASR credential controls: `access_keys_dialog.py`, `credential_runtime_status.py`, `credential_store.py`, narrow `main.py` wiring, and focused tests now allow explicit Save/Clear only for supported cloud-ASR entries through the row 2C1 secure-store abstraction. The field is masked from widget creation onward, has no reveal/copy control, does not preload stored values, clears after Save/Clear paths, refreshes safe configured/missing/unavailable/error status and provenance, preserves environment-variable presence reporting, and adds no provider/API/OAuth/browser/network behavior.
- Secure YouTube credential migration and legacy cleanup: `core/settings.py`, `youtube_credential_migration.py`, narrow `main.py` wiring, and focused tests now provide secure-only YouTube Save/Update, explicit legacy plaintext migration, no plaintext fallback for new writes, no automatic migration, truthful Clear/partial-failure semantics, malformed-settings protection, no reveal/copy control, no stored-key UI preload, empty field after reopen/status refresh/migration/Clear, and internal action-time credential resolution for existing extraction.
- Evidence database taxonomy/dry-run/reclassification/history schema with sensitive-classification safeguards.

Docs-only/spec-only:

- Production credential consumption by cloud-ASR providers, real connection testing/provider access, OAuth, cloud ASR uploads/runs, and all network behavior.
- Any future reveal/copy/export behavior for credentials.
- Generalized non-YouTube adapters.
- Website/page capture.
- Screenshots and scrollable-container capture execution.
- Archive checks and archive submissions.
- ArchiveBox execution.
- Public-media discovery/download/capture.
- Add Media/evidence queue UI and storage.
- Evidence database scanning/indexing/reclassification.
- Behavior/activity log implementation.
- Source credit/witness UI/workflow.

## Deferred General GUI Responsiveness Note

- Manual user testing accepted the corrected Access & Keys catalog, hover, family filtering, platform-selection behavior, and immediate visibility of short families after switching from a long scrolled family.
- Some broader pauses remain while moving or closing windows in the main application. These are recorded for a later whole-application GUI responsiveness/performance audit and are not treated as an unresolved Access & Keys row-1 interaction defect.

## Ordered Next Boundary

Row 1 bounded GUI presentation, row 2A non-secret credential architecture/audit, row 2B read-only local credential status integration, row 2C1 backend-only secure credential-store infrastructure, row 2C2 masked cloud-ASR Save/Clear UI, and the approved secure YouTube credential migration/legacy-cleanup boundary are complete.

The next ordered credential boundary is provider credential consumption and/or explicit connection testing for stored credentials. The current roadmap documents do not define a precise row label for that boundary, so it must remain a separately approved credential-consumption/testing milestone rather than an implicitly numbered row.

That boundary must not silently expand into provider/API calls, OAuth, cloud ASR execution, browser access, uploads, network behavior, or credential reveal/copy/export behavior. Those remain separate approval boundaries unless the next prompt explicitly includes them. Do not skip to later roadmap rows.

## Risk Warning

The next runtime-adjacent milestone could accidentally introduce network/API calls, browser automation, scraping, archive submission, media downloading, credential handling, or filesystem movement.

Keep the next implementation skeleton local-only, deterministic, and testable. Require explicit approval before any external access, media capture, archive service, browser, credential, or file-movement behavior is added.
