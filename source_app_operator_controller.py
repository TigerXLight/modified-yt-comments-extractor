from __future__ import annotations

import tempfile
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from evidence_database_operator_workflow import (
    DatabaseOperatorWorkflowStatus,
    build_database_migration_operator_preview,
    execute_database_migration_operator_preview,
    propose_database_taxonomy_path,
    scan_temp_evidence_database_tree,
)
from evidence_movement_approval import EvidenceMovementMode
from capture_media_download import build_media_component_record, build_separate_av_mux_plan
from source_archive_execution_bridge import (
    ArchiveProviderKind,
    build_archive_today_check_request,
    build_archive_today_submit_request,
    build_archivebox_default_execution_plans,
    build_wayback_availability_request,
    build_wayback_submit_request,
    execute_archive_http_request,
    interpret_archive_today_check_response,
    interpret_wayback_availability_response,
)
from source_live_smoke_runner import (
    build_live_smoke_runner_plan_collection,
    evaluate_live_smoke_runner_plan,
    import_manual_live_smoke_result,
)
from source_media_execution_bridge import (
    copy_selected_local_media_files,
    execute_ffmpeg_mux_plan,
    execute_yt_dlp_command,
)
from source_operator_approval_gateway import (
    OperatorApprovalToken,
    OperatorExecutionAction,
    OperatorExecutionScope,
    build_operator_approval_gateway_summary,
    build_operator_approval_token,
)
from source_url_files_bridge import (
    SourceUrlFilesBridgeState,
    accept_source_url_on_enter,
    build_default_source_url_files_bridge_state,
    clear_editor_transcript_without_deleting_file,
    inject_source_url_choice_to_files,
    replace_editor_transcript_without_deleting_previous,
    set_discussion_screenshot_tick,
    set_discussion_source_selector,
    set_source_url_download_tick,
    validate_source_url_files_bridge_state,
)
from source_unified_execution_runner import (
    UnifiedExecutionJobOptions,
    run_unified_local_execution_job,
)


SOURCE_APP_OPERATOR_CONTROLLER_SCHEMA_VERSION = "source_app_operator_controller_v1"


def _value_for_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _value_for_dict(value[key]) for key in sorted(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


@dataclass(frozen=True)
class AppOperatorControllerState:
    controller_id: str
    source_url_files: Mapping[str, Any]
    operator_approval: Mapping[str, Any]
    unified_execution: Mapping[str, Any]
    local_e2e_total_export: Mapping[str, Any]
    database_movement: Mapping[str, Any]
    live_smoke: Mapping[str, Any]
    archive_media_archivebox_launch: Mapping[str, Any]
    receipt_import_review: Mapping[str, Any]
    access_online_asr_preservation: Mapping[str, Any]
    schema_version: str = SOURCE_APP_OPERATOR_CONTROLLER_SCHEMA_VERSION
    no_live_execution_performed: bool = True
    no_credentials_read: bool = True
    no_asr_run: bool = True
    no_user_evidence_files_moved: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["controller_surface_count"] = 9
        return data


def _safe_id(prefix: str, *parts: object) -> str:
    import hashlib
    import json

    payload = json.dumps(_value_for_dict(parts), sort_keys=True, separators=(",", ":"))
    return f"{prefix}_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_source_url_files_controller_state(
    *,
    state: SourceUrlFilesBridgeState | None = None,
    accepted_url: str = "https://example.invalid/story",
    fixture_html: str = "<html><body><img src='/image.jpg'><video src='/video.mp4'></video></body></html>",
) -> dict[str, Any]:
    working = state or build_default_source_url_files_bridge_state()
    accepted = accept_source_url_on_enter(
        working,
        url=accepted_url,
        fixture_html_by_url={accepted_url: fixture_html},
    )
    first_choice_id = ""
    for row in accepted.source_rows:
        for choice in row.get("resource_choices", ()):
            first_choice_id = str(choice.get("choice_id") or "")
            break
        if first_choice_id:
            break
    ticked = set_source_url_download_tick(accepted, choice_id=first_choice_id, selected=True) if first_choice_id else accepted
    injected = inject_source_url_choice_to_files(ticked, choice_id=first_choice_id) if first_choice_id else ticked
    selected = set_discussion_source_selector(injected, source_row_id=injected.comments_livechat_dropdown_source_id or "source_row_1")
    comments_screenshot = set_discussion_screenshot_tick(selected, mode="comments", selected=True)
    livechat_screenshot = set_discussion_screenshot_tick(comments_screenshot, mode="livechat", selected=True)
    cleared = clear_editor_transcript_without_deleting_file(livechat_screenshot)
    replaced = replace_editor_transcript_without_deleting_previous(cleared, choice_id=first_choice_id) if first_choice_id else cleared
    data = replaced.to_dict()
    data.update(
        {
            "controller_id": _safe_id("source_url_files_controller", data.get("bridge_id")),
            "url_enter_accepts_source": True,
            "resolved_title_row_available": bool(data.get("source_rows")),
            "image_icon_state": data.get("image_icon_enabled", False),
            "video_audio_icon_state": data.get("video_audio_icon_enabled", False),
            "archive_org_icon_state": data.get("archive_org_icon_enabled", False),
            "archive_today_icon_state": data.get("archive_today_icon_enabled", False),
            "comments_source_dropdown_state": "enabled" if data.get("comments_livechat_dropdown_source_id") else "disabled",
            "livechat_source_dropdown_state": "enabled" if data.get("comments_livechat_dropdown_source_id") else "disabled",
            "comments_screenshot_tick": data.get("comments_screenshot_requested", False),
            "livechat_screenshot_tick": data.get("livechat_screenshot_requested", False),
            "inject_icon_count": data.get("media_transcript_inject_icon_count", 0),
            "download_tick_count": data.get("media_row_download_tick_count", 0),
            "files_hierarchy_pinned": data.get("injected_files_pinned_top", False),
            "sort_modes": ["injected_first_then_newest", "newest", "oldest", "name"],
            "validation_errors": list(validate_source_url_files_bridge_state(replaced)),
        }
    )
    return data


def build_operator_approval_controller_state(
    *,
    token: OperatorApprovalToken | None = None,
    requested_scope: OperatorExecutionScope = OperatorExecutionScope.PREVIEW_ONLY,
) -> dict[str, Any]:
    actions = tuple(OperatorExecutionAction)
    summary = build_operator_approval_gateway_summary(actions, token=token, requested_scope=requested_scope)
    rows = []
    for decision in summary.decisions:
        rows.append(
            {
                "action": decision.action.value,
                "status": decision.status.value,
                "allowed_to_execute": decision.allowed_to_execute,
                "blocked_reason_text": "; ".join(decision.reasons) or "",
                "requires_external_network_approval": decision.requires_external_network_approval,
                "requires_user_evidence_approval": decision.requires_user_evidence_approval,
                "requires_subprocess_approval": decision.requires_subprocess_approval,
                "requires_asr_approval": decision.requires_asr_approval,
            }
        )
    return {
        "controller_id": _safe_id("operator_approval_controller", summary.summary_id),
        "summary": summary.to_dict(),
        "approval_preview_rows": rows,
        "required_approval_flags": sorted(
            {
                flag
                for row in rows
                for flag, required in (
                    ("external_network", row["requires_external_network_approval"]),
                    ("user_evidence", row["requires_user_evidence_approval"]),
                    ("subprocess", row["requires_subprocess_approval"]),
                    ("asr", row["requires_asr_approval"]),
                )
                if required
            }
        ),
        "asr_readiness_state": "readiness_only_no_asr_run",
        "credentials_read": False,
    }


def build_unified_execution_controller_state(
    *,
    source_url: str = "https://example.invalid/story",
    output_root: str | Path | None = None,
    preview_only: bool = True,
) -> dict[str, Any]:
    token = None
    if not preview_only:
        token = build_operator_approval_token(
            actions=(
                OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
                OperatorExecutionAction.SCREENSHOT_CAPTURE,
                OperatorExecutionAction.ARTICLE_CAPTURE,
                OperatorExecutionAction.PAGE_OUTLINE_CAPTURE,
                OperatorExecutionAction.COMMENTS_CAPTURE,
                OperatorExecutionAction.LIVECHAT_CAPTURE,
                OperatorExecutionAction.MEDIA_DOWNLOAD_COPY,
                OperatorExecutionAction.ARCHIVE_CHECK,
                OperatorExecutionAction.OFFLINE_BUNDLE_WRITE,
            ),
            scope=OperatorExecutionScope.LOCAL_TEMP,
            approved_by_operator=True,
            approval_note="local temp fixture execution controller approval",
            allow_external_network=True,
        )
    target_root = Path(output_root) if output_root is not None else Path(tempfile.mkdtemp(prefix="source_app_job_"))
    media_source = target_root / "_media_source.txt"
    media_source.parent.mkdir(parents=True, exist_ok=True)
    media_source.write_text("fixture-media", encoding="utf-8")
    result = run_unified_local_execution_job(
        source_url=source_url,
        fixture_html="""
        <html><body>
          <article><h1>Fixture story</h1><p>Fixture article text.</p></article>
          <section id="comments"><p data-comment-id="c1">Fixture comment</p></section>
        </body></html>
        """,
        output_directory=target_root,
        options=UnifiedExecutionJobOptions(
            run_browser_capture=True,
            run_media_copy=True,
            run_archive_check=True,
            write_offline_bundle=True,
            selected_media_resource_ids=("media_1",),
        ),
        approval_token=token,
        media_resources=(
            {
                "resource_id": "media_1",
                "path": str(media_source),
                "media_type": "text_fixture",
            },
        ),
        archive_http_client=lambda request: {
            "status": 200,
            "body": '{"archived_snapshots":{"closest":{"available":true,"url":"https://web.archive.org/fixture"}}}',
            "archive_url": "https://web.archive.org/fixture",
        },
    )
    return {
        "controller_id": _safe_id("unified_execution_controller", result.job_id),
        "job_id": result.job_id,
        "preview_mode": preview_only,
        "approved_local_temp_execution": not preview_only,
        "status": result.status.value,
        "progress_events": [event.to_dict() for event in result.progress_events],
        "artifact_paths": list(result.artifact_names),
        "hashes": list(result.artifact_hashes),
        "result_summary": result.to_dict(),
        "behavior_provenance_log_summary": {
            "event_labels": list(result.behavior_event_labels),
            "redaction_applied": result.redaction_applied,
        },
        "sidecar_summary": {"execution_job_result": result.job_id, "path_names_only": True},
    }


def build_local_e2e_total_export_controller_state(*, output_root: str | Path) -> dict[str, Any]:
    from source_local_e2e_export import write_local_e2e_fixture_total_export

    result = write_local_e2e_fixture_total_export(
        output_directory=output_root,
        fixture_html="<html><body><article><h1>Fixture</h1><p>Local E2E article.</p></article></body></html>",
        selected_media_payloads=(("media.txt", b"fixture-media", "text_fixture"),),
    )
    return {
        "controller_id": _safe_id("local_e2e_total_export_controller", result.package_name),
        "package_id": result.package_name,
        "package_directory_name": result.package_name,
        "status": result.status.value,
        "manifest_file_name": result.manifest_name,
        "asset_count": len(result.asset_names),
        "artifact_names": tuple(Path(path).name for path in result.asset_names),
        "hash_count": len(result.asset_hashes),
        "offline_bundle_written": bool(result.offline_bundle_name),
        "completed_evidence_receipt_created": bool(result.completed_evidence_receipt_id),
        "result": result.to_dict(),
    }


def build_database_movement_controller_state(
    *,
    source_root: str | Path,
    destination_root: str | Path,
    execute: bool = False,
    mode: str = "copy",
) -> dict[str, Any]:
    movement_mode = EvidenceMovementMode(mode)
    scan = scan_temp_evidence_database_tree(source_root)
    scan_row = scan.rows[0] if scan.rows else None
    if scan_row is None:
        return {
            "controller_id": _safe_id("database_movement_controller", str(source_root), "empty"),
            "scan_row_count": 0,
            "status": DatabaseOperatorWorkflowStatus.APPROVAL_REQUIRED.value,
            "no_automatic_classification": True,
            "sensitive_inference_prohibited": True,
        }
    taxonomy_path = propose_database_taxonomy_path(
        database_name=Path(destination_root).name or "database",
        category_parts=("review", "operator_confirmed"),
        item_label=scan_row.file_name,
    )
    preview = build_database_migration_operator_preview(
        root=source_root,
        scan_row=scan_row,
        taxonomy_path=taxonomy_path,
        mode=movement_mode,
    )
    token = ""
    execution = None
    if execute:
        token = "approved-temp-fixture-movement"
        execution = execute_database_migration_operator_preview(
            preview,
            approved_root=source_root,
            approved_by_operator=True,
        )
    return {
        "controller_id": _safe_id("database_movement_controller", preview.preview_id, execute),
        "scan_row_count": scan.row_count,
        "review_needed_count": scan.row_count,
        "preview": preview.to_dict(),
        "copy_move_mode": movement_mode.value,
        "approval_token_required": True,
        "approval_token_supplied": bool(token),
        "execution_receipt": execution.to_dict() if execution else {},
        "old_new_path_history": [
            {
                "old_path_name": scan_row.file_name,
                "new_path_name": Path(str(preview.proposed_relative_path)).name,
            }
        ],
        "completed_evidence_receipt_created": bool(execution and execution.completed_evidence_receipt),
        "no_automatic_classification": True,
        "sensitive_inference_prohibited": True,
    }


def build_manual_live_smoke_helper_controller_state(
    *,
    source_url: str = "https://example.invalid/story",
    method_ids: Sequence[str] = (),
) -> dict[str, Any]:
    collection = build_live_smoke_runner_plan_collection(source_url=source_url)
    if method_ids:
        allowed = set(method_ids)
        collection = type(collection)(
            collection_id=collection.collection_id,
            plans=tuple(plan for plan in collection.plans if plan.method_id in allowed),
        )
    decisions = tuple(evaluate_live_smoke_runner_plan(plan) for plan in collection.plans)
    imports = tuple(
        import_manual_live_smoke_result(
            collection.plans[0],
            operator_result_summary={"status": "dry_run_import_preview", "artifact_count": 0},
        ).to_dict()
    ) if collection.plans else ()
    return {
        "controller_id": _safe_id("manual_live_smoke_helper_controller", collection.collection_id),
        "collection": collection.to_dict(),
        "dry_run_decisions": [decision.to_dict() for decision in decisions],
        "receipt_import_preview": list(imports),
        "live_execution_performed": False,
        "approval_required": True,
        "output_receipt_path_required": True,
    }


def build_archive_media_archivebox_launch_controller_state(*, output_root: str | Path | None = None) -> dict[str, Any]:
    output = Path(output_root) if output_root is not None else Path(tempfile.mkdtemp(prefix="source_launch_"))
    target_url = "https://example.invalid/story"

    class FakeArchiveHttpClient:
        def __call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
            url = str(getattr(request, "url", "") or request.get("url") if isinstance(request, Mapping) else "")
            if "available" in url:
                return {"status_code": 200, "body": '{"archived_snapshots":{"closest":{"available":true,"url":"https://web.archive.org/fixture"}}}'}
            if "archive.ph" in url:
                return {"status_code": 200, "body": "challenge/manual review required"}
            return {"status_code": 200, "body": "fixture ok"}

    fake_client = FakeArchiveHttpClient()
    wayback_check = execute_archive_http_request(
        build_wayback_availability_request(target_url),
        http_client=fake_client,
    )
    archive_today_check = execute_archive_http_request(
        build_archive_today_check_request(target_url),
        http_client=fake_client,
    )
    media_source = output / "local-media.txt"
    media_source.parent.mkdir(parents=True, exist_ok=True)
    media_source.write_text("fixture-media", encoding="utf-8")
    media_queue = copy_selected_local_media_files(
        resources=(
            {"resource_id": "media_1", "path": str(media_source), "media_type": "text_fixture"},
        ),
        output_directory=output / "media",
        selected_resource_ids=("media_1",),
    )
    mux_plan = build_separate_av_mux_plan(
        video_component=build_media_component_record(resource_id="v", role="video", path=str(media_source)),
        audio_component=build_media_component_record(resource_id="a", role="audio", path=str(media_source)),
        output_path=str(output / "muxed.mp4"),
    )
    ffmpeg_preview = execute_ffmpeg_mux_plan(
        mux_plan,
        dry_run=True,
    )
    ytdlp_preview = execute_yt_dlp_command(
        command=("yt-dlp", target_url, "-o", str(output / "%(id)s.%(ext)s")),
        dry_run=True,
    )
    archivebox_plans = build_archivebox_default_execution_plans(target_url)
    return {
        "controller_id": _safe_id("archive_media_archivebox_launch_controller", target_url),
        "wayback_check": wayback_check.to_dict(),
        "wayback_interpretation": interpret_wayback_availability_response(wayback_check).to_dict(),
        "wayback_submit_preview": build_wayback_submit_request(target_url, explicit_submit_granted=False).to_dict(),
        "archive_today_check": archive_today_check.to_dict(),
        "archive_today_interpretation": interpret_archive_today_check_response(archive_today_check).to_dict(),
        "archive_today_submit_preview": build_archive_today_submit_request(target_url, explicit_submit_granted=False).to_dict(),
        "archive_challenge_manual_handoff_state": "manual_handoff_required_when_challenge_detected",
        "media_selected_download_queue": media_queue.to_dict(),
        "local_media_copy_receipt_count": len(media_queue.local_copy_receipts),
        "ffmpeg_mux_preview": ffmpeg_preview.to_dict(),
        "yt_dlp_preview": ytdlp_preview.to_dict(),
        "archivebox_command_previews": [plan.to_dict() for plan in archivebox_plans],
        "archivebox_approved_execution_state": "approval_required_not_run",
        "fake_http_used": True,
        "mocked_subprocess_required_for_execution_tests": True,
        "external_network_performed": False,
        "real_subprocess_performed": False,
        "archive_provider_kind": ArchiveProviderKind.WAYBACK.value,
    }


def build_access_online_asr_preservation_controller_state() -> dict[str, Any]:
    return {
        "controller_id": "access_online_asr_preservation_controller_v1",
        "keys_accounts_sidebar_label": "KEYS/ACCOUNTS",
        "access_keys_window_title": "Access & Keys",
        "added_providers_vs_catalogue_split": True,
        "online_asr_readiness_without_provider_calls": True,
        "local_asr_preferred_profile": {
            "engine": "whispercpp_vulkan",
            "model": "large-v3",
            "device": "vulkan",
        },
        "credentials_read": False,
        "provider_call_performed": False,
        "asr_job_run": False,
    }


def build_app_operator_controller_state() -> AppOperatorControllerState:
    source_url_files = build_source_url_files_controller_state()
    approval = build_operator_approval_controller_state()
    unified_preview = build_unified_execution_controller_state(preview_only=True)
    with tempfile.TemporaryDirectory(prefix="source_app_controller_") as tmp:
        tmp_path = Path(tmp)
        source_root = tmp_path / "db_source"
        source_root.mkdir()
        (source_root / "item.txt").write_text("fixture evidence item", encoding="utf-8")
        local_e2e = build_local_e2e_total_export_controller_state(output_root=tmp_path / "e2e")
        database_movement = build_database_movement_controller_state(
            source_root=source_root,
            destination_root=tmp_path / "db_dest",
            execute=False,
        )
        launch = build_archive_media_archivebox_launch_controller_state(output_root=tmp_path / "launch")
    live_smoke = build_manual_live_smoke_helper_controller_state()
    access_asr = build_access_online_asr_preservation_controller_state()
    receipt_import_review = {
        "controller_id": "receipt_import_review_controller_pending",
        "supported_receipt_types": [
            "browser_capture",
            "screenshot",
            "article_page",
            "comments",
            "livechat",
            "media",
            "archive",
            "archivebox",
            "offline_bundle",
            "evidence_movement",
            "completed_evidence",
            "manual_source_note",
        ],
        "unsafe_claim_rejection_enabled": True,
    }
    return AppOperatorControllerState(
        controller_id=_safe_id("source_app_operator_controller", source_url_files, approval, unified_preview),
        source_url_files=source_url_files,
        operator_approval=approval,
        unified_execution=unified_preview,
        local_e2e_total_export=local_e2e,
        database_movement=database_movement,
        live_smoke=live_smoke,
        archive_media_archivebox_launch=launch,
        receipt_import_review=receipt_import_review,
        access_online_asr_preservation=access_asr,
    )
