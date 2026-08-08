from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_adapter_runtime_operator_acceptance_closeout import build_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_operator_acceptance_closeout_store import store_source_adapter_runtime_operator_acceptance_closeout
from source_adapter_runtime_operator_acceptance_closeout_verifier import verify_source_adapter_runtime_operator_acceptance_closeout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build source adapter runtime operator acceptance closeout outputs.")
    parser.add_argument("--runtime-ui-provider-integration-json", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--acceptance-profile", default="source_adapter_runtime_operator_acceptance_v1")
    parser.add_argument("--acceptance-decision", default="ACCEPTED_FOR_OPERATOR_APPROVED_EXECUTION")
    parser.add_argument("--enabled-capability", action="append", default=None)
    parser.add_argument("--acceptance-note", action="append", default=[])
    args = parser.parse_args(argv)

    data = json.loads(Path(args.runtime_ui_provider_integration_json).read_text(encoding="utf-8"))
    package = build_source_adapter_runtime_operator_acceptance_closeout(
        data,
        enabled_capabilities=args.enabled_capability,
        operator_id=args.operator_id,
        acceptance_profile=args.acceptance_profile,
        acceptance_decision=args.acceptance_decision,
        acceptance_notes=args.acceptance_note,
    )
    if args.output_dir:
        print(json.dumps(store_source_adapter_runtime_operator_acceptance_closeout(package, args.output_dir), indent=2, sort_keys=True))
    else:
        print(json.dumps(verify_source_adapter_runtime_operator_acceptance_closeout(package), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
