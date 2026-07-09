# ASR Provider Leaderboard Notes

Date: 2026-07-10

## Scope

This file preserves user-supplied ASR/STT research leads, leaderboard notes, and possible offline/model leads for later comparison planning.

This is a research-notes document only. It does not independently verify external leaderboard claims, does not call providers, does not add provider integration, and does not change current ASR behavior.

Local project status statements are grounded in the existing repo docs/state files, especially `ASR_TEST_PLAN.md`, `CURRENT_DEV_STATE.md`, and `asr_provider_metadata.py`.

## Why External Leaderboards Can Contradict Local Project Results

External ASR/STT leaderboards can be useful leads, but they may not predict this project's real clip performance because:

- Datasets differ from the project reference clips.
- Raw WER and formatted WER can rank systems differently.
- Punctuation, casing, paragraphing, speaker labels, and disfluency formatting can change measured output.
- Accents, background noise, overlapping speech, and specialist vocabulary affect systems differently.
- Proper nouns and glossary terms matter heavily here: `Kingman`, `ZoneX`, `Shadowsmith`, `Nicolas Cage`, `Freckelston`, `Caltheris`, and `Nyxara`.
- Streaming and non-streaming products may use different models, defaults, or latency/quality tradeoffs.
- Cost, quota, latency, and rate limits matter even when WER is strong.
- Diarization, timestamps, and transcript formatting quality are not fully captured by plain WER.
- Benchmarks age quickly because provider models and pricing change.

For this project, any future provider/model still needs the same strict reference scoring, important-term checks, Term QA/glossary review, and explicit user approval before integration.

## User-Supplied Leaderboard And Benchmark Links

These links are research leads supplied by the user, not independently verified facts in this repo:

- `https://voicewriter.io/speech-recognition-leaderboard`
- `https://artificialanalysis.ai/speech-to-text/non-streaming`
- `https://huggingface.co/spaces/hf-audio/open_asr_leaderboard`
- `https://www.braintrust.dev/blog/voice-evals-stt`
  - User noted this article was made about 3 days before their message.
- Reddit discussion:
  - `https://www.reddit.com/r/speechtech/comments/1kd9abp/i_benchmarked_12_speechtotext_apis_under_various/`

## User-Supplied Voicewriter Numbers

These Voicewriter leaderboard values are preserved as user-supplied notes. They should be rechecked before being used for product decisions.

Raw WER:

| Category | User-supplied leader |
| --- | --- |
| Overall | GPT-4o Transcribe [Mean 5.4%, Std Dev 4.6%, $0.36 per hour] |
| Clean | GPT-4o Transcribe [Mean 5.5%, Std Dev 4.9%, $0.36 per hour] |
| Noisy | GPT-4o Transcribe [Mean 5.8%, Std dev 4.5%, $0.36 per hour] |
| Accented | Gemini 2.5 Pro [Mean 4.0%, Std Dev 2.5%, $0.22 per hour] |
| Specialist | GPT-4o Transcribe [Mean 5.3%, Std Dev 6.2%, $0.36 per hour] |

Formatted WER:

| Category | User-supplied leader |
| --- | --- |
| Overall | GPT-4o Transcribe [Mean 12.2%, Std Dev 4.8%, $0.36 per hour] |
| Clean | GPT-4o Transcribe [Mean 13.5%, Std Dev 5.0%, $0.36 per hour] |
| Noisy | GPT-4o Transcribe [Mean 14.2%, Std Dev 5.0%, $0.36 per hour] |
| Accented | Gemini 2.5 Pro [Mean 12.4%, Std Dev 4.4%, $0.22 per hour] |
| Specialist | GPT-4o Transcribe [Mean 7.9%, Std Dev 0.8%, $0.36 per hour] |

## Local Project ASR Snapshot

Known ASR test terms:

- `Kingman`
- `ZoneX`
- `Shadowsmith`
- `Nicolas Cage`
- `Freckelston`
- `Caltheris`
- `Nyxara`

Known reference phrase:

- `Oh, I've completed the Nicolas Cage event.`

Best tested cloud result so far:

- ElevenLabs Scribe v2 with keyterms: 84.95% strict 30s reference accuracy.
- It preserved the key phrase around `Oh I've completed the Nicolas Cage event`.
- It found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`.
- It still missed `Kingman`, `ZoneX`, `Freckelston`, and `Nyxara`.
- It remains a leading optional cloud integration candidate, not final truth.

Best tested local/free result so far:

- whisper.cpp Vulkan large-v3-turbo with phrase prompt: about 74.19% strict 30s reference accuracy.
- This remains the best no-cloud/free local fallback currently recorded.

Blocked but not rejected:

- AWS Transcribe custom vocabulary.
- It was blocked by `SubscriptionRequiredException` in `eu-west-2` / Europe London before any transcript or score was produced.
- It should not be ranked against tested providers.

Rejected or lower-ranked manual provider results:

| Provider/config | Strict reference accuracy |
| --- | ---: |
| AssemblyAI Universal-3.5 Pro default/prompted | 70.97% |
| Deepgram Nova-3 keyterms | 66.67% |
| Speechmatics enhanced custom dictionary | 65.59% |
| Azure Speech SDK phrase list | 64.52% |
| Google STT video enhanced phrases | 61.29% |
| Cohere Transcribe 03-2026 | 58.06% |
| Google STT latest_long phrases | 50.54% |

Project policy:

- ASR output remains draft unless quality and term checks pass.
- Term QA/glossary review is mandatory.
- No ASR provider should be wired into the GUI or core export flow without explicit approval.

## Meta / Seamless / Instagram-Adjacent Leads

User observation:

- The user reported using Instagram's speech-to-text API and that it got most messages correct very fast.

Related user-supplied links:

- `https://seamless.metademolab.com/demo`
- `https://www.edenai.co/`
- `https://huggingface.co/docs/transformers/en/model_doc/seamless_m4t_v2`

Caution:

- Treat this as a research lead only.
- Do not claim what Instagram production uses unless a reliable source is added later.
- Meta Seamless / SeamlessM4T v2 may be worth investigating for offline or research comparison, but it is not currently integrated or validated for this project.

## Provider And Model Leads To Investigate Later

Cloud/provider leads:

- GPT-4o Transcribe.
- Gemini 2.5 Pro.
- Meta Seamless / SeamlessM4T v2 / Instagram-adjacent STT observation.
- Groq-backed workflows, including VillFlowSTT.
- Witsy.
- Kolwrite.
- Eden AI as an aggregator lead.

Benchmark/reference leads:

- Voicewriter speech-recognition leaderboard.
- Artificial Analysis non-streaming speech-to-text leaderboard.
- Hugging Face Open ASR leaderboard.
- Braintrust voice evals article.
- Reddit benchmark discussion.

Local/offline/browser/STT leads supplied by the user:

- `https://github.com/lucky-bai/wasm-speech-streaming`
- `https://huggingface.co/spaces/efficient-nlp/wasm-streaming-speech`
- `https://github.com/lucky-bai/moshi`
- `https://github.com/lucky-bai/transformers`
- `https://github.com/Kochava-Studios/witsy`
- `https://console.kolwrite.com/`
- `https://github.com/SreekarGpalli/VillFlowSTT/releases`

User-supplied Reddit quote for VillFlowSTT:

> I kept running out of speech-to-text free trials, so I built my own Windows dictation tool powered by Groq. It's open source and free to use. Would love your feedback (and a star if you find it useful): https://github.com/SreekarGpalli/VillFlowSTT/releases

Preserve VillFlowSTT as a lead only. It is not a validated dependency or project integration.

## Candidate Future Test Design

Future comparison notes should separate:

- Raw WER.
- Formatted WER.
- Strict project reference accuracy.
- Important-term hit rate.
- Critical phrase recovery.
- Candidate word count and truncation checks.
- Hallucination/deletion checks.
- Latency per audio minute.
- Cost per audio hour.
- Quota/rate-limit constraints.
- Privacy mode: local/offline vs cloud.
- Custom vocabulary/keyterm/prompt support.
- Local/offline feasibility and hardware requirements.

Suggested repeatable local comparison workflow:

1. Use the same known 15s/30s project reference clips.
2. Normalize transcript outputs into a common scoring format.
3. Score with the strict reference-window scorer.
4. Record raw transcript previews and candidate word counts.
5. Record important-term checks for `Kingman`, `ZoneX`, `Shadowsmith`, `Nicolas Cage`, `Freckelston`, `Caltheris`, and `Nyxara`.
6. Record whether `Oh, I've completed the Nicolas Cage event.` is recovered.
7. Keep all provider comparison manual until a provider clearly beats existing local/cloud baselines and is explicitly approved.

## Recommended Future Milestone

Recommended next ASR docs/tooling step:

- Create a local-only ASR comparison report/table format.
- It should record WER, strict reference accuracy, important-term checks, latency, cost notes, privacy mode, and provider/model configuration.
- It should not call providers.
- It should not add credentials.
- It should not wire any provider into the app.

Later optional provider adapters must remain:

- Explicitly opt-in.
- Separated from deterministic local tests.
- Cost/quota/API-key aware.
- Draft-output only unless strict quality gates pass.
