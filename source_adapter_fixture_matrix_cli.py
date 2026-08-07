from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_adapter_fixture_matrix import build_source_adapter_fixture_matrix, load_adapter_specs_json
from source_adapter_fixture_matrix_store import store_source_adapter_fixture_matrix
from source_adapter_fixture_matrix_verifier import verify_source_adapter_fixture_matrix_file


def _load_optional_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("optional JSON inputs must be objects")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared source adapter fixture matrix from explicit adapter specs.")
    parser.add_argument("--adapter-specs-json", required=True, help="JSON array or object containing adapter_specs/adapters.")
    parser.add_argument("--pipeline-closeout-json", help="Optional source pipeline closeout JSON object.")
    parser.add_argument("--output-dir", help="Directory where matrix files should be stored.")
    parser.add_argument("--verify", help="Verify an existing source adapter fixture matrix JSON file instead of building.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)
    if args.verify:
        result = verify_source_adapter_fixture_matrix_file(args.verify)
    else:
        adapter_specs = load_adapter_specs_json(args.adapter_specs_json)
        pipeline_closeout = _load_optional_json(args.pipeline_closeout_json)
        if args.output_dir:
            result = store_source_adapter_fixture_matrix(adapter_specs, args.output_dir, pipeline_closeout=pipeline_closeout)
        else:
            result = build_source_adapter_fixture_matrix(adapter_specs, pipeline_closeout=pipeline_closeout)
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    else:
        print(f"Source adapter fixture matrix: {result.get('adapter_fixture_matrix_id', 'verified')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
