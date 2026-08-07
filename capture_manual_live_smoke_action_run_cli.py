from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from capture_manual_live_smoke_action_implementation import (
    MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN,
    build_manual_live_smoke_action_plan,
    execute_manual_live_smoke_action_plan,
    list_manual_live_smoke_actions,
    manual_live_smoke_action_plan_to_dict,
    manual_live_smoke_action_run_to_dict,
)
from capture_manual_live_smoke_action_run_store import (
    manual_live_smoke_action_run_store_result_to_json,
    store_manual_live_smoke_action_run,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or run approved manual live smoke actions.")
    parser.add_argument("--list-actions", action="store_true", help="List built-in named manual smoke actions as JSON.")
    parser.add_argument("--site-id", default="msn")
    parser.add_argument("--action-id", default="msn_article_capture")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--operator-intent", default="Manual live smoke action requested by operator.")
    parser.add_argument("--approval-token", default="")
    parser.add_argument("--execute-approved", action="store_true", help="Allow approved browser launch when token matches.")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--file-prefix", default="manual_live_smoke_action_run")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list_actions:
        print(json.dumps({"actions": list_manual_live_smoke_actions()}, sort_keys=True, indent=2))
        return 0
    if not args.source_url:
        print("--source-url is required unless --list-actions is used", file=sys.stderr)
        return 2

    dry_run = not bool(args.execute_approved)
    plan = build_manual_live_smoke_action_plan(
        site_id=args.site_id,
        action_id=args.action_id,
        source_url=args.source_url,
        operator_intent=args.operator_intent,
        approval_token=args.approval_token or None,
        dry_run=dry_run,
    )
    run = execute_manual_live_smoke_action_plan(plan)
    response: dict[str, Any] = {
        "plan": manual_live_smoke_action_plan_to_dict(plan),
        "run": manual_live_smoke_action_run_to_dict(run),
        "approval_token_name": "MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN",
        "approval_token_required_value": MANUAL_LIVE_SMOKE_ACTION_APPROVAL_TOKEN if args.execute_approved else "not_required_for_dry_run",
    }
    if args.output_dir:
        result = store_manual_live_smoke_action_run(output_dir=Path(args.output_dir), plan=plan, run=run, file_prefix=args.file_prefix)
        response["store_result"] = json.loads(manual_live_smoke_action_run_store_result_to_json(result))
    print(json.dumps(response, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
