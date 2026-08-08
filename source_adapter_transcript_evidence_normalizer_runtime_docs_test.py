from pathlib import Path

doc = Path("SOURCE_ADAPTER_TRANSCRIPT_EVIDENCE_NORMALIZER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Transcript Evidence Normalizer Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_TRANSCRIPT_EVIDENCE_NORMALIZER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_TRANSCRIPT_EVIDENCE_NORMALIZER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Transcript Evidence Normalizer Runtime docs self-test passed.")
