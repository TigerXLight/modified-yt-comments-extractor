# Project Capability Gaps And Next Steps V76M

Audit date: 2026-08-16

This file lists concrete gaps found while building the V76M current-capabilities audit. Each gap names current status, missing code, suggested files/tests, and safety notes.

Interpretation: a gap may sit beside `IMPLEMENTED` foundations. The gap rows below call out what remains `PARTIAL`, `DOCUMENTED_ONLY`, `BLOCKED_BY_DEPENDENCY`, or `NEEDS_MANUAL_REVIEW` without demoting the implemented modules named as foundations.

## Gap 1: Full Profile/Media HOME Ingestion

- Current status: `PARTIAL`.
- Missing code: direct ingestion of a real HOME repository tree with source.txt, RTF, media source folders, and existing sidecars. Current workflows use explicit folder-tree text, explicit batch JSON, and confirmation-gated writes.
- Suggested implementation files: `profile_media_home_ingestion.py`, `profile_media_database_gui_controller.py`, `profile_media_database_workbench_panel.py`.
- Suggested tests: `profile_media_home_ingestion_test.py`, `profile_media_database_gui_controller_test.py`.
- Risk/safety note: must not scan arbitrary user media folders without explicit root selection and dry-run preview; must not infer sensitive identifiers.

## Gap 2: Article Extraction Optional Dependencies

- Current status: `PARTIAL`, `BLOCKED_BY_DEPENDENCY`, `REFERENCE_ONLY`.
- Missing code: packaged/declared dependency integration for `trafilatura`, `newspaper4k`, and `metadata_parser`. Current adapter attempts imports and falls back to stdlib.
- Suggested implementation files: `profile_media_article_extraction_adapter.py`, dependency setup/docs, `tools/run_profile_media_article_extraction_cli_v76l.py`.
- Suggested tests: `profile_media_article_extraction_adapter_test.py` with dependency-present and dependency-missing fixtures.
- Risk/safety note: libraries must not crawl/fetch URLs unless an explicit network mode is added and approved. They should process supplied HTML/local files by default.

## Gap 3: Segment-Level First-Person And Claim Role Review

- Current status: `PARTIAL`.
- Missing code: segment-level claim extraction/review rows that preserve first-person "I" / authored-source signals without automatic final classification.
- Suggested implementation files: `profile_media_source_criticism_model.py`, `profile_media_article_extraction_adapter.py`, new `profile_media_claim_segment_review.py`.
- Suggested tests: `profile_media_claim_segment_review_test.py`.
- Risk/safety note: do not infer identity or protected attributes; keep results as review lanes/candidates.

## Gap 4: Profile/Media GUI Add/Import Wizard

- Current status: `PARTIAL`, `GUI_ONLY` for state helpers.
- Missing code: complete end-user Add/Import flow that hides batch JSON details and accepts source files, URLs, and existing folders through explicit review.
- Suggested implementation files: `main.py`, `profile_media_database_gui_controller.py`, `profile_media_database_workbench_panel.py`, `profile_media_database_gui_state_store.py`.
- Suggested tests: `profile_media_database_gui_panel_main_test.py`, `profile_media_database_ui_rethink_main_test.py`.
- Risk/safety note: importing must remain preview-first and must not silently move/copy user evidence.

## Gap 5: WARC/WACZ Replay Verification

- Current status: `PARTIAL`, `NEEDS_MANUAL_REVIEW`.
- Missing code: automated replay smoke verification for generated WARC/WACZ artifacts that can distinguish generated, listed, resource-loadable, visually partial, and visually verified.
- Suggested implementation files: `source_local_web_archive_actions.py`, `source_local_web_archive_repair_cli.py`, `source_msn_live_viewable_capture_cli.py`.
- Suggested tests: `source_local_web_archive_actions_test.py`, `source_msn_live_viewable_capture_test.py`.
- Risk/safety note: do not claim full replay success from artifact generation alone. Use local files/fake fixtures unless operator approves live/manual replay.

## Gap 6: Cross-Adapter Source Evidence To Profile/Media HOME Bridge

- Current status: `PARTIAL`.
- Missing code: direct bridge from Source Evidence/Twitter/MSN/YouTube capture outputs into Profile/Media HOME review items.
- Suggested implementation files: `source_evidence_workflow_state.py`, `profile_media_source_intake.py`, `profile_media_database_gui_controller.py`, new `profile_media_source_evidence_bridge.py`.
- Suggested tests: `profile_media_source_evidence_bridge_test.py`.
- Risk/safety note: role assignment must stay claim-level and reviewable; repeated reports must not be promoted to primary/original source automatically.

## Gap 7: Twitter/X Completeness And Live Capture Semantics

- Current status: `PARTIAL`, `NEEDS_MANUAL_REVIEW`.
- Missing code: product-level success gates for complete X/Twitter post/thread/profile captures under current platform behavior.
- Suggested implementation files: `twitter_browser_capture_runner.py`, `twitter_timeline_cursor_scheduler.py`, `source_twitter_compact_row.py`.
- Suggested tests: browser fixture tests and fake-HAR cursor tests.
- Risk/safety note: avoid credentials/cookies leakage; redact sensitive headers; rate limits and session validity require operator review.

## Gap 8: MSN Live Adapter Success Criteria Regression Pack

- Current status: `PARTIAL`, `NEEDS_MANUAL_REVIEW`.
- Missing code: one small acceptance runner that proves current MSN York closeout with expected counts/media/screenshots/archive status in the production adapter without relying on older manual zip references.
- Suggested implementation files: `msn_source_adapter.py`, `source_msn_adapter_acceptance_suite.py`.
- Suggested tests: `msn_source_adapter_test.py`, `source_msn_adapter_acceptance_suite_test.py`.
- Risk/safety note: live MSN network/browser use must be explicit and side-by-side; old accepted captures must not be overwritten.

## Gap 9: ASR Runtime Environment Proof

- Current status: `PARTIAL`.
- Missing code: consolidated environment proof that links local ASR binary readiness, preferred profile, and a non-secret online ASR readiness summary to GUI state.
- Suggested implementation files: `asr_whispercpp.py`, `local_asr_capabilities.py`, `online_asr_execution_gate.py`, `access_online_asr_bridge.py`.
- Suggested tests: existing ASR readiness tests plus one GUI state integration test.
- Risk/safety note: do not run ASR or provider jobs unless explicitly requested; do not read credentials.

## Gap 10: Documentation Sprawl Cleanup

- Current status: `DOCUMENTED_ONLY` overload.
- Missing code/docs: a stable index distinguishing current docs from superseded runbooks and old milestone handoffs.
- Suggested implementation files: documentation only; optionally extend `tools/run_project_capabilities_audit_cli_v76m.py`.
- Suggested tests: `project_capabilities_audit_v76m_test.py`.
- Risk/safety note: avoid deleting old docs without a separate archival plan; this patch only adds an index.
