from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_reference_sources import write_twitter_reference_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the YTCE Twitter/X reference-source registry.")
    parser.add_argument("--output", default="twitter_reference_registry.json")
    parser.add_argument("--inspect-local-manifests", action="store_true")
    parser.add_argument("--local-root", action="append", default=[])
    args = parser.parse_args(argv)

    output = write_twitter_reference_registry(
        args.output,
        include_local_manifest_status=args.inspect_local_manifests,
        local_roots=args.local_root,
    )
    print(f"WROTE {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
