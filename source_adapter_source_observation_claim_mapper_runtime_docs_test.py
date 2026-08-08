from pathlib import Path

doc = Path("SOURCE_ADAPTER_SOURCE_OBSERVATION_CLAIM_MAPPER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Source Observation Claim Mapper Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_SOURCE_OBSERVATION_CLAIM_MAPPER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_SOURCE_OBSERVATION_CLAIM_MAPPER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Source Observation Claim Mapper Runtime docs self-test passed.")
