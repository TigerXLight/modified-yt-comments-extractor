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