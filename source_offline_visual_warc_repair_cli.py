from __future__ import annotations

import argparse
from source_offline_visual_warc_repair import DEFAULT_TARGET_URL, generate_static_visual_replay, print_generation_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate static MSN visual replay HTML/WARC from local closeout artifacts.")
    parser.add_argument("--output-root", required=True, help="MSN closeout output root")
    parser.add_argument("--target-url", default=DEFAULT_TARGET_URL, help="Synthetic WARC target URL")
    args = parser.parse_args()
    result = generate_static_visual_replay(args.output_root, target_url=args.target_url)
    print_generation_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
