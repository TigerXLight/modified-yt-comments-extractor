from __future__ import annotations

from pathlib import Path


def test_release_upload_target_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_RELEASE_UPLOAD_TARGET_RUNTIME.md").read_text(encoding="utf-8")
    assert "Release Upload Target Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_RELEASE_UPLOAD_TARGET_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_release_upload_target_runtime_docs()
    print("Source Adapter Release Upload Target Runtime docs self-test passed.")
