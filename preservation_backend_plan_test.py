import json

from preservation_backend_plan import (
    BACKEND_STATUS_FUTURE,
    BACKEND_STATUS_MANUAL,
    MEDIA_PRESERVATION_CHOICE_ALL,
    MEDIA_PRESERVATION_CHOICE_NONE,
    MEDIA_PRESERVATION_CHOICE_SELECT,
    PLAN_STATUS_NEEDS_SELECTION,
    PLAN_STATUS_READY,
    build_preservation_backend_plan,
    build_preservation_backend_plan_markdown,
    build_preservation_backend_plan_text,
    normalize_media_preservation_choice,
    preservation_backend_plan_to_dict,
    render_preservation_backend_plan,
)


def run_self_test() -> None:
    plan = build_preservation_backend_plan(
        source_url=" https://www.telegraph.co.uk/news/example/?utm=x ",
        selected_backend_ids=[
            "manual_local_files",
            "archivebox_self_hosted",
            "manual_local_files",
            "unknown_backend",
        ],
        selected_format_ids=["html", "pdf", "warc", "html", "unknown_format"],
        selected_capture_method_ids=[
            "visible_screenshot",
            "scrollable_container_screenshot",
            "visible_screenshot",
            "unknown_capture",
        ],
        media_preservation_choice=" select ",
        notes="User wants a local backup plan.",
    )

    assert plan.status == PLAN_STATUS_READY
    assert plan.source_url == "https://www.telegraph.co.uk/news/example/?utm=x"
    assert plan.selected_backend_ids == (
        "manual_local_files",
        "archivebox_self_hosted",
    )
    assert plan.selected_format_ids == ("html", "pdf", "warc")
    assert plan.unknown_backend_ids == ("unknown_backend",)
    assert plan.unknown_format_ids == ("unknown_format",)
    assert plan.duplicate_backend_ids == ("manual_local_files",)
    assert plan.duplicate_format_ids == ("html",)
    assert plan.selected_capture_method_ids == (
        "visible_screenshot",
        "scrollable_container_screenshot",
    )
    assert plan.unknown_capture_method_ids == ("unknown_capture",)
    assert plan.duplicate_capture_method_ids == ("visible_screenshot",)
    assert plan.media_preservation_choice == MEDIA_PRESERVATION_CHOICE_SELECT
    assert "Unknown preservation backends ignored: unknown_backend" in plan.warnings
    assert "Unknown preservation formats ignored: unknown_format" in plan.warnings
    assert "Duplicate preservation backends ignored: manual_local_files" in plan.warnings
    assert "Duplicate preservation formats ignored: html" in plan.warnings
    assert "Unknown capture methods ignored: unknown_capture" in plan.warnings
    assert "Duplicate capture methods ignored: visible_screenshot" in plan.warnings
    assert "no fetch" in plan.scope
    assert "ArchiveBox execution" in plan.scope

    data = preservation_backend_plan_to_dict(plan)
    assert data["status"] == PLAN_STATUS_READY
    assert data["selected_backend_ids"] == [
        "manual_local_files",
        "archivebox_self_hosted",
    ]
    assert data["selected_format_ids"] == ["html", "pdf", "warc"]
    assert data["media_preservation_choice"] == MEDIA_PRESERVATION_CHOICE_SELECT
    assert data["selected_capture_method_ids"] == [
        "visible_screenshot",
        "scrollable_container_screenshot",
    ]
    assert [method["method_id"] for method in data["capture_methods"]] == [
        "visible_screenshot",
        "scrollable_container_screenshot",
    ]
    assert "focused or selected" in data["capture_methods"][1]["limitations"]
    choices = {
        item["choice_id"]: item
        for item in data["available_media_preservation_choices"]
    }
    assert set(choices) == {"none", "select", "all"}
    assert choices["none"]["explicit_opt_in"] is False
    assert choices["all"]["explicit_opt_in"] is True
    backends = {item["backend_id"]: item for item in data["available_backends"]}
    assert backends["manual_local_files"]["status"] == BACKEND_STATUS_MANUAL
    assert backends["archivebox_self_hosted"]["status"] == BACKEND_STATUS_FUTURE
    assert backends["archivebox_self_hosted"]["execution_supported"] is False
    formats = {item["format_id"]: item for item in data["available_formats"]}
    assert ".warc" in formats["warc"]["file_extensions"]
    assert ".mp4" in formats["media"]["file_extensions"]
    assert ".sqlite" in formats["sqlite"]["file_extensions"]

    markdown = build_preservation_backend_plan_markdown(plan)
    assert "# Preservation Backend Plan" in markdown
    assert "Selected backends: manual_local_files, archivebox_self_hosted" in markdown
    assert "Selected formats: html, pdf, warc" in markdown
    assert "does not fetch URLs" in markdown
    assert "run ArchiveBox" in markdown
    assert "Available Formats" in markdown
    assert "Media preservation choice: select" in markdown
    assert "choices are `none`, `select`, or `all`" in markdown
    assert "does not discover or download media" in markdown
    assert "Selected capture methods: visible_screenshot, scrollable_container_screenshot" in markdown
    assert "Scrollable-container screenshot" in markdown
    assert "No capture is executed" not in markdown

    text = build_preservation_backend_plan_text(plan)
    assert "Preservation backend plan" in text
    assert "archivebox_self_hosted" in text
    assert "no fetch/capture/network" in text
    assert "media_preservation_choice: select" in text
    assert "choices are none, select, or all" in text
    assert "selected_capture_method_ids: visible_screenshot, scrollable_container_screenshot" in text
    assert "execution=metadata only" in text

    rendered_json = render_preservation_backend_plan(plan, output_format="json")
    parsed = json.loads(rendered_json)
    assert parsed["selected_format_ids"] == ["html", "pdf", "warc"]
    assert parsed["media_preservation_choice"] == "select"
    assert parsed["selected_capture_method_ids"] == [
        "visible_screenshot",
        "scrollable_container_screenshot",
    ]

    assert render_preservation_backend_plan(plan, output_format="markdown") == markdown
    assert render_preservation_backend_plan(plan, output_format="text") == text

    empty = build_preservation_backend_plan()
    assert empty.media_preservation_choice == MEDIA_PRESERVATION_CHOICE_NONE
    assert empty.selected_capture_method_ids == ()
    assert empty.unknown_capture_method_ids == ()
    assert empty.duplicate_capture_method_ids == ()
    empty_data = preservation_backend_plan_to_dict(empty)
    assert empty_data["selected_capture_method_ids"] == []
    assert empty_data["capture_methods"] == []
    assert empty.status == PLAN_STATUS_NEEDS_SELECTION
    assert "No preservation backend selected." in empty.warnings
    assert "No preservation formats selected." in empty.warnings
    assert "none specified; no capture is executed" in build_preservation_backend_plan_text(empty)

    explicit_all = build_preservation_backend_plan(media_preservation_choice="all")
    assert explicit_all.media_preservation_choice == MEDIA_PRESERVATION_CHOICE_ALL
    assert normalize_media_preservation_choice("SELECT") == MEDIA_PRESERVATION_CHOICE_SELECT
    try:
        normalize_media_preservation_choice("everything")
    except ValueError as exc:
        assert "expected one of none, select, all" in str(exc)
    else:
        raise AssertionError("unknown media preservation choice should fail")

    try:
        render_preservation_backend_plan(plan, output_format="html")
    except ValueError as exc:
        assert "unsupported output format" in str(exc)
    else:
        raise AssertionError("unsupported format should fail")


if __name__ == "__main__":
    run_self_test()
    print("Preservation backend plan self-test passed.")
