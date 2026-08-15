from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from twitter_reference_pack_index import build_reference_pack_index, write_reference_pack_index

def main(argv=None):
    p = argparse.ArgumentParser(description="Index a Twitter/X external reference source pack.")
    p.add_argument("--source", required=True)
    p.add_argument("--output", default="twitter_reference_pack_index.json")
    a = p.parse_args(argv)
    idx = build_reference_pack_index(a.source)
    write_reference_pack_index(a.source, a.output)
    print(f"WROTE {a.output}")
    print(f"TOTAL_PATHS {idx.total_paths}")
    print(f"HIGH_PRIORITY_SOURCES {len(idx.high_priority_sources)}")
    print(f"EXTRA_CAPTURE_SOURCES {len(idx.extra_capture_sources)}")
    for c in idx.clusters: print(f"CLUSTER {c.cluster_id} {len(c.matched_paths)}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
