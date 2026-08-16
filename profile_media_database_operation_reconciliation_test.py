from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from profile_media_database_operation_reconciliation import (
    PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION,
    build_batch_reconciliation_plan,
    reconciliation_payload,
    render_batch_reconciliation_plan_text,
    write_reconciled_batch_preview_if_confirmed,
)


def _batch_payload() -> dict:
    return {
        "database_root": "Demo Database",
        "case_title": "V76I Demo Case",
        "sources": [
            {
                "source_title": "Old Article Folder",
                "source_bucket": "Articles",
                "source_role": "UNKNOWN_SOURCE_ROLE",
                "claim_basis": "UNKNOWN_CLAIM_BASIS",
                "currentness_status": "UNKNOWN",
            },
            {
                "source_title": "Misfiled Offline Bundle",
                "source_bucket": "Social Media/Online",
                "source_role": "UNKNOWN_SOURCE_ROLE",
                "claim_basis": "UNKNOWN_CLAIM_BASIS",
                "currentness_status": "UNKNOWN",
            },
        ],
        "profiles": [],
    }


def _operations_payload() -> dict:
    return {
        "operations": [
            {
                "operation_id": "op_rename",
                "operation_type": "rename_folder",
                "source_path": "Cases/V76I Demo Case/Sources/Articles/Old Article Folder",
                "destination_path": "Cases/V76I Demo Case/Sources/Articles/Renamed Article Folder",
            },
            {
                "operation_id": "op_move",
                "operation_type": "move_folder",
                "source_path": "Cases/V76I Demo Case/Sources/Social Media/Online/Misfiled Offline Bundle",
                "destination_path": "Cases/V76I Demo Case/Sources/Social Media/Offline/Misfiled Offline Bundle",
            },
        ]
    }


def test_reconciliation_updates_source_title_and_bucket_without_writing() -> None:
    plan = build_batch_reconciliation_plan(batch_payload=_batch_payload(), operations_payload=_operations_payload())
    payload = reconciliation_payload(plan)
    sources = payload["reconciled_payload"]["sources"]
    assert payload["change_count"] == 2
    assert sources[0]["source_title"] == "Renamed Article Folder"
    assert sources[0]["source_bucket"] == "Articles"
    assert sources[1]["source_title"] == "Misfiled Offline Bundle"
    assert sources[1]["source_bucket"] == "Social Media/Offline"
    assert payload["folder_scan_performed"] is False
    assert payload["folder_move_performed"] is False
    assert payload["folder_rename_performed"] is False
    assert payload["file_write_performed"] is False
    assert "Changes: 2" in render_batch_reconciliation_plan_text(plan)


def test_guarded_write_requires_confirmation() -> None:
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "reconciled.json"
        plan = build_batch_reconciliation_plan(
            batch_payload=_batch_payload(),
            operations_payload=_operations_payload(),
            output_batch_json=out,
        )
        blocked = write_reconciled_batch_preview_if_confirmed(plan, confirmation_phrase="WRONG")
        assert blocked.status == "blocked_confirmation_required"
        assert not out.exists()
        written = write_reconciled_batch_preview_if_confirmed(
            plan,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_RECONCILIATION_WRITE_CONFIRMATION,
        )
        assert written.status == "reconciled_batch_preview_written"
        assert written.file_write_performed is True
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["sources"][0]["source_title"] == "Renamed Article Folder"
        assert data["sources"][1]["source_bucket"] == "Social Media/Offline"


def main() -> int:
    test_reconciliation_updates_source_title_and_bucket_without_writing()
    test_guarded_write_requires_confirmation()
    print("profile_media_database_operation_reconciliation v76i OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
