# ASR Provider Status Notes

Date: 2026-07-10

Branch: `v2.6.0-asr-engines`

## Purpose

This document is a docs-only status clarification for ASR provider/model records in the local manual reporting stack.

It helps prevent future sessions from confusing:

- `accepted`,
- `candidate`,
- `rejected`,
- `blocked`,
- `needs_review`,
- external leaderboard leads,
- user-observation leads.

It does not implement provider behavior and does not change ASR runtime behavior.

## Scope And Boundaries

This document is local/manual reporting guidance only.

It does not:

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
- modify extractor/export/ASR runtime behavior.

## Status Semantics

| Status | Meaning | Current handling |
| --- | --- | --- |
| `accepted` | A future provider/model explicitly accepted after project-specific evidence meets the strict gate and Term QA/user review requirements. | No current seed record is accepted. |
| `candidate` | Worth considering, retesting, or preserving as a lead, but not accepted. | ElevenLabs and several user-observation leads are candidates. |
| `rejected` | Tested on the project clip and unsuitable for integration for now. | Lower-scoring project-tested cloud/local rows remain rejected for now. |
| `blocked` | No comparable quality score exists because access, subscription, configuration, or another blocker prevented scoring. | AWS Transcribe custom vocabulary is blocked, not rejected. |
| `needs_review` | External or incomplete lead requiring future local/manual review. | External leaderboard rows remain needs-review unless project-scored later. |

## Current Project Gate

The strict project acceptance threshold remains 95% project-reference accuracy.

A provider/model below the gate is not accepted even if it is the best current candidate.

Term QA and explicit user review remain required because WER/reference accuracy can hide failures on names, lore terms, and known phrases.

## Current Seed Status

Current local/manual seed interpretation:

- Accepted: none.
- Leading project-scored cloud candidate: ElevenLabs Scribe v2 with keyterms at 84.95%.
- Leading project-scored local/offline result: whisper.cpp Vulkan large-v3-turbo phrase prompt at about 74.19%.
- AWS Transcribe custom vocabulary: blocked before scoring by `SubscriptionRequiredException`; do not rank it as quality-rejected.
- External leaderboard and user-observation rows: research leads only; do not treat them as project-scored acceptance evidence.

## Provider Notes

### ElevenLabs Scribe v2 with keyterms

Current status: `candidate`.

Why:

- It is the leading project-scored cloud candidate in the checked-in seed.
- It remains below the 95% strict project gate.
- It recovered the known Nicolas Cage phrase in the current seed.
- It still missed important key terms including Kingman, ZoneX, Freckelston, and Nyxara.

Handling:

- Preserve as a leading optional candidate.
- Do not call it accepted.
- Do not silently use it as final truth.
- Require Term QA and user review.

### whisper.cpp Vulkan large-v3-turbo phrase prompt

Current status: `candidate`.

Why:

- It is the leading local/no-cloud result in the checked-in seed.
- It remains below the 95% strict project gate.
- It is useful as a local/offline fallback but not accepted for final transcript trust.

Handling:

- Preserve for local/offline workflows where appropriate.
- Keep ASR output as draft.
- Require Term QA and user review.

### AWS Transcribe custom vocabulary

Current status: `blocked`.

Why:

- The transcription job did not produce a comparable quality result.
- Access/subscription state blocked testing before scoring.

Handling:

- Do not call AWS rejected on quality.
- Do not rank it against scored providers.
- Keep it as blocked unless a later approved test produces a transcript and score.

### Rejected project-tested providers

Current status: `rejected` for integration for now.

Includes currently recorded lower-scoring project rows such as:

- AssemblyAI Universal-3.5 Pro default/prompted,
- Deepgram Nova-3 keyterms,
- Speechmatics enhanced custom dictionary,
- Azure Speech SDK phrase list,
- Google Speech-to-Text phrase hints,
- Cohere Transcribe 03-2026.

Handling:

- Keep the records for comparison.
- Do not reclassify without new project-specific evidence.
- Do not remove because they explain why the current candidate/fallback decisions were made.

### External leaderboard and user-observation leads

Current status: usually `needs_review` or `candidate` depending on the seed row.

Handling:

- Preserve as research leads only.
- Do not rank them above project-scored rows unless they are separately tested on the project reference clip.
- Do not infer current pricing/specs from old notes without later verification.
- Do not integrate them without a separate provider milestone and local/mocked tests.

## Safe Update Rules

Future edits to provider status should:

1. Keep `accepted` reserved for evidence that meets the project gate.
2. Keep `blocked` distinct from `rejected`.
3. Keep external leaderboard rows distinct from project-scored rows.
4. Preserve notes explaining why each provider is classified.
5. Avoid changing ASR runtime behavior under docs/reporting milestones.
6. Avoid adding secrets, transcripts, API calls, downloads, or generated artifacts to status docs.

## Related Files

- `ASR_REPORTING_CURRENT_STATE.md`
- `ASR_COMPARISON_REPORT_FORMAT.md`
- `ASR_DECISION_SUMMARY.md`
- `ASR_TERM_COVERAGE_SUMMARY.md`
- `ASR_PROVIDER_LEADERBOARD_NOTES.md`
- `ASR_MANUAL_RESULTS_SEED.json`
- `ASR_MANUAL_RESULTS_SEED.md`
