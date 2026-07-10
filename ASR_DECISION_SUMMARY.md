# ASR Decision Summary Report

Date: 2026-07-10

## Purpose

`asr_decision_summary.py` turns existing `ASRComparisonRecord` objects into a concise, deterministic acceptance/decision summary.

It reports the current strict threshold, status counts, best project-scored and local/offline results, below-threshold candidates, blocked items, external research leads, warnings, and a safe next action.

## Local Manual-Data-Only Scope

The helper consumes in-memory comparison records only. It does not load media, run ASR, call providers, transcribe, fetch URLs, download files, use network/API/archive services, scrape pages, capture screenshots, store credentials, inspect ZIPs, or wire into the GUI.

The helper writes no files and creates no generated report artifacts. The CLI writes only when `--output` is explicitly supplied and preserves existing files unless `--overwrite` is used.

## Strict Threshold

The default project acceptance threshold is 95% strict reference accuracy.

Project-specific scoring and Term QA take priority over external leaderboard rankings. A result below the threshold remains draft/not final truth even when it is the strongest tested candidate.

## Status Semantics

- `accepted`: A provider/model explicitly marked accepted and backed by project-specific evidence at or above the gate.
- `candidate`: Worth considering or retesting, but not accepted.
- `rejected`: Tested and not currently suitable for integration.
- `blocked`: No comparable quality result because access, subscription, configuration, or another blocker prevented scoring. Blocked is not quality-rejected.
- `needs_review`: An external or incomplete lead requiring later local/manual review.

External leaderboard and user-observation records are counted as research leads based on their source metadata. They may overlap candidate/needs-review status counts, but they are not accepted providers and are excluded from project-score ranking unless separately represented as project-specific scored records.

## Current Seed Interpretation

For the checked-in `ASR_MANUAL_RESULTS_SEED.json`:

- No record is accepted.
- ElevenLabs Scribe v2 with keyterms is the best project-scored result at 84.95%, below the 95% gate.
- whisper.cpp Vulkan large-v3-turbo with phrase prompt is the best local/offline result at about 74.19%.
- AWS Transcribe custom vocabulary is blocked without a quality score and must not be ranked as rejected.
- External leaderboard/user-observation rows remain informational leads.

ASR output therefore remains draft text with Term QA/glossary review and explicit user review.

## Report Functions

- `build_asr_decision_summary()`
- `asr_decision_summary_to_dict()`
- `build_asr_decision_summary_text()`
- `build_asr_decision_summary_markdown()`

Dictionary output has deterministic keys suitable for a future local-only CLI or report writer.

## Local CLI Usage

`asr_decision_summary_cli.py` reads manually entered ASR comparison JSON records, builds the local decision summary, and renders Markdown, text, or JSON.

```cmd
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format text
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format json
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --output ASR_DECISION_SUMMARY_REPORT.md
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --output ASR_DECISION_SUMMARY_REPORT.md --overwrite
```

The CLI supports the checked-in seed object shape with a `records` list and a bare list of record objects. It prints to stdout by default, writes a file only with `--output`, and refuses to overwrite existing output unless `--overwrite` is supplied.

The CLI does not run ASR, call providers, transcribe media, fetch/download sources, use network/API/archive services, scrape pages, capture screenshots, store credentials, inspect ZIPs, or wire into the GUI.

## Related Term Coverage Summary

The decision summary and term coverage summary answer different local questions. `asr_decision_summary.py` summarizes provider/model status, ranking, and safe next-action guidance. `asr_term_coverage_summary.py` summarizes manually recorded glossary/key-term hits, misses, known-phrase performance, and provider gaps.

Term coverage can guide retesting and manual review, but it does not by itself accept a provider or override the 95% project gate.

## Safety Notes

- Do not infer provider acceptance from leaderboard placement.
- Do not treat candidate as accepted.
- Do not treat blocked as rejected.
- Do not add provider calls, transcription, downloads, network/API/archive behavior, scraping, screenshots, credentials, ZIP extraction, or GUI wiring through this report helper.
