from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_database_materialize_workflow import (
    PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
    apply_database_materialize_plan,
    build_database_materialize_plan,
    materialize_workflow_payload,
)
from profile_media_case_batch import build_demo_case_batch_payload


def _write_batch(path: Path, database_root: Path) -> None:
    payload = build_demo_case_batch_payload(database_root=str(database_root), case_title="V76F Controlled Demo Case")
    payload["sources"][1]["source_role"] = "SECONDARY_WITNESS_SOURCE"
    payload["profiles"][1]["source_role"] = "SECONDARY_WITNESS_SOURCE"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        root = tmp_path / "db"
        batch = tmp_path / "batch.json"
        _write_batch(batch, root)

        plan = build_database_materialize_plan(database_root=str(root), batch_json_files=[str(batch)])
        assert plan.batch_reviews[0].status == "ready"
        dry = apply_database_materialize_plan(plan)
        assert dry.status == "planned_dry_run"
        assert dry.folder_creation_performed is False
        assert dry.file_write_performed is False
        assert not root.exists()

        blocked_plan = build_database_materialize_plan(database_root=str(root), batch_json_files=[str(batch)], execute=True, confirmation_phrase="WRONG")
        blocked = apply_database_materialize_plan(blocked_plan)
        assert blocked.status == "blocked_confirmation_required"
        assert blocked.folder_creation_performed is False
        assert blocked.file_write_performed is False
        assert not root.exists()

        exec_plan = build_database_materialize_plan(
            database_root=str(root),
            batch_json_files=[str(batch)],
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_DATABASE_MATERIALIZE_CONFIRMATION,
        )
        result = apply_database_materialize_plan(exec_plan)
        assert result.status == "materialized", result.to_dict()
        assert result.folder_creation_performed is True
        assert result.file_write_performed is True
        assert result.folder_scan_performed is False
        assert result.folder_move_performed is False
        assert result.folder_rename_performed is False
        assert result.file_copy_performed is False
        assert result.media_download_performed is False
        assert result.automatic_classification_performed is False
        assert result.sensitive_identifier_inference_performed is False
        assert root.exists()
        assert len(result.written_files) >= 6
        source_records = [Path(item) for item in result.written_files if item.endswith("source_claim_evaluation.json")]
        assert source_records
        joined = "\n".join(path.read_text(encoding="utf-8") for path in source_records)
        assert "SECONDARY_WITNESS_ACCOUNT" in joined
        assert "SECONDARY_WITNESS_SOURCE" not in joined
        payload = materialize_workflow_payload(result, plan=exec_plan)
        assert payload["plan"]["confirmation_valid"] is True
        assert payload["written_file_count"] == len(result.written_files)

    print("profile_media_database_materialize_workflow v76f OK")


if __name__ == "__main__":
    main()
