from pathlib import Path

doc = Path("SOURCE_ADAPTER_EVIDENCE_CLAIM_LINK_RUNTIME.md").read_text(encoding="utf-8")
assert "Source Adapter Evidence Claim Link Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_EVIDENCE_CLAIM_LINK_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_EVIDENCE_CLAIM_LINK_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Evidence Claim Link Runtime docs self-test passed.")
