from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_database import ClaimBasis, CurrentnessStatus, MediaBucket, ProfileSourceRole
from profile_media_source_intake import (
    PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION,
    apply_source_intake_plan,
    build_source_intake_plan,
    coerce_claim_basis,
    coerce_currentness_status,
    coerce_source_role,
    render_source_intake_text,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_dry_run_plans_article_source_without_filesystem_work() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        plan = build_source_intake_plan(
            database_root=tmp,
            case_title="Example Case",
            source_page="BelfastLive",
            source_title="June 2026 - Example Article",
            source_bucket=MediaBucket.ARTICLES,
            source_role=ProfileSourceRole.TERTIARY_PROPAGATED_SOURCE,
            claim_basis=ClaimBasis.AGENCY_OR_OUTSIDE_RETELLING,
            currentness_status=CurrentnessStatus.CURRENT,
            source_chain_gap=True,
            disputed_framing=True,
            notes_on_context_dispute="Publisher framing disputed by original uploader.",
        )
        result = apply_source_intake_plan(plan)
        _assert(result.status == "planned_dry_run", result.status)
        _assert(result.folder_creation_performed is False, "dry-run must not create folders")
        _assert(result.file_write_performed is False, "dry-run must not write files")
        _assert("Sources\\Articles" in plan.source_folder_path or "Sources/Articles" in plan.source_folder_path, plan.source_folder_path)
        _assert("June 2026 - Example Article" in render_source_intake_text(plan), "plan text should identify source")
        _assert(plan.source_claim_evaluation.source_chain_gap is True, "source-chain gap should be retained")
        _assert(plan.source_claim_evaluation.disputed_framing is True, "disputed framing should be retained")
        _assert(plan.source_claim_evaluation.weak_sensitive_inference_prohibited is True, "weak sensitive inference must remain prohibited")


def test_social_media_online_and_internal_media_bucket_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        online = build_source_intake_plan(
            database_root=tmp,
            case_title="Example Case",
            source_page="https://x.com/example/status/1",
            source_title="Example Thread",
            source_bucket="Social Media/Online",
        )
        internal = build_source_intake_plan(
            database_root=tmp,
            case_title="Example Case",
            source_page="Creator note",
            source_title="Internal interview notes",
            source_bucket="Internal Media",
            source_role="PRIMARY_SELF_AUTHORED_SCOPE",
            claim_basis="SELF_AUTHORED_EXPERIENCE",
        )
        _assert("Social Media" in online.source_folder_path and "Online" in online.source_folder_path, online.source_folder_path)
        _assert("Internal Media" in internal.source_folder_path, internal.source_folder_path)
        _assert(internal.source_claim_evaluation.source_role == ProfileSourceRole.PRIMARY_SELF_AUTHORED_SCOPE, "role coercion failed")
        _assert(internal.source_claim_evaluation.claim_basis == ClaimBasis.SELF_AUTHORED_EXPERIENCE, "basis coercion failed")


def test_confirmation_gate_and_execute_manifest_write() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        blocked_plan = build_source_intake_plan(
            database_root=tmp,
            case_title="Example Case",
            source_page="USB acquired document",
            source_title="Scanned USB document",
            source_bucket="Social Media/Offline",
            execute=True,
            confirmation_phrase="WRONG",
        )
        blocked = apply_source_intake_plan(blocked_plan)
        _assert(blocked.status == "blocked_confirmation_required", blocked.status)
        _assert(not Path(blocked_plan.source_folder_path).exists(), "wrong confirmation should not create source folder")

        plan = build_source_intake_plan(
            database_root=tmp,
            case_title="Example Case",
            source_page="USB acquired document",
            source_title="Scanned USB document",
            source_bucket="Social Media/Offline",
            source_role=ProfileSourceRole.SECONDARY_WITNESS_ACCOUNT,
            claim_basis=ClaimBasis.WITNESS_ACCOUNT,
            currentness_status=CurrentnessStatus.HISTORICAL,
            confidence_or_verification_notes="Witnessed original document handling.",
            execute=True,
            confirmation_phrase=PROFILE_MEDIA_SOURCE_INTAKE_CONFIRMATION,
        )
        result = apply_source_intake_plan(plan)
        _assert(result.status == "created", result.status)
        _assert(result.folder_creation_performed is True, "confirmed source intake should create source folder")
        _assert(result.file_write_performed is True, "confirmed source intake should write manifests")
        payload = json.loads(Path(plan.manifest_json_path).read_text(encoding="utf-8"))
        _assert(payload["source_bucket"] == "Social Media/Offline", payload["source_bucket"])
        _assert(payload["source_claim_evaluation"]["source_role"] == "SECONDARY_WITNESS_ACCOUNT", payload)
        _assert(payload["file_copy_performed"] is False, "source intake must not copy media")
        _assert(payload["sensitive_identifier_inference_performed"] is False, "source intake must not infer identifiers")
        text = Path(plan.manifest_text_path).read_text(encoding="utf-8")
        _assert("Sensitive identifier inference prohibited: true" in text, text)


def test_enum_coercion_accepts_names_values_and_unknowns() -> None:
    _assert(coerce_source_role("PRIMARY_SELF_AUTHORED_SCOPE") == ProfileSourceRole.PRIMARY_SELF_AUTHORED_SCOPE, "source role by name failed")
    _assert(coerce_claim_basis("WITNESS_ACCOUNT") == ClaimBasis.WITNESS_ACCOUNT, "claim basis by name failed")
    _assert(coerce_currentness_status("CURRENT") == CurrentnessStatus.CURRENT, "currentness by name failed")
    _assert(coerce_source_role("not-real") == ProfileSourceRole.UNKNOWN_SOURCE_ROLE, "unknown role should fall back")


if __name__ == "__main__":
    test_dry_run_plans_article_source_without_filesystem_work()
    test_social_media_online_and_internal_media_bucket_paths()
    test_confirmation_gate_and_execute_manifest_write()
    test_enum_coercion_accepts_names_values_and_unknowns()
    print("profile_media_source_intake v75r OK")
