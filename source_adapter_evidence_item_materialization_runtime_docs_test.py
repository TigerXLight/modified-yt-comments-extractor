from __future__ import annotations

from pathlib import Path


def test_evidence_item_materialization_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_EVIDENCE_ITEM_MATERIALIZATION_RUNTIME.md").read_text(encoding="utf-8")
    assert "Evidence Item Materialization Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_EVIDENCE_ITEM_MATERIALIZATION_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_evidence_item_materialization_runtime_docs()
    print("Source Adapter Evidence Item Materialization Runtime docs self-test passed.")
