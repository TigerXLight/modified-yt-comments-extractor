from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from capture_msn_manual_action_total_export_pipeline import (
    build_msn_manual_action_total_export_pipeline,
    msn_manual_action_total_export_pipeline_result_to_json,
)
from capture_msn_manual_action_total_export_pipeline_store import (
    msn_manual_action_total_export_pipeline_store_result_to_json,
    store_msn_manual_action_total_export_pipeline_result,
)
from capture_msn_manual_action_total_export_pipeline_verifier import (
    msn_manual_action_total_export_pipeline_verification_report_to_json,
    verify_msn_manual_action_total_export_pipeline_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the implemented MSN manual action-to-Total-Export pipeline from explicit artifact files.")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--article-file", required=True)
    parser.add_argument("--comments-file", default="")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--package-id", default="msn_manual_total_export")
    parser.add_argument("--file-prefix", default="msn_manual_action_total_export")
    parser.add_argument("--operator-intent", default="MSN manual capture for Total Export review")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = build_msn_manual_action_total_export_pipeline(
            source_url=args.source_url,
            article_file=Path(args.article_file),
            comments_file=Path(args.comments_file) if args.comments_file else None,
            output_dir=Path(args.output_dir),
            package_id=args.package_id,
            file_prefix=args.file_prefix,
            operator_intent=args.operator_intent,
        )
        report_payload = json.loads(msn_manual_action_total_export_pipeline_result_to_json(result))
        verifier = verify_msn_manual_action_total_export_pipeline_payload(report_payload)
        store_result = store_msn_manual_action_total_export_pipeline_result(
            output_dir=Path(args.output_dir) / "pipeline_report",
            result=result,
            file_prefix=args.file_prefix,
        )
        print(
            json.dumps(
                {
                    "pipeline_result": report_payload,
                    "pipeline_verifier": json.loads(msn_manual_action_total_export_pipeline_verification_report_to_json(verifier)),
                    "pipeline_store_result": json.loads(msn_manual_action_total_export_pipeline_store_result_to_json(store_result)),
                },
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0 if verifier.ready_for_total_export_review else 3
    except Exception as exc:  # pragma: no cover - exercised by subprocess tests
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
