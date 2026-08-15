from __future__ import annotations

import json
from dataclasses import replace, asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping


TWITTER_BROWSER_CAPTURE_INSPECTOR_SCHEMA_VERSION = "twitter_browser_capture_inspector.v72"


@dataclass(frozen=True)
class TwitterBrowserCaptureInspection:
    schema_version: str
    output_dir: str
    status: str
    diagnosis: str
    source_url: str = ""
    canonical_url: str = ""
    api_page_count: int = 0
    network_event_count: int = 0
    media_item_count: int = 0
    matched_query_names: tuple[str, ...] = ()
    boundary_states: tuple[str, ...] = ()
    screenshot_exists: bool = False
    rendered_dom_exists: bool = False
    manifest_exists: bool = False
    network_events_exists: bool = False
    api_pages_exists: bool = False
    media_inventory_exists: bool = False
    cursor_boundaries_exists: bool = False
    safe_to_handoff_to_jd: bool = False
    evidence_completion_claim: str = ""
    rendered_dom_status_available: bool = False
    rendered_dom_media_item_count: int = 0
    rendered_dom_fallback_used: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    next_action: str = ""

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


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> tuple[Any, ...]:
    if not path.exists():
        return ()
    rows: list[Any] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"parse_error": True, "raw": line[:500]})
    except OSError:
        return ()
    return tuple(rows)


def _unique(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if value}))


def _media_items_include_rendered_dom(media_items: Any) -> int:
    if not isinstance(media_items, list):
        return 0
    count = 0
    for item in media_items:
        if not isinstance(item, Mapping):
            continue
        source_kind = str(item.get("source_kind") or "").lower()
        from_query = str(item.get("from_query_name") or "").lower()
        provenance = str(item.get("provenance") or "").lower()
        if source_kind.startswith("rendered_dom") or from_query == "rendered_dom" or provenance.startswith("rendered_dom"):
            count += 1
    return count


def _boundaries_are_http_404_no_items(boundaries: Any) -> bool:
    if not isinstance(boundaries, list) or not boundaries:
        return False
    saw_404 = False
    for item in boundaries:
        if not isinstance(item, Mapping):
            continue
        status = int(item.get("http_status") or 0)
        returned = int(item.get("returned_items_count") or 0)
        if status == 404:
            saw_404 = True
        if returned > 0:
            return False
    return saw_404


def _inspect_twitter_browser_capture_output_impl(output_dir: str | Path) -> TwitterBrowserCaptureInspection:
    output = Path(output_dir)
    manifest_path = output / "browser_session_manifest.json"
    network_path = output / "network_events.jsonl"
    api_pages_path = output / "api_pages.jsonl"
    boundaries_path = output / "cursor_boundaries.json"
    media_path = output / "media_inventory.json"
    screenshot_path = output / "screenshot.png"
    dom_path = output / "rendered_dom_snapshot.html"

    manifest = _read_json(manifest_path, {})
    network_rows = _read_jsonl(network_path)
    api_pages = _read_jsonl(api_pages_path)
    boundaries = _read_json(boundaries_path, [])
    media_items = _read_json(media_path, [])

    errors = tuple(str(item) for item in manifest.get("errors", ()) or ())
    warnings = tuple(str(item) for item in manifest.get("warnings", ()) or ())
    rendered_dom_media_count = _media_items_include_rendered_dom(media_items)
    api_404_no_items = _boundaries_are_http_404_no_items(boundaries)
    matched_query_names = _unique(
        [str(row.get("query_name") or "") for row in network_rows if isinstance(row, Mapping)]
        + [str(row.get("query_name") or "") for row in api_pages if isinstance(row, Mapping)]
    )
    boundary_states = _unique(
        [str(item.get("completeness_state") or item.get("stop_reason") or "") for item in boundaries if isinstance(item, Mapping)]
    )

    status = str(manifest.get("status") or "missing_manifest")
    diagnosis = "unknown"
    next_action = "review output files manually"

    if not manifest_path.exists():
        status = "missing_manifest"
        diagnosis = "no_capture_output"
        next_action = "run the browser capture tool first"
    elif any("playwright_unavailable" in error for error in errors):
        diagnosis = "playwright_missing"
        next_action = "install Playwright and its Chromium runtime, then rerun live capture"
    elif status == "failed":
        diagnosis = "capture_failed"
        next_action = "inspect manifest errors and rerun with headful browser if needed"
    elif not network_rows and not api_pages and status in {"planned", "success"}:
        diagnosis = "no_network_capture"
        next_action = "rerun with --live after Playwright is installed and a logged-in isolated profile is available"
    elif api_pages and not matched_query_names:
        diagnosis = "api_pages_without_query_names"
        next_action = "inspect api_pages.jsonl query matching"
    elif rendered_dom_media_count and api_404_no_items:
        diagnosis = "rendered_dom_status_available_api_404"
        next_action = "safe to hand rendered-DOM media URLs to the shared media backend/JDownloader; API 404 zero-items was preserved as an API-only result"
    elif rendered_dom_media_count:
        diagnosis = "rendered_dom_media_metadata_captured"
        next_action = "safe to hand rendered-DOM media URLs to the shared media backend/JDownloader"
    elif media_items:
        diagnosis = "media_discovered"
        next_action = "safe to hand discovered media URLs to the shared media backend/JDownloader"
    elif api_pages:
        diagnosis = "api_captured_no_media"
        next_action = "review whether this status/user/list actually contains media or needs additional scrolling/login"
    else:
        diagnosis = "needs_review"

    safe_to_handoff = bool(media_items) and diagnosis in {
        "media_discovered",
        "rendered_dom_media_metadata_captured",
        "rendered_dom_status_available_api_404",
    }

    return TwitterBrowserCaptureInspection(
        schema_version=TWITTER_BROWSER_CAPTURE_INSPECTOR_SCHEMA_VERSION,
        output_dir=str(output),
        status=status,
        diagnosis=diagnosis,
        source_url=str(manifest.get("source_url") or ""),
        canonical_url=str(manifest.get("canonical_url") or ""),
        api_page_count=int(manifest.get("api_page_count") or len(api_pages)),
        network_event_count=int(manifest.get("network_event_count") or len(network_rows)),
        media_item_count=int(manifest.get("media_item_count") or len(media_items)),
        matched_query_names=matched_query_names,
        boundary_states=boundary_states,
        screenshot_exists=screenshot_path.exists() and screenshot_path.stat().st_size > 0,
        rendered_dom_exists=dom_path.exists() and dom_path.stat().st_size > 0,
        manifest_exists=manifest_path.exists(),
        network_events_exists=network_path.exists(),
        api_pages_exists=api_pages_path.exists(),
        media_inventory_exists=media_path.exists(),
        cursor_boundaries_exists=boundaries_path.exists(),
        safe_to_handoff_to_jd=safe_to_handoff,
        evidence_completion_claim=str(manifest.get("evidence_completion_claim") or ""),
        rendered_dom_status_available=bool(manifest.get("rendered_dom_status_available") or rendered_dom_media_count),
        rendered_dom_media_item_count=int(manifest.get("rendered_dom_media_item_count") or rendered_dom_media_count),
        rendered_dom_fallback_used=bool(manifest.get("rendered_dom_fallback_used") or (rendered_dom_media_count and api_404_no_items)),
        warnings=warnings,
        errors=errors,
        next_action=next_action,
    )


def write_twitter_browser_capture_inspection(output_path: str | Path, inspection: TwitterBrowserCaptureInspection) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inspection.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return output


# --- V72B inspection policy hardening ---

def _ytce_v72b_inspector_read_json(path: str | Path, default: Any) -> Any:
    try:
        p = Path(path)
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def _ytce_v72b_inspector_is_markdown_url(value: Any) -> bool:
    text = str(value or "").strip()
    return text.startswith("[") and "](" in text and text.endswith(")")


def _ytce_v72b_inspector_boundaries_are_http_404_no_items(boundaries: Any) -> bool:
    if not isinstance(boundaries, list) or not boundaries:
        return False
    saw_404 = False
    for item in boundaries:
        if not isinstance(item, Mapping):
            continue
        status = int(item.get("http_status") or 0)
        returned = int(item.get("returned_items_count") or 0)
        if status == 404:
            saw_404 = True
        if returned > 0:
            return False
    return saw_404


def inspect_twitter_browser_capture_output(output_dir: str | Path) -> TwitterBrowserCaptureInspection:
    inspection = _inspect_twitter_browser_capture_output_impl(output_dir)
    output = Path(output_dir)
    boundaries = _ytce_v72b_inspector_read_json(output / "cursor_boundaries.json", [])
    media_items = _ytce_v72b_inspector_read_json(output / "media_inventory.json", [])

    if _ytce_v72b_inspector_is_markdown_url(inspection.source_url) or _ytce_v72b_inspector_is_markdown_url(inspection.canonical_url):
        return replace(
            inspection,
            diagnosis="runner_url_not_normalized",
            safe_to_handoff_to_jd=False,
            evidence_completion_claim="not_completed",
            next_action="rerun after runner URL unwrapping, using a plain https://x.com/... URL",
        )

    if _ytce_v72b_inspector_boundaries_are_http_404_no_items(boundaries) and not media_items:
        return replace(
            inspection,
            status="needs_review",
            diagnosis="twitter_api_http_404_no_items",
            safe_to_handoff_to_jd=False,
            evidence_completion_claim="not_completed",
            next_action="use a real public status/list/user URL or a logged-in isolated profile; do not treat the 404 zero-item capture as completed",
        )

    return inspection
