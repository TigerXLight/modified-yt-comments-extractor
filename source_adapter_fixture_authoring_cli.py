from __future__ import annotations

import argparse
import json

from source_adapter_fixture_authoring import build_source_adapter_fixture_authoring, load_fixture_matrix_json
from source_adapter_fixture_authoring_store import store_source_adapter_fixture_authoring
from source_adapter_fixture_authoring_verifier import verify_source_adapter_fixture_authoring_file


def _adapter_ids(value: str | None) -> list[str] | None:
    if not value:
        return None
    ids = [item.strip() for item in value.split(",") if item.strip()]
    return ids or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build shared source adapter fixture-authoring templates.")
    parser.add_argument("--fixture-matrix-json", help="Source adapter fixture matrix JSON package.")
    parser.add_argument("--adapter-ids", help="Optional comma-separated adapter ids to author.")
    parser.add_argument("--output-dir", help="Directory where authoring package files should be stored.")
    parser.add_argument("--verify", help="Verify an existing source adapter fixture-authoring package JSON file.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)
    if args.verify:
        result = verify_source_adapter_fixture_authoring_file(args.verify)
    else:
        if not args.fixture_matrix_json:
            raise SystemExit("--fixture-matrix-json is required unless --verify is used")
        matrix = load_fixture_matrix_json(args.fixture_matrix_json)
        adapter_ids = _adapter_ids(args.adapter_ids)
        if args.output_dir:
            result = store_source_adapter_fixture_authoring(matrix, args.output_dir, adapter_ids=adapter_ids)
        else:
            result = build_source_adapter_fixture_authoring(matrix, adapter_ids=adapter_ids)
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    else:
        print(f"Source adapter fixture authoring: {result.get('source_adapter_fixture_authoring_id', 'verified')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
