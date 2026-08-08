from pathlib import Path

doc = Path("SOURCE_ADAPTER_COMMENT_TREE_MATERIALIZER_RUNTIME.md").read_text(encoding="utf-8")
assert "# Source Adapter Comment Tree Materializer Runtime" in doc
assert "KEYS/ACCOUNTS" in doc
assert "SOURCE_ADAPTER_COMMENT_TREE_MATERIALIZER_RUNTIME_BUILT" in doc
assert "SOURCE_ADAPTER_COMMENT_TREE_MATERIALIZER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE" in doc
print("Source Adapter Comment Tree Materializer Runtime docs self-test passed.")
