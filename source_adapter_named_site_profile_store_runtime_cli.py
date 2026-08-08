from __future__ import annotations

import argparse
import json

from source_adapter_named_site_profile_store_runtime import example_source_adapter_named_site_profile_store_runtime_package
from source_adapter_named_site_profile_store_runtime_store import store_source_adapter_named_site_profile_store_runtime_package
from source_adapter_named_site_profile_store_runtime_verifier import verify_source_adapter_named_site_profile_store_runtime_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Source Adapter Named-Site Profile Store Runtime")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--store-dir", default=None)
    args = parser.parse_args(argv)
    package = example_source_adapter_named_site_profile_store_runtime_package()
    verification = verify_source_adapter_named_site_profile_store_runtime_package(package)
    result = {"package": package, "verification": verification}
    if args.store_dir:
        result["store"] = store_source_adapter_named_site_profile_store_runtime_package(package, args.store_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Source Adapter Named-Site Profile Store Runtime: " + package["status"])
        print("handoff: " + package["handoff"]["handoff_status"])
        print("rows: " + str(package["named_site_profile_rows_row_count"]))
        print("issues: " + str(verification["issue_count"]))
    return 0 if verification["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
