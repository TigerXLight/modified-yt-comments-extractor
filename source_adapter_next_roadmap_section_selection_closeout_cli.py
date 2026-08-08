from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_next_roadmap_section_selection_closeout import build_source_adapter_next_roadmap_section_selection_closeout
from source_adapter_next_roadmap_section_selection_closeout_store import store_source_adapter_next_roadmap_section_selection_closeout
from source_adapter_release_regression_next_roadmap_closeout import example_release_regression_next_roadmap_closeout_package


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build source adapter next roadmap section selection closeout artifacts.")
    parser.add_argument("--release-regression-next-roadmap-json")
    parser.add_argument("--output-dir")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--section", action="append", default=[])
    parser.add_argument("--closeout-note", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_package = _load_json(args.release_regression_next_roadmap_json) or example_release_regression_next_roadmap_closeout_package()
    package = build_source_adapter_next_roadmap_section_selection_closeout(
        input_package,
        selected_sections=args.section,
        operator_id=args.operator_id,
        closeout_notes=args.closeout_note,
    ).as_dict()
    if args.output_dir:
        print(json.dumps(store_source_adapter_next_roadmap_section_selection_closeout(package, args.output_dir), indent=2, sort_keys=True))
    else:
        print(json.dumps({"package": package}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
