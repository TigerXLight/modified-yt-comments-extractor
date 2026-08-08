from __future__ import annotations

from pathlib import Path


def test_operational_runtime_bundle_closeout_docs() -> None:
    text = Path("SOURCE_ADAPTER_OPERATIONAL_RUNTIME_BUNDLE_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "Operational Runtime Bundle Closeout" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_OPERATIONAL_RUNTIME_BUNDLE_CLOSEOUT" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_operational_runtime_bundle_closeout_docs()
    print("Source Adapter Operational Runtime Bundle Closeout docs self-test passed.")
