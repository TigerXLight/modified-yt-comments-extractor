from __future__ import annotations

import json

from capture_msn_manual_article_extraction import extract_msn_manual_article
from capture_msn_manual_capture_bundle import build_msn_manual_capture_bundle
from capture_msn_manual_comments_extraction import extract_msn_manual_comments
from capture_msn_manual_total_export_manifest import build_msn_manual_total_export_packet, msn_manual_total_export_packet_to_json


def _bundle():
    article = extract_msn_manual_article(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text="MSN Example Headline\nArticle body copied by operator for review.",
        artifact_file_name="article.txt",
    )
    comments = extract_msn_manual_comments(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text='[{"author":"Alice","text":"Visible comment"}]',
        artifact_file_name="comments.json",
    )
    return build_msn_manual_capture_bundle(article=article, comments=comments)


def test_builds_total_export_manifest_packet_with_relative_assets() -> None:
    packet = build_msn_manual_total_export_packet(bundle=_bundle(), package_id="msn_manual_example")
    payload = json.loads(msn_manual_total_export_packet_to_json(packet))
    assert payload["total_export_manifest_implemented"] is True
    assert payload["ready_for_total_export_review"] is True
    assert payload["comment_count"] == 1
    assert "page_capture/msn_manual_example_article_text.txt" in payload["asset_paths"]
    assert "metadata/msn_manual_example_comments.json" in payload["asset_paths"]
    assert payload["manifest"]["output_folder"] == ""
    assert payload["full_local_path_serialized"] is False
    assert "C:\\" not in msn_manual_total_export_packet_to_json(packet)


if __name__ == "__main__":
    test_builds_total_export_manifest_packet_with_relative_assets()
    print("MSN manual Total Export manifest self-test passed.")
