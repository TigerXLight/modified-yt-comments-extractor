from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from capture_manual_live_smoke_action_implementation import (
    ManualLiveSmokeActionPlan,
    ManualLiveSmokeActionRun,
    manual_live_smoke_action_plan_to_dict,
    manual_live_smoke_action_run_to_dict,
)


MANUAL_LIVE_SMOKE_ACTION_RUN_STORE_SCHEMA_VERSION = "manual_live_smoke_action_run_store_v1"


@dataclass(frozen=True)
class ManualLiveSmokeActionRunStoredArtifact:
    role: str
    file_name: str
    sha256: str
    byte_count: int


@dataclass(frozen=True)
class ManualLiveSmokeActionRunStoreResult:
    schema_version: str
    artifact_count: int
    artifacts: tuple[ManualLiveSmokeActionRunStoredArtifact, ...]
    safety_flags: tuple[str, ...]


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")


def _safe_file_name(value: str) -> str:
    name = Path(value).name
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- ")
    cleaned = "".join(ch if ch in allowed else "_" for ch in name).strip(" .")
    if not cleaned:
        raise ValueError("safe file name could not be derived")
    return cleaned[:180]


def _write_json(output_dir: Path, file_name: str, payload: dict[str, Any]) -> ManualLiveSmokeActionRunStoredArtifact:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_file_name(file_name)
    data = _json_bytes(payload)
    target = output_dir / safe_name
    target.write_bytes(data)
    return ManualLiveSmokeActionRunStoredArtifact(
        role=safe_name.rsplit(".", 1)[0],
        file_name=safe_name,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
    )


def store_manual_live_smoke_action_run(
    *,
    output_dir: str | Path,
    plan: ManualLiveSmokeActionPlan,
    run: ManualLiveSmokeActionRun,
    file_prefix: str = "manual_live_smoke_action_run",
) -> ManualLiveSmokeActionRunStoreResult:
    prefix = _safe_file_name(file_prefix).rsplit(".", 1)[0]
    root = Path(output_dir)
    plan_artifact = _write_json(root, f"{prefix}_plan.json", manual_live_smoke_action_plan_to_dict(plan))
    run_artifact = _write_json(root, f"{prefix}_run.json", manual_live_smoke_action_run_to_dict(run))
    result_payload = {
        "schema_version": MANUAL_LIVE_SMOKE_ACTION_RUN_STORE_SCHEMA_VERSION,
        "artifacts": [asdict(plan_artifact), asdict(run_artifact)],
        "safety_flags": [
            "safe_file_names_only",
            "sha256_and_byte_counts_recorded",
            "no_full_local_paths_serialized",
            "no_raw_media_serialized",
        ],
    }
    result_artifact = _write_json(root, f"{prefix}_store_result.json", result_payload)
    return ManualLiveSmokeActionRunStoreResult(
        schema_version=MANUAL_LIVE_SMOKE_ACTION_RUN_STORE_SCHEMA_VERSION,
        artifact_count=3,
        artifacts=(plan_artifact, run_artifact, result_artifact),
        safety_flags=tuple(result_payload["safety_flags"]),
    )


def manual_live_smoke_action_run_store_result_to_json(result: ManualLiveSmokeActionRunStoreResult) -> str:
    return _json_bytes(asdict(result)).decode("utf-8")
