from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from capture_media_discovery import (
    MEDIA_RESOURCE_KIND_AUDIO,
    MEDIA_RESOURCE_KIND_IMAGE,
    MEDIA_RESOURCE_KIND_VIDEO,
)
from source_msn_adapter_media_download_cli import (
    MsnMediaDownloadPlan,
    write_msn_media_download_plan,
)
from source_resource_state import (
    RESOURCE_KIND_IMAGE,
    RESOURCE_KIND_VIDEO_AUDIO,
    ResourceSelectionDialogState,
    SourceResourceRowState,
)


MEDIA_GUI_DOWNLOAD_STATUS_READY = "ready"
MEDIA_GUI_DOWNLOAD_STATUS_NOT_SELECTED = "not_selected"
MEDIA_GUI_DOWNLOAD_STATUS_UNSUPPORTED = "unsupported"
MEDIA_GUI_DOWNLOAD_STATUS_MISSING_INPUT = "missing_input"
MEDIA_GUI_DOWNLOAD_STATUS_FAILED = "failed"

MEDIA_GUI_BRIDGE_HOTFIX = "v3_no_fixture_selection_required"

MEDIA_GUI_BRIDGE_SCOPE = (
    "GUI bridge to existing source media discovery/download helpers; no automatic bulk "
    "download, no DRM bypass, no archive submission, and no hidden/private media access"
)


@dataclass(frozen=True)
class SourceMediaGuiDownloadResult:
    status: str
    message: str
    source_row_id: str = ""
    adapter_id: str = ""
    resource_kind: str = ""
    selected_count: int = 0
    dry_run: bool = True
    rendered_html_path: str = ""
    output_dir: str = ""
    selected_direct_hostnames: tuple[str, ...] = ()
    inventory_json: str = ""
    inventory_csv: str = ""
    download_results_json: str = ""
    summary_markdown: str = ""
    resources_discovered: int = 0
    resources_selected: int = 0
    resources_downloaded: int = 0
    unsupported_or_metadata_only: int = 0
    warnings: tuple[str, ...] = ()
    scope: str = MEDIA_GUI_BRIDGE_SCOPE

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


def _value_for_dict(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _value_for_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, list):
        return [_value_for_dict(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _value_for_dict(item) for key, item in value.items()}
    return value


def _host(url: str) -> str:
    return (urlsplit(str(url or "")).hostname or "").lower()


def _selected_category_flags(
    state: ResourceSelectionDialogState,
) -> tuple[bool, bool]:
    """Select the media category represented by the window, not old fixture IDs.

    The source-row GUI originally displayed deterministic fixture resources. That made
    old tests pass, but it was misleading in live use. For MSN, the real candidate
    list is discovered from the rendered HTML when the user clicks Download, so an
    empty pre-discovery selection window is valid.
    """
    return (
        state.resource_kind == RESOURCE_KIND_IMAGE,
        state.resource_kind == RESOURCE_KIND_VIDEO_AUDIO,
    )


def selected_direct_hostnames_from_plan(plan: MsnMediaDownloadPlan | Mapping[str, Any]) -> tuple[str, ...]:
    data = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    selected = {str(item) for item in data.get("selected_resource_ids") or ()}
    hosts: list[str] = []
    for resource in data.get("resources") or ():
        if str(resource.get("resource_id") or "") not in selected:
            continue
        if str(resource.get("kind") or "") not in {
            MEDIA_RESOURCE_KIND_IMAGE,
            MEDIA_RESOURCE_KIND_VIDEO,
            MEDIA_RESOURCE_KIND_AUDIO,
        }:
            continue
        if not bool(resource.get("downloadable", False)):
            continue
        host = _host(str(resource.get("url") or ""))
        if host:
            hosts.append(host)
    return tuple(dict.fromkeys(hosts))


def media_gui_result_from_msn_plan(
    *,
    row: SourceResourceRowState,
    state: ResourceSelectionDialogState,
    plan: MsnMediaDownloadPlan,
    dry_run: bool,
) -> SourceMediaGuiDownloadResult:
    data = plan.to_dict()
    counts = data.get("counts") or {}
    hostnames = selected_direct_hostnames_from_plan(data)
    downloaded = int(counts.get("downloaded") or 0)
    selected = int(counts.get("selected") or 0)
    resources = int(counts.get("resources") or 0)
    unsupported = int(counts.get("unsupported_or_metadata_only") or 0)
    mode = "review files written" if dry_run else "download attempt completed"
    message = (
        f"MSN media {mode}.\n\n"
        f"Resources discovered: {resources}\n"
        f"Selected direct resources: {selected}\n"
        f"Downloaded: {downloaded}\n"
        f"Metadata-only/unsupported: {unsupported}\n\n"
        f"Summary:\n{data.get('summary_markdown') or ''}"
    )
    return SourceMediaGuiDownloadResult(
        status=MEDIA_GUI_DOWNLOAD_STATUS_READY,
        message=message,
        source_row_id=row.row_id,
        adapter_id=row.adapter_id,
        resource_kind=state.resource_kind,
        selected_count=len(state.selected_resource_ids),
        dry_run=dry_run,
        rendered_html_path=str(data.get("rendered_html_path") or ""),
        output_dir=str(Path(str(data.get("summary_markdown") or "")).parent if data.get("summary_markdown") else ""),
        selected_direct_hostnames=hostnames,
        inventory_json=str(data.get("inventory_json") or ""),
        inventory_csv=str(data.get("inventory_csv") or ""),
        download_results_json=str(data.get("download_results_json") or ""),
        summary_markdown=str(data.get("summary_markdown") or ""),
        resources_discovered=resources,
        resources_selected=selected,
        resources_downloaded=downloaded,
        unsupported_or_metadata_only=unsupported,
        warnings=tuple(str(item) for item in data.get("warnings") or ()),
    )


def run_source_media_gui_download(
    *,
    row: SourceResourceRowState,
    state: ResourceSelectionDialogState,
    rendered_html_path: str | Path = "",
    output_dir: str | Path = "",
    allowed_hostnames: Sequence[str] = (),
    dry_run: bool = True,
) -> SourceMediaGuiDownloadResult:
    if row.adapter_id != "msn":
        return SourceMediaGuiDownloadResult(
            status=MEDIA_GUI_DOWNLOAD_STATUS_UNSUPPORTED,
            message=(
                "Direct GUI media execution is currently connected for MSN rows only. "
                "This source row remains a selection/registration scaffold."
            ),
            source_row_id=row.row_id,
            adapter_id=row.adapter_id,
            resource_kind=state.resource_kind,
            selected_count=len(state.selected_resource_ids),
            dry_run=dry_run,
            warnings=("Non-MSN media GUI rows are not connected to a live download backend yet.",),
        )
    if state.resource_kind not in {RESOURCE_KIND_IMAGE, RESOURCE_KIND_VIDEO_AUDIO}:
        return SourceMediaGuiDownloadResult(
            status=MEDIA_GUI_DOWNLOAD_STATUS_NOT_SELECTED,
            message="No supported media category was selected.",
            source_row_id=row.row_id,
            adapter_id=row.adapter_id,
            resource_kind=state.resource_kind,
            selected_count=len(state.selected_resource_ids),
            dry_run=dry_run,
        )
    html_path = Path(rendered_html_path)
    if not html_path.is_file():
        return SourceMediaGuiDownloadResult(
            status=MEDIA_GUI_DOWNLOAD_STATUS_MISSING_INPUT,
            message="Select a rendered MSN article HTML file before running MSN media discovery/download.",
            source_row_id=row.row_id,
            adapter_id=row.adapter_id,
            resource_kind=state.resource_kind,
            selected_count=len(state.selected_resource_ids),
            dry_run=dry_run,
            rendered_html_path=str(rendered_html_path or ""),
            warnings=("Rendered MSN article HTML was missing or not a file.",),
        )
    if not output_dir:
        return SourceMediaGuiDownloadResult(
            status=MEDIA_GUI_DOWNLOAD_STATUS_MISSING_INPUT,
            message="Select an output folder before running MSN media discovery/download.",
            source_row_id=row.row_id,
            adapter_id=row.adapter_id,
            resource_kind=state.resource_kind,
            selected_count=len(state.selected_resource_ids),
            dry_run=dry_run,
            rendered_html_path=str(html_path),
            warnings=("Output folder was not supplied.",),
        )

    select_all_images, select_all_direct_video = _selected_category_flags(state)
    try:
        plan = write_msn_media_download_plan(
            rendered_html_path=html_path,
            source_url=row.canonical_url,
            output_dir=output_dir,
            select_all_images=select_all_images,
            select_all_direct_video=select_all_direct_video,
            allowed_hostnames=tuple(dict.fromkeys(str(host).lower() for host in allowed_hostnames if str(host))),
            dry_run=dry_run,
        )
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        raise
    except Exception:
        return SourceMediaGuiDownloadResult(
            status=MEDIA_GUI_DOWNLOAD_STATUS_FAILED,
            message="MSN media discovery/download failed with a non-secret exception.",
            source_row_id=row.row_id,
            adapter_id=row.adapter_id,
            resource_kind=state.resource_kind,
            selected_count=len(state.selected_resource_ids),
            dry_run=dry_run,
            rendered_html_path=str(html_path),
            output_dir=str(output_dir),
            warnings=("The detailed exception is intentionally not exposed in the GUI result.",),
        )
    return media_gui_result_from_msn_plan(row=row, state=state, plan=plan, dry_run=dry_run)


def source_media_gui_download_result_to_json(result: SourceMediaGuiDownloadResult) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)
