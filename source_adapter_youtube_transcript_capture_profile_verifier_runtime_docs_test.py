from pathlib import Path

doc = Path("SOURCE_ADAPTER_YOUTUBE_TRANSCRIPT_CAPTURE_PROFILE_VERIFIER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter YouTube Transcript Capture Profile Verifier Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_YOUTUBE_TRANSCRIPT_CAPTURE_PROFILE_VERIFIER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_YOUTUBE_TRANSCRIPT_CAPTURE_PROFILE_VERIFIER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter YouTube Transcript Capture Profile Verifier Runtime docs self-test passed.")
