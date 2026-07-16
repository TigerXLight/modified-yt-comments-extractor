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

    assert len(report.records) == 3
    youtube_record = report.records[0]
    assert youtube_record.adapter_id == "youtube"
    assert youtube_record.display_name == "YouTube"
    assert youtube_record.platform_family == "video_social"
    assert youtube_record.credential_type == "api_key"
    assert youtube_record.credentials_required is True
    assert youtube_record.supports_browser_capture is False
    assert youtube_record.supports_manual_import is False
    assert youtube_record.capabilities["supports_comments"] is True
    assert youtube_record.capabilities["supports_transcripts"] is True

    msn_record = report.records[1]
    assert msn_record.adapter_id == "msn"
    assert msn_record.display_name == "MSN"
    assert msn_record.platform_family == "news_website"
    assert msn_record.credential_type == "none"
    assert msn_record.credentials_required is False
    assert msn_record.supports_browser_capture is False
    assert msn_record.supports_manual_import is True
    assert msn_record.capabilities["supports_comments"] is True
    assert msn_record.capabilities["supports_replies"] is True
    assert "deterministic local fixture" in msn_record.access_limitations

    news_record = report.records[2]
    assert news_record.adapter_id == "news_website"
    assert news_record.display_name == "News Website"
    assert news_record.platform_family == "news_website"
    assert news_record.credential_type == "none"
    assert news_record.credentials_required is False
    assert news_record.supports_browser_capture is False
    assert news_record.supports_manual_import is True
    assert news_record.capabilities["supports_comments"] is False
    assert news_record.capabilities["supports_timestamps"] is True
    assert "metadata/URL-recognition skeleton only" in news_record.access_limitations
    assert "no fetch" in report.scope

    data = source_adapter_capability_report_to_dict(report)
    assert data["adapter_count"] == 3
    assert [item["adapter_id"] for item in data["source_adapters"]] == [
        "youtube",
        "msn",
        "news_website",
    ]
    assert data["source_adapters"][0]["capabilities"]["supports_comments"] is True
    assert data["source_adapters"][1]["capabilities"]["supports_comments"] is True
    assert data["source_adapters"][2]["supports_manual_import"] is True
    assert "Source adapter metadata" not in data

    markdown = build_source_adapter_capability_markdown(report)
    assert "# Source Adapter Capability Report" in markdown
    assert "Adapter ID: youtube" in markdown
    assert "Adapter ID: msn" in markdown
    assert "Adapter ID: news_website" in markdown
    assert "Credentials required: yes" in markdown
    assert "Enabled capabilities:" in markdown
    assert "does not fetch URLs" in markdown
    assert "existing YouTube fetching behavior remains implemented elsewhere" in markdown
    assert "metadata/URL-recognition skeleton only" in markdown

    text = build_source_adapter_capability_text(report)
    assert "Source adapter capability report" in text
    assert "youtube (YouTube)" in text
    assert "msn (MSN)" in text
    assert "news_website (News Website)" in text
    assert "credentials_required: True" in text
    assert "no fetch/capture/network" in text

    rendered_json = render_source_adapter_capability_report(report, output_format="json")
    parsed = json.loads(rendered_json)
    assert parsed["adapter_count"] == 3
    assert parsed["source_adapters"][2]["adapter_id"] == "news_website"

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
