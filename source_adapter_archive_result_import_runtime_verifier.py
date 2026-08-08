from __future__ import annotations

from typing import Any

from source_adapter_archive_result_import_runtime import verify_package


def verify_archive_result_import_runtime_package(package: dict[str, Any]) -> dict[str, Any]:
    return verify_package(package)


__all__ = ["verify_archive_result_import_runtime_package"]
