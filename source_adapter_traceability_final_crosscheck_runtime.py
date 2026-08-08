from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

RUNTIME_TITLE = 'Traceability Final Crosscheck'
RUNTIME_STAGE = 'traceability_final_crosscheck'
DEFAULT_STATUS = "ready_for_operator_approved_execution"
DEFAULT_NOTES = 'operator-approved execution only; live/manual smoke paths require named sites and explicit approval; credential material remains redacted and represented by aliases or hashes; generated receipt data is deterministic.'


@dataclass(frozen=True)
class TraceabilityFinalCrosscheckRecord:
    runtime_id: str
    stage: str = RUNTIME_STAGE
    status: str = DEFAULT_STATUS
    input_refs: tuple[str, ...] = field(default_factory=tuple)
    output_refs: tuple[str, ...] = field(default_factory=tuple)
    receipt_type: str = "redacted_operator_receipt"
    operator_approved: bool = False
    credential_policy: str = "redacted_reference_only"
    notes: str = DEFAULT_NOTES
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["input_refs"] = list(self.input_refs)
        data["output_refs"] = list(self.output_refs)
        data["metadata"] = dict(self.metadata)
        data["digest"] = compute_digest(data)
        return data


def _clean_ref(value: str) -> str:
    ref = str(value).strip()
    if not ref:
        raise ValueError("reference values must not be empty")
    return ref


def _clean_refs(values: Iterable[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(_clean_ref(value) for value in values)


def compute_digest(payload: Mapping[str, Any]) -> str:
    stable = {k: v for k, v in payload.items() if k != "digest"}
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_record(
    runtime_id: str,
    *,
    input_refs: Sequence[str] | None = None,
    output_refs: Sequence[str] | None = None,
    operator_approved: bool = False,
    metadata: Mapping[str, Any] | None = None,
    status: str = DEFAULT_STATUS,
) -> TraceabilityFinalCrosscheckRecord:
    clean_id = str(runtime_id).strip()
    if not clean_id:
        raise ValueError("runtime_id must not be empty")
    clean_status = str(status).strip()
    if not clean_status:
        raise ValueError("status must not be empty")
    return TraceabilityFinalCrosscheckRecord(
        runtime_id=clean_id,
        status=clean_status,
        input_refs=_clean_refs(input_refs),
        output_refs=_clean_refs(output_refs),
        operator_approved=bool(operator_approved),
        metadata=dict(metadata or {}),
    )


def build_default_record() -> TraceabilityFinalCrosscheckRecord:
    return build_record(
        "traceability_final_crosscheck-default",
        input_refs=("source-evidence-roadmap", "operator-approval-gate"),
        output_refs=("redacted-receipt", "total-export-source-evidence"),
        metadata={"runtime_title": RUNTIME_TITLE, "slice": "traceability_final_crosscheck"},
    )


def summarise_record(record: TraceabilityFinalCrosscheckRecord) -> dict[str, Any]:
    data = record.to_dict()
    return {
        "runtime_id": data["runtime_id"],
        "stage": data["stage"],
        "status": data["status"],
        "input_count": len(data["input_refs"]),
        "output_count": len(data["output_refs"]),
        "operator_approved": data["operator_approved"],
        "credential_policy": data["credential_policy"],
        "digest": data["digest"],
    }


def render_record_text(record: TraceabilityFinalCrosscheckRecord) -> str:
    summary = summarise_record(record)
    return "\n".join(f"{key}: {summary[key]}" for key in sorted(summary))


def record_from_dict(payload: Mapping[str, Any]) -> TraceabilityFinalCrosscheckRecord:
    return build_record(
        str(payload.get("runtime_id", "")),
        input_refs=payload.get("input_refs") or (),
        output_refs=payload.get("output_refs") or (),
        operator_approved=bool(payload.get("operator_approved", False)),
        metadata=payload.get("metadata") or {},
        status=str(payload.get("status", DEFAULT_STATUS)),
    )


def write_record(path: str | Path, record: TraceabilityFinalCrosscheckRecord) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def read_record(path: str | Path) -> TraceabilityFinalCrosscheckRecord:
    return record_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def main() -> None:
    print(render_record_text(build_default_record()))


if __name__ == "__main__":
    main()
