from __future__ import annotations

from pathlib import Path


def test_live_smoke_readiness_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_LIVE_SMOKE_READINESS_RUNTIME.md").read_text(encoding="utf-8")
    assert "Live Smoke Readiness Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_LIVE_SMOKE_READINESS_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_live_smoke_readiness_runtime_docs()
    print("Source Adapter Live Smoke Readiness Runtime docs self-test passed.")
