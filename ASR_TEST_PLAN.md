# ASR Test Plan

Goal:
The app should run a short self-test/probe, compare practical ASR candidates, and choose the best available method by accuracy first.

Acceptance policy:
- Clear audio and normal/common words should be near-perfect.
- If common words are wrong, the method/settings are unsuitable.
- Rare words / names / game terms can use phrase hints or vocabulary packs.
- Do not auto-replace a good imported transcript when the probe fails threshold.
- Mark machine ASR output as draft unless it passes the quality gate.

Current candidates:
- faster-whisper CPU profiles.
- whisper.cpp Vulkan large-v3 phrase prompt.
- whisper.cpp Vulkan large-v3 unprompted.
- whisper.cpp Vulkan large-v3-turbo phrase prompt.
- whisper.cpp Vulkan large-v3-turbo terms-only.

Still to evaluate:
- Canary if a workable local path exists.
- Online transcription providers after local methods are assessed.
- DirectML medium/large are deferred and should only be tested if explicitly approved later.

Offline/hardware ASR profile planning:
- AMD Windows, older Radeon such as RX 5700:
  - Recommended local path: whisper.cpp Vulkan.
  - Keep local whisper.cpp Vulkan as the best no-cloud/free local baseline.
  - Best tested local/no-cloud result remains whisper.cpp Vulkan large-v3-turbo with phrase prompt at about 74.19% reference accuracy.
  - CPU/quantized whisper.cpp is fallback only.
  - DirectML is experimental/low-return based on local tests.
  - ROCm/PyTorch is not a reliable Windows path for this RX 5700/RDNA1 setup.
- NVIDIA Windows/Linux:
  - Recommended GPU paths:
    - faster-whisper / CTranslate2 CUDA.
    - whisper.cpp CUDA.
  - Advanced Linux/NVIDIA users may test NeMo/Parakeet/Canary-style models separately.
  - Do not make this the default for the current AMD test machine.
- Intel CPU / iGPU / Arc:
  - Recommended path: OpenVINO Whisper / Distil-Whisper-style route.
  - CPU fallback remains available.
  - This is a profile for Intel users, not tested on the current AMD RX 5700 machine.
- CPU-only:
  - Recommended path: whisper.cpp quantized models.
  - Use strict draft-only mode.
  - Expect slower speed and no guarantee of better accuracy.

Provider confidence / architecture notes:
- ElevenLabs Scribe v2 with keyterms is the leading optional cloud integration candidate after the provider confidence pass, at 84.95% reference accuracy.
- AWS Transcribe custom vocabulary is BLOCKED, not rejected, because no score was produced.
- Local ASR and cloud ASR should both be treated as draft text unless a strict quality gate passes.
- Term QA/glossary review remains mandatory for names and lore terms.
- whisper.cpp Vulkan remains the best free/local fallback.
- Hardware acceleration does not guarantee higher accuracy by itself. It mainly enables faster testing of larger models or better settings.
- Offline ASR is not fully exhausted globally, but the practical AMD paths tested so far are below the project acceptance threshold.
- DirectML medium/large remain deferred unless explicitly approved later.

YouTube URL ingestion and context/glossary pipeline planning:
- Phase 1 URL validation/normalization is implemented; later fetch/glossary/ASR phases are not implemented yet.
- Target pipeline:
  - YouTube URL.
  - Validate/normalize URL.
  - Extract video ID.
  - Fetch metadata where available.
  - Fetch existing captions/transcripts where available.
  - Fetch comments/livechat where available and user-selected.
  - Collect contextual text from metadata/comments/transcripts.
  - Optionally collect external background context later.
  - Extract candidate glossary/entities.
  - Let user review/edit glossary.
  - Pass glossary/keyterms into ASR providers that support it.
  - Run ASR as draft.
  - Run Term QA/glossary checks.
  - User reviews/accepts/edits final transcript.

Feature principles:
- Existing captions/transcripts should be preferred when available and acceptable.
- ASR should be used when no reliable transcript exists or when user requests it.
- Metadata/comments/context are for glossary discovery and QA, not a replacement for transcription.
- Metadata/comments/transcripts/external context are only used to propose glossary/entity candidates and QA warnings.
- External/background context is optional.
- External/background context must be strict-filtered.
- External/background context must never block local transcript/ASR work.
- External/background context must never be trusted as ground truth.
- No silent auto-correction of transcript terms.
- User must be able to review/edit glossary before it affects ASR or QA.
- User review remains required before glossary candidates affect ASR prompts/keyterms or final transcript decisions.
- Provider-specific glossary support should be optional:
  - ElevenLabs keyterms.
  - Deepgram keyterms.
  - Speechmatics custom dictionary.
  - Azure phrase list.
  - AWS custom vocabulary only if future access works.
  - whisper.cpp prompt/initial prompt.
- If a provider has no glossary support, glossary still feeds Term QA after transcription.
- Keep local/offline ASR available for privacy/no-cloud mode.
- Keep cloud ASR opt-in because of cost/privacy/API-key concerns.

Likely implementation phases:
1. URL validation and video ID extraction.
2. Metadata/transcript/comment fetch plumbing.
3. Context-to-glossary resolver.
4. Glossary review UI.
5. Provider keyterm/prompt mapping.
6. ASR run + Term QA review flow.
7. Evidence/debug export for transcript decisions.

## Parakeet local probe result — 2026-07-07

Completed:
- Tested whisper.cpp `parakeet-cli.exe` on AMD Vulkan.
- Tested q8_0 and f16 Parakeet TDT 0.6B v3 GGML models.
- Both ran successfully and very quickly.

Result:
- q8_0 strict 30s reference accuracy: 49.46%.
- f16 strict 30s reference accuracy: 47.31%.
- Both failed on important names and phrases.

Decision:
- Parakeet should not be added to the Auto Quality Probe candidate list for now.
- It can remain a future experimental engine, but the current project should prioritize stronger ASR methods.

## DirectML / TorchCodec feasibility result - 2026-07-07

Completed:
- Confirmed local ONNX Runtime DirectML availability through `DmlExecutionProvider`.
- Confirmed DirectML Whisper tiny.en ONNX export, load, and direct generation through `ORTModelForSpeechSeq2Seq`.
- Confirmed TorchCodec and the Transformers pipeline path work after registering the FFmpeg 7 shared DLL folder.

Result:
- DirectML tiny.en direct generation was fast but only reached about 49.46% strict 30s reference word accuracy.
- The result proves the DirectML runtime path can work locally, but tiny.en is too small to judge final quality for this workflow.

Runtime requirement:
- TorchCodec needs the FFmpeg 7 shared DLL folder registered before TorchCodec-related imports.
- Default local folder: `C:\ffmpeg-7-shared\bin`.
- Optional override: `ASR_FFMPEG7_SHARED_BIN`.
- `asr_runtime_paths.add_ffmpeg7_shared_dll_directory()` is available for experimental scripts and is not wired into the main app.

Decision:
- Do not add DirectML to the main UI or Auto Quality Probe yet.
- Next DirectML test should be an explicit experimental script using direct `AutoProcessor` plus `ORTModelForSpeechSeq2Seq.generate()` with `openai/whisper-base.en` and `openai/whisper-small.en`.

Manual runner:
- `RUN_DIRECTML_WHISPER_MATRIX.py` exists for manual DirectML ONNX comparison only.
- It tests `openai/whisper-base.en` and `openai/whisper-small.en` on the same strict 30s reference probe.
- It writes `DIRECTML_WHISPER_MATRIX_SUMMARY.txt`, which is a local ignored output.

Manual DirectML matrix result:
- The runner completed after fixing generation config. These are manual matrix results, not final ASR quality results.
- Provider: `DmlExecutionProvider`.
- `openai/whisper-small.en`: 58.06% strict 30s reference accuracy, 41.94% WER, 65 candidate words, 11.37s elapsed.
- `openai/whisper-base.en`: 55.91% strict 30s reference accuracy, 44.09% WER, 63 candidate words, 12.97s elapsed.
- Important failures:
  - `Shadowsmith` became `Shousemith` / `chat's missing`.
  - `Caltheris` became `Kalfirisk` / `Calfare, Wisconsin`.
  - `I've cleared the Nicolas Cage event` was not recovered correctly.
  - base.en produced `Miyas`.

Decision:
- Reject DirectML base.en and small.en for Auto Quality Probe for now.
- DirectML is technically viable on AMD Windows, but current base/small ONNX quality is below whisper.cpp Vulkan on this clip.
- Do not test medium/large DirectML models yet unless explicitly approved later.

Manual scoring helper:
- `RUN_TRANSCRIPT_REFERENCE_SCORE.py` exists for manual provider-agnostic transcript comparison.
- It scores offline or online transcript files against the same strict reference window without adding any provider integration.
- It writes `TRANSCRIPT_REFERENCE_SCORE_SUMMARY.txt`, which is a local ignored output.
- No new ASR/provider results are recorded by adding this helper.

AssemblyAI manual API transcript results:
- Default/no-context:
  - `speech_model_used`: `universal-3-5-pro`.
  - Input: `directml_probe_30s.wav`.
  - Candidate file: `candidate_assemblyai.txt`.
  - Reference scoring window: strict first 30s.
  - Reference words: 93.
  - Candidate words: 74.
  - WER: 29.03%.
  - Reference accuracy: 70.97%.
  - Important terms:
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Caltheris`: MISSING.
  - Important failures:
    - `I've cleared the Nicolas Cage event` was rendered as `it's weird, the Nicolas Cage event`.
    - `Caltheris` was rendered as `Calpheon`.
- Prompted/keyterms:
  - `speech_model_used`: `universal-3-5-pro`.
  - `keyterms_prompt` accepted:
    - `Kingman`
    - `ZoneX`
    - `Shadowsmith`
    - `Nicolas Cage`
    - `Freckelston`
    - `Caltheris`
    - `Nyxara`
  - Candidate file: `candidate_assemblyai_prompted.txt`.
  - Reference scoring window: strict first 30s.
  - Reference words: 93.
  - Candidate words: 76.
  - WER: 29.03%.
  - Reference accuracy: 70.97%.
  - Important terms:
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Caltheris`: FOUND.
  - Important failures:
    - `I've cleared the Nicolas Cage event` was still rendered as `it's weird, the Nicolas Cage event`.
    - It added `Cool.` at the start.
  - Prompting fixed `Caltheris` but did not improve the overall WER/accuracy.

Decision:
- Reject AssemblyAI Universal-3.5 Pro default and prompted/keyterms results for integration for now.
- Both are below the 95% acceptance threshold.
- The prompted/keyterms run still does not beat the best local whisper.cpp Vulkan result on this clip.
- Keep provider comparison manual until a provider clearly beats the local options.

Deepgram Nova-3 keyterms manual transcript result:
- Provider: Deepgram Nova-3 prerecorded transcription with keyterm prompting.
- Keyterms used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Nicolas Cage`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
- Generated files, local only:
  - `TEMP_DEEPGRAM_TRANSCRIBE.py`
  - `candidate_deepgram_nova3_keyterms.txt`
  - `candidate_deepgram_nova3_keyterms.json`
- Score from `RUN_TRANSCRIPT_REFERENCE_SCORE.py` after correcting the reference line to `Oh, I've completed the Nicolas Cage event`:
  - Candidate: `candidate_deepgram_nova3_keyterms.txt`.
  - Reference words: 93.
  - Candidate words: 77.
  - WER: 33.33%.
  - Reference accuracy: 66.67%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: FOUND.
  - `Nicolas Cage`: FOUND.
  - `Freckelston`: MISSING.
  - `Caltheris`: FOUND.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cutscene, to be honest. I I think it's it's a lot of great content there. I think I think there's a there's a lot to digest in that cutscene. Yeah. But, like, you know, when the Shadowsmith is on screen. When she's not, you know, don't care. But I I understand the blindfold. It's all I'm saying. Mhmm. Fuck. We have Nicolas Cage event. Trying to insinuate. I just We need more Caltheris content.`

Decision:
- Reject Deepgram Nova-3 keyterms for integration for now.
- It found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`, but strict reference accuracy was only 66.67%.
- It does not beat AssemblyAI at 70.97%.
- It does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- It badly misrecognized the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `Fuck. We have Nicolas Cage event`, so it is not acceptable for this workflow.

Speechmatics enhanced custom dictionary manual transcript result:
- Provider: Speechmatics Batch API on EU1 endpoint.
- Model/config: enhanced model with custom dictionary / additional vocabulary.
- Notes:
  - An older key returned 401 Unauthorized.
  - A new key worked on EU1.
  - Initial config failed with HTTP 400 because `remove_disfluencies` is not allowed in the current Speechmatics job config.
  - Removing `remove_disfluencies` allowed the job to run.
- Custom dictionary terms / `sounds_like` hints included:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Nicolas Cage`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
- Generated files, local only:
  - `TEMP_SPEECHMATICS_TRANSCRIBE.py`
  - `candidate_speechmatics_enhanced_vocab.txt`
  - `candidate_speechmatics_enhanced_vocab.json`
  - `candidate_speechmatics_enhanced_vocab_job.json`
- Score from `RUN_TRANSCRIPT_REFERENCE_SCORE.py`:
  - Candidate: `candidate_speechmatics_enhanced_vocab.txt`.
  - Reference words: 93.
  - Candidate words: 71.
  - WER: 34.41%.
  - Reference accuracy: 65.59%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: FOUND.
  - `Nicolas Cage`: FOUND.
  - `Freckelston`: MISSING.
  - `Caltheris`: FOUND.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cut scene, to be honest. I think it's a lot of great content in there. I think there's a lot to digest in that cutscene. Yeah. But like, you know, when, uh, the Shadowsmith is on screen, when she's not, you know, don't care, but I understand the blindfold. That's all I'm saying. Mhm. I played the Nicolas Cage event. I just we need more Caltheris content. MM.`

Decision:
- Reject Speechmatics enhanced custom dictionary for integration for now.
- It found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`, but strict reference accuracy was only 65.59%.
- It does not beat Deepgram at 66.67%.
- It does not beat AssemblyAI at 70.97%.
- It does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- It misrecognized the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `I played the Nicolas Cage event`, so it is not acceptable for this workflow.

Google Speech-to-Text v1 phrase-hint manual transcript results:
- Provider: Google Speech-to-Text v1 synchronous recognize.
- Authentication: API key.
- Input file: `directml_probe_30s.wav`.
- WAV info: mono, 16000 Hz, 16-bit PCM.
- Phrase hints used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Shadowsmith's`
  - `Nicolas Cage`
  - `Nicolas Cage event`
  - `I've completed the Nicolas Cage event`
  - `Oh I've completed the Nicolas Cage event`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
  - `blindfold`
- Generated files, local only:
  - `TEMP_GOOGLE_STT_TRANSCRIBE.py`
  - `candidate_google_stt_latest_long_phrases.txt`
  - `candidate_google_stt_latest_long_phrases.json`
  - `candidate_google_stt_video_enhanced_phrases.txt`
  - `candidate_google_stt_video_enhanced_phrases.json`
- Run 1:
  - Model/config: `latest_long` with phrase hints.
  - Candidate: `candidate_google_stt_latest_long_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 66.
  - WER: 49.46%.
  - Reference accuracy: 50.54%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: MISSING.
    - `Nicolas Cage`: FOUND.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `Oh, it's a Great Cuts in me Oz. I think it's a lot of great content there. I mean, that's a lot to digest in that cutting. Yeah. Like, you know, when the child Smith is on screen when she's not, you know, don't care, but I understand the blindfold. So I'm saying. I've played the Nicolas Cage. I just we need more Calvin. Harris content.`
- Run 2:
  - Model/config: `video` with `useEnhanced=true` and phrase hints.
  - Candidate: `candidate_google_stt_video_enhanced_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 70.
  - WER: 38.71%.
  - Reference accuracy: 61.29%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: MISSING.
    - `Nicolas Cage`: MISSING.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `It's a great cutscene to be honest. I I think it's a long break content there. I think there's a lot to digest in that cut scene. Yeah. So like you know when uh, the Sha Smith's on screen when she's not, you know, don't care. But I I understand the blindfold. That's why I'm saying, mhm. Oh, I believe the Nicholas Cage. I just we need more cerus content.`

Decision:
- Reject Google Speech-to-Text v1 phrase-hint runs for integration for now.
- The best Google run was video enhanced at 61.29%, which is below Speechmatics at 65.59%, Deepgram at 66.67%, AssemblyAI at 70.97%, and the best local whisper.cpp Vulkan run at about 74.19%.
- Google `latest_long` performed worse at 50.54%.
- Google failed the critical phrase around `Oh, I've completed the Nicolas Cage event`.
- Google also failed key glossary terms, including `Shadowsmith` and `Caltheris`.
- Keep Google out of provider integration unless a clearly better Google configuration is tested later.

Azure Speech SDK phrase-list manual transcript results:
- Provider: Azure Speech SDK.
- Azure Speech resource: UK South.
- Python SDK installed in venv:
  - `azure-cognitiveservices-speech` 1.50.0.
  - `azure-core` 1.41.0.
- Input file: `directml_probe_30s.wav`.
- Phrase list used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Shadowsmith's`
  - `Nicolas Cage`
  - `Nicolas Cage event`
  - `I've completed the Nicolas Cage event`
  - `Oh I've completed the Nicolas Cage event`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
  - `blindfold`
  - `cut scene`
- Generated files, local only:
  - `TEMP_AZURE_SPEECH_TRANSCRIBE.py`
  - `candidate_azure_speech_en_us_phrases.txt`
  - `candidate_azure_speech_en_gb_phrases.txt`
- Run 1:
  - Model/config: Azure Speech SDK, language=`en-US`, phrase list.
  - Candidate: `candidate_azure_speech_en_us_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 68.
  - WER: 35.48%.
  - Reference accuracy: 64.52%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `It's a great cut scene. Be honest. I think it's a lot of great content there. I think there's a lot to digest in that cut scene, yeah. Like, you know, when the Shadowsmith is on screen, when she's not, you know, don't care. But I, I understand the blindfold, that's all I'm saying. I believe the Nicolas Cage event. I just we need more Cal fearless content.`
- Run 2:
  - Model/config: Azure Speech SDK, language=`en-GB`, phrase list.
  - Candidate: `candidate_azure_speech_en_gb_phrases.txt`.
  - Reference words: 93.
  - Candidate words: 68.
  - WER: 35.48%.
  - Reference accuracy: 64.52%.
  - Important terms:
    - `Kingman`: MISSING.
    - `ZoneX`: MISSING.
    - `Shadowsmith`: FOUND.
    - `Nicolas Cage`: FOUND.
    - `Freckelston`: MISSING.
    - `Caltheris`: MISSING.
    - `Nyxara`: MISSING.
  - Transcript preview: `It's a great cut scene. Be honest. I think it's a lot of great content there. I think there's a lot to digest in that cut scene, yeah. Like, you know, when the Shadowsmith is on screen, when she's not, you know, don't care. But I, I understand the blindfold, that's all I'm saying. I believe the Nicolas Cage event. I just we need more Cal fearless content.`

Decision:
- Reject Azure Speech SDK phrase-list runs for integration for now.
- `en-US` and `en-GB` produced the same result.
- Strict reference accuracy was only 64.52%.
- Azure does not beat Speechmatics at 65.59%.
- Azure does not beat Deepgram at 66.67%.
- Azure does not beat AssemblyAI at 70.97%.
- Azure does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- Azure failed the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `I believe the Nicolas Cage event`.
- Azure also failed `Caltheris`, producing `Cal fearless`.
- Keep Azure out of provider integration unless a clearly better Azure configuration is tested later.

Cohere Transcribe manual transcript result:
- Provider: Cohere Transcribe API.
- Model/config: `cohere-transcribe-03-2026`.
- Endpoint/script used local temp script:
  - `TEMP_COHERE_TRANSCRIBE.py`
- Input file:
  - `directml_probe_30s.wav`
- Output files, local only:
  - `candidate_cohere_transcribe_03_2026.txt`
  - `candidate_cohere_transcribe_03_2026.json`
- The test was run twice and produced the same transcript preview/output.
- Score:
  - Candidate: `candidate_cohere_transcribe_03_2026.txt`.
  - Reference words: 93.
  - Candidate words: 74.
  - WER: 41.94%.
  - Reference accuracy: 58.06%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: MISSING.
  - `Nicolas Cage`: MISSING.
  - `Freckelston`: MISSING.
  - `Caltheris`: MISSING.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cutscene, to be honest. I think it's a lot of great content there. I think there's a lot to digest in that cutscene. Yeah. For, like, you know, when the Shouse Mist is on screen. When she's not, you know, don't care. I understand the blindfold. That's what I'm saying. I believe the Nicholas Cage event. I'm just trying to insinuate. I just. We need more Carl Fairis content. Hmm. Yeah.`

Decision:
- Reject Cohere Transcribe 03-2026 for integration for now.
- Strict reference accuracy was only 58.06%.
- Cohere does not beat Google STT video enhanced phrases at 61.29%.
- Cohere does not beat Azure Speech SDK phrase list at 64.52%.
- Cohere does not beat Speechmatics at 65.59%.
- Cohere does not beat Deepgram at 66.67%.
- Cohere does not beat AssemblyAI at 70.97%.
- Cohere does not beat the best local whisper.cpp Vulkan run at about 74.19%.
- Cohere failed the key phrase around `Oh, I've completed the Nicolas Cage event`, producing `I believe the Nicholas Cage event`.
- Cohere failed `Shadowsmith`, producing `Shouse Mist`.
- Cohere failed `Caltheris`, producing `Carl Fairis`.
- Cohere missed all tracked important terms.
- Keep Cohere out of provider integration unless a clearly better Cohere configuration is tested later.

AWS Transcribe custom vocabulary manual test status:
- Provider: AWS Transcribe batch transcription with custom vocabulary.
- Region attempted: `eu-west-2` / Europe London.
- IAM user/access key was created for a temporary local test.
- `AWS_SESSION_TOKEN` was intentionally cleared because normal IAM user access keys do not use a session token.
- Local temp script:
  - `TEMP_AWS_TRANSCRIBE_CUSTOM_VOCAB.py`
- Input file:
  - `directml_probe_30s.wav`
- Planned language/config:
  - `en-GB` with custom vocabulary.
  - `en-US` with custom vocabulary.
- Planned local output files:
  - `candidate_aws_transcribe_custom_vocab_en_gb.txt`
  - `candidate_aws_transcribe_custom_vocab_en_gb.json`
  - `candidate_aws_transcribe_custom_vocab_en_us.txt`
  - `candidate_aws_transcribe_custom_vocab_en_us.json`
- Observed run result:
  - S3 setup succeeded:
    - Temporary bucket was created.
    - Audio was uploaded to S3.
    - Vocabulary table was uploaded to S3.
  - AWS Transcribe failed before any transcription job could run.
  - Failure occurred on `CreateVocabulary`.
  - Error:
    - `SubscriptionRequiredException`
    - `The AWS Access Key Id needs a subscription for the service`
  - The AWS Console in Europe London showed the same service-subscription error.
  - Temporary S3 cleanup succeeded:
    - Vocabulary object deleted.
    - Audio object deleted.
    - Temporary bucket deleted.
  - No transcript candidate was produced.
  - No WER/reference-accuracy score was produced.

Decision:
- Mark AWS Transcribe custom vocabulary as BLOCKED, not rejected.
- Do not rank AWS against the tested ASR providers because no model-quality result exists.
- Cause appears to be AWS account/service subscription access under the current free-plan/account state, not local script failure.
- Do not upgrade to paid AWS solely for this test unless explicitly approved later.
- Keep AWS Transcribe as a possible future retest only if service access becomes available without unwanted billing risk.

ElevenLabs Scribe v2 keyterms manual transcript result:
- Provider: ElevenLabs Speech-to-Text API.
- Model/config: Scribe v2 with keyterms.
- Local temp script:
  - `TEMP_ELEVENLABS_SCRIBE_TRANSCRIBE.py`
- Input file:
  - `directml_probe_30s.wav`
- Output files, local only:
  - `candidate_elevenlabs_scribe_v2_keyterms.txt`
  - `candidate_elevenlabs_scribe_v2_keyterms.json`
- API key was cleared from the CMD session after the test.
- Keyterms used:
  - `Kingman`
  - `ZoneX`
  - `Shadowsmith`
  - `Shadowsmith's`
  - `Nicolas Cage`
  - `Nicolas Cage event`
  - `completed Nicolas Cage event`
  - `Oh I've completed`
  - `Freckelston`
  - `Caltheris`
  - `Nyxara`
  - `blindfold`
  - `cut scene`
  - `cutscene`
- Score:
  - Candidate: `candidate_elevenlabs_scribe_v2_keyterms.txt`.
  - Reference words: 93.
  - Candidate words: 85.
  - WER: 15.05%.
  - Reference accuracy: 84.95%.
- Important terms:
  - `Kingman`: MISSING.
  - `ZoneX`: MISSING.
  - `Shadowsmith`: FOUND.
  - `Nicolas Cage`: FOUND.
  - `Freckelston`: MISSING.
  - `Caltheris`: FOUND.
  - `Nyxara`: MISSING.
- Transcript preview: `It's a great cut scene to be honest. I, I think it's a lot of great content in there Gotcha I think, I think there's a, there's a lot to digest in that cut scene, yeah. For like, you know, when, uh, the Shadowsmith's on screen. When she's not, you know, don't care, but- I, I understand the blindfold. That's all I'm saying Mm-hmm. Oh I've completed the Nicolas Cage event Like what you're trying to insinuate I just- We need more Caltheris content`

Decision:
- Mark ElevenLabs Scribe v2 with keyterms as the new best tested online ASR provider result so far.
- Reference accuracy was 84.95%, clearly above all previously tested providers and the previous best local whisper.cpp Vulkan run at about 74.19%.
- ElevenLabs correctly preserved the critical phrase around `Oh I've completed the Nicolas Cage event`.
- ElevenLabs correctly found `Shadowsmith`, `Nicolas Cage`, and `Caltheris`.
- ElevenLabs still missed `Kingman`, `ZoneX`, `Freckelston`, and `Nyxara`, so ASR output must still be treated as draft text with Term QA/glossary review.
- Do not treat ElevenLabs as final truth; treat it as a leading integration candidate subject to cost, quota, API reliability, and user opt-in.
- Keep local whisper.cpp Vulkan as the best no-cloud/free local baseline.
- Current architecture decision remains: ASR draft + glossary/context QA + explicit user review.
