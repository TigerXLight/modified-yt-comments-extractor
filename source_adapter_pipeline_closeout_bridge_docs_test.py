from __future__ import annotations

from pathlib import Path


def test_docs_define_adapter_pipeline_closeout_bridge() -> None:
    text = Path("SOURCE_ADAPTER_PIPELINE_CLOSEOUT_BRIDGE.md").read_text(encoding="utf-8")
    required = [
        "Shared Source Adapter Pipeline Closeout Bridge",
        "source_adapter_pipeline_closeout_bridge.py",
        "source_pipeline_closeout",
        "operator-approved handoffs",
        "instead of cloning the MSN-specific path",
    ]
    for needle in required:
        assert needle in text


if __name__ == "__main__":
    test_docs_define_adapter_pipeline_closeout_bridge()
    print("Source Adapter Pipeline Closeout Bridge docs self-test passed.")
