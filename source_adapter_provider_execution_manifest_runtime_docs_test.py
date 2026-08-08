from __future__ import annotations

from pathlib import Path


def test_provider_execution_manifest_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_PROVIDER_EXECUTION_MANIFEST_RUNTIME.md").read_text(encoding="utf-8")
    assert "Provider Execution Manifest Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_PROVIDER_EXECUTION_MANIFEST_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_provider_execution_manifest_runtime_docs()
    print("Source Adapter Provider Execution Manifest Runtime docs self-test passed.")
