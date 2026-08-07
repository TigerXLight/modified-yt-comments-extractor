from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_extraction_bridge import build_source_adapter_extraction_bridge
from source_adapter_extraction_bridge_store import store_source_adapter_extraction_bridge


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a shared Adapter Extraction Bridge package.")
    parser.add_argument("--artifact-intake-json", required=True, help="Adapter Artifact Intake package JSON.")
    parser.add_argument("--artifact-files-json", required=True, help="Explicit artifact file bindings JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for store artifacts.")
    parser.add_argument("--source-url", default="", help="Fallback source URL when collections do not include one.")
    args = parser.parse_args(argv)

    intake = _load_json(args.artifact_intake_json)
    artifact_files = _load_json(args.artifact_files_json)
    package = build_source_adapter_extraction_bridge(intake, artifact_files, source_url=args.source_url)
    result = store_source_adapter_extraction_bridge(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
