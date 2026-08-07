from __future__ import annotations

import argparse
import json

from source_adapter_fixture_review import build_source_adapter_fixture_review, load_json
from source_adapter_fixture_review_store import store_source_adapter_fixture_review
from source_adapter_fixture_review_verifier import verify_source_adapter_fixture_review_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review shared source adapter fixture-authoring output.")
    parser.add_argument("--fixture-authoring-json", help="Source adapter fixture-authoring package JSON.")
    parser.add_argument("--authored-fixtures-json", help="Operator-authored fixture JSON packet.")
    parser.add_argument("--output-dir", help="Directory where fixture review package files should be stored.")
    parser.add_argument("--verify", help="Verify an existing source adapter fixture-review package JSON file.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)
    if args.verify:
        result = verify_source_adapter_fixture_review_file(args.verify)
    else:
        if not args.fixture_authoring_json or not args.authored_fixtures_json:
            raise SystemExit("--fixture-authoring-json and --authored-fixtures-json are required unless --verify is used")
        fixture_authoring = load_json(args.fixture_authoring_json)
        authored_fixtures = load_json(args.authored_fixtures_json)
        if args.output_dir:
            result = store_source_adapter_fixture_review(fixture_authoring, authored_fixtures, args.output_dir)
        else:
            result = build_source_adapter_fixture_review(fixture_authoring, authored_fixtures)
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    else:
        print(f"Source adapter fixture review: {result.get('source_adapter_fixture_review_id', 'verified')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
