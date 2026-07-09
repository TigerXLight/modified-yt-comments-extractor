# ASR Manual Results Seed

Date: 2026-07-10

## Scope

`ASR_MANUAL_RESULTS_SEED.json` preserves manually entered ASR comparison records for known project-specific results and user-supplied external research leads.

This seed is local-only data. It does not call ASR providers, run transcription, fetch media, store credentials, include transcripts, include audio, or wire any provider into the GUI or export flow.

## What Is Included

- Project-specific manual results from the strict 30s reference scoring pass.
- Blocked provider status where no transcript score exists, such as AWS Transcribe custom vocabulary.
- Rejected/lower provider results that should not be mistaken for integration candidates.
- User-supplied external leaderboard leads for GPT-4o Transcribe, Gemini 2.5 Pro, and other research candidates.
- User-observation leads such as Meta/Seamless/Instagram-adjacent STT and Groq/VillFlowSTT.

## Current Local Ranking Snapshot

- Leading optional cloud candidate: ElevenLabs Scribe v2 with keyterms at 84.95% strict reference accuracy.
- Best no-cloud/free local fallback: whisper.cpp Vulkan large-v3-turbo with phrase prompt at about 74.19% strict reference accuracy.
- AWS Transcribe custom vocabulary is blocked, not rejected, because `SubscriptionRequiredException` prevented any transcript or score.
- Other tested providers remain rejected for integration for now because they did not beat the local baseline or preserve the critical phrase and key terms well enough.

## Draft-ASR Policy

ASR output remains draft text unless strict quality gates and Term QA/glossary review pass.

Even the current leading cloud candidate missed `Kingman`, `ZoneX`, `Freckelston`, and `Nyxara`, so manual review remains required.

## Safety Notes

- External leaderboard records are leads only.
- External records do not override project-specific strict reference scoring.
- This seed must not contain API keys, endpoints, transcripts, audio files, or provider-call logic.
- Future behavior changes must remain explicit, opt-in, and locally/mocked tested before any provider integration.
