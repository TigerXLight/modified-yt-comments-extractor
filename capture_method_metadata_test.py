import json

from capture_method_metadata import (
    CAPTURE_CATEGORY_BUNDLE,
    CAPTURE_CATEGORY_HTML,
    CAPTURE_CATEGORY_SCREENSHOT,
    CAPTURE_METHOD_SCOPE,
    CAPTURE_STATUS_MANUAL_ONLY,
    available_capture_methods,
    build_capture_method_metadata_markdown,
    build_capture_method_metadata_text,
    capture_method_by_id,
    capture_method_catalog_to_dict,
    capture_method_metadata_to_dict,
    render_capture_method_metadata,
)


EXPECTED_IDS = (
    "visible_screenshot",
    "full_page_screenshot",
    "scrollable_container_screenshot",
    "stitched_multi_image_capture",
    "selected_dom_print_html",
    "raw_saved_html",
    "manual_evidence_bundle",
)


def run_self_test() -> None:
    methods = available_capture_methods()
    assert tuple(method.method_id for method in methods) == EXPECTED_IDS
    assert len({method.method_id for method in methods}) == len(EXPECTED_IDS)
    assert all(method.status == CAPTURE_STATUS_MANUAL_ONLY for method in methods)
    assert all(method.manual_only is True for method in methods)
    assert all(method.scope == CAPTURE_METHOD_SCOPE for method in methods)
    assert "no fetch" in CAPTURE_METHOD_SCOPE
    assert "screenshot" in CAPTURE_METHOD_SCOPE

    visible = capture_method_by_id(" visible_screenshot ")
    assert visible is not None
    assert visible.display_name == "Visible screenshot"
    assert visible.category == CAPTURE_CATEGORY_SCREENSHOT
    assert visible.output_kinds == ("png",)
    assert visible.automation_candidate is True
    assert "nested scroll" in visible.limitations

    full_page = capture_method_by_id("FULL_PAGE_SCREENSHOT")
    assert full_page is not None
    assert "document scrolling" in full_page.limitations
    assert "nested" in full_page.limitations

    container = capture_method_by_id("scrollable_container_screenshot")
    assert container is not None
    assert "focused or selected" in container.limitations
    assert "ordering and overlap" in container.recommended_next_step

    stitched = capture_method_by_id("stitched_multi_image_capture")
    assert stitched is not None
    assert stitched.category == CAPTURE_CATEGORY_SCREENSHOT
    assert "sequence" in stitched.limitations

    selected_dom = capture_method_by_id("selected_dom_print_html")
    assert selected_dom is not None
    assert selected_dom.category == CAPTURE_CATEGORY_HTML
    assert selected_dom.output_kinds == ("html", "pdf")
    assert "Print Edit WE" in selected_dom.limitations

    raw_html = capture_method_by_id("raw_saved_html")
    assert raw_html is not None
    assert raw_html.category == CAPTURE_CATEGORY_HTML
    assert raw_html.output_kinds == ("html",)
    assert "unloaded" in raw_html.limitations

    bundle = capture_method_by_id("manual_evidence_bundle")
    assert bundle is not None
    assert bundle.category == CAPTURE_CATEGORY_BUNDLE
    assert bundle.automation_candidate is False
    assert bundle.output_kinds == (
        "png",
        "html",
        "pdf",
        "json",
        "warc",
        "text",
        "media",
    )
    assert capture_method_by_id("unknown") is None
    assert capture_method_by_id("") is None

    method_dict = capture_method_metadata_to_dict(visible)
    assert list(method_dict) == [
        "automation_candidate",
        "category",
        "display_name",
        "limitations",
        "manual_only",
        "method_id",
        "output_kinds",
        "recommended_next_step",
        "scope",
        "status",
    ]

    catalog = capture_method_catalog_to_dict()
    assert list(catalog) == [
        "capture_method_count",
        "capture_methods",
        "scope",
    ]
    assert catalog["capture_method_count"] == 7
    assert catalog["capture_methods"][2]["method_id"] == "scrollable_container_screenshot"

    markdown = build_capture_method_metadata_markdown()
    assert "# Capture Method Metadata" in markdown
    assert "## Scrollable-container screenshot" in markdown
    assert "## Selected DOM / print-cleaned HTML" in markdown
    assert "does not fetch pages" in markdown
    assert "not implemented execution" in markdown

    text = build_capture_method_metadata_text()
    assert "Capture method metadata" in text
    assert "scrollable_container_screenshot" in text
    assert "no fetch/capture/browser/screenshot/network" in text

    rendered_json = render_capture_method_metadata(output_format="json")
    parsed = json.loads(rendered_json)
    assert parsed["capture_method_count"] == 7
    assert parsed["capture_methods"][6]["method_id"] == "manual_evidence_bundle"
    assert render_capture_method_metadata(output_format="markdown") == markdown
    assert render_capture_method_metadata(output_format="text") == text

    try:
        render_capture_method_metadata(output_format="html")
    except ValueError as exc:
        assert "unsupported output format" in str(exc)
    else:
        raise AssertionError("unsupported format should fail")


if __name__ == "__main__":
    run_self_test()
    print("Capture method metadata self-test passed.")
