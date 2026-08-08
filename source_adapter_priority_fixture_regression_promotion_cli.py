from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_priority_fixture_pack_implementation import example_priority_fixture_pack_implementation_package
from source_adapter_priority_fixture_regression_promotion import build_source_adapter_priority_fixture_regression_promotion
from source_adapter_priority_fixture_regression_promotion_store import store_source_adapter_priority_fixture_regression_promotion
from source_adapter_priority_fixture_regression_promotion_verifier import verify_source_adapter_priority_fixture_regression_promotion


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote source adapter priority fixture pack receipts into a regular regression queue.")
    parser.add_argument("--priority-fixture-pack-implementation-json", help="Path to priority fixture pack implementation JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for stored JSON artifacts.")
    parser.add_argument("--operator-id", default="operator")
    parser.add_argument("--promotion-note", action="append", default=[])
    args = parser.parse_args(argv)
    input_package = _load_json(args.priority_fixture_pack_implementation_json) or example_priority_fixture_pack_implementation_package()
    package = build_source_adapter_priority_fixture_regression_promotion(
        input_package,
        operator_id=args.operator_id,
        promotion_notes=args.promotion_note,
    ).as_dict()
    if args.output_dir:
        result = store_source_adapter_priority_fixture_regression_promotion(package, args.output_dir)
    else:
        result = {"package": package, "verification": verify_source_adapter_priority_fixture_regression_promotion(package)}
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
