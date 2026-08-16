from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_workbench_panel import (  # noqa: E402
    build_profile_media_database_gui_panel_state,
    gui_panel_payload,
    render_profile_media_database_gui_panel_text,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render V76C profile/media Database GUI panel state.")
    parser.add_argument("--mode", default="DATABASE", choices=["FILES", "DATABASE"])
    parser.add_argument("--database-root", default="")
    parser.add_argument("--batch-json", action="append", default=[])
    parser.add_argument("--workbench-payload-json", default="")
    parser.add_argument("--print-panel", action="store_true")
    args = parser.parse_args()

    workbench_payload = None
    if args.workbench_payload_json:
        workbench_payload = json.loads(Path(args.workbench_payload_json).read_text(encoding="utf-8"))

    state = build_profile_media_database_gui_panel_state(
        mode=args.mode,
        database_root=args.database_root,
        batch_json_files=tuple(args.batch_json),
        workbench_payload=workbench_payload,
    )
    payload = gui_panel_payload(state)
    if args.print_panel:
        payload["panel_text"] = render_profile_media_database_gui_panel_text(state)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
