from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from source_adapter_capture_action_kit import build_source_adapter_capture_action_kit
from source_adapter_capture_action_kit_store import store_source_adapter_capture_action_kit


def _load_json(path: str | Path) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a shared Adapter Capture Action Kit package.")
    parser.add_argument("--capture-setup-json", required=True, help="Adapter Capture Setup package JSON.")
    parser.add_argument("--output-dir", help="Optional output directory for store artifacts.")
    parser.add_argument("--operator-profile-json", help="Optional local operator profile metadata JSON.")
    args = parser.parse_args(argv)

    capture_setup = _load_json(args.capture_setup_json)
    operator_profile = _load_json(args.operator_profile_json) if args.operator_profile_json else None
    package = build_source_adapter_capture_action_kit(capture_setup, operator_profile=operator_profile)
    result = store_source_adapter_capture_action_kit(package, args.output_dir) if args.output_dir else package
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
