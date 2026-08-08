from __future__ import annotations

from pathlib import Path


def test_docs_cover_command_runtime_contract() -> None:
    text = Path("SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME.md").read_text(encoding="utf-8")
    required = [
        "executable provider-command runtime",
        "SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_BUILT",
        "SOURCE_ADAPTER_PROVIDER_COMMAND_RUNTIME_READY_FOR_NAMED_SITE_SMOKE_EXECUTION",
        "KEYS/ACCOUNTS",
        "real provider command adapters",
        "redacted hashes",
    ]
    for item in required:
        assert item in text


if __name__ == "__main__":
    test_docs_cover_command_runtime_contract()
    print("Source Adapter Provider Command Runtime docs self-test passed.")
