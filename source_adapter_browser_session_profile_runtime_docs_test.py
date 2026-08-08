from __future__ import annotations

from pathlib import Path


def test_browser_session_profile_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_BROWSER_SESSION_PROFILE_RUNTIME.md").read_text(encoding="utf-8")
    assert "Browser Session Profile Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_BROWSER_SESSION_PROFILE_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_browser_session_profile_runtime_docs()
    print("Source Adapter Browser Session Profile Runtime docs self-test passed.")
