import json

from source_adapter_capability_report import (
    build_source_adapter_capability_markdown,
    build_source_adapter_capability_report,
    build_source_adapter_capability_text,
    render_source_adapter_capability_report,
    source_adapter_capability_report_to_dict,
)


def run_self_test() -> None:
    report = build_source_adapter_capability_report()

    assert len(report.records) == 1
    record = report.records[0]
    assert record.adapter_id == "youtube"
    assert record.display_name == "YouTube"
    assert record.platform_family == "video_social"
    assert record.credential_type == "api_key"
    assert record.credentials_required is True
    assert record.supports_browser_capture is False
    assert record.supports_manual_import is False
    assert record.capabilities["supports_comments"] is True
    assert record.capabilities["supports_transcripts"] is True
    assert "no fetch" in report.scope

    data = source_adapter_capability_report_to_dict(report)
    assert data["adapter_count"] == 1
    assert data["source_adapters"][0]["adapter_id"] == "youtube"
    assert data["source_adapters"][0]["capabilities"]["supports_comments"] is True
    assert "Source adapter metadata" not in data

    markdown = build_source_adapter_capability_markdown(report)
    assert "# Source Adapter Capability Report" in markdown
    assert "Adapter ID: youtube" in markdown
    assert "Credentials required: yes" in markdown
    assert "Enabled capabilities:" in markdown
    assert "does not fetch URLs" in markdown
    assert "existing YouTube fetching behavior remains implemented elsewhere" in markdown

    text = build_source_adapter_capability_text(report)
    assert "Source adapter capability report" in text
    assert "youtube (YouTube)" in text
    assert "credentials_required: True" in text
    assert "no fetch/capture/network" in text

    rendered_json = render_source_adapter_capability_report(report, output_format="json")
    parsed = json.loads(rendered_json)
    assert parsed["adapter_count"] == 1
    assert parsed["source_adapters"][0]["adapter_id"] == "youtube"

    assert render_source_adapter_capability_report(report, output_format="markdown") == markdown
    assert render_source_adapter_capability_report(report, output_format="text") == text

    try:
        render_source_adapter_capability_report(report, output_format="html")
    except ValueError as exc:
        assert "unsupported output format" in str(exc)
    else:
        raise AssertionError("unsupported format should fail")


if __name__ == "__main__":
    run_self_test()
    print("Source adapter capability report self-test passed.")
