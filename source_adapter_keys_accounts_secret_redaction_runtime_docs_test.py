from __future__ import annotations

from pathlib import Path


def test_keys_accounts_secret_redaction_runtime_docs() -> None:
    text = Path("SOURCE_ADAPTER_KEYS_ACCOUNTS_SECRET_REDACTION_RUNTIME.md").read_text(encoding="utf-8")
    assert "KEYS Accounts Secret Redaction Runtime" in text
    assert "KEYS/ACCOUNTS" in text
    assert "SOURCE_ADAPTER_KEYS_ACCOUNTS_SECRET_REDACTION_RUNTIME" in text
    assert "operator" in text.lower()


if __name__ == "__main__":
    test_keys_accounts_secret_redaction_runtime_docs()
    print("Source Adapter KEYS Accounts Secret Redaction Runtime docs self-test passed.")
