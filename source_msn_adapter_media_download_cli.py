from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from capture_media_discovery import (
    MEDIA_RESOURCE_KIND_AUDIO,
    MEDIA_RESOURCE_KIND_BLOB,
    MEDIA_RESOURCE_KIND_FRAME,
    MEDIA_RESOURCE_KIND_IMAGE,
    MEDIA_RESOURCE_KIND_MANIFEST,
    MEDIA_RESOURCE_KIND_VIDEO,
    MediaResource,
)
from capture_media_download import MediaDownloadResult, download_media_resource
from capture_status import CAPTURE_STATUS_NOT_REQUESTED, CAPTURE_STATUS_UNSUPPORTED
from source_msn_adapter_manifest import (
    MsnArticleExtraction,
    _discover_msn_structured_media_resources,
    extract_msn_article_from_html,
)

MSN_MEDIA_DOWNLOAD_PLAN_SCHEMA_VERSION = "msn_media_download_plan_v1"
MSN_MEDIA_INVENTORY_JSON = "msn-media-inventory.json"
MSN_MEDIA_INVENTORY_CSV = "msn-media-inventory.csv"
MSN_MEDIA_DOWNLOAD_RESULTS_JSON = "msn-media-download-results.json"
MSN_MEDIA_DOWNLOAD_SUMMARY_MD = "msn-media-download-summary.md"

_DIRECT_DOWNLOAD_KINDS = {MEDIA_RESOURCE_KIND_IMAGE, MEDIA_RESOURCE_KIND_VIDEO, MEDIA_RESOURCE_KIND_AUDIO}
_METADATA_ONLY_KINDS = {MEDIA_RESOURCE_KIND_MANIFEST, MEDIA_RESOURCE_KIND_BLOB, MEDIA_RESOURCE_KIND_FRAME}


@dataclass(frozen=True)
class MsnMediaDownloadPlan:
    schema_version: str = MSN_MEDIA_DOWNLOAD_PLAN_SCHEMA_VERSION
    source_url: str = ""
    rendered_html_path: str = ""
    inventory_json: str = ""
    inventory_csv: str = ""
    download_results_json: str = ""
    summary_markdown: str = ""
    resources: tuple[Mapping[str, Any], ...] = ()
    selected_resource_ids: tuple[str, ...] = ()
    allowed_hostnames: tuple[str, ...] = ()
    download_results: tuple[Mapping[str, Any], ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    manual_review_required: bool = True

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


def _read_text(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_file():
        return ""
    return candidate.read_text(encoding="utf-8", errors="replace")


def _hostname(url: str) -> str:
    return (urlsplit(str(url or "")).hostname or "").lower()


def _as_resource(data: Mapping[str, Any]) -> MediaResource:
    fields = {field.name for field in __import__("dataclasses").fields(MediaResource)}
    kwargs: dict[str, Any] = {}
    for key in fields:
        value = data.get(key)
        if key in {"warnings", "discovery_methods"} and isinstance(value, list):
            value = tuple(str(item) for item in value)
        kwargs[key] = value if value is not None else ""
    for bool_key in ("downloadable", "requires_playback", "signed_url"):
        kwargs[bool_key] = bool(data.get(bool_key))
    for int_key in ("width", "height", "bitrate"):
        try:
            kwargs[int_key] = int(data.get(int_key) or 0)
        except (TypeError, ValueError):
            kwargs[int_key] = 0
    try:
        kwargs["duration_seconds"] = float(data.get("duration_seconds") or 0.0)
    except (TypeError, ValueError):
        kwargs["duration_seconds"] = 0.0
    if not kwargs.get("resource_id") or not kwargs.get("url"):
        raise ValueError("Media resource data must include resource_id and url")
    return MediaResource(**kwargs)


def discover_msn_media_resources_for_download(
    *,
    rendered_html: str = "",
    rendered_html_path: str | Path = "",
    source_url: str = "",
    article: MsnArticleExtraction | None = None,
) -> tuple[MediaResource, ...]:
    html = rendered_html or (_read_text(rendered_html_path) if rendered_html_path else "")
    extracted_article = article or extract_msn_article_from_html(html, source_url=source_url)
    return _discover_msn_structured_media_resources(html, article=extracted_article)


def _select_resource_ids(
    resources: Sequence[MediaResource],
    *,
    selected_resource_ids: Sequence[str] = (),
    select_all_images: bool = False,
    select_all_direct_video: bool = False,
) -> tuple[str, ...]:
    selected = {str(item) for item in selected_resource_ids if str(item)}
    if select_all_images:
        selected.update(resource.resource_id for resource in resources if resource.kind == MEDIA_RESOURCE_KIND_IMAGE and resource.downloadable)
    if select_all_direct_video:
        selected.update(resource.resource_id for resource in resources if resource.kind in {MEDIA_RESOURCE_KIND_VIDEO, MEDIA_RESOURCE_KIND_AUDIO} and resource.downloadable)
    return tuple(resource.resource_id for resource in resources if resource.resource_id in selected)


def _result_for_not_requested(resource: MediaResource, *, source_url: str) -> MediaDownloadResult:
    warning = "Media resource was discovered/registered but not explicitly selected for download."
    if resource.kind in _METADATA_ONLY_KINDS or not resource.downloadable:
        warning = "Media resource is metadata-only, streamed, framed, blob/MediaSource, or otherwise not directly downloadable by this safe helper."
    return MediaDownloadResult(
        status=CAPTURE_STATUS_NOT_REQUESTED if resource.downloadable and resource.kind in _DIRECT_DOWNLOAD_KINDS else CAPTURE_STATUS_UNSUPPORTED,
        resource_id=resource.resource_id,
        selected_resource_id="",
        source_url=source_url,
        media_type=resource.kind,
        url=resource.url,
        warnings=(warning,),
    )


def _write_inventory_csv(resources: Sequence[MediaResource], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "resource_id",
                "kind",
                "url",
                "source_tag",
                "display_name",
                "downloadable",
                "requires_playback",
                "manifest_kind",
                "drm_status",
                "skipped_reason",
                "host",
            ),
        )
        writer.writeheader()
        for resource in resources:
            writer.writerow(
                {
                    "resource_id": resource.resource_id,
                    "kind": resource.kind,
                    "url": resource.url,
                    "source_tag": resource.source_tag,
                    "display_name": resource.display_name,
                    "downloadable": resource.downloadable,
                    "requires_playback": resource.requires_playback,
                    "manifest_kind": resource.manifest_kind,
                    "drm_status": resource.drm_status,
                    "skipped_reason": resource.skipped_reason,
                    "host": _hostname(resource.url),
                }
            )


def render_msn_media_download_summary(plan: MsnMediaDownloadPlan | Mapping[str, Any]) -> str:
    data = plan.to_dict() if hasattr(plan, "to_dict") else plan
    lines = [
        "# MSN Media Download / Registration Summary",
        "",
        f"Schema version: `{data.get('schema_version')}`",
        f"Source URL: `{data.get('source_url') or 'not supplied'}`",
        f"Rendered HTML: `{data.get('rendered_html_path') or 'not supplied'}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in (data.get("counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Selected resource IDs", ""])
    selected = data.get("selected_resource_ids") or []
    lines.append(", ".join(f"`{item}`" for item in selected) if selected else "No resources were selected for download.")
    lines.extend(["", "## Resources", ""])
    results_by_id = {item.get("resource_id"): item for item in data.get("download_results") or [] if isinstance(item, Mapping)}
    for resource in data.get("resources") or []:
        if not isinstance(resource, Mapping):
            continue
        result = results_by_id.get(resource.get("resource_id")) or {}
        lines.append(
            f"- `{resource.get('resource_id')}` `{resource.get('kind')}` status=`{result.get('status') or 'unknown'}` "
            f"downloadable=`{resource.get('downloadable')}` host=`{_hostname(str(resource.get('url') or ''))}` url=`{resource.get('url')}`"
        )
    if data.get("warnings"):
        lines.extend(["", "## Warnings / limits", ""])
        for warning in data.get("warnings") or []:
            lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Source-chain reminder",
            "",
            "Downloading an MSN-visible image/video only proves that this media was observed or acquired from the selected URL. It does not prove MSN, a republisher such as The Independent, or a visible credit is the original primary source unless the original authored source is separately located.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_msn_media_download_plan(
    *,
    rendered_html_path: str | Path,
    source_url: str,
    output_dir: str | Path,
    selected_resource_ids: Sequence[str] = (),
    select_all_images: bool = False,
    select_all_direct_video: bool = False,
    allowed_hostnames: Sequence[str] = (),
    dry_run: bool = False,
) -> MsnMediaDownloadPlan:
    output_root = Path(output_dir)
    media_output = output_root / "media"
    output_root.mkdir(parents=True, exist_ok=True)
    resources = discover_msn_media_resources_for_download(rendered_html_path=rendered_html_path, source_url=source_url)
    selected = _select_resource_ids(
        resources,
        selected_resource_ids=selected_resource_ids,
        select_all_images=select_all_images,
        select_all_direct_video=select_all_direct_video,
    )
    allowed = tuple(dict.fromkeys(host.lower() for host in allowed_hostnames if host))
    results: list[MediaDownloadResult] = []
    for resource in resources:
        if dry_run or resource.resource_id not in selected:
            results.append(_result_for_not_requested(resource, source_url=source_url))
            continue
        results.append(
            download_media_resource(
                resource,
                output_folder=str(media_output),
                selected_resource_ids=selected,
                source_url=source_url,
                allowed_hostnames=allowed,
            )
        )
    inventory_json = output_root / MSN_MEDIA_INVENTORY_JSON
    inventory_csv = output_root / MSN_MEDIA_INVENTORY_CSV
    results_json = output_root / MSN_MEDIA_DOWNLOAD_RESULTS_JSON
    summary_md = output_root / MSN_MEDIA_DOWNLOAD_SUMMARY_MD
    resources_dict = tuple(resource.to_dict() for resource in resources)
    results_dict = tuple(result.to_dict() for result in results)
    counts = {
        "resources": len(resources),
        "images": sum(1 for resource in resources if resource.kind == MEDIA_RESOURCE_KIND_IMAGE),
        "direct_video_or_audio": sum(1 for resource in resources if resource.kind in {MEDIA_RESOURCE_KIND_VIDEO, MEDIA_RESOURCE_KIND_AUDIO}),
        "manifests_or_streams": sum(1 for resource in resources if resource.kind == MEDIA_RESOURCE_KIND_MANIFEST),
        "selected": len(selected),
        "downloaded": sum(1 for result in results if result.status == "SUCCESS"),
        "unsupported_or_metadata_only": sum(1 for result in results if result.status == CAPTURE_STATUS_UNSUPPORTED),
    }
    warnings = [
        "External media download is never automatic; resources must be explicitly selected and their host must be allowed.",
        "HLS/DASH manifests, blob URLs, frames, and playback-only resources are recorded as metadata/status unless a separate approved video workflow captures them.",
        "Media source-chain review remains required for MSN reposts and publisher/credit separation.",
    ]
    plan = MsnMediaDownloadPlan(
        source_url=source_url,
        rendered_html_path=str(rendered_html_path),
        inventory_json=str(inventory_json),
        inventory_csv=str(inventory_csv),
        download_results_json=str(results_json),
        summary_markdown=str(summary_md),
        resources=resources_dict,
        selected_resource_ids=selected,
        allowed_hostnames=allowed,
        download_results=results_dict,
        counts=counts,
        warnings=tuple(warnings),
    )
    inventory_json.write_text(json.dumps({"resources": list(resources_dict)}, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    _write_inventory_csv(resources, inventory_csv)
    results_json.write_text(json.dumps({"download_results": list(results_dict)}, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    summary_md.write_text(render_msn_media_download_summary(plan), encoding="utf-8")
    return plan


def _split_csv(values: Sequence[str]) -> tuple[str, ...]:
    output: list[str] = []
    for value in values:
        for part in str(value or "").split(","):
            part = part.strip()
            if part:
                output.append(part)
    return tuple(output)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover/register MSN article media and explicitly download selected direct media assets.")
    parser.add_argument("--rendered-html", required=True, help="Path to rendered-page.html or equivalent MSN article HTML.")
    parser.add_argument("--source-url", default="", help="Original MSN source URL.")
    parser.add_argument("--output-dir", required=True, help="Output folder for inventory, download results, and downloaded media.")
    parser.add_argument("--select", action="append", default=(), help="Resource ID to download. Can be repeated or comma-separated.")
    parser.add_argument("--select-all-images", action="store_true", help="Select all direct image candidates for download.")
    parser.add_argument("--select-all-direct-video", action="store_true", help="Select all direct video/audio candidates. Stream manifests remain metadata-only.")
    parser.add_argument("--allow-host", action="append", default=(), help="Allowed media hostname. Can be repeated or comma-separated.")
    parser.add_argument("--allow-source-host", action="store_true", help="Allow the host from --source-url as a media download host.")
    parser.add_argument("--dry-run", action="store_true", help="Only write inventory/status files; do not download media.")
    parser.add_argument("--json", action="store_true", help="Print plan JSON to stdout.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    hosts = list(_split_csv(args.allow_host))
    if args.allow_source_host and _hostname(args.source_url):
        hosts.append(_hostname(args.source_url))
    plan = write_msn_media_download_plan(
        rendered_html_path=args.rendered_html,
        source_url=args.source_url,
        output_dir=args.output_dir,
        selected_resource_ids=_split_csv(args.select),
        select_all_images=args.select_all_images,
        select_all_direct_video=args.select_all_direct_video,
        allowed_hostnames=hosts,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"MSN media resources discovered: {plan.counts.get('resources', 0)}")
        print(f"Selected for download: {plan.counts.get('selected', 0)}")
        print(f"Downloaded: {plan.counts.get('downloaded', 0)}")
        print(f"Inventory: {plan.inventory_json}")
        print(f"Download results: {plan.download_results_json}")
        print(f"Summary: {plan.summary_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
