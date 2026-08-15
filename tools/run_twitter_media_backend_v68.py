from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_media_backend import (
    build_twitter_media_backend_plan,
    run_twitter_media_download_via_shared_backend,
    write_twitter_media_backend_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or plan a Twitter/X shared-media-backend download.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--package-name", default="")
    parser.add_argument("--max-height", type=int, default=1080)
    parser.add_argument("--capability-manifest", default="jd_capabilities_manifest.json")
    parser.add_argument("--direct-media-capability-evidence", default="")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--block-untested-jd", action="store_true")
    parser.add_argument("--plan-json", default="")
    args = parser.parse_args(argv)

    plan = build_twitter_media_backend_plan(
        source_url=args.source_url,
        output_dir=args.output_dir,
        package_name=args.package_name,
        max_height=args.max_height,
        capability_manifest_path=args.capability_manifest,
        allow_untested_jdownloader=not args.block_untested_jd,
        direct_media_capability_evidence_path=args.direct_media_capability_evidence,
    )
    if args.plan_json:
        write_twitter_media_backend_plan(args.plan_json, plan)
    if args.plan_only:
        print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if plan.execution_allowed else 2

    result = run_twitter_media_download_via_shared_backend(
        source_url=args.source_url,
        output_dir=args.output_dir,
        package_name=args.package_name,
        max_height=args.max_height,
        capability_manifest_path=args.capability_manifest,
        allow_untested_jdownloader=not args.block_untested_jd,
        direct_media_capability_evidence_path=args.direct_media_capability_evidence,
    )
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
