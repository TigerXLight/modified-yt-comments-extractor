from __future__ import annotations

from pathlib import Path


def test_docs_describe_local_only_closeout() -> None:
    text = Path("SOURCE_ADAPTER_FIXTURE_PIPELINE_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "Source Adapter Fixture Pipeline Closeout" in text
    assert "does not fetch URLs" in text
    assert "does not" in text and "read credentials" in text
    assert "adapter coverage acceptance handoff" in text


if __name__ == "__main__":
    test_docs_describe_local_only_closeout()
    print("Source Adapter Fixture Pipeline Closeout docs self-test passed.")
