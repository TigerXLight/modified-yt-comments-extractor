from __future__ import annotations

import argparse
import json
from pathlib import Path

from source_content_extraction import SourceContentArtifact, build_source_content_extraction, build_source_content_extraction_from_collection
from source_content_extraction_store import write_source_content_extraction_store
from source_content_extraction_verifier import verify_source_content_extraction


def _parse_artifact(value: str) -> SourceContentArtifact:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must use role=path syntax")
    role, path = value.split("=", 1)
    role = role.strip()
    path = path.strip()
    if not role or not path:
        raise argparse.ArgumentTypeError("artifact role and path are required")
    return SourceContentArtifact(role=role, path=path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build shared source content extraction from explicit artifacts.")
    parser.add_argument("--adapter-id", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--artifact", action="append", type=_parse_artifact, default=[])
    parser.add_argument("--artifact-collection")
    parser.add_argument("--base-dir")
    parser.add_argument("--output-dir")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.artifact_collection:
        extraction = build_source_content_extraction_from_collection(
            artifact_collection_path=args.artifact_collection,
            adapter_id=args.adapter_id,
            source_url=args.source_url,
            base_dir=args.base_dir,
        )
    else:
        if not args.artifact:
            raise SystemExit("at least one --artifact role=path is required when --artifact-collection is not used")
        extraction = build_source_content_extraction(
            adapter_id=args.adapter_id,
            source_url=args.source_url,
            artifacts=args.artifact,
            base_dir=args.base_dir,
        )
    verification = verify_source_content_extraction(extraction)
    if args.output_dir:
        result = write_source_content_extraction_store(extraction, Path(args.output_dir))
        result["verification"] = verification
    else:
        result = {"extraction": extraction, "verification": verification}
    print(json.dumps(result if args.json else result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
