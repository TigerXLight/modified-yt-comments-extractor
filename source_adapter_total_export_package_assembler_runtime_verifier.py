from __future__ import annotations

from typing import Any

from source_adapter_total_export_package_assembler_runtime import verify_package


def verify_total_export_package_assembler_runtime_package(package: dict[str, Any]) -> dict[str, Any]:
    return verify_package(package)


__all__ = ["verify_total_export_package_assembler_runtime_package"]
