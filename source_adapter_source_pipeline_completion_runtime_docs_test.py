from __future__ import annotations

from pathlib import Path


def test_source_pipeline_completion_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_SOURCE_PIPELINE_COMPLETION_RUNTIME.md").read_text(encoding="utf-8")
    assert "Source Pipeline Completion Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_SOURCE_PIPELINE_COMPLETION_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_source_pipeline_completion_runtime_docs()
    print("Source Adapter Source Pipeline Completion Runtime docs self-test passed.")
