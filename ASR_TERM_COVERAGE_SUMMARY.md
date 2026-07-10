# ASR Term Coverage / Gap Summary Report

Date: 2026-07-10

## Purpose

`asr_term_coverage_summary.py` turns existing `ASRComparisonRecord` objects into a concise, deterministic glossary/key-term coverage report.

It summarizes project-scored term hits and misses, consistently missed terms, mixed terms, known-phrase performance, and provider/model-specific gaps.

## Local Manual-Data-Only Scope

The helper consumes in-memory comparison records only. It does not load media, run ASR, call providers, transcribe, fetch URLs, download files, use network/API/archive services, scrape pages, capture screenshots, store credentials, inspect ZIPs, or wire into the GUI.

The helper writes no files and creates no generated report artifacts. A future CLI requires separate approval and must preserve explicit-output-only behavior.

## Inclusion Rules

- Main term coverage uses project-scored local/manual comparison rows.
- Blocked rows are excluded from term hit/miss rates because they have no comparable transcript score.
- External leaderboard and user-observation leads remain research leads unless separately represented as project-scored records.
- A term is counted only when it is explicitly listed in `key_terms_hit` or `key_terms_missed`.
- The helper does not infer hits or misses from transcripts.
- Aggregate keyterm counts without explicit term names are not used for per-term tables.

## Current Seed Interpretation

For the checked-in `ASR_MANUAL_RESULTS_SEED.json`:

- There are 11 project-scored rows.
- AWS Transcribe remains blocked and excluded from term rates.
- External leaderboard and user-observation rows remain informational leads.
- Kingman, ZoneX, Freckelston, and Nyxara are consistently missed in the explicitly scored term records.
- Nicolas Cage, Shadowsmith, and Caltheris have mixed hit/miss coverage.
- The known reference phrase is hit only by the ElevenLabs Scribe v2 with keyterms row in the current scored seed.

ASR output therefore remains draft text with Term QA/glossary review and explicit user review.

## Report Functions

- `build_asr_term_coverage_summary()`
- `asr_term_coverage_item_to_dict()`
- `asr_term_coverage_summary_to_dict()`
- `build_asr_term_coverage_summary_text()`
- `build_asr_term_coverage_summary_markdown()`

Dictionary output has deterministic keys suitable for a future local-only CLI or report writer.

## Safety Notes

- Do not infer provider acceptance from term coverage alone.
- Do not treat blocked rows as rejected term failures.
- Do not let external leaderboard leads override project-specific Term QA.
- Do not add provider calls, transcription, downloads, network/API/archive behavior, scraping, screenshots, credentials, ZIP extraction, or GUI wiring through this report helper.
