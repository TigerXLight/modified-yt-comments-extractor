from pathlib import Path

doc = Path("SOURCE_ADAPTER_BROWSER_OBSERVATION_IMPORT_RUNTIME.md").read_text(encoding="utf-8")
assert "Source Adapter Browser Observation Import Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_BROWSER_OBSERVATION_IMPORT_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_BROWSER_OBSERVATION_IMPORT_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_STAGE" in doc
print("Source Adapter Browser Observation Import Runtime docs self-test passed.")
