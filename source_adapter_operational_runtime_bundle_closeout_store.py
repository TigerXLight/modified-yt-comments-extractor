from __future__ import annotations

from pathlib import Path
from typing import Any

from source_adapter_operational_runtime_bundle_closeout import write_package


def write_operational_runtime_bundle_closeout_package(output_dir: str | Path, *, operator_id: str = "operator") -> dict[str, Any]:
    return write_package(output_dir, operator_id=operator_id)


__all__ = ["write_operational_runtime_bundle_closeout_package"]
