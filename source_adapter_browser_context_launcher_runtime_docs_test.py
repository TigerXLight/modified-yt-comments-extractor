from pathlib import Path

doc = Path("SOURCE_ADAPTER_BROWSER_CONTEXT_LAUNCHER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Browser Context Launcher Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_BROWSER_CONTEXT_LAUNCHER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_BROWSER_CONTEXT_LAUNCHER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Browser Context Launcher Runtime docs self-test passed.")
