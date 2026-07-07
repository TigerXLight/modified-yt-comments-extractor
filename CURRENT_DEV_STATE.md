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

## 2026-07-07 Local ASR result: DirectML / TorchCodec feasibility

Status:
- `onnxruntime-directml==1.24.4` is installed locally and ONNX Runtime reports `DmlExecutionProvider`.
- `optimum-onnx==0.1.0`, `optimum==2.1.0`, and `onnx==1.22.0` are installed locally.
- DirectML Whisper tiny.en ONNX export, load, and direct `ORTModelForSpeechSeq2Seq.generate()` completed successfully.
- The tiny.en DirectML probe was fast but scored about 49.46% strict 30s reference word accuracy, so it is only a runtime proof, not a quality verdict.
- The Transformers pipeline path initially failed because TorchCodec could not load FFmpeg DLLs.
- TorchCodec import and the Transformers pipeline path work after registering the FFmpeg 7 shared DLL folder before importing TorchCodec-related libraries.

Runtime note:
- The local FFmpeg 7 shared build used for TorchCodec is `C:\ffmpeg-7-shared\bin`.
- Experimental DirectML/TorchCodec scripts should call `os.add_dll_directory(r"C:\ffmpeg-7-shared\bin")` before TorchCodec imports, or use `asr_runtime_paths.add_ffmpeg7_shared_dll_directory()`.
- The helper also supports overriding that folder with `ASR_FFMPEG7_SHARED_BIN`.

Decision:
- Do not integrate DirectML into the main UI yet.
- Do not treat tiny.en as representative of final DirectML quality.
- Next DirectML work should remain an explicit experimental script using direct `AutoProcessor` plus `ORTModelForSpeechSeq2Seq.generate()` with larger models.

Next local-ASR branches:
1. DirectML feasibility check.
2. Canary / other offline model feasibility if practical.
3. Online transcription comparison if local methods remain below threshold.
