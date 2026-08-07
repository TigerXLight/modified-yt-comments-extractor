from __future__ import annotations

import json

from capture_msn_manual_comments_extraction import extract_msn_manual_comments, msn_manual_comments_extraction_to_json


def test_extracts_json_comments() -> None:
    payload = json.dumps({"comments": [{"id": "c1", "author": "A User", "text": "First visible comment", "likes": 3}, {"author": "B User", "comment": "Second visible comment"}]})
    extraction = extract_msn_manual_comments(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text=payload,
        artifact_file_name="comments.json",
    )
    assert extraction.comment_count == 2
    assert extraction.comments[0].author_display == "A User"
    assert extraction.comments[0].like_count == 3
    assert extraction.raw_payload_included is False
    assert "First visible comment" in msn_manual_comments_extraction_to_json(extraction)


def test_extracts_transcript_comments() -> None:
    extraction = extract_msn_manual_comments(
        source_url="https://www.msn.com/en-gb/news/example/story-id",
        artifact_text="Alice: Comment copied from the visible MSN thread.\n\nBob: Another visible comment.",
        artifact_file_name="comments.txt",
    )
    assert extraction.comment_count == 2
    assert extraction.comments[1].author_display == "Bob"


if __name__ == "__main__":
    test_extracts_json_comments()
    test_extracts_transcript_comments()
    print("MSN manual comments extraction self-test passed.")
