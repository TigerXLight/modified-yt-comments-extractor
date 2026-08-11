from __future__ import annotations

import argparse
from pathlib import Path

from source_archive_discovery import discover_archives, normalize_target_url, write_discovery_sidecars
from source_capture_interaction_metadata import build_interaction_metadata, write_interaction_sidecars


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write Memento/Mink archive discovery and WARCreate-style interaction sidecars.")
    parser.add_argument("--target-url", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--capture-root", action="append", default=[])
    parser.add_argument("--production-root", action="append", default=[])
    parser.add_argument("--no-network", action="store_true")
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    normalized = normalize_target_url(args.target_url)
    discovery = discover_archives(args.target_url, network=not args.no_network)
    discovery_json, discovery_txt = write_discovery_sidecars(discovery, output_dir)
    interaction = build_interaction_metadata(
        target_url=args.target_url,
        normalized_target_url=normalized,
        capture_roots=args.capture_root,
        production_roots=args.production_root,
    )
    interaction_json, interaction_txt = write_interaction_sidecars(interaction, output_dir)
    print("ARCHIVE_DISCOVERY_JSON:", discovery_json)
    print("ARCHIVE_DISCOVERY_TXT:", discovery_txt)
    print("INTERACTION_METADATA_JSON:", interaction_json)
    print("INTERACTION_METADATA_TXT:", interaction_txt)
    print("OUTPUT_DIR=", output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
