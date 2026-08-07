from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from source_comment_extraction import SourceCommentArtifact, build_source_comment_extraction, build_source_comment_extraction_from_collection
from source_comment_extraction_store import store_source_comment_extraction
from source_comment_extraction_verifier import verify_source_comment_extraction


def _parse_artifact(value: str) -> SourceCommentArtifact:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must use ROLE=PATH")
    role, path = value.split("=", 1)
    role = role.strip()
    path = path.strip()
    if not role or not path:
        raise argparse.ArgumentTypeError("artifact role and path are required")
    return SourceCommentArtifact(role=role, path=path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract adapter-neutral source comments from explicit artifacts.")
    parser.add_argument("--adapter-id", default="unknown_adapter")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--artifact", action="append", type=_parse_artifact, default=[])
    parser.add_argument("--artifact-collection")
    parser.add_argument("--base-dir")
    parser.add_argument("--out-dir")
    parser.add_argument("--store", action="store_true")
    parser.add_argument("--verify", action="store_true")
    return parser


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = build_parser().parse_args(argv)
    if args.artifact_collection:
        extraction = build_source_comment_extraction_from_collection(
            artifact_collection_path=args.artifact_collection,
            adapter_id=args.adapter_id if args.adapter_id != "unknown_adapter" else None,
            source_url=args.source_url or None,
            base_dir=args.base_dir,
        )
    else:
        extraction = build_source_comment_extraction(
            adapter_id=args.adapter_id,
            source_url=args.source_url,
            artifacts=args.artifact,
            base_dir=args.base_dir,
        )
    if args.verify:
        extraction["verification"] = verify_source_comment_extraction(extraction)
    if args.store:
        if not args.out_dir:
            raise SystemExit("--out-dir is required with --store")
        return store_source_comment_extraction(extraction, Path(args.out_dir))
    return extraction


def main(argv: list[str] | None = None) -> None:
    print(json.dumps(run(argv), sort_keys=True, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
