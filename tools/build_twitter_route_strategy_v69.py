from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from twitter_route_strategy import build_twitter_route_strategy, write_twitter_route_strategy

def main(argv=None):
    p = argparse.ArgumentParser(description="Build a Twitter/X route strategy manifest.")
    p.add_argument("--source-url", required=True)
    p.add_argument("--capture-goal", default="")
    p.add_argument("--output-dir", default="")
    p.add_argument("--capability-manifest", default="jd_capabilities_manifest.json")
    p.add_argument("--block-untested-jd", action="store_true")
    p.add_argument("--output", default="")
    a = p.parse_args(argv)
    s = build_twitter_route_strategy(a.source_url, capture_goal=a.capture_goal, output_dir=a.output_dir, allow_untested_jdownloader=not a.block_untested_jd, capability_manifest_path=a.capability_manifest)
    if a.output:
        write_twitter_route_strategy(a.output, s); print(f"WROTE {a.output}")
    print(json.dumps(s.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    return 0
if __name__ == "__main__": raise SystemExit(main())
