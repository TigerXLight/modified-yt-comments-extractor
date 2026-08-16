from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_database_folder_operations import (
    PROFILE_MEDIA_DATABASE_FOLDER_OPERATIONS_CONFIRMATION,
    build_demo_folder_operations_payload,
    build_folder_operations_plan,
    folder_operations_payload,
    render_folder_operations_plan_text,
    write_demo_folder_operations_json,
)
from profile_media_database_folder_operations_gui_adapter import build_folder_operations_gui_payload


def _prepare_demo_tree(root: Path) -> None:
    (root / "Cases" / "Demo Case" / "Sources" / "Articles" / "Old Article Folder").mkdir(parents=True, exist_ok=True)
    (root / "Cases" / "Demo Case" / "Sources" / "Social Media" / "Online" / "Misfiled Offline Bundle").mkdir(parents=True, exist_ok=True)
    (root / "Cases" / "Demo Case" / "Sources" / "Social Media" / "Offline").mkdir(parents=True, exist_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run V76G reviewed folder operations workflow")
    parser.add_argument("--database-root", default="")
    parser.add_argument("--operations-json", default="")
    parser.add_argument("--write-demo-operations", default="")
    parser.add_argument("--prepare-demo-tree", action="store_true")
    parser.add_argument("--reset-demo-tree", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirmation", default="")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--print-gui-payload", action="store_true")
    args = parser.parse_args(argv)

    if args.write_demo_operations:
        write_demo_folder_operations_json(args.write_demo_operations)
        if not args.operations_json:
            args.operations_json = args.write_demo_operations

    root = Path(args.database_root or "")
    if args.reset_demo_tree and root:
        shutil.rmtree(root, ignore_errors=True)
    if args.prepare_demo_tree and root:
        _prepare_demo_tree(root)

    if not args.operations_json:
        payload = build_demo_folder_operations_payload()
        operations_json_path = None
    else:
        payload = None
        operations_json_path = args.operations_json

    plan = build_folder_operations_plan(
        database_root=args.database_root,
        operations_payload=payload,
        operations_json_path=operations_json_path,
        execute=args.execute,
        confirmation_phrase=args.confirmation,
    )
    if args.print_gui_payload:
        gui_payload = build_folder_operations_gui_payload(
            database_root=args.database_root,
            operations_payload=payload,
            operations_json_path=operations_json_path,
            execute=args.execute,
            confirmation_phrase=args.confirmation,
        )
        print(json.dumps(gui_payload, indent=2, sort_keys=True))
    else:
        from profile_media_database_folder_operations import apply_folder_operations_plan
        result = apply_folder_operations_plan(plan)
        payload_out = folder_operations_payload(result, plan=plan)
        if args.print_plan:
            payload_out["plan_text"] = render_folder_operations_plan_text(plan)
        print(json.dumps(payload_out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
