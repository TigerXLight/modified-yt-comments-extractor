#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_bounded_debug_zip_r42ef import build_bounded_debug_zip  # noqa: E402


def main() -> int:
    summary = build_bounded_debug_zip(root=ROOT, label="r42ef_bounded_debug_zip64_hotfix_upload", print_json=True)
    return 0 if summary.verdict.get("ready_for_upload") else 2


if __name__ == "__main__":
    raise SystemExit(main())
