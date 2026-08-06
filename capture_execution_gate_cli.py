from __future__ import annotations

import argparse
import sys

from capture_execution_gate import (
    ACTION_KINDS,
    ExecutionGateApprovalMetadata,
    build_execution_gate_plan,
    build_execution_gate_plan_text,
    build_execution_gate_request,
    execution_gate_plan_to_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a local-only execution-gate plan. No runtime action is executed."
    )
    parser.add_argument("--action", action="append", choices=ACTION_KINDS, required=True)
    parser.add_argument("--source-label", default="")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--scope", default="")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--approve-manual", action="store_true")
    parser.add_argument("--approved-by-label-recorded", action="store_true")
    parser.add_argument("--approved-at-utc", default="")
    parser.add_argument("--approval-reference-id", default="")
    parser.add_argument("--ack-safety-boundaries", action="store_true")
    return parser


def run_cli(argv: list[str] | None = None) -> str:
    args = build_parser().parse_args(argv)
    requests = tuple(
        build_execution_gate_request(
            action_kind=action,
            source_label=args.source_label,
            source_url=args.source_url,
            intended_scope=args.scope,
        )
        for action in args.action
    )
    approval_metadata = None
    if args.approve_manual:
        approval_metadata = ExecutionGateApprovalMetadata(
            approved_by_label_recorded=args.approved_by_label_recorded,
            approved_at_utc=args.approved_at_utc,
            approved_action_ids=tuple(request.request_id for request in requests),
            approval_reference_id=args.approval_reference_id,
            safety_boundaries_acknowledged=args.ack_safety_boundaries,
        )
    plan = build_execution_gate_plan(requests, approval_metadata=approval_metadata)
    if args.format == "json":
        return execution_gate_plan_to_json(plan)
    return build_execution_gate_plan_text(plan)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.write(run_cli(argv))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
