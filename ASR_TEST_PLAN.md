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

Topic resolver:
- Optional background helper for vocabulary/phrase hints.
- Must be strict-filtered.
- Must never block ASR.
- Must never be trusted as ground truth.

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
