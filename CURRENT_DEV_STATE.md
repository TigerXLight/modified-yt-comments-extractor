# Current Dev State

Branch: v2.6.0-asr-engines

Current focus:
- Local ASR engine testing and Auto Quality selection.
- Accuracy is priority over speed.
- Clear/common speech should not be silently accepted if wrong.
- Weak ASR output should stay marked as draft or be rejected by threshold.

Important context:
- Python GUI already has Transcript tab, local ASR dialog, Auto Probe 30s, Self-Test 15s, linked media, waveform/timeline work, and ASR warning export.
- There is no separate asr_hardware.py file. Hardware/environment detection currently lives in asr_quality_policy.py.
- whisper.cpp Vulkan works on AMD RX 5700 through C:\whisper.cpp.
- Manual matrix result: large-v3 phrase prompt is best quality; large-v3-turbo is faster but weaker on important terms.
- Topic resolver / Common Crawl / Serper / Exa are later background glossary helpers only. They are not ASR engines and must be strict-filtered.

Command style preference:
- Do not put multiple separate CMD commands in one copy block.
- Avoid repeating cd/venv activation when already in the project venv.
- Prefer one large Python patch/update file over many manual code edits.

## 2026-07-07 Local ASR result: Parakeet rejected

Status:
- whisper.cpp Vulkan is working on AMD RX 5700.
- Built-in ASR Self-Test 15s passed with AMD GPU — whisper.cpp large-v3-turbo terms only.
- Real media Auto Probe 30s still failed the 95% reference threshold.
- Best real-media whisper.cpp candidate remained AMD GPU — whisper.cpp large-v3-turbo phrase prompt at about 74.19% reference word accuracy.
- The app correctly kept the imported reference transcript and did not load the failed ASR draft.

Parakeet test:
- `parakeet-cli.exe` exists in the whisper.cpp Vulkan build and runs on AMD Vulkan.
- Downloaded and tested:
  - `ggml-parakeet-tdt-0.6b-v3-q8_0.bin`
  - `ggml-parakeet-tdt-0.6b-v3-f16.bin`
- Parakeet q8_0 strict 30s score: 49.46% word accuracy.
- Parakeet f16 strict 30s score: 47.31% word accuracy.
- Both Parakeet outputs were very fast but missed critical wording/names:
  - `Shadowsmith` became `Shadow Smith`
  - `blindfold` became `blindfold plan thing` / `blind fault plant thing`
  - `I've cleared the Nicolas Cage event` became `that's really the Nicholas cage of it`
  - `Caltheris` became `Cal Ferris`

Decision:
- Do not integrate Parakeet into Auto Quality Probe yet.
- It is practical and fast on AMD Vulkan, but not accurate enough for this subtitle workflow.
- Keep Parakeet models installed for future comparison only.

Next local-ASR branches:
1. DirectML feasibility check.
2. Canary / other offline model feasibility if practical.
3. Online transcription comparison if local methods remain below threshold.
