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