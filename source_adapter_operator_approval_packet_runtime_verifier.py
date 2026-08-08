from __future__ import annotations

from typing import Any

from source_adapter_operator_approval_packet_runtime import verify_package


def verify_operator_approval_packet_runtime_package(package: dict[str, Any]) -> dict[str, Any]:
    return verify_package(package)


__all__ = ["verify_operator_approval_packet_runtime_package"]
