import json

from preservation_evidence_bundle import (
    BUNDLE_STATUS_MANUAL_SUPPLIED,
    BUNDLE_STATUS_PLANNED,
    build_preservation_evidence_bundle,
    build_preservation_evidence_bundle_markdown,
    build_preservation_evidence_bundle_text,
    build_preservation_evidence_bundle_from_dict,
    build_preservation_evidence_item,
    build_preservation_evidence_items_from_specs,
    preservation_evidence_bundle_to_dict,
    render_preservation_evidence_bundle,
)


def run_self_test() -> None:
    empty = build_preservation_evidence_bundle(bundle_label="Future evidence")
    assert empty.status == BUNDLE_STATUS_PLANNED
    assert empty.items == ()
    assert "empty/planned metadata bundle" in empty.warnings[0]
    empty_data = preservation_evidence_bundle_to_dict(empty)
    assert empty_data["items"] == []
    assert "no file open" in empty_data["scope"]
    assert "no file existence or capture execution is implied" in (
        build_preservation_evidence_bundle_text(empty)
    )

    screenshot = build_preservation_evidence_item(
        artifact_id="screenshot",
        artifact_format="png",
        capture_method_id="scrollable_container_screenshot",
        artifact_role="primary",
        origin="manual",
        path_hint=r"captures\comments.png",
        notes="User-supplied path hint only.",
    )
    assert screenshot.artifact_format == "png"
    assert screenshot.capture_method_id == "scrollable_container_screenshot"
    assert "focused or selected" in screenshot.limitations

    parsed_items = build_preservation_evidence_items_from_specs(
        ("screenshot:png:scrollable_container_screenshot",),
        item_role_specs=("screenshot=primary",),
        item_origin_specs=("screenshot=manual",),
        item_path_hint_specs=(r"screenshot=captures\comments.png",),
        item_note_specs=("screenshot=Parsed from shared spec helper.",),
    )
    assert len(parsed_items) == 1
    assert parsed_items[0].artifact_id == "screenshot"
    assert parsed_items[0].artifact_role == "primary"
    assert parsed_items[0].origin == "manual"
    assert parsed_items[0].path_hint == r"captures\comments.png"
    assert parsed_items[0].notes == "Parsed from shared spec helper."

    try:
        build_preservation_evidence_items_from_specs(
            ("screenshot:png",),
            item_role_specs=("missing=primary",),
        )
    except ValueError as exc:
        assert "unknown artifact IDs" in str(exc)
    else:
        raise AssertionError("Expected unknown detail artifact ID rejection.")

    try:
        build_preservation_evidence_items_from_specs(
            ("screenshot:png",),
            item_role_specs=("screenshot=primary", "screenshot=supporting"),
        )
    except ValueError as exc:
        assert "duplicate item role metadata" in str(exc)
    else:
        raise AssertionError("Expected duplicate item detail rejection.")

    try:
        build_preservation_evidence_items_from_specs(
            ("screenshot:png",),
            item_role_specs=("screenshot-primary",),
        )
    except ValueError as exc:
        assert "item role must use artifact_id=value" in str(exc)
    else:
        raise AssertionError("Expected malformed item detail rejection.")

    html = build_preservation_evidence_item(
        artifact_id="saved_html",
        artifact_format="html",
        capture_method_id="raw_saved_html",
        origin="external_tool",
    )
    assert "unloaded" in html.limitations

    bundle = build_preservation_evidence_bundle(
        source_url=" https://www.telegraph.co.uk/news/example/ ",
        source_id="example",
        source_name="news_website",
        bundle_label="Manual preservation evidence",
        status="manual_supplied",
        notes="Metadata only.",
        items=(screenshot, html),
    )
    assert bundle.status == BUNDLE_STATUS_MANUAL_SUPPLIED
    assert bundle.source_url == "https://www.telegraph.co.uk/news/example/"
    assert bundle.warnings == ()

    bundle_from_dict = build_preservation_evidence_bundle_from_dict(
        {
            "source_url": " https://www.telegraph.co.uk/news/example/ ",
            "bundle_label": "Manual preservation evidence",
            "status": "manual_supplied",
            "notes": "Metadata only.",
            "items": [
                {
                    "artifact_id": "screenshot",
                    "artifact_format": "png",
                    "capture_method_id": "scrollable_container_screenshot",
                    "artifact_role": "primary",
                    "origin": "manual",
                    "path_hint": r"captures\comments.png",
                    "notes": "JSON input path hint only.",
                }
            ],
        }
    )
    assert bundle_from_dict.status == BUNDLE_STATUS_MANUAL_SUPPLIED
    assert bundle_from_dict.items[0].artifact_id == "screenshot"
    assert bundle_from_dict.items[0].artifact_role == "primary"
    assert bundle_from_dict.items[0].origin == "manual"
    assert bundle_from_dict.items[0].path_hint == r"captures\comments.png"
    assert bundle_from_dict.items[0].notes == "JSON input path hint only."

    try:
        build_preservation_evidence_bundle_from_dict({"items": {}})
    except ValueError as exc:
        assert "evidence_bundle.items must be a list" in str(exc)
    else:
        raise AssertionError("Expected invalid evidence bundle items rejection.")

    data = preservation_evidence_bundle_to_dict(bundle)
    assert data["status"] == "manual_supplied"
    assert [item["artifact_id"] for item in data["items"]] == [
        "screenshot",
        "saved_html",
    ]
    assert data["items"][0]["artifact_format"] == "png"
    assert data["items"][0]["capture_method_id"] == "scrollable_container_screenshot"
    assert data["items"][0]["capture_method"]["display_name"] == "Scrollable-container screenshot"
    assert "no file open" in data["scope"]

    markdown = build_preservation_evidence_bundle_markdown(bundle)
    assert "# Preservation Evidence Bundle Metadata" in markdown
    assert "Scrollable" not in markdown
    assert "focused or selected" in markdown
    assert "- Notes: User-supplied path hint only." in markdown
    assert "does not prove file existence" in markdown

    text = build_preservation_evidence_bundle_text(bundle)
    assert "screenshot: format=png" in text
    assert "notes=User-supplied path hint only." in text
    assert "execution=metadata only" in text

    parsed = json.loads(render_preservation_evidence_bundle(bundle, output_format="json"))
    assert parsed["source_url"] == "https://www.telegraph.co.uk/news/example/"
    assert parsed["items"][1]["capture_method_id"] == "raw_saved_html"

    for kwargs, message in (
        (
            {"artifact_id": "bad_method", "artifact_format": "png", "capture_method_id": "unknown"},
            "invalid capture method ID",
        ),
        (
            {"artifact_id": "bad_format", "artifact_format": "exe"},
            "invalid artifact format",
        ),
    ):
        try:
            build_preservation_evidence_item(**kwargs)
        except ValueError as exc:
            assert message in str(exc)
        else:
            raise AssertionError(f"{message} should fail")

    duplicate = build_preservation_evidence_item(
        artifact_id="screenshot",
        artifact_format="png",
    )
    try:
        build_preservation_evidence_bundle(items=(screenshot, duplicate))
    except ValueError as exc:
        assert "duplicate artifact IDs: screenshot" in str(exc)
    else:
        raise AssertionError("duplicate artifact IDs should fail")

    try:
        render_preservation_evidence_bundle(bundle, output_format="xml")
    except ValueError as exc:
        assert "unsupported output format" in str(exc)
    else:
        raise AssertionError("unsupported output format should fail")


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle self-test passed.")
