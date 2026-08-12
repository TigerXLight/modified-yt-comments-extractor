from __future__ import annotations

import argparse
from source_offline_evidence_viewer import generate_offline_backup_viewer, print_generation_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate static offline evidence backup viewer for an MSN closeout folder.")
    parser.add_argument("--output-root", required=True, help="MSN closeout output root")
    args = parser.parse_args()
    result = generate_offline_backup_viewer(args.output_root)
    print_generation_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
