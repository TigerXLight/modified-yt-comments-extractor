from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_runtime import (
    build_profile_media_runtime_state,
    load_profile_media_runtime_state,
    save_profile_media_runtime_state,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile/media Database runtime mode helper (V75P).")
    parser.add_argument("--state-path", required=True, help="JSON state path to read/write.")
    parser.add_argument("--set-mode", choices=("FILES", "DATABASE"), default=None, help="Persist a mode-only state.")
    args = parser.parse_args()

    state_path = Path(args.state_path)
    if args.set_mode:
        state = save_profile_media_runtime_state(build_profile_media_runtime_state(args.set_mode), state_path)
    else:
        state = load_profile_media_runtime_state(state_path)

    print(json.dumps({
        "schema_version": state.schema_version,
        "status": "success",
        "state_path": str(state_path),
        "sidebar_mode": state.sidebar_mode,
        "filesystem_work_performed": state.filesystem_work_performed,
        **state.safety_claims,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
