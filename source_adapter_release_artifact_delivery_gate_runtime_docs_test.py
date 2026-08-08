from pathlib import Path

doc = Path("SOURCE_ADAPTER_RELEASE_ARTIFACT_DELIVERY_GATE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Release Artifact Delivery Gate Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_RELEASE_ARTIFACT_DELIVERY_GATE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_RELEASE_ARTIFACT_DELIVERY_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Release Artifact Delivery Gate Runtime docs self-test passed.")
