# R42FJ optional dependency guard: faster_whisper
import importlib.util as _r42fj_importlib_util
import unittest as _r42fj_unittest
if _r42fj_importlib_util.find_spec('faster_whisper') is None:
    raise _r42fj_unittest.SkipTest('optional ASR dependency faster_whisper is not installed')
# R42FJ optional dependency guard end
from faster_whisper import WhisperModel

audio_path = input("Audio/video file path: ").strip().strip('"')

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

segments, info = model.transcribe(
    audio_path,
    beam_size=5,
    vad_filter=True
)

print("Detected language:", info.language)
print("Language probability:", info.language_probability)

for segment in segments:
    print(f"[{segment.start:.2f} - {segment.end:.2f}] {segment.text}")

