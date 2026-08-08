from __future__ import annotations

from typing import Any

from source_adapter_release_publish_receipt_runtime import verify_package


def verify_release_publish_receipt_runtime_package(package: dict[str, Any]) -> dict[str, Any]:
    return verify_package(package)


__all__ = ["verify_release_publish_receipt_runtime_package"]
