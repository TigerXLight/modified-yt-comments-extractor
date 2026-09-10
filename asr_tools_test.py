# R42FJ optional dependency guard: faster_whisper
import importlib.util as _r42fj_importlib_util
import unittest as _r42fj_unittest
if _r42fj_importlib_util.find_spec('faster_whisper') is None:
    raise _r42fj_unittest.SkipTest('optional ASR dependency faster_whisper is not installed')
# R42FJ optional dependency guard end
from asr_tools import transcribe_media_file

media_path = input("Audio/video file path: ").strip().strip('"')

segments, metadata = transcribe_media_file(
    media_path,
    model_name="base",
    device="cpu",
    compute_type="int8",
    speaker_name="ASR",
)

print("Metadata:")
for key, value in metadata.items():
    print(f"{key}: {value}")

print()
print("Transcript:")
for segment in segments:
    print(f"{segment.speaker} [{segment.start} - {segment.end}] {segment.text}")

