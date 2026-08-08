from __future__ import annotations

from pathlib import Path


def test_provider_healthcheck_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_PROVIDER_HEALTHCHECK_RUNTIME.md").read_text(encoding="utf-8")
    assert "Provider Healthcheck Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_PROVIDER_HEALTHCHECK_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_provider_healthcheck_runtime_docs()
    print("Source Adapter Provider Healthcheck Runtime docs self-test passed.")
