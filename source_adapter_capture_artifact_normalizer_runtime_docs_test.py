from __future__ import annotations

from pathlib import Path


def test_capture_artifact_normalizer_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_CAPTURE_ARTIFACT_NORMALIZER_RUNTIME.md").read_text(encoding="utf-8")
    assert "Capture Artifact Normalizer Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_CAPTURE_ARTIFACT_NORMALIZER_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_capture_artifact_normalizer_runtime_docs()
    print("Source Adapter Capture Artifact Normalizer Runtime docs self-test passed.")
