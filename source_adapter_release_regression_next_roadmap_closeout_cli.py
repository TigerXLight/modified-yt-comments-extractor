from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_release_regression_next_roadmap_closeout import build_source_adapter_release_regression_next_roadmap_closeout
from source_adapter_release_regression_next_roadmap_closeout_store import store_source_adapter_release_regression_next_roadmap_closeout
from source_adapter_roadmap_audit_final_closeout import example_roadmap_audit_final_closeout_package


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build source adapter release/regression/next-roadmap closeout artifacts.")
    parser.add_argument("--roadmap-audit-final-closeout-json")
    parser.add_argument("--output-dir")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--commit-checkpoint", default="c063336")
    parser.add_argument("--release-note", action="append", default=[])
    parser.add_argument("--closeout-note", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_package = _load_json(args.roadmap_audit_final_closeout_json) or example_roadmap_audit_final_closeout_package()
    package = build_source_adapter_release_regression_next_roadmap_closeout(
        input_package,
        release_notes=args.release_note,
        commit_checkpoint=args.commit_checkpoint,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    ).as_dict()
    if args.output_dir:
        output = store_source_adapter_release_regression_next_roadmap_closeout(package, args.output_dir)
    else:
        output = {"package": package}
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
