# ASR Reporting Current State

Date: 2026-07-10

Branch: `v2.6.0-asr-engines`

Latest expected checkpoint when this document was added:

```text
a1d9d36 Add ASR decision summary CLI
2af464a Add ASR term coverage summary CLI
f30c7d5 Add ASR term coverage summary report
6cede20 Add ASR decision summary report
a5cfe85 Add cross-project current-state handoff
```

## Purpose

This document is the local ASR reporting handoff/index for the manual comparison, decision, and term-coverage reporting stack.

It records what exists, how the helpers/CLIs fit together, what they are allowed to do, and which local tests verify them. It is documentation only.

## Hard Boundaries

The ASR reporting helpers and CLIs are local/manual-data-only tools.

They must not:

- run ASR,
- call providers,
- transcribe media,
- fetch or download media,
- fetch source URLs,
- use network/API/archive services,
- scrape pages,
- capture screenshots,
- store credentials or secrets,
- inspect or extract ZIPs,
- wire into the GUI,
- modify runtime ASR/extractor/export behavior.

They only transform manually entered comparison records into deterministic local reports.

## Current Reporting Stack

| Layer | Main file | CLI | Test files | Purpose |
| --- | --- | --- | --- | --- |
| Comparison records | `asr_comparison_report.py` | `asr_comparison_report_cli.py` | `asr_comparison_report_test.py`, `asr_comparison_report_cli_test.py`, `asr_manual_results_seed_test.py` | Manual provider/model records, ranking metrics, WER/reference accuracy, key-term fields, known phrase, cost/latency notes, and statuses. |
| Decision summary | `asr_decision_summary.py` | `asr_decision_summary_cli.py` | `asr_decision_summary_test.py`, `asr_decision_summary_cli_test.py` | 95% gate, status counts, best project-scored/local rows, blocked/external-lead safeguards, warnings, and safe next action. |
| Term coverage | `asr_term_coverage_summary.py` | `asr_term_coverage_summary_cli.py` | `asr_term_coverage_summary_test.py`, `asr_term_coverage_summary_cli_test.py` | Explicit key-term hit/miss patterns, known phrase counts, consistently missed/mixed terms, and provider/model gap labels. |
| Combined report | n/a | `asr_combined_report_cli.py` | `asr_combined_report_cli_test.py` | Renders comparison, decision summary, and term coverage together as Markdown, text, or JSON. |
| Manual seed | `ASR_MANUAL_RESULTS_SEED.json` | n/a | `asr_manual_results_seed_test.py` | Checked-in local/manual records for project results, blocked AWS state, rejected providers, and external/user-observation leads. |

## Current Seed Interpretation

The checked-in manual seed currently represents:

- 11 project-scored local/manual rows.
- 0 accepted providers/models.
- 1 blocked provider row: AWS Transcribe custom vocabulary.
- 13 external leaderboard or user-observation lead rows.
- Leading project-scored result: ElevenLabs Scribe v2 with keyterms at 84.95%, still below the 95% gate.
- Leading local/offline result: whisper.cpp Vulkan large-v3-turbo phrase prompt at about 74.19%.
- Kingman, ZoneX, Freckelston, and Nyxara consistently missed across explicitly scored term rows.
- Nicolas Cage, Shadowsmith, and Caltheris have mixed hit/miss coverage.
- Known reference phrase is currently hit only by the ElevenLabs Scribe v2 with keyterms row.

These are manual reporting facts, not provider integrations.

## Manual Seed Metadata

`ASR_MANUAL_RESULTS_SEED.json` metadata now records the strict 95% gate, Term QA requirement, accepted/candidate/blocked/external-lead policy summaries, current leading project/local candidates, the AWS blocked note, and the local reporting CLIs. The metadata is descriptive only and does not change scoring, provider status, or runtime behavior.

## Provider Status Notes

`ASR_PROVIDER_STATUS_NOTES.md` clarifies provider/model status semantics for the current manual reporting stack. It keeps `accepted` reserved for future project-gated evidence, keeps AWS Transcribe custom vocabulary as `blocked` rather than quality-rejected, and keeps ElevenLabs Scribe v2 with keyterms as a below-threshold `candidate` rather than accepted.

## CLI Usage

Comparison report:

```cmd
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format markdown
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format json
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format markdown --output ASR_MANUAL_RESULTS_REPORT.md --overwrite
```

Decision summary:

```cmd
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format text
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format json
python asr_decision_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --output ASR_DECISION_SUMMARY_REPORT.md --overwrite
```

Term coverage summary:

```cmd
python asr_term_coverage_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json
python asr_term_coverage_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format text
python asr_term_coverage_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format json
python asr_term_coverage_summary_cli.py --input ASR_MANUAL_RESULTS_SEED.json --output ASR_TERM_COVERAGE_REPORT.md --overwrite
```

Combined report:

```cmd
python asr_combined_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json
python asr_combined_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format text
python asr_combined_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format json
python asr_combined_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --output ASR_COMBINED_REPORT.md --overwrite
```

All CLIs print to stdout by default. They write only when `--output` is explicitly supplied and preserve existing output unless `--overwrite` is used.

## Local Verification

Run from Windows CMD with the project virtual environment active.

```cmd
python -m py_compile asr_comparison_report.py asr_comparison_report_test.py asr_comparison_report_cli.py asr_comparison_report_cli_test.py asr_manual_results_seed_test.py asr_decision_summary.py asr_decision_summary_test.py asr_decision_summary_cli.py asr_decision_summary_cli_test.py asr_term_coverage_summary.py asr_term_coverage_summary_test.py asr_term_coverage_summary_cli.py asr_term_coverage_summary_cli_test.py asr_combined_report_cli.py asr_combined_report_cli_test.py & python asr_comparison_report_test.py & python asr_comparison_report_cli_test.py & python asr_manual_results_seed_test.py & python asr_decision_summary_test.py & python asr_decision_summary_cli_test.py & python asr_term_coverage_summary_test.py & python asr_term_coverage_summary_cli_test.py & python asr_combined_report_cli_test.py
```

Final repository checks:

```cmd
git diff --check & git status --short
```

## Safe Next Milestones

1. Stop and prepare a new cross-project handoff if the session becomes slow.

Do not start networked ASR/provider/downloader/archive behavior unless separately approved later with explicit opt-in and local/mocked tests.
