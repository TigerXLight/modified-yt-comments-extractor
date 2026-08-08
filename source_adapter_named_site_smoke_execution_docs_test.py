from __future__ import annotations

from pathlib import Path


def test_docs_cover_named_site_smoke_execution() -> None:
    text = Path("SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION.md").read_text(encoding="utf-8")
    required = [
        "named-site smoke execution engine",
        "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_BUILT",
        "SOURCE_ADAPTER_NAMED_SITE_SMOKE_EXECUTION_READY_FOR_RECEIPT_REVIEW",
        "browser/archive/release/file-library",
        "KEYS/ACCOUNTS",
        "redacted hashes",
    ]
    for item in required:
        assert item in text


if __name__ == "__main__":
    test_docs_cover_named_site_smoke_execution()
    print("Source Adapter Named-Site Smoke Execution docs self-test passed.")
