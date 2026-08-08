from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence

from evidence_movement_approval import (
    EvidenceMovementCollisionPolicy,
    EvidenceMovementMode,
    build_completed_evidence_receipt,
    build_evidence_movement_approval_token,
    execute_approved_evidence_movement,
    preview_evidence_movement,
)
from source_operator_approval_gateway import (
    OperatorExecutionAction,
    OperatorExecutionScope,
    build_operator_approval_token,
)
from source_unified_execution_runner import (
    UnifiedExecutionJobOptions,
    UnifiedExecutionJobResult,
    run_unified_local_execution_job,
)
from total_export_manifest import (
    ASSET_ARCHIVE_RESULT,
    ASSET_EXTRACTED_TEXT,
    ASSET_HTML_SNAPSHOT,
    ASSET_MANIFEST,
    ASSET_MEDIA,
    ASSET_RAW_SIDECAR,
    ASSET_SCREENSHOT,
    ExportAsset,
    TotalExportManifest,
    manifest_filename,
    safe_package_id,
    write_manifest_json,
)


SOURCE_LOCAL_E2E_EXPORT_SCHEMA_VERSION = "source_local_e2e_export_v1"


class LocalE2EExportStatus(str, Enum):
    WRITTEN = "written"
    FAILED = "failed"


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


def _stable_json(value: Any, *, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(_value_for_dict(value), indent=2, sort_keys=True)
    return json.dumps(_value_for_dict(value), sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha16(value: Any) -> str:
    return _sha256_bytes(_stable_json(value).encode("utf-8"))[:16]


def _write_text(path: Path, text: str) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode("utf-8")
    path.write_bytes(encoded)
    return _sha256_bytes(encoded), len(encoded)


def _write_json(path: Path, value: Any) -> tuple[str, int]:
    return _write_text(path, _stable_json(value, pretty=True) + "\n")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset(
    *,
    package_root: Path,
    path: Path,
    asset_type: str,
    description: str,
    source_url: str,
    created_at_utc: str,
    mime_type: str,
) -> ExportAsset:
    return ExportAsset(
        asset_type=asset_type,
        path=path.relative_to(package_root).as_posix(),
        description=description,
        source_url=source_url,
        created_at_utc=created_at_utc,
        sha256=_sha256_file(path),
        mime_type=mime_type,
        size_bytes=path.stat().st_size,
    )


@dataclass(frozen=True)
class LocalE2ETotalExportResult:
    export_id: str
    package_name: str
    manifest_name: str
    status: LocalE2EExportStatus
    runner_job: UnifiedExecutionJobResult
    asset_names: tuple[str, ...]
    asset_hashes: tuple[tuple[str, str], ...]
    offline_bundle_name: str
    movement_preview_id: str
    movement_receipt_id: str
    completed_evidence_receipt_id: str
    local_fixture_tested: bool = True
    fake_http_tested: bool = True
    mocked_subprocess_tested: bool = False
    live_network_performed: bool = False
    real_user_evidence_moved: bool = False
    credentials_read: bool = False
    asr_job_run: bool = False
    schema_version: str = SOURCE_LOCAL_E2E_EXPORT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = _value_for_dict(self)
        data["asset_count"] = len(self.asset_names)
        return data


def write_local_e2e_fixture_total_export(
    *,
    output_directory: str | Path,
    source_url: str = "local-fixture://e2e-story",
    fixture_html: str,
    selected_media_payloads: Sequence[tuple[str, bytes, str]] = (),
    created_at_utc: str = "2026-08-08T00:00:00Z",
) -> LocalE2ETotalExportResult:
    package_root = Path(output_directory) / safe_package_id("local_e2e_total_export")
    package_root.mkdir(parents=True, exist_ok=True)
    media_source_root = package_root / "_fixture_media_sources"
    media_resources: list[Mapping[str, Any]] = []
    selected_ids: list[str] = []
    for index, (name, payload, media_type) in enumerate(selected_media_payloads, start=1):
        source_path = media_source_root / name
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(payload)
        resource_id = f"media_{index}"
        selected_ids.append(resource_id)
        media_resources.append({"resource_id": resource_id, "path": str(source_path), "media_type": media_type})

    actions = (
        OperatorExecutionAction.BROWSER_LOCAL_CAPTURE,
        OperatorExecutionAction.SCREENSHOT_CAPTURE,
        OperatorExecutionAction.ARTICLE_CAPTURE,
        OperatorExecutionAction.PAGE_OUTLINE_CAPTURE,
        OperatorExecutionAction.COMMENTS_CAPTURE,
        OperatorExecutionAction.LIVECHAT_CAPTURE,
        OperatorExecutionAction.MEDIA_DOWNLOAD_COPY,
        OperatorExecutionAction.ARCHIVE_CHECK,
        OperatorExecutionAction.OFFLINE_BUNDLE_WRITE,
    )
    token = build_operator_approval_token(
        actions=actions,
        scope=OperatorExecutionScope.LOCAL_TEMP,
        approved_by_operator=True,
        allow_external_network=True,
        approval_note="local E2E fixture fake-client archive check",
    )
    runner = run_unified_local_execution_job(
        source_url=source_url,
        fixture_html=fixture_html,
        output_directory=package_root / "execution",
        options=UnifiedExecutionJobOptions(
            run_browser_capture=True,
            run_media_copy=bool(media_resources),
            run_archive_check=True,
            write_offline_bundle=True,
            selected_media_resource_ids=tuple(selected_ids),
            element_selector="article",
        ),
        approval_token=token,
        media_resources=tuple(media_resources),
        archive_http_client=lambda request: {
            "status": 200,
            "body": '{"archived_snapshots":{"closest":{"available":true}}}',
            "archive_url": "https://web.archive.org/web/fixture/local",
        },
    )

    assets: list[ExportAsset] = []
    browser_dir = package_root / "execution" / "browser"
    article_text = runner.browser_result.article.text if runner.browser_result and runner.browser_result.article else ""
    outline_text = "\n".join(runner.browser_result.page_outline.outline_lines) if runner.browser_result and runner.browser_result.page_outline else ""
    article_path = package_root / "page_capture" / "article_text.txt"
    outline_path = package_root / "page_capture" / "visible_page_outline.txt"
    comments_path = package_root / "metadata" / "comments.json"
    livechat_path = package_root / "metadata" / "livechat.json"
    media_path = package_root / "metadata" / "selected_media_receipts.json"
    archive_path = package_root / "metadata" / "archive_fake_client_result.json"
    behavior_path = package_root / "metadata" / "behavior_provenance_events.json"
    execution_path = package_root / "metadata" / "execution_job_result.json"
    movement_path = package_root / "metadata" / "movement_preview_receipts.json"

    _write_text(article_path, article_text)
    _write_text(outline_path, outline_text)
    _write_json(comments_path, tuple(comment.to_dict() for comment in runner.browser_result.comments.comments) if runner.browser_result and runner.browser_result.comments else ())
    _write_json(livechat_path, tuple(event.to_dict() for event in runner.browser_result.livechat.events) if runner.browser_result and runner.browser_result.livechat else ())
    _write_json(media_path, runner.media_copy_queue.to_dict() if runner.media_copy_queue else {})
    _write_json(archive_path, runner.archive_result.to_dict() if runner.archive_result else {})
    _write_json(behavior_path, {"events": runner.behavior_event_labels, "hash_chain_preserved": True, "redaction_applied": True})
    _write_json(execution_path, runner.to_dict())

    movement_source = package_root / "_movement_fixture" / "source.txt"
    movement_source.parent.mkdir(parents=True, exist_ok=True)
    movement_source.write_text("temp movement fixture", encoding="utf-8")
    movement_preview = preview_evidence_movement(
        old_path=str(movement_source),
        new_path=str(package_root / "completed_evidence_fixture" / "source.txt"),
        taxonomy_changes={"category": "local_fixture_reviewed"},
        mode=EvidenceMovementMode.COPY,
        approval_granted=True,
    )
    movement_token = build_evidence_movement_approval_token(
        movement_preview,
        approved_by_operator=True,
        operator_label="fixture-test-operator",
    )
    movement_receipt = execute_approved_evidence_movement(
        movement_preview,
        approval_token=movement_token,
        approved_root=str(package_root),
        collision_policy=EvidenceMovementCollisionPolicy.FAIL,
    )
    completed_receipt = build_completed_evidence_receipt(movement_receipt)
    _write_json(
        movement_path,
        {
            "preview": movement_preview.to_dict(),
            "movement_receipt": movement_receipt.to_dict(),
            "completed_evidence_receipt": completed_receipt.to_dict(),
            "temp_fixture_only": True,
        },
    )

    assets.extend(
        (
            _asset(package_root=package_root, path=article_path, asset_type=ASSET_EXTRACTED_TEXT, description="Local fixture article text.", source_url=source_url, created_at_utc=created_at_utc, mime_type="text/plain"),
            _asset(package_root=package_root, path=outline_path, asset_type=ASSET_EXTRACTED_TEXT, description="Local fixture visible page outline.", source_url=source_url, created_at_utc=created_at_utc, mime_type="text/plain"),
            _asset(package_root=package_root, path=browser_dir / "rendered_dom.html", asset_type=ASSET_HTML_SNAPSHOT, description="Local fixture rendered DOM snapshot.", source_url=source_url, created_at_utc=created_at_utc, mime_type="text/html"),
            _asset(package_root=package_root, path=browser_dir / "faithful_full_page.png", asset_type=ASSET_SCREENSHOT, description="Local fixture faithful screenshot artifact.", source_url=source_url, created_at_utc=created_at_utc, mime_type="image/png"),
            _asset(package_root=package_root, path=comments_path, asset_type=ASSET_RAW_SIDECAR, description="Local fixture comments export.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/json"),
            _asset(package_root=package_root, path=livechat_path, asset_type=ASSET_RAW_SIDECAR, description="Local fixture livechat text-first export.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/json"),
            _asset(package_root=package_root, path=media_path, asset_type=ASSET_MEDIA, description="Selected local media copy receipt metadata.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/json"),
            _asset(package_root=package_root, path=archive_path, asset_type=ASSET_ARCHIVE_RESULT, description="Archive fake-client result metadata.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/json"),
            _asset(package_root=package_root, path=behavior_path, asset_type=ASSET_RAW_SIDECAR, description="Behavior/provenance log event summary.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/json"),
            _asset(package_root=package_root, path=execution_path, asset_type=ASSET_RAW_SIDECAR, description="Unified execution bridge sidecar.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/json"),
            _asset(package_root=package_root, path=movement_path, asset_type=ASSET_RAW_SIDECAR, description="Temp-fixture movement preview and completed-evidence receipt.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/json"),
        )
    )
    if runner.offline_bundle_result is not None:
        offline_path = package_root / "execution" / runner.offline_bundle_result.output_name
        assets.append(
            _asset(package_root=package_root, path=offline_path, asset_type=ASSET_MANIFEST, description="Offline compressed evidence bundle.", source_url=source_url, created_at_utc=created_at_utc, mime_type="application/zip")
        )
    manifest = TotalExportManifest(
        package_id=package_root.name,
        created_at_utc=created_at_utc,
        source_urls=[source_url],
        output_folder=package_root.name,
        capture_options=[
            "Local fixture article/page capture",
            "Local fixture comments/livechat capture",
            "Local fixture selected media copy receipt",
            "Fake-client archive result",
            "Offline compressed bundle",
            "Temp-fixture evidence movement receipt",
        ],
        assets=assets,
        archive_results=[runner.archive_result.to_dict()] if runner.archive_result else [],
        notes="Local E2E fixture Total Export package. No external site, provider, ASR, or user evidence execution.",
    )
    manifest_path = package_root / manifest_filename(package_root.name)
    write_manifest_json(manifest, str(manifest_path))
    asset_names = tuple(asset.path for asset in assets) + (manifest_path.name,)
    asset_hashes = tuple((asset.path, asset.sha256) for asset in assets) + ((manifest_path.name, _sha256_file(manifest_path)),)
    return LocalE2ETotalExportResult(
        export_id="local_e2e_total_export_" + _sha16(asset_hashes),
        package_name=package_root.name,
        manifest_name=manifest_path.name,
        status=LocalE2EExportStatus.WRITTEN,
        runner_job=runner,
        asset_names=asset_names,
        asset_hashes=asset_hashes,
        offline_bundle_name=runner.offline_bundle_result.output_name if runner.offline_bundle_result else "",
        movement_preview_id=movement_preview.movement_id,
        movement_receipt_id=movement_receipt.receipt_id,
        completed_evidence_receipt_id=completed_receipt.receipt_id,
    )


def local_e2e_total_export_result_to_json(result: LocalE2ETotalExportResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)
