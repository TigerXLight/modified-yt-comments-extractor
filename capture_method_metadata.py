from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


REPORT_FORMATS = ("markdown", "text", "json")

CAPTURE_CATEGORY_SCREENSHOT = "screenshot"
CAPTURE_CATEGORY_HTML = "html"
CAPTURE_CATEGORY_BUNDLE = "bundle"

CAPTURE_STATUS_MANUAL_ONLY = "manual_only"

CAPTURE_METHOD_SCOPE = (
    "local capture-method metadata only; no fetch, capture, browser, screenshot, "
    "network, scraping, archive, download, credential, provider, or GUI behavior"
)


@dataclass(frozen=True)
class CaptureMethodMetadata:
    method_id: str
    display_name: str
    category: str
    status: str
    output_kinds: tuple[str, ...]
    manual_only: bool
    automation_candidate: bool
    limitations: str
    recommended_next_step: str
    scope: str = CAPTURE_METHOD_SCOPE


CAPTURE_METHOD_OPTIONS: tuple[CaptureMethodMetadata, ...] = (
    CaptureMethodMetadata(
        method_id="visible_screenshot",
        display_name="Visible screenshot",
        category=CAPTURE_CATEGORY_SCREENSHOT,
        status=CAPTURE_STATUS_MANUAL_ONLY,
        output_kinds=("png",),
        manual_only=True,
        automation_candidate=True,
        limitations=(
            "Captures the current viewport only and may miss offscreen content or content "
            "inside nested scroll containers."
        ),
        recommended_next_step=(
            "Record the visible viewport and note whether comments or other evidence continue offscreen."
        ),
    ),
    CaptureMethodMetadata(
        method_id="full_page_screenshot",
        display_name="Full-page screenshot",
        category=CAPTURE_CATEGORY_SCREENSHOT,
        status=CAPTURE_STATUS_MANUAL_ONLY,
        output_kinds=("png",),
        manual_only=True,
        automation_candidate=True,
        limitations=(
            "Captures document scrolling but may miss unloaded content or content inside nested "
            "scroll containers and modals."
        ),
        recommended_next_step=(
            "Record the capture tool and separately inspect nested containers before treating the page capture as complete."
        ),
    ),
    CaptureMethodMetadata(
        method_id="scrollable_container_screenshot",
        display_name="Scrollable-container screenshot",
        category=CAPTURE_CATEGORY_SCREENSHOT,
        status=CAPTURE_STATUS_MANUAL_ONLY,
        output_kinds=("png",),
        manual_only=True,
        automation_candidate=True,
        limitations=(
            "Targets a nested container or modal and requires the container to be focused or "
            "selected; long threads may require repeated captures."
        ),
        recommended_next_step=(
            "Identify the container, record its scroll position, and preserve repeated captures with ordering and overlap notes."
        ),
    ),
    CaptureMethodMetadata(
        method_id="stitched_multi_image_capture",
        display_name="Stitched/multi-image capture",
        category=CAPTURE_CATEGORY_SCREENSHOT,
        status=CAPTURE_STATUS_MANUAL_ONLY,
        output_kinds=("png",),
        manual_only=True,
        automation_candidate=True,
        limitations=(
            "Uses multiple images assembled into one image or retained as a sequence; missing "
            "overlap, repeated regions, or ordering mistakes can obscure context."
        ),
        recommended_next_step=(
            "Preserve original images, sequence order, stitching method, and overlap notes alongside any combined image."
        ),
    ),
    CaptureMethodMetadata(
        method_id="selected_dom_print_html",
        display_name="Selected DOM / print-cleaned HTML",
        category=CAPTURE_CATEGORY_HTML,
        status=CAPTURE_STATUS_MANUAL_ONLY,
        output_kinds=("html", "pdf"),
        manual_only=True,
        automation_candidate=True,
        limitations=(
            "Manual DOM or print-edit output such as Print Edit WE can simplify evidence but may "
            "lose scripts, styles, surrounding context, hidden content, or dynamic state."
        ),
        recommended_next_step=(
            "Record the selected block and editing tool, preserve limitations, and keep a less-modified source reference when available."
        ),
    ),
    CaptureMethodMetadata(
        method_id="raw_saved_html",
        display_name="Raw saved HTML",
        category=CAPTURE_CATEGORY_HTML,
        status=CAPTURE_STATUS_MANUAL_ONLY,
        output_kinds=("html",),
        manual_only=True,
        automation_candidate=True,
        limitations=(
            "Saved browser HTML or page source may contain dynamic placeholders, omit unloaded "
            "comments or assets, and depend on external scripts or files."
        ),
        recommended_next_step=(
            "Record how the HTML was saved and pair it with visible evidence and notes about unloaded or dynamic content."
        ),
    ),
    CaptureMethodMetadata(
        method_id="manual_evidence_bundle",
        display_name="Manual evidence bundle",
        category=CAPTURE_CATEGORY_BUNDLE,
        status=CAPTURE_STATUS_MANUAL_ONLY,
        output_kinds=("png", "html", "pdf", "json", "warc", "text", "media"),
        manual_only=True,
        automation_candidate=False,
        limitations=(
            "The user supplies screenshots, HTML, PDF, WARC, media, metadata, or notes created "
            "outside the app; completeness and provenance depend on the supplied materials."
        ),
        recommended_next_step=(
            "Inventory user-supplied files, preserve original ordering and notes, and register hashes/provenance in a later approved manifest workflow."
        ),
    ),
)


def available_capture_methods() -> tuple[CaptureMethodMetadata, ...]:
    return CAPTURE_METHOD_OPTIONS


def capture_method_by_id(method_id: str) -> CaptureMethodMetadata | None:
    normalized = str(method_id or "").strip().lower()
    return next(
        (method for method in CAPTURE_METHOD_OPTIONS if method.method_id == normalized),
        None,
    )


def capture_method_metadata_to_dict(
    method: CaptureMethodMetadata,
) -> dict[str, Any]:
    return {
        "automation_candidate": method.automation_candidate,
        "category": method.category,
        "display_name": method.display_name,
        "limitations": method.limitations,
        "manual_only": method.manual_only,
        "method_id": method.method_id,
        "output_kinds": list(method.output_kinds),
        "recommended_next_step": method.recommended_next_step,
        "scope": method.scope,
        "status": method.status,
    }


def capture_method_catalog_to_dict() -> dict[str, Any]:
    return {
        "capture_method_count": len(CAPTURE_METHOD_OPTIONS),
        "capture_methods": [
            capture_method_metadata_to_dict(method)
            for method in CAPTURE_METHOD_OPTIONS
        ],
        "scope": CAPTURE_METHOD_SCOPE,
    }


def build_capture_method_metadata_markdown() -> str:
    lines = [
        "# Capture Method Metadata",
        "",
        "Local metadata only. This catalog does not fetch pages, run browsers, capture screenshots, scrape content, download media, call network/archive/provider services, store credentials, or wire into the GUI.",
        "",
        f"- Capture method count: {len(CAPTURE_METHOD_OPTIONS)}",
        "- Current status: manual metadata only; automation-candidate flags describe possible future review, not implemented execution.",
        "",
    ]
    for method in CAPTURE_METHOD_OPTIONS:
        lines.extend(
            [
                f"## {method.display_name}",
                "",
                f"- Method ID: {method.method_id}",
                f"- Category: {method.category}",
                f"- Status: {method.status}",
                f"- Output kinds: {', '.join(method.output_kinds)}",
                f"- Manual only: {'yes' if method.manual_only else 'no'}",
                f"- Future automation candidate: {'yes' if method.automation_candidate else 'no'}",
                f"- Limitations: {method.limitations}",
                f"- Recommended next step: {method.recommended_next_step}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_capture_method_metadata_text() -> str:
    lines = [
        "Capture method metadata",
        "Scope: local metadata only; no fetch/capture/browser/screenshot/network/scraping/archive/download/credential/provider/GUI behavior is performed.",
        f"capture_method_count: {len(CAPTURE_METHOD_OPTIONS)}",
    ]
    for method in CAPTURE_METHOD_OPTIONS:
        lines.extend(
            [
                "",
                f"{method.method_id} ({method.display_name})",
                f"category: {method.category}",
                f"status: {method.status}",
                f"output_kinds: {', '.join(method.output_kinds)}",
                f"manual_only: {method.manual_only}",
                f"automation_candidate: {method.automation_candidate}",
                f"limitations: {method.limitations}",
                f"recommended_next_step: {method.recommended_next_step}",
            ]
        )
    return "\n".join(lines)


def render_capture_method_metadata(*, output_format: str) -> str:
    if output_format == "markdown":
        return build_capture_method_metadata_markdown()
    if output_format == "text":
        return build_capture_method_metadata_text()
    if output_format == "json":
        return json.dumps(capture_method_catalog_to_dict(), indent=2, sort_keys=True)
    raise ValueError(f"unsupported output format: {output_format}")
