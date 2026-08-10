from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from source_msn_adapter_final_validator import (
    MSN_FINAL_VALIDATION_REPORT_JSON,
    build_msn_adapter_final_validation_report,
    write_msn_adapter_final_validation_outputs,
)
from source_msn_adapter_media_download_cli import MsnMediaDownloadPlan, write_msn_media_download_plan
from source_msn_adapter_total_package import (
    MsnTotalPackageResult,
    discover_msn_total_package_inputs,
    write_msn_source_adapter_total_package,
)

MSN_COMPLETION_SCHEMA_VERSION = "msn_source_adapter_completion_run_v1"
MSN_COMPLETION_JSON = "MSN_SOURCE_ADAPTER_COMPLETION_RUN.json"
MSN_COMPLETION_MD = "MSN_SOURCE_ADAPTER_COMPLETION_RUN.md"


@dataclass(frozen=True)
class MsnSourceAdapterCompletionRun:
    schema_version: str = MSN_COMPLETION_SCHEMA_VERSION
    root_path: str = ""
    source_url: str = ""
    output_dir: str = ""
    rendered_html_path: str = ""
    comments_json_path: str = ""
    request_log_path: str = ""
    media_plan_json: str = ""
    total_package_summary_json: str = ""
    final_validation_json: str = ""
    completion_json: str = ""
    completion_markdown: str = ""
    overall_status: str = ""
    manual_review_required: bool = True
    counts: Mapping[str, int] = field(default_factory=dict)
    output_paths: Mapping[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

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


def _read_json(path: str | Path) -> Mapping[str, Any]:
    candidate = Path(path)
    if not candidate.is_file():
        return {}
    try:
        value = json.loads(candidate.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return value if isinstance(value, Mapping) else {}


def _hostname(url: str) -> str:
    return (urlsplit(str(url or "")).hostname or "").lower()


def _split_csv(values: Sequence[str]) -> tuple[str, ...]:
    output: list[str] = []
    for value in values:
        for part in str(value or "").split(","):
            part = part.strip()
            if part:
                output.append(part)
    return tuple(output)


def render_msn_source_adapter_completion_markdown(run: MsnSourceAdapterCompletionRun | Mapping[str, Any]) -> str:
    data = run.to_dict() if hasattr(run, "to_dict") else run
    lines = [
        "# MSN Source Adapter Completion Run",
        "",
        f"Schema version: `{data.get('schema_version')}`",
        f"Root: `{data.get('root_path') or ''}`",
        f"Source URL: `{data.get('source_url') or 'not supplied'}`",
        f"Overall status: `{data.get('overall_status') or 'UNKNOWN'}`",
        f"Manual review required: `{data.get('manual_review_required')}`",
        "",
        "## Inputs",
        "",
        f"- Rendered HTML: `{data.get('rendered_html_path') or 'not found'}`",
        f"- Comments JSON: `{data.get('comments_json_path') or 'not found'}`",
        f"- Request log: `{data.get('request_log_path') or 'not found'}`",
        "",
        "## Output paths",
        "",
    ]
    for key, value in (data.get("output_paths") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Counts", ""])
    for key, value in (data.get("counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    if data.get("warnings"):
        lines.extend(["", "## Warnings / manual limits", ""])
        for warning in data.get("warnings") or []:
            lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Completion rule",
            "",
            "This command is the operator-facing join step for the MSN adapter. It does not prove that MSN is the original source of republished articles or media. It packages article extraction, comments/profile exports, offline archive/viewer artifacts, media inventory/download sidecars, readiness/release/final validation, and source-role/source-chain provenance so the final manual review can decide whether the adapter output is complete for a real MSN capture.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_msn_source_adapter_completion(
    root_path: str | Path,
    *,
    source_url: str = "",
    output_dir: str | Path = "",
    rendered_html_path: str | Path = "",
    comments_json_path: str | Path = "",
    request_log_path: str | Path = "",
    skip_media: bool = False,
    media_dry_run: bool = True,
    selected_resource_ids: Sequence[str] = (),
    select_all_images: bool = False,
    select_all_direct_video: bool = False,
    allowed_hostnames: Sequence[str] = (),
    allow_source_host: bool = False,
) -> MsnSourceAdapterCompletionRun:
    root = Path(root_path)
    output_root = Path(output_dir) if output_dir else root / "msn_source_adapter_completion"
    media_dir = output_root / "media_registration"
    total_dir = output_root / "total_package"
    reports_dir = output_root / "reports"
    output_root.mkdir(parents=True, exist_ok=True)

    discovered = discover_msn_total_package_inputs(
        root,
        source_url=source_url,
        rendered_html_path=rendered_html_path,
        comments_json_path=comments_json_path,
        request_log_path=request_log_path,
        output_dir=total_dir,
    )

    warnings: list[str] = []
    media_plan: MsnMediaDownloadPlan | None = None
    media_results_path = ""
    hosts = list(dict.fromkeys(str(host).lower() for host in allowed_hostnames if str(host).strip()))
    if allow_source_host and _hostname(discovered.source_url):
        hosts.append(_hostname(discovered.source_url))

    if skip_media:
        warnings.append("Media inventory/download stage was explicitly skipped; final media confidence should remain partial unless a prior media sidecar is supplied.")
    elif discovered.rendered_html_path:
        media_plan = write_msn_media_download_plan(
            rendered_html_path=discovered.rendered_html_path,
            source_url=discovered.source_url,
            output_dir=media_dir,
            selected_resource_ids=selected_resource_ids,
            select_all_images=select_all_images,
            select_all_direct_video=select_all_direct_video,
            allowed_hostnames=hosts,
            dry_run=media_dry_run,
        )
        media_results_path = media_plan.download_results_json
        if media_dry_run:
            warnings.append("Media stage ran in dry-run/registration mode; direct media files were not downloaded unless a prior sidecar already exists.")
    else:
        warnings.append("Rendered HTML was not found, so media discovery/download registration could not run.")

    total = write_msn_source_adapter_total_package(
        root,
        source_url=discovered.source_url,
        output_dir=total_dir,
        rendered_html_path=discovered.rendered_html_path,
        comments_json_path=discovered.comments_json_path,
        request_log_path=discovered.request_log_path,
        media_download_results_path=media_results_path,
    )
    final_outputs = write_msn_adapter_final_validation_outputs(root, output_dir=reports_dir, source_url=discovered.source_url)
    final_report = build_msn_adapter_final_validation_report(root, source_url=discovered.source_url)

    completion_json = output_root / MSN_COMPLETION_JSON
    completion_md = output_root / MSN_COMPLETION_MD
    output_paths = {
        "completion_json": str(completion_json),
        "completion_markdown": str(completion_md),
        "total_package_summary_json": total.output_paths.get("total_package_summary_json", ""),
        "total_package_index_markdown": total.output_paths.get("total_package_index_markdown", ""),
        "media_inventory_json": media_plan.inventory_json if media_plan else "",
        "media_inventory_csv": media_plan.inventory_csv if media_plan else "",
        "media_download_results_json": media_plan.download_results_json if media_plan else "",
        "media_download_summary_markdown": media_plan.summary_markdown if media_plan else "",
        **final_outputs,
    }
    counts = {
        "media_resources": int(media_plan.counts.get("resources", 0)) if media_plan else 0,
        "media_selected": int(media_plan.counts.get("selected", 0)) if media_plan else 0,
        "media_downloaded": int(media_plan.counts.get("downloaded", 0)) if media_plan else 0,
        "total_manifest_assets": int(total.counts.get("manifest_assets", 0)),
        "total_provenance_records": int(total.counts.get("provenance_records", 0)),
        "final_validation_area_count": len(final_report.areas),
    }
    run = MsnSourceAdapterCompletionRun(
        root_path=str(root),
        source_url=discovered.source_url,
        output_dir=str(output_root),
        rendered_html_path=discovered.rendered_html_path,
        comments_json_path=discovered.comments_json_path,
        request_log_path=discovered.request_log_path,
        media_plan_json=media_plan.inventory_json if media_plan else "",
        total_package_summary_json=total.output_paths.get("total_package_summary_json", ""),
        final_validation_json=final_outputs.get("final_validation_json", ""),
        completion_json=str(completion_json),
        completion_markdown=str(completion_md),
        overall_status=final_report.overall_status,
        manual_review_required=True,
        counts=counts,
        output_paths=output_paths,
        warnings=tuple(warnings + [
            "Manual live review is still required for real MSN pages, ReplayWeb/WACZ behaviour, video delivery, and primary-source/original-media claims.",
            "MSN, The Independent, Google Street View, wire/agency labels, visible credits, and unknown original uploaders must remain separate source-chain records.",
        ]),
    )
    completion_json.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    completion_md.write_text(render_msn_source_adapter_completion_markdown(run), encoding="utf-8")
    return run


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the operator-facing MSN adapter completion step against an existing MSN capture/export folder.")
    parser.add_argument("root", help="Existing MSN output folder containing rendered HTML/archive/comments/media sidecars.")
    parser.add_argument("--source-url", default="", help="Original MSN URL.")
    parser.add_argument("--output-dir", default="", help="Output folder; defaults to <root>/msn_source_adapter_completion.")
    parser.add_argument("--rendered-html", default="", help="Override rendered HTML path.")
    parser.add_argument("--comments-json", default="", help="Override comments JSON path.")
    parser.add_argument("--request-log", default="", help="Override request log JSON path.")
    parser.add_argument("--skip-media", action="store_true", help="Skip media inventory/download registration.")
    parser.add_argument("--media-dry-run", action="store_true", default=True, help="Register media only; do not download direct assets. This is the default.")
    parser.add_argument("--download-media", action="store_true", help="Allow explicitly selected direct media downloads. Requires selected IDs/flags and allowed hosts.")
    parser.add_argument("--select", action="append", default=(), help="Resource ID to download. Can be repeated or comma-separated.")
    parser.add_argument("--select-all-images", action="store_true", help="Select all direct image resources.")
    parser.add_argument("--select-all-direct-video", action="store_true", help="Select all direct video/audio resources. Stream manifests remain metadata-only.")
    parser.add_argument("--allow-host", action="append", default=(), help="Allowed media hostname. Can be repeated or comma-separated.")
    parser.add_argument("--allow-source-host", action="store_true", help="Allow the host from --source-url as a media download host.")
    parser.add_argument("--json", action="store_true", help="Print completion run JSON.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    run = run_msn_source_adapter_completion(
        args.root,
        source_url=args.source_url,
        output_dir=args.output_dir,
        rendered_html_path=args.rendered_html,
        comments_json_path=args.comments_json,
        request_log_path=args.request_log,
        skip_media=args.skip_media,
        media_dry_run=not args.download_media,
        selected_resource_ids=_split_csv(args.select),
        select_all_images=args.select_all_images,
        select_all_direct_video=args.select_all_direct_video,
        allowed_hostnames=_split_csv(args.allow_host),
        allow_source_host=args.allow_source_host,
    )
    if args.json:
        print(json.dumps(run.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"MSN adapter completion status: {run.overall_status}")
        print(f"Completion JSON: {run.completion_json}")
        print(f"Completion Markdown: {run.completion_markdown}")
        print(f"Output dir: {run.output_dir}")
    return 0 if run.overall_status != "NOT_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
