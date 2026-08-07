from __future__ import annotations

from pathlib import Path


def test_docs_describe_local_only_contract() -> None:
    text = Path("SOURCE_ADAPTER_COVERAGE_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "Adapter Coverage Acceptance" in text
    assert "never fetches URLs" in text
    assert "adapter registry handoff" in text


if __name__ == "__main__":
    test_docs_describe_local_only_contract()
    print("Source Adapter Coverage Acceptance docs self-test passed.")
