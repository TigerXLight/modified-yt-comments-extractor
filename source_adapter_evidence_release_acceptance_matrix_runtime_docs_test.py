from pathlib import Path

doc = Path("SOURCE_ADAPTER_EVIDENCE_RELEASE_ACCEPTANCE_MATRIX_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Evidence Release Acceptance Matrix Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_EVIDENCE_RELEASE_ACCEPTANCE_MATRIX_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_EVIDENCE_RELEASE_ACCEPTANCE_MATRIX_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Evidence Release Acceptance Matrix Runtime docs self-test passed.")
