from pathlib import Path

doc = Path("SOURCE_ADAPTER_EVIDENCE_REVIEW_GATE_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Evidence Review Gate Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_EVIDENCE_REVIEW_GATE_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_EVIDENCE_REVIEW_GATE_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Evidence Review Gate Runtime docs self-test passed.")
