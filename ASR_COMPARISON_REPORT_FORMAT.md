# ASR Comparison Report Format

Date: 2026-07-10

## Scope

This document describes the local-only ASR comparison report skeleton in `asr_comparison_report.py`.

The format is for manually recording provider/model results from local tests, external leaderboard notes, or user observations. It does not call providers, run transcription, fetch media, store credentials, or wire any ASR provider into the app.

See `ASR_REPORTING_CURRENT_STATE.md` for the current local ASR reporting helper/CLI/test index and safe next milestones.

See `ASR_PROVIDER_STATUS_NOTES.md` for accepted/candidate/rejected/blocked/needs-review semantics and current provider status handling.

## Purpose

External ASR leaderboards can highlight useful candidates, but the project still needs project-specific comparison records because the reference clips contain important names, lore terms, and a known phrase that plain WER may not protect.

The report format keeps these separate:

- External leaderboard metrics.
- Local/manual project reference scores.
- Keyterm hit/miss results.
- Known phrase recovery.
- Cost, latency, and privacy notes.
- Blocked/rejected/candidate status.

## Local Project Key Terms

Default key terms are:

- `Kingman`
- `ZoneX`
- `Shadowsmith`
- `Nicolas Cage`
- `Freckelston`
- `Caltheris`
- `Nyxara`

Known reference phrase:

- `Oh, I've completed the Nicolas Cage event.`

## Record Fields

Manual records can include:

- `provider`: Provider or tool name.
- `model`: Model/config name.
- `engine_type`: `local`, `cloud`, `offline`, `browser`, or `unknown`.
- `source`: `local_test`, `external_leaderboard`, `user_observation`, `manual`, or `unknown`.
- `clip_name`: Reference clip or benchmark source label.
- `duration_seconds`: Audio duration when known.
- `raw_wer_percent`: Raw WER from local test or external source.
- `formatted_wer_percent`: Formatted WER when reported separately.
- `reference_accuracy_percent`: Project strict-reference accuracy when available.
- `cost_per_hour_usd`: Manual cost note when known.
- `latency_seconds`: Manual latency note when known.
- `key_terms_expected`: Terms expected for the test.
- `key_terms_hit`: Important terms recovered.
- `key_terms_missed`: Important terms missed.
- `known_phrase_expected`: Expected phrase.
- `known_phrase_hit`: Whether the known phrase was recovered.
- `status`: `accepted`, `rejected`, `blocked`, `candidate`, `needs_review`, or another explicit local status.
- `notes`: Short explanation, limitation, or source note.

Records are intentionally tolerant of missing fields because many external leaderboard leads do not provide project-specific accuracy, keyterm checks, or phrase checks.

`ASR_MANUAL_RESULTS_SEED.json` metadata may also include descriptive local policy fields such as the 95% gate, Term QA requirement, status-policy notes, leading candidate labels, blocked-provider notes, and reporting CLI names. These metadata fields are documentation for local reporting and do not call providers or change runtime behavior.

## Raw WER vs Formatted WER

Raw WER and formatted WER must be recorded separately when both are available.

Raw WER may ignore formatting differences, while formatted WER can include punctuation, casing, paragraphing, disfluencies, and display choices. A model can rank differently depending on which measure is used.

## Cost And Latency

Cost and latency are manual notes only in this skeleton.

Use `cost_per_hour_usd` only when a source or local calculation gives a clear value. Use `latency_seconds` only when the timing is known for the recorded clip/run. Do not infer current provider pricing from old notes without later verification.

## Provider Status

Suggested status values:

- `candidate`: promising but not final.
- `rejected`: tested and unsuitable for current workflow.
- `blocked`: no quality score because access/config/account state blocked the test.
- `accepted`: reserved for a future provider/model that passes the project gate.
- `needs_review`: external or incomplete lead requiring later testing.

AWS Transcribe custom vocabulary is currently `blocked`, not rejected, because no transcript score was produced.

## External Leaderboards

External leaderboard rows should usually use:

- `source`: `external_leaderboard`
- WER fields if supplied.
- Empty `reference_accuracy_percent` unless the model was scored on the project reference clip.
- Notes that identify the leaderboard/source and that the row is not locally verified.

Do not let external leaderboard rank override strict local reference scoring or Term QA results.

## Draft ASR Policy

ASR output remains draft text unless strict quality gates and Term QA/glossary review pass.

Even the current leading cloud candidate, ElevenLabs Scribe v2 with keyterms at 84.95% strict reference accuracy, missed `Kingman`, `ZoneX`, `Freckelston`, and `Nyxara`. Manual review remains required.

## Local CLI

`asr_comparison_report_cli.py` renders manually entered JSON records as text, Markdown, or JSON.

Examples:

```cmd
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format markdown
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format json
python asr_comparison_report_cli.py --input ASR_MANUAL_RESULTS_SEED.json --format markdown --output ASR_MANUAL_RESULTS_REPORT.md --overwrite
```

Supported ranking metrics are `reference_accuracy_percent`, `raw_wer_percent`, `formatted_wer_percent`, `cost_per_hour_usd`, and `latency_seconds`.

The CLI is local-only. It reads manually entered JSON records and writes a file only when `--output` is provided. It does not call providers, run transcription, fetch media, store credentials, or wire any ASR provider into the app.

`asr_combined_report_cli.py` renders comparison, decision summary, and term coverage sections together from the same local/manual input. It also writes only with explicit `--output` and does not call providers, run transcription, fetch media, store credentials, inspect ZIPs, or wire into the GUI.

## Decision Summary

`asr_decision_summary.py` provides a local/manual-data-only decision layer over existing comparison records. It summarizes the 95% project gate, status counts, leading project-scored and local/offline results, blocked items, external leads, below-threshold candidates, warnings, and safe next-action guidance.

See `ASR_DECISION_SUMMARY.md` for status semantics, current seed interpretation, and CLI usage. The helper writes no files; `asr_decision_summary_cli.py` writes only when `--output` is supplied. Neither the helper nor CLI calls providers, runs transcription, fetches/downloads media, uses network APIs, stores credentials, inspects ZIPs, or wires into the GUI.

## Term Coverage Summary

`asr_term_coverage_summary.py` provides a local/manual-data-only term coverage layer over existing comparison records. It summarizes explicitly recorded key-term hits and misses, consistently missed terms, mixed terms, known-phrase performance, blocked-row exclusions, external-lead limitations, and provider/model-specific gaps.

See `ASR_TERM_COVERAGE_SUMMARY.md` for inclusion rules, current seed interpretation, and CLI usage. The helper writes no files; `asr_term_coverage_summary_cli.py` writes only when `--output` is supplied. Neither the helper nor CLI calls providers, runs transcription, fetches/downloads media, uses network APIs, stores credentials, inspects ZIPs, or wires into the GUI.

## Future Use

Future milestones may add:

- An explicit-output-only CLI for the decision summary.
- A local term coverage/gap summary over manual comparison records.
- Additional local/manual seed or report-format improvements.

Those future steps should remain local-only unless provider integrations are explicitly approved later.
