from __future__ import annotations

from typing import Any

from source_adapter_keys_accounts_secret_redaction_runtime import verify_package


def verify_keys_accounts_secret_redaction_runtime_package(package: dict[str, Any]) -> dict[str, Any]:
    return verify_package(package)


__all__ = ["verify_keys_accounts_secret_redaction_runtime_package"]
