# Source Evidence Roadmap Coverage Audit

Date: 2026-07-11

Checkpoint: `65cf20f Document access keys manager flow`

Branch: `v2.6.0-asr-engines`

## Purpose

This document records the current roadmap coverage audit for the larger source-evidence, Access & Keys, Total Export, Add Media queue, database taxonomy, public-media evidence, behavior logging, and source-crediting plans.

It is a checklist for future sessions so completed roadmap coverage is not duplicated and roadmap-only items are not mistaken for implemented behavior.

This is documentation only. It does not implement adapters, capture, downloads, archive checks, archive submission, browser automation, scraping, credential storage, GUI behavior, database scanning, file movement, or provider/API calls.

## Coverage Audit

| User requirement | Covered? | Where covered | Current state | Gap / next milestone | Do not duplicate? |
| --- | --- | --- | --- | --- | --- |
| KEYS / Access & Keys manager window | Covered in roadmap/spec | `SOURCE_EVIDENCE_ROADMAP.md`; `ACCESS_KEYS_MANAGER_SPEC.md` | Docs-only; no window or credential storage | Future UI/security implementation design after approval | Yes; extend spec instead |
| API/cloud ASR provider credentials | Partly covered | `ACCESS_KEYS_MANAGER_SPEC.md`; ASR provider metadata notes in `CURRENT_DEV_STATE.md` | Non-secret provider metadata exists; no credential manager | Define storage/masking/clearing/migration in a later explicit milestone | Yes |
| Platform/source access families beyond one API key | Covered in roadmap/spec | `SOURCE_EVIDENCE_ROADMAP.md`; `ACCESS_KEYS_MANAGER_SPEC.md` | Access taxonomy planned; no UI | Implement shared access-state model only after spec/test milestone | Yes |
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
| Add Media / evidence item queue | Covered in roadmap/spec | `SOURCE_EVIDENCE_ROADMAP.md`; `EVIDENCE_ITEM_QUEUE_UI_SPEC.md` | Docs-only spec; no UI/storage | Future item model skeleton or UI mock after approval | Yes |
| Old ASR reference workflow compatibility | Covered in spec | `EVIDENCE_ITEM_QUEUE_UI_SPEC.md` | YouTube URL, TXT reference, source media, subtitle/transcript compatibility explicitly preserved | Specify implementation mapping when queue model starts | Yes |
| Evidence database taxonomy/repository recognition | Covered in roadmap/spec | `SOURCE_EVIDENCE_ROADMAP.md`; `EVIDENCE_DATABASE_TAXONOMY_SPEC.md` | Docs-only spec; no scanner/indexer/storage | First milestone should be read-only index/dry-run schema | Yes |
| Unknown-to-known reclassification | Covered in spec | `EVIDENCE_DATABASE_TAXONOMY_SPEC.md` | Review flags, suggested path, history, approval documented | Future dry-run conflict detector | Yes |
| Sensitive classification safeguards | Covered in spec | Database taxonomy spec and roadmap | Explicit evidence/user confirmation required; unknown remains valid | Define audit trail and permissions before implementation | Yes |
| Public-media download/capture for open public media | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Public Media Download / Evidence Capture Policy | Future explicit capability target; not implemented | Source-aware media selection/capture spec before runtime | Yes |
| Behavior/activity log | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Behavior / Activity Log And Research Metrics | Future local logging only; not telemetry; not implemented | Define local event schema and privacy controls before implementation | Yes |
| Compression/external archive-tool guidance | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Compression / External Archive Tool Guidance | Planning only; no compression execution/dependency | Define provenance fields and optional user-triggered tool workflow | Yes |
| Source crediting/witness/access-actor accounting | Covered in roadmap | `SOURCE_EVIDENCE_ROADMAP.md`, Future Source Crediting / Witness And Access-Actor Accounting | Planning only; no UI/workflow | Map actors to claim/source-role records and queue items | Yes |
| Total Export folder/package of selected outputs | Implemented local-only | Total Export helpers; `TOTAL_EXPORT_DEV_CLI_EXAMPLES.md`; current-state docs | Local package shell, manifest, assets, review files, ZIP, sidecars, batch/index/reconcile exist | GUI integration and actual capture outputs remain absent | Yes |
| Current Total Export local capabilities | Implemented local-only | `PROJECT_CURRENT_STATE_HANDOFF.md`; `CURRENT_DEV_STATE.md`; Total Export docs | Plan/package/manifest, validation, inventory, summaries, ZIP, sidecars, verification, batch, index, reconciliation | Consolidate into GUI only after deliberate UX milestone | Yes |
| Remaining roadmap-only work | Roadmap-only | Roadmap/spec docs | Keys UI, non-YouTube adapters, page capture, screenshots, archives, media acquisition, queue UI, database indexing/reclassification are not implemented | Keep each operational area separately approved and locally/mocked | Yes |
| Most important next milestone | Gap remains | This audit plus queue/database/access specs | Requirements exist; no implemented bridge to GUI/workflows | Choose between item model skeleton, database read-only index schema, or Access & Keys metadata/status model | Do not start runtime capture accidentally |

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

Docs-only/spec-only:

- Access & Keys window.
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

## Recommended Next Milestone Choices

Choose one deliberate next milestone rather than returning to unfocused micro-cleanups.

1. **Implementation skeleton: evidence item queue model**
   - Local dataclass/schema only.
   - No GUI.
   - No file opening/watching.
   - No capture/network/download behavior.
   - Tests for roles, statuses, linking, ASR pairing metadata, and Total Export include/exclude flags.

2. **Implementation skeleton: Access & Keys metadata/status model**
   - Non-secret metadata/status only.
   - No credential storage.
   - No key testing.
   - No provider/API calls.
   - Tests for access modes, credential statuses, provider/source/archive metadata rendering.

3. **Implementation skeleton: database taxonomy read-only schema**
   - Local schema and dry-run structures only.
   - No folder scanning yet, or scan only tiny temp test fixtures if explicitly approved.
   - No file movement.
   - Tests for unknown-to-known review, sensitive classification safeguards, alias suggestions, and history records.

4. **Docs-only closeout/handoff**
   - Update cross-project handoff/current-state docs to checkpoint these new specs.
   - Useful before starting a new session or after Codex reset.

## Risk Warning

The next runtime-adjacent milestone could accidentally introduce network/API calls, browser automation, scraping, archive submission, media downloading, credential handling, or filesystem movement.

Keep the next implementation skeleton local-only, deterministic, and testable. Require explicit approval before any external access, media capture, archive service, browser, credential, or file-movement behavior is added.
