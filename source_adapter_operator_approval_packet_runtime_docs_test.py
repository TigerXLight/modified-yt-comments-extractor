from __future__ import annotations

from pathlib import Path


def test_operator_approval_packet_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_OPERATOR_APPROVAL_PACKET_RUNTIME.md").read_text(encoding="utf-8")
    assert "Operator Approval Packet Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_OPERATOR_APPROVAL_PACKET_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_operator_approval_packet_runtime_docs()
    print("Source Adapter Operator Approval Packet Runtime docs self-test passed.")
