from __future__ import annotations

from pathlib import Path
from typing import Any

from source_adapter_audit_log_replay_runtime import write_package


def write_audit_log_replay_runtime_package(output_dir: str | Path, *, operator_id: str = "operator") -> dict[str, Any]:
    return write_package(output_dir, operator_id=operator_id)


__all__ = ["write_audit_log_replay_runtime_package"]
