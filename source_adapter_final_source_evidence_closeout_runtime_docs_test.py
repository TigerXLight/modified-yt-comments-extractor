from pathlib import Path

doc = Path("SOURCE_ADAPTER_FINAL_SOURCE_EVIDENCE_CLOSEOUT_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Final Source Evidence Closeout Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "Online ASR" in doc
assert "large-v3 Vulkan" in doc
assert "SOURCE_ADAPTER_FINAL_SOURCE_EVIDENCE_CLOSEOUT_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_FINAL_SOURCE_EVIDENCE_CLOSEOUT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Final Source Evidence Closeout Runtime docs self-test passed.")
