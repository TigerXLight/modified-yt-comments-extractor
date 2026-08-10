from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

PASS = "PASS"
PARTIAL = "PARTIAL"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNKNOWN = "UNKNOWN"

COMPLETE = "COMPLETE"
CONFIDENT_WITH_MANUAL_REVIEW = "CONFIDENT_WITH_MANUAL_REVIEW"
BLOCKED = "BLOCKED"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

GOAL_SCHEMA = "msn.source_adapter.goal_matrix.v1"
GOAL_JSON = "MSN_SOURCE_ADAPTER_GOAL_MATRIX.json"
GOAL_MD = "MSN_SOURCE_ADAPTER_GOAL_MATRIX.md"


@dataclass
class GoalCriterion:
    key: str
    label: str
    required_for_static_confidence: bool = True
    required_for_live_complete: bool = True
    status: str = UNKNOWN
    evidence: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass
class GoalMatrix:
    schema: str
    generated_at_utc: str
    final_status: str
    static_status: str
    live_status: str
    criteria: List[GoalCriterion]
    missing_static: List[str]
    missing_live: List[str]
    blocking_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "generated_at_utc": self.generated_at_utc,
            "final_status": self.final_status,
            "static_status": self.static_status,
            "live_status": self.live_status,
            "criteria": [c.to_dict() for c in self.criteria],
            "missing_static": list(self.missing_static),
            "missing_live": list(self.missing_live),
            "blocking_reasons": list(self.blocking_reasons),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_criteria() -> List[GoalCriterion]:
    return [
        GoalCriterion("article", "Article extraction evidence"),
        GoalCriterion("comments", "Comments export evidence"),
        GoalCriterion("profiles", "Profile export evidence"),
        GoalCriterion("offline_viewer", "Offline viewer / rendered HTML evidence"),
        GoalCriterion("archive", "WARC/WACZ/archive evidence", required_for_live_complete=False),
        GoalCriterion("media", "Image/media inventory and download status evidence"),
        GoalCriterion("video", "Video/stream candidate status when present", required_for_static_confidence=False, required_for_live_complete=False),
        GoalCriterion("source_roles", "Source role / primary-source status evidence"),
        GoalCriterion("source_chain", "MSN/publisher/media-credit/original-source separation"),
        GoalCriterion("readiness_reports", "Readiness/release/final validation reports"),
        GoalCriterion("done_acceptance_reports", "Done-gate/acceptance/operator/reconciliation reports"),
        GoalCriterion("manual_live_result", "Filled manual/live result", required_for_static_confidence=False, required_for_live_complete=True),
    ]


def _normalize_status(status: Any) -> str:
    value = str(status or UNKNOWN).strip().upper()
    aliases = {
        "OK": PASS,
        "PASSED": PASS,
        "TRUE": PASS,
        "SUCCESS": PASS,
        "COMPLETE": PASS,
        "CONFIDENT_WITH_MANUAL_REVIEW": PARTIAL,
        "REVIEW": PARTIAL,
        "PARTLY": PARTIAL,
        "MISSING": FAIL,
        "NO": FAIL,
        "FALSE": FAIL,
        "FAILED": FAIL,
        "BLOCKED": FAIL,
    }
    value = aliases.get(value, value)
    if value not in {PASS, PARTIAL, FAIL, NOT_APPLICABLE, UNKNOWN}:
        return UNKNOWN
    return value


def update_criteria(criteria: Sequence[GoalCriterion], status_map: Mapping[str, Any], evidence_map: Optional[Mapping[str, Sequence[str]]] = None, notes_map: Optional[Mapping[str, Sequence[str]]] = None) -> List[GoalCriterion]:
    evidence_map = evidence_map or {}
    notes_map = notes_map or {}
    out: List[GoalCriterion] = []
    for item in criteria:
        clone = GoalCriterion(
            key=item.key,
            label=item.label,
            required_for_static_confidence=item.required_for_static_confidence,
            required_for_live_complete=item.required_for_live_complete,
            status=_normalize_status(status_map.get(item.key, item.status)),
            evidence=[str(x) for x in evidence_map.get(item.key, item.evidence)],
            notes=[str(x) for x in notes_map.get(item.key, item.notes)],
        )
        out.append(clone)
    return out


def decide_goal_matrix(criteria: Sequence[GoalCriterion]) -> GoalMatrix:
    missing_static: List[str] = []
    missing_live: List[str] = []
    blocking: List[str] = []

    for item in criteria:
        if item.status == FAIL:
            blocking.append(f"{item.key}: {item.label} failed or is missing")
        if item.required_for_static_confidence and item.status not in {PASS, NOT_APPLICABLE}:
            missing_static.append(item.key)
        if item.required_for_live_complete and item.status not in {PASS, NOT_APPLICABLE}:
            missing_live.append(item.key)

    if blocking:
        final = BLOCKED
    elif not criteria:
        final = INSUFFICIENT_EVIDENCE
    elif not missing_static and not missing_live:
        final = COMPLETE
    elif not missing_static:
        final = CONFIDENT_WITH_MANUAL_REVIEW
    else:
        final = PARTIAL

    static_status = PASS if not missing_static and not blocking else (FAIL if blocking else PARTIAL)
    live_status = PASS if not missing_live and not blocking else (FAIL if blocking else PARTIAL)
    return GoalMatrix(
        schema=GOAL_SCHEMA,
        generated_at_utc=utc_now(),
        final_status=final,
        static_status=static_status,
        live_status=live_status,
        criteria=list(criteria),
        missing_static=missing_static,
        missing_live=missing_live,
        blocking_reasons=blocking,
    )


def render_goal_matrix_markdown(matrix: GoalMatrix) -> str:
    lines = [
        "# MSN Source Adapter Goal Matrix",
        "",
        f"Generated: `{matrix.generated_at_utc}`",
        f"Final status: `{matrix.final_status}`",
        f"Static status: `{matrix.static_status}`",
        f"Live status: `{matrix.live_status}`",
        "",
        "| Criterion | Static required | Live required | Status | Evidence |",
        "|---|---:|---:|---|---|",
    ]
    for item in matrix.criteria:
        evidence = "; ".join(item.evidence[:3]) if item.evidence else "-"
        lines.append(f"| {item.label} | {item.required_for_static_confidence} | {item.required_for_live_complete} | `{item.status}` | {evidence} |")
    if matrix.missing_static:
        lines.extend(["", "## Missing static confidence criteria", ""])
        lines.extend(f"- `{x}`" for x in matrix.missing_static)
    if matrix.missing_live:
        lines.extend(["", "## Missing live completion criteria", ""])
        lines.extend(f"- `{x}`" for x in matrix.missing_live)
    if matrix.blocking_reasons:
        lines.extend(["", "## Blocking reasons", ""])
        lines.extend(f"- {x}" for x in matrix.blocking_reasons)
    lines.append("")
    return "\n".join(lines)


def write_goal_matrix(matrix: GoalMatrix, out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / GOAL_JSON
    md_path = out_dir / GOAL_MD
    json_path.write_text(json.dumps(matrix.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_goal_matrix_markdown(matrix), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def build_goal_matrix(status_map: Mapping[str, Any], evidence_map: Optional[Mapping[str, Sequence[str]]] = None, notes_map: Optional[Mapping[str, Sequence[str]]] = None) -> GoalMatrix:
    return decide_goal_matrix(update_criteria(default_criteria(), status_map, evidence_map, notes_map))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Build an MSN adapter goal matrix from a JSON status map.")
    parser.add_argument("--status-json", required=True, help="JSON file containing criterion status values by key.")
    parser.add_argument("--out", required=True, help="Output directory.")
    args = parser.parse_args(argv)
    data = json.loads(Path(args.status_json).read_text(encoding="utf-8"))
    matrix = build_goal_matrix(data if isinstance(data, Mapping) else {})
    written = write_goal_matrix(matrix, Path(args.out))
    print("MSN goal matrix status:", matrix.final_status)
    print("JSON:", written["json"])
    print("Markdown:", written["markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
