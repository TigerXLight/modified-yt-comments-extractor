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
