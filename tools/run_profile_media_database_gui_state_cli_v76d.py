from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_gui_controller import (
    build_database_gui_clear_selection,
    build_database_gui_selection_from_batch_json,
    build_database_gui_selection_from_saved_state,
    database_gui_selection_result_payload,
    render_database_gui_selection_text,
)
from profile_media_database_gui_state_store import (
    PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION,
    PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile/media Database GUI state controller proof CLI v76d")
    parser.add_argument("--batch-json", action="append", default=[])
    parser.add_argument("--database-root", default="")
    parser.add_argument("--state-path", default="")
    parser.add_argument("--save-state", action="store_true")
    parser.add_argument("--load-state", action="store_true")
    parser.add_argument("--clear-state", action="store_true")
    parser.add_argument("--print-text", action="store_true")
    args = parser.parse_args(argv)

    state_path = args.state_path or None
    if args.clear_state:
        result = build_database_gui_clear_selection(
            state_path=state_path,
            clear_persisted_state=True,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_CLEAR_CONFIRMATION,
        )
    elif args.load_state:
        result = build_database_gui_selection_from_saved_state(state_path=state_path)
    else:
        result = build_database_gui_selection_from_batch_json(
            args.batch_json,
            database_root=args.database_root,
            state_path=state_path,
            persist_state=args.save_state,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_GUI_STATE_SAVE_CONFIRMATION if args.save_state else "",
        )

    payload = database_gui_selection_result_payload(result, include_text=True)
    if args.print_text:
        print(render_database_gui_selection_text(result))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
