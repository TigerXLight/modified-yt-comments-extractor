from pathlib import Path

doc = Path("SOURCE_ADAPTER_YOUTUBE_MEDIA_DELIVERY_PROFILE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter YouTube Media Delivery Profile Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_YOUTUBE_MEDIA_DELIVERY_PROFILE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_YOUTUBE_MEDIA_DELIVERY_PROFILE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter YouTube Media Delivery Profile Runtime docs self-test passed.")
