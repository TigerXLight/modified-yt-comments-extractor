import json

from source_adapter_gap_analysis import (
    STATUS_FUTURE_BACKEND,
    STATUS_FUTURE_CANDIDATE,
    STATUS_IMPLEMENTED,
    build_source_adapter_gap_analysis,
    build_source_adapter_gap_analysis_markdown,
    build_source_adapter_gap_analysis_text,
    render_source_adapter_gap_analysis,
    source_adapter_gap_analysis_to_dict,
)


def run_self_test() -> None:
    analysis = build_source_adapter_gap_analysis()

    assert analysis.current_adapter_ids == ("youtube", "msn", "news_website")
    assert "no fetch" in analysis.scope

    data = source_adapter_gap_analysis_to_dict(analysis)
    assert data["implemented_adapter_count"] == 3
    assert data["current_adapter_ids"] == ["youtube", "msn", "news_website"]

    categories = {category["category_id"]: category for category in data["categories"]}
    assert categories["youtube"]["status"] == STATUS_IMPLEMENTED
    assert categories["msn"]["status"] == STATUS_IMPLEMENTED
    assert categories["msn"]["current_adapter_ids"] == ["msn"]
    assert categories["news_website"]["status"] == STATUS_IMPLEMENTED
    assert categories["social_video"]["status"] == STATUS_FUTURE_CANDIDATE
    assert "TikTok" in categories["social_video"]["example_platforms"]
    assert "Instagram" in categories["social_video"]["example_platforms"]
    assert "Facebook video" in categories["social_video"]["example_platforms"]
    assert "Twitter/X" in categories["text_microblogging"]["example_platforms"]
    assert "Threads" in categories["text_microblogging"]["example_platforms"]
    assert "Reddit" in categories["community_forum"]["example_platforms"]
    assert "Trustpilot" in categories["review_platforms"]["example_platforms"]
    assert "Google Reviews" in categories["review_platforms"]["example_platforms"]
    assert "Amazon reviews" in categories["review_platforms"]["example_platforms"]
    assert "Substack" in categories["newsletter_sites"]["example_platforms"]
    assert "Discord" in categories["workplace_chat"]["example_platforms"]
    assert categories["self_hosted_preservation"]["status"] == STATUS_FUTURE_BACKEND
    assert "ArchiveBox" in categories["self_hosted_preservation"]["example_platforms"][0]
    assert "WARC" in categories["self_hosted_preservation"]["notes"]

    markdown = build_source_adapter_gap_analysis_markdown(analysis)
    assert "# Source Adapter / Preservation Gap Analysis" in markdown
    assert "Current adapters: youtube, msn, news_website" in markdown
    assert "Newsletter / publication websites" in markdown
    assert "Self-hosted preservation backend" in markdown
    assert "does not fetch URLs" in markdown

    text = build_source_adapter_gap_analysis_text(analysis)
    assert "Source adapter / preservation gap analysis" in text
    assert "social_video" in text
    assert "newsletter_sites" in text
    assert "no fetch/capture/network" in text

    rendered_json = render_source_adapter_gap_analysis(analysis, output_format="json")
    parsed = json.loads(rendered_json)
    assert parsed["implemented_adapter_count"] == 3
    assert parsed["current_adapter_ids"] == ["youtube", "msn", "news_website"]

    assert render_source_adapter_gap_analysis(analysis, output_format="markdown") == markdown
    assert render_source_adapter_gap_analysis(analysis, output_format="text") == text

    try:
        render_source_adapter_gap_analysis(analysis, output_format="html")
    except ValueError as exc:
        assert "unsupported output format" in str(exc)
    else:
        raise AssertionError("unsupported format should fail")


if __name__ == "__main__":
    run_self_test()
    print("Source adapter gap analysis self-test passed.")
