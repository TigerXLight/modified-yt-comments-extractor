from __future__ import annotations

from typing import Any

from source_adapter_operational_runtime_bundle_closeout import verify_package


def verify_operational_runtime_bundle_closeout_package(package: dict[str, Any]) -> dict[str, Any]:
    return verify_package(package)


__all__ = ["verify_operational_runtime_bundle_closeout_package"]
