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
- ONNX Runtime DirectML if practical on AMD Windows.
- Parakeet / Canary if a workable local path exists.
- Online transcription providers after local methods are assessed.

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
