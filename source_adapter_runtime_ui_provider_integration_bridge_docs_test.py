from __future__ import annotations

from pathlib import Path


def test_docs_name_shared_ui_provider_bridge() -> None:
    text = Path("SOURCE_ADAPTER_RUNTIME_UI_PROVIDER_INTEGRATION_BRIDGE.md").read_text(encoding="utf-8")
    assert "Runtime UI Provider Integration Bridge" in text
    assert "Keys/Accounts" in text
    assert "file-library publication" in text
    assert "operator-acceptance handoff" in text


if __name__ == "__main__":
    test_docs_name_shared_ui_provider_bridge()
    print("Source Adapter Runtime UI Provider Integration Bridge docs self-test passed.")
