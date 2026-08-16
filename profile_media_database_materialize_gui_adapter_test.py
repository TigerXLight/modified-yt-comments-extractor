from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from profile_media_case_batch import build_demo_case_batch_payload
from profile_media_database_materialize_gui_adapter import build_materialize_gui_payload, materialize_gui_payload_dict
from profile_media_database_materialize_workflow import (
    PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
    apply_database_materialize_plan,
    build_database_materialize_plan,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "db"
        batch = Path(tmp) / "batch.json"
        batch.write_text(json.dumps(build_demo_case_batch_payload(database_root=str(root), case_title="V76F GUI Demo")), encoding="utf-8")
        plan = build_database_materialize_plan(database_root=str(root), batch_json_files=[str(batch)])
        review_payload = build_materialize_gui_payload(plan)
        assert review_payload.status == "ready_for_confirmation"
        assert review_payload.batch_json_file_count == 1
        assert review_payload.review_source_count == 2
        assert review_payload.review_profile_count == 2
        assert review_payload.folder_scan_performed is False
        assert review_payload.file_write_performed is False
        assert any(action.status == "guarded_confirmation_required" for action in review_payload.actions)

        exec_plan = build_database_materialize_plan(
            database_root=str(root),
            batch_json_files=[str(batch)],
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
        )
        result = apply_database_materialize_plan(exec_plan)
        executed_payload = build_materialize_gui_payload(exec_plan, result)
        data = materialize_gui_payload_dict(executed_payload)
        assert data["status"] == "materialized"
        assert data["folder_creation_performed"] is True
        assert data["file_write_performed"] is True
        assert data["folder_scan_performed"] is False
        assert data["media_download_performed"] is False

    print("profile_media_database_materialize_gui_adapter v76f OK")


if __name__ == "__main__":
    main()
