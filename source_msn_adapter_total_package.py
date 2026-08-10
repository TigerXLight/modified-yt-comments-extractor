from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from source_msn_adapter_final_validator import write_msn_adapter_final_validation_outputs
from source_msn_adapter_manifest import build_msn_source_adapter_bundle, write_msn_source_adapter_bundle_json
from source_msn_adapter_readiness import evaluate_msn_source_adapter_readiness, write_msn_source_adapter_readiness_report
from source_msn_adapter_release_report import write_msn_source_adapter_release_outputs

MSN_TOTAL_PACKAGE_SCHEMA_VERSION = "msn_source_adapter_total_package_v1"
MSN_TOTAL_PACKAGE_INDEX_MD = "MSN_SOURCE_ADAPTER_TOTAL_PACKAGE_INDEX.md"
MSN_TOTAL_PACKAGE_SUMMARY_JSON = "MSN_SOURCE_ADAPTER_TOTAL_PACKAGE_SUMMARY.json"
MSN_BUNDLE_JSON = "MSN_SOURCE_ADAPTER_BUNDLE.json"
MSN_READINESS_JSON = "MSN_SOURCE_ADAPTER_READINESS.json"

_HTML_NAMES = ("rendered-page.html", "article.html", "page.html")
_REQUEST_LOG_NAMES = ("request-log.json", "requests.json", "network-requests.json", "network_log.json")
_MEDIA_DOWNLOAD_NAMES = ("msn-media-download-results.json", "media-download-results.json", "download-results.json")
_IGNORE_DIR_PARTS = {".git", "__pycache__", ".pytest_cache", "venv", ".venv", "node_modules"}


@dataclass(frozen=True)
class MsnTotalPackageInputs:
    root_path: str
    source_url: str = ""
    rendered_html_path: str = ""
    comments_json_path: str = ""
    request_log_path: str = ""
    media_download_results_path: str = ""
    output_dir: str = ""
    offline_archive_dir: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _value_for_dict(self)


@dataclass(frozen=True)
class MsnTotalPackageResult:
    schema_version: str = MSN_TOTAL_PACKAGE_SCHEMA_VERSION
    inputs: MsnTotalPackageInputs = field(default_factory=lambda: MsnTotalPackageInputs(root_path=""))
    output_paths: Mapping[str, str] = field(default_factory=dict)
    counts: Mapping[str, int] = field(default_factory=dict)
    overall_note: str = ""
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


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    def generator() -> Iterable[Path]:
        for path in root.rglob("*"):
            if any(part in _IGNORE_DIR_PARTS for part in path.parts):
                continue
            if path.is_file():
                yield path
    return generator()


def _read_json(path: str | Path) -> Mapping[str, Any]:
    candidate = Path(path)
    if not candidate.is_file():
        return {}
    try:
        data = json.loads(candidate.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return data if isinstance(data, Mapping) else {}


def _find_first_named(root: Path, names: Sequence[str]) -> Path | None:
    lowered = {name.lower() for name in names}
    for path in _iter_files(root):
        if path.name.lower() in lowered:
            return path
    return None


def _find_comments_json(root: Path) -> Path | None:
    candidates = [path for path in _iter_files(root) if path.suffix.lower() == ".json" and "comment" in path.name.lower()]
    for path in candidates:
        data = _read_json(path)
        if isinstance(data.get("comments"), list) or isinstance(data.get("items"), list):
            return path
    return None


def _load_request_log(path: str | Path) -> tuple[Mapping[str, Any], ...]:
    data = _read_json(path)
    for key in ("requests", "entries", "request_log", "network_requests"):
        value = data.get(key)
        if isinstance(value, list):
            return tuple(item for item in value if isinstance(item, Mapping))
    if isinstance(data.get("url"), str):
        return (data,)
    return ()


def _load_media_download_results(path: str | Path) -> tuple[Mapping[str, Any], ...]:
    data = _read_json(path)
    for key in ("download_results", "media_download_results", "results"):
        value = data.get(key)
        if isinstance(value, list):
            return tuple(item for item in value if isinstance(item, Mapping))
    if data.get("resource_id") or data.get("url"):
        return (data,)
    return ()


def discover_msn_total_package_inputs(
    root_path: str | Path,
    *,
    source_url: str = "",
    rendered_html_path: str | Path = "",
    comments_json_path: str | Path = "",
    request_log_path: str | Path = "",
    media_download_results_path: str | Path = "",
    output_dir: str | Path = "",
) -> MsnTotalPackageInputs:
    root = Path(root_path)
    html = Path(rendered_html_path) if rendered_html_path else (_find_first_named(root, _HTML_NAMES) or Path())
    comments = Path(comments_json_path) if comments_json_path else (_find_comments_json(root) or Path())
    request_log = Path(request_log_path) if request_log_path else (_find_first_named(root, _REQUEST_LOG_NAMES) or Path())
    media_results = Path(media_download_results_path) if media_download_results_path else (_find_first_named(root, _MEDIA_DOWNLOAD_NAMES) or Path())
    out = Path(output_dir) if output_dir else root / "msn_source_adapter_total_package"
    return MsnTotalPackageInputs(
        root_path=str(root),
        source_url=source_url,
        rendered_html_path=str(html) if str(html) != "." else "",
        comments_json_path=str(comments) if str(comments) != "." else "",
        request_log_path=str(request_log) if str(request_log) != "." else "",
        media_download_results_path=str(media_results) if str(media_results) != "." else "",
        output_dir=str(out),
        offline_archive_dir=str(root),
    )


def _comments_export(path: str) -> Mapping[str, Any]:
    data = _read_json(path)
    if isinstance(data.get("comments"), list):
        return data
    if isinstance(data.get("items"), list):
        return {**data, "comments": data.get("items")}
    return {}


def _comments_files(path: str) -> Mapping[str, str]:
    if not path:
        return {}
    root = Path(path).parent
    output: dict[str, str] = {"comments_json": path}
    for file_path in root.iterdir() if root.is_dir() else ():
        name = file_path.name.lower()
        if "profile" in name and file_path.suffix.lower() in {".json", ".csv", ".txt", ".html"}:
            output[f"profiles_{file_path.suffix.lower().lstrip('.')}"] = str(file_path)
        if "comment" in name and file_path.suffix.lower() in {".txt", ".md", ".html"}:
            output[f"comments_{file_path.suffix.lower().lstrip('.')}"] = str(file_path)
    return output


def render_msn_total_package_index(result: MsnTotalPackageResult | Mapping[str, Any]) -> str:
    data = result.to_dict() if hasattr(result, "to_dict") else result
    inputs = data.get("inputs") or {}
    lines = [
        "# MSN Source Adapter Total Package Index",
        "",
        f"Schema version: `{data.get('schema_version')}`",
        f"Root: `{inputs.get('root_path') or ''}`",
        f"Source URL: `{inputs.get('source_url') or 'not supplied'}`",
        f"Rendered HTML: `{inputs.get('rendered_html_path') or 'not found'}`",
        f"Comments JSON: `{inputs.get('comments_json_path') or 'not found'}`",
        f"Media download results: `{inputs.get('media_download_results_path') or 'not supplied'}`",
        "",
        "## Output files",
        "",
    ]
    for key, value in (data.get("output_paths") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Counts", ""])
    for key, value in (data.get("counts") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Review rule",
            "",
            "This total package joins article extraction, comments/profile exports, offline viewer/archive files, media registration/download sidecars, readiness/release/final validation, and source-role provenance. It still requires manual review for real MSN pages, ReplayWeb/WACZ behaviour, and original media/source-chain claims.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def write_msn_source_adapter_total_package(
    root_path: str | Path,
    *,
    source_url: str = "",
    output_dir: str | Path = "",
    rendered_html_path: str | Path = "",
    comments_json_path: str | Path = "",
    request_log_path: str | Path = "",
    media_download_results_path: str | Path = "",
) -> MsnTotalPackageResult:
    inputs = discover_msn_total_package_inputs(
        root_path,
        source_url=source_url,
        output_dir=output_dir,
        rendered_html_path=rendered_html_path,
        comments_json_path=comments_json_path,
        request_log_path=request_log_path,
        media_download_results_path=media_download_results_path,
    )
    out = Path(inputs.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    comments = _comments_export(inputs.comments_json_path)
    request_entries = _load_request_log(inputs.request_log_path)
    download_results = _load_media_download_results(inputs.media_download_results_path)
    bundle = build_msn_source_adapter_bundle(
        source_url=inputs.source_url,
        rendered_html_path=inputs.rendered_html_path,
        comments_export=comments,
        comments_export_files=_comments_files(inputs.comments_json_path),
        offline_archive_dir=inputs.offline_archive_dir,
        request_log_entries=request_entries,
        media_download_results=download_results,
        package_id="msn-source-adapter-total-package",
    )
    bundle_json = out / MSN_BUNDLE_JSON
    readiness_json = out / MSN_READINESS_JSON
    summary_json = out / MSN_TOTAL_PACKAGE_SUMMARY_JSON
    index_md = out / MSN_TOTAL_PACKAGE_INDEX_MD
    write_msn_source_adapter_bundle_json(bundle, bundle_json)
    readiness = evaluate_msn_source_adapter_readiness(bundle)
    write_msn_source_adapter_readiness_report(readiness, readiness_json)
    release_outputs = write_msn_source_adapter_release_outputs(bundle=bundle, output_dir=out, base_name="msn-source-adapter-release")
    # Validate the original capture/export root so article/archive/comments/media files are
    # checked together with the reports written under the default root subfolder.
    final_outputs = write_msn_adapter_final_validation_outputs(inputs.root_path, output_dir=out, source_url=inputs.source_url)
    output_paths = {
        "bundle_json": str(bundle_json),
        "readiness_json": str(readiness_json),
        **release_outputs,
        **final_outputs,
        "total_package_summary_json": str(summary_json),
        "total_package_index_markdown": str(index_md),
    }
    counts = {
        "media_records": len(bundle.media_records),
        "local_media_assets": sum(1 for record in bundle.media_records if record.local_media_path),
        "comments_supplied": 1 if bool(comments) else 0,
        "request_log_entries": len(request_entries),
        "download_result_records": len(download_results),
        "manifest_assets": len(bundle.manifest.assets),
        "provenance_records": len(bundle.manifest.provenance_records),
    }
    result = MsnTotalPackageResult(
        inputs=inputs,
        output_paths=output_paths,
        counts=counts,
        overall_note=(
            "MSN total package written. Use the final validation and release report to decide whether the current output folder is confident, partial, or not ready. "
            "Manual review is still required for live MSN behaviour, video delivery, and primary-source/original-media claims."
        ),
    )
    summary_json.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    index_md.write_text(render_msn_total_package_index(result), encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a joined MSN source adapter total package from an existing MSN capture/export folder.")
    parser.add_argument("root", help="Existing MSN output folder containing rendered HTML/archive/comments/media sidecars.")
    parser.add_argument("--source-url", default="", help="Original MSN URL.")
    parser.add_argument("--output-dir", default="", help="Output folder; defaults to <root>/msn_source_adapter_total_package.")
    parser.add_argument("--rendered-html", default="", help="Override rendered HTML path.")
    parser.add_argument("--comments-json", default="", help="Override comments JSON path.")
    parser.add_argument("--request-log", default="", help="Override request log JSON path.")
    parser.add_argument("--media-download-results", default="", help="Override media download results JSON path.")
    parser.add_argument("--json", action="store_true", help="Print package summary JSON.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = write_msn_source_adapter_total_package(
        args.root,
        source_url=args.source_url,
        output_dir=args.output_dir,
        rendered_html_path=args.rendered_html,
        comments_json_path=args.comments_json,
        request_log_path=args.request_log,
        media_download_results_path=args.media_download_results,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print("MSN source adapter total package written.")
        print(f"Index: {result.output_paths.get('total_package_index_markdown')}")
        print(f"Final validation: {result.output_paths.get('final_validation_markdown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
