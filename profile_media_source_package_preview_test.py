from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_database_batch_import_assistant import validate_batch_json_file
from profile_media_database_import_review_decisions import build_import_review_decision_state
from profile_media_source_package_preview import (
    WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_CONFIRMATION,
    build_profile_media_source_package_preview,
    extract_preserved_youtube_comment_threads,
    format_youtube_comment_threads_for_review_display,
    normalise_source_package_artifact_kind,
    claim_basis_for_package_artifact_kind,
    render_profile_media_source_package_preview_text,
    source_bucket_for_package_artifact_kind,
    source_package_preview_payload,
    source_role_for_package_artifact_kind,
    write_profile_media_source_package_preview_json,
)
from profile_media_link_source_decisions import append_link_source_decision, link_source_object_key
from profile_media_source_text_sections import sections_by_type, split_source_text_sections


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_preserved_youtube_comment_thread_extractor_handles_brett_authored_replies_only() -> None:
    comments_text = """
@andreadewsbury3958
1 month ago
Loved listening to this.
12
Reply

    @RevBrettMurphy
    1 month ago
    A truly prophetic word!
    3
    Reply

@OtherUser
1 month ago
@RevBrettMurphy this is only a mention, not Brett authoring a comment.
Reply

    @RevBrettMurphy 1 month ago Inline reply two.
    Reply

@gtf1783
1 month ago
 @RevBrettMurphy
This is @gtf1783 replying to Brett, not Brett authoring a comment.
Reply

@gtf1783 | 1 month ago
@RevBrettMurphy
This is also a non-Brett comment with Brett as reply target.
Reply

@gtf1783 1 month ago @RevBrettMurphy inline target mention, not Brett authoring.
Reply

@editedparent
2 weeks ago (edited)
Edited time parent context.
Reply

@ParentTwo
1 month ago
Parent two text.
Hide replies

@RevBrettMurphy
1 month ago
Split reply three.
Reply
"""
    threads = extract_preserved_youtube_comment_threads(comments_text, author_handle="@RevBrettMurphy")

    _assert(len(threads) == 3, str(threads))
    brett_texts = [thread["brett"]["text"] for thread in threads]
    _assert(brett_texts == ["A truly prophetic word!", "Inline reply two.", "Split reply three."], str(brett_texts))
    _assert("only a mention" not in " ".join(brett_texts), str(brett_texts))
    _assert("replying to Brett" not in " ".join(brett_texts), str(brett_texts))
    _assert("inline target mention" not in " ".join(brett_texts), str(brett_texts))
    _assert(threads[0]["original_context"]["author_handle"] == "@andreadewsbury3958", str(threads[0]))
    _assert(threads[1]["original_context"]["author_handle"] == "@OtherUser", str(threads[1]))
    _assert(threads[2]["original_context"]["author_handle"] == "@ParentTwo", str(threads[2]))
    _assert(all(thread["counts_as_person"] is False for thread in threads), str(threads))
    _assert(all(thread["merged_into_canonical_transcript"] is False for thread in threads), str(threads))
    _assert(all(thread["affects_transcript_claim_span_counts"] is False for thread in threads), str(threads))

    rendered = format_youtube_comment_threads_for_review_display(threads[:1])
    _assert(rendered.startswith("------\nYouTube Comments\n\n@andreadewsbury3958 | 1 month ago"), rendered)
    _assert("\n    @RevBrettMurphy | 1 month ago\n    A truly prophetic word!" in rendered, rendered)
    _assert("Preserved YouTube comments linked to transcript/source persons" not in rendered, rendered)
    _assert("[Section: comments" not in rendered, rendered)
    _assert("\nReply\n" not in rendered, rendered)
    _assert("\n12\n" not in rendered, rendered)


def test_preserved_brett_comment_sections_have_semantic_claim_spans() -> None:
    source_text = """Title: Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=kQGOEJb76rU

Transcript
So we moved to the Diocese of Leicester.
00:01 - 00:03 [Brett Murphy]

257 Comments
-----
Top Comments

@parent1
1 month ago
First parent.

@RevBrettMurphy
1 month ago
A truly prophetic word!

@parent2
1 month ago
Second parent.

@RevBrettMurphy
1 month ago
The short answer is because of my Anglican theological convictions 😊

@parent3
1 month ago
Third parent.

@RevBrettMurphy
1 month ago
Simply because my theological convictions keep me Anglican
"""
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp) / "04 07 source.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="04 07 source",
            source_url="https://www.youtube.com/watch?v=kQGOEJb76rU",
            source_title="Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
    comments = preview.batch_payload["source_package_preview"]["claim_role_classification_preview"]["related_comment_review_sections"]
    span_by_text = {
        span["text"]: span
        for section in comments
        for span in section.get("claim_role_spans", [])
    }
    _assert(span_by_text["A truly prophetic word!"]["role"] == "UNKNOWN", str(span_by_text))
    _assert(span_by_text["The short answer is because of my Anglican theological convictions 😊"]["role"] == "PRIMARY", str(span_by_text))
    _assert(span_by_text["Simply because my theological convictions keep me Anglican"]["role"] == "PRIMARY", str(span_by_text))
    _assert(all(span["media_source_role"] == "SECONDARY_MEDIA_COPY" for span in span_by_text.values()), str(span_by_text))
    transcript_counts = preview.batch_payload["source_package_preview"]["claim_span_counts"]
    _assert(transcript_counts["PRIMARY"] == 1, str(transcript_counts))
    _assert(preview.batch_payload["source_package_preview"]["source_record_count_breakdown"]["youtube_comment_source_role_threads"] == 3, str(comments))
    _assert(preview.batch_payload["source_package_preview"]["source_record_count_breakdown"]["youtube_comment_source_role_records"] == 6, str(comments))


def test_metro_source_artifacts_build_importable_batch_payload() -> None:
    preview = build_profile_media_source_package_preview(
        database_root=r"T:\ProfileMediaHOME",
        case_title="Metro source evidence review",
        source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
        source_title="People shout seagull eater street far right lies",
        artifacts=[
            {
                "artifact_kind": "video",
                "display_name": "1024x576_MP4_6022863600552461299.mp4",
                "local_path": r"T:\Temp\session\1024x576_MP4_6022863600552461299.mp4",
                "width": 576,
                "height": 1024,
                "byte_size": 5300000,
                "reference_url": "https://videos.example.invalid/1024x576.mp4",
            },
            {
                "artifact_kind": "image",
                "display_name": "metro-image.webp",
                "local_path": r"T:\Temp\session\metro-image.webp",
                "width": 1200,
                "height": 675,
            },
            {
                "artifact_kind": "article_text",
                "display_name": "metro-article.txt",
                "local_path": r"T:\Temp\session\metro-article.txt",
            },
            {
                "artifact_kind": "screenshot",
                "display_name": "metro-page.png",
                "local_path": r"T:\Temp\session\metro-page.png",
            },
        ],
    )
    payload = preview.batch_payload
    _assert(preview.status == "preview_ready", preview.status)
    _assert(preview.artifact_count == 4, str(preview.artifact_count))
    _assert(preview.source_count == 5, str(preview.source_count))
    _assert(payload["schema_version"].startswith("profile-media-case-batch-"), payload["schema_version"])
    _assert(payload["case_title"] == "Metro source evidence review", payload["case_title"])
    _assert(len(payload["sources"]) == 5, str(payload["sources"]))
    _assert(payload["profiles"] == [], "V82A must not infer profiles")
    _assert(payload["source_package_preview"]["artifact_count"] == 4, str(payload["source_package_preview"]))
    _assert(payload["source_package_preview"]["source_role_policy_applied"] is True, str(payload["source_package_preview"]))
    _assert(payload["sources"][0]["source_role"] == "TERTIARY_PROPAGATED_SOURCE", str(payload["sources"][0]))
    url_bound_sources = [item for item in payload["sources"] if item.get("source_page")]
    unlinked_media_sources = [item for item in payload["sources"] if item.get("unlinked_media")]
    _assert(url_bound_sources, str(payload["sources"]))
    _assert(all(item["source_role"] == "TERTIARY_PROPAGATED_SOURCE" for item in url_bound_sources), str(payload["sources"]))
    _assert(unlinked_media_sources, str(payload["sources"]))
    _assert(all(item.get("source_role", "") == "" for item in unlinked_media_sources), str(payload["sources"]))
    _assert(all(item["source_role_review_required"] is True for item in unlinked_media_sources), str(payload["sources"]))
    _assert(not any(item.get("source_role_segment_candidate") for item in payload["sources"]), str(payload["sources"]))
    _assert(payload["source_package_preview"]["source_role_segment_count"] == 0, str(payload["source_package_preview"]))
    _assert(payload["source_package_preview"]["source_role_matching_preview"]["match_count"] == 0, str(payload["source_package_preview"]["source_role_matching_preview"]))
    _assert(all(item["final_source_role_decision"] is False for item in payload["sources"]), str(payload["sources"]))
    _assert(payload["source_package_preview"]["temporary_local_paths_preserved"] is True, str(payload["source_package_preview"]))
    _assert(payload["source_package_preview"]["media_download_performed"] is False, "preview builder must not download")
    _assert(payload["source_package_preview"]["file_copy_performed"] is False, "preview builder must not copy")
    text = render_profile_media_source_package_preview_text(preview)
    _assert("Profiles: 0" in text, text)
    _assert("1024x576_MP4_6022863600552461299.mp4" in text, text)


def test_preview_json_write_is_confirmation_gated_and_import_validator_accepts_it() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "metro_profile_media_import.json"
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Metro source evidence review",
            source_url="https://metro.co.uk/example",
            source_title="Metro example",
            artifacts=[{"artifact_kind": "image", "display_name": "image.webp", "local_path": str(Path(tmp) / "image.webp")}],
        )
        blocked = write_profile_media_source_package_preview_json(preview, output, confirmation_phrase="WRONG")
        _assert(blocked.status == "blocked_confirmation_required", blocked.status)
        _assert(blocked.file_write_performed is False, "wrong confirmation should not write JSON")
        _assert(not output.exists(), "wrong confirmation wrote a file")

        written = write_profile_media_source_package_preview_json(
            preview,
            output,
            confirmation_phrase=WRITE_PROFILE_MEDIA_SOURCE_PACKAGE_PREVIEW_CONFIRMATION,
        )
        _assert(written.status == "written", written.status)
        _assert(written.file_write_performed is True, "confirmed write should report file write")
        data = json.loads(output.read_text(encoding="utf-8"))
        _assert(len(data["sources"]) == 2, str(data))
        validation = validate_batch_json_file(output)
        _assert(validation.status in {"accepted", "accepted_with_warnings"}, validation.status)
        _assert(validation.source_count == 2, str(validation.source_count))


def test_kind_and_bucket_mapping_are_review_conservative() -> None:
    _assert(normalise_source_package_artifact_kind("video", path="clip.mp4") == "video", "video kind failed")
    _assert(normalise_source_package_artifact_kind("", path="article.txt") == "article_text", "txt should map to article text")
    _assert(source_bucket_for_package_artifact_kind("article_text") == "Articles", "article bucket")
    _assert(source_bucket_for_package_artifact_kind("video") == "Reference Extants", "video should remain reference extant")
    _assert(source_bucket_for_package_artifact_kind("screenshot") == "Reference Extants", "screenshot should remain reference extant")
    _assert(source_role_for_package_artifact_kind("article_text") == "TERTIARY_PROPAGATED_SOURCE", "article text role")
    _assert(source_role_for_package_artifact_kind("video") == "TERTIARY_PROPAGATED_SOURCE", "embedded media role")
    _assert(claim_basis_for_package_artifact_kind("screenshot") == "AGENCY_OR_OUTSIDE_RETELLING", "claim basis")



def test_source_package_preview_adds_mixed_role_segment_candidates_from_article_text() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        article_path = Path(tmp) / "article_text.txt"
        article_path.write_text(
            "A Muslim woman has spoken out after a clip of her rescuing a baby seagull went viral.\n\n"
            "Nora Mubarak was secretly filmed as she tried to save an infant seagull.\n\n"
            "She told Metro: ‘When I go out, people stare, and sometimes they say things.’\n\n"
            "But Oliver Freeston, the Reform UK leader of North East Lincolnshire Council, "
            "shared the video on Facebook with the caption: ‘Grimsby in 2026’.\n\n"
            "Far-right leader Tommy Robinson also shared the video, adding his own agenda. "
            "He wrote: ‘Invaders catching and killing gulls in broad daylight in Modern England. "
            "Get these backwards people out!’\n",
            encoding="utf-8",
        )
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Metro source evidence review",
            source_url="https://metro.co.uk/example",
            source_title="Metro example",
            artifacts=[
                {"artifact_kind": "article_text", "display_name": "article_text.txt", "local_path": str(article_path)},
                {"artifact_kind": "video", "display_name": "clip.mp4", "local_path": str(Path(tmp) / "clip.mp4")},
            ],
        )
        segments = preview.batch_payload["source_package_preview"]["source_role_segments"]
        roles = {item["candidate_source_role"] for item in segments}
        _assert("SECONDARY_WITNESS_ACCOUNT" in roles, str(segments))
        _assert("UNKNOWN_SOURCE_ROLE" in roles, str(segments))
        _assert(any(item.get("potential_source_role_after_chain_verification") == "PRIMARY_SELF_AUTHORED_SCOPE" for item in segments), str(segments))
        _assert(any("source-chain" in item["review_reason"] or item["source_chain_gap"] for item in segments), str(segments))
        oliver = next(item for item in segments if item["segment_id"].startswith("oliver"))
        tommy = next(item for item in segments if item["segment_id"].startswith("tommy"))
        _assert(oliver["excerpt"].endswith("‘Grimsby in 2026’."), oliver["excerpt"])
        _assert("Tommy Robinson" not in oliver["excerpt"], oliver["excerpt"])
        _assert(tommy["excerpt"].endswith("Get these backwards people out!’"), tommy["excerpt"])
        source_roles = {item["source_role"] for item in preview.batch_payload["sources"]}
        _assert("UNKNOWN_SOURCE_ROLE" in source_roles, str(preview.batch_payload["sources"]))
        _assert("SECONDARY_WITNESS_ACCOUNT" in source_roles, str(preview.batch_payload["sources"]))
        _assert(preview.batch_payload["profiles"], "person candidates should produce review profiles")
        _assert(any("Religion: Muslim" in item["profile_text"] for item in preview.batch_payload["profiles"]), str(preview.batch_payload["profiles"]))


def test_internal_media_artifact_is_primary_media_source() -> None:
    preview = build_profile_media_source_package_preview(
        database_root="C:/HOME",
        case_title="Internal media case",
        source_url="",
        source_title="Offline capture",
        include_source_page_record=False,
        artifacts=[
            {
                "artifact_kind": "video",
                "display_name": "offline-video.mp4",
                "local_path": "C:/captures/offline-video.mp4",
                "internal_media": True,
            }
        ],
    )
    source = preview.batch_payload["sources"][0]
    _assert(source["source_bucket"] == "Internal Media", str(source))
    _assert(source["source_role"] == "PRIMARY_SELF_AUTHORED_SCOPE", str(source))
    _assert(source["claim_basis"] == "SELF_AUTHORED_EXPERIENCE", str(source))
    _assert(source["source_chain_gap"] is False, str(source))
    _assert(source["source_role_review_required"] is False, str(source))
    _assert(source["media_personhood_role"] == "", str(source))
    _assert(source["media_personhood_review_required"] is True, str(source))


def test_payload_includes_text_without_mutation_flags() -> None:
    preview = build_profile_media_source_package_preview(
        case_title="Untitled source evidence",
        source_url="https://example.test/article",
        artifacts=[],
    )
    payload = source_package_preview_payload(preview, include_text=True)
    _assert("preview_text" in payload, str(payload.keys()))
    _assert(payload["folder_scan_performed"] is False, "no scan")
    _assert(payload["media_download_performed"] is False, "no download")
    _assert(payload["automatic_classification_performed"] is False, "no classification")
    _assert(payload["sensitive_identifier_inference_performed"] is False, "no sensitive inference")
    _assert(payload["batch_payload"]["profiles"] == [], "no inferred profiles")


def test_section_aware_source_txt_person_contexts_for_metro_sources() -> None:
    source_text = """Title: 4 08 source
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=example

Transcript:
22:21 - 22:28 [Brett Murphy] My best mate, Father Calvin Robinson, was then a member of the FCE.
22:29 - 22:40 [Brett Murphy] Pastor Doug Wilson says this in his sermon.

Comments:
Doug Wilson was also mentioned by a commenter.

Research:
Sarah Mullally is named in later research notes only.
"""
    sections = sections_by_type(split_source_text_sections(source_text))
    _assert("Calvin Robinson" in sections["transcript"], str(sections))
    _assert("Sarah Mullally" not in sections["transcript"], str(sections))
    _assert("Sarah Mullally" in sections["research"], str(sections))

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "4 08 source.txt"
        path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Metro source evidence review",
            source_url="https://metro.co.uk/example",
            source_title="Metro example",
            artifacts=[{"artifact_kind": "article_text", "display_name": path.name, "local_path": str(path)}],
        )
    people = preview.batch_payload["source_package_preview"]["person_review_candidates"]
    names = {item["canonical_name"]: item for item in people}
    _assert("Sarah Mullally" not in names, str(people))
    _assert("Calvin Robinson" in names, str(people))
    _assert("FCE / Free Church of England" in names["Calvin Robinson"].get("associations", []), str(names["Calvin Robinson"]))
    _assert("Doug Wilson" in names, str(people))


def test_metro_article_and_0407_0408_source_txt_acceptance() -> None:
    article_text = (
        "Brett Murphy told Metro that his Christian faith shaped his response. "
        "In a video from July on Project Britannia YouTube Channel, Father Calvin Robinson was described as part of the Free Church of England. "
        "The article also quotes Pastor Doug Wilson in a comment context."
    )
    source_0407 = """Title: 04 07 source
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=0407

Transcript:
00:01 - 00:06 [Brett Murphy] I told Metro that my Christian faith shaped my response.
00:07 - 00:12 [Brett Murphy] Project Britannia YouTube Channel carried the interview.
"""
    source_0408 = """Title: 4 08 source
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=0408

Transcript:
22:21 - 22:28 [Brett Murphy] My best mate, Father Calvin Robinson, was then a member of the FCE.
22:29 - 22:40 [Brett Murphy] Pastor Doug Wilson says this in his sermon.

Comments:
Doug Wilson was also mentioned by a commenter.

Research:
Sarah Mullally is named in later research notes only.
"""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        article_path = root / "metro_article.txt"
        s0407 = root / "04 07 source.txt"
        s0408 = root / "4 08 source.txt"
        article_path.write_text(article_text, encoding="utf-8")
        s0407.write_text(source_0407, encoding="utf-8")
        s0408.write_text(source_0408, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Metro URL + 04 07 + 4 08 acceptance",
            source_url="https://metro.co.uk/example-article",
            source_title="Metro source evidence review",
            artifacts=[
                {"kind": "article_text", "local_path": str(article_path), "text_preview": article_text},
                {"kind": "source_txt", "local_path": str(s0407), "text_preview": source_0407},
                {"kind": "source_txt", "local_path": str(s0408), "text_preview": source_0408},
            ],
        )
    people = preview.batch_payload["source_package_preview"]["person_review_candidates"]
    names = {item["canonical_name"]: item for item in people}
    _assert("Sarah Mullally" not in names, str(people))
    _assert("Calvin Robinson" in names, str(people))
    _assert("FCE / Free Church of England" in names["Calvin Robinson"].get("associations", []), str(names["Calvin Robinson"]))
    _assert("Doug Wilson" in names, str(people))
    matching = preview.batch_payload["source_package_preview"]["source_role_matching_preview"]
    _assert(matching["match_count"] >= 1, str(matching))
    _assert(matching["final_source_role_decision"] is False, str(matching))



def test_source_transcript_scope_excludes_comment_only_persons() -> None:
    source_text = """Title: 04 07 source
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=0407
----
Transcript
Thomas Gregory Moffitt - "Young Bob"

So we moved to the Diocese of Leicester.
5:44 - 6:01 [Brett Murphy]
My best mate, Father Calvin Robinson, was then a member of the FCE.
22:21 - 22:28 [Brett Murphy]
----
Hello, duplicate/raw transcript material.

Comments
Top Comments
@RevBrettMurphy
A fair criticism, but I am more inclined towards Doug Wilson than Joel Webbon.

@viewer
The issue here is that Joel Webbon is the fruit of the Doug Wilson tree.
"""
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp) / "04 07 source.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="04 07 source",
            source_url="https://www.youtube.com/watch?v=0407",
            source_title="04 07 source",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
    people = {item["canonical_name"]: item for item in preview.batch_payload["source_package_preview"]["person_review_candidates"]}
    _assert("Brett Murphy" in people, str(people))
    _assert("Thomas Gregory Moffitt (Young Bob)" in people, str(people))
    _assert("Calvin Robinson" in people, str(people))
    _assert("Doug Wilson" not in people, str(people))


def test_transcript_people_can_carry_related_comment_user_context_without_comment_only_people() -> None:
    source_text = """Title: Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=kQGOEJb76rU
----
Transcript
Thomas Gregory Moffitt - "Young Bob"

Hello, I am Young Bob.
00:01 - 00:02 [Young Bob]
My best mate, Father Calvin Robinson, was then a member of the FCE.
22:21 - 22:28 [Brett Murphy]
----
Hello, duplicate/raw transcript material.

257 Comments
-----
Top Comments

@viewer_parent
1 month ago
A parent comment preserved as context.

@RevBrettMurphy
1 month ago
A fair criticism but I would contend that Christ and His Holy Apostles were frequently abrasive.

Reply

@viewer1
The issue here is that Joel Webbon is the fruit of the Doug Wilson tree.
"""
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp) / "04 07 source.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="04 07 source",
            source_url="https://www.youtube.com/watch?v=kQGOEJb76rU",
            source_title="Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
    people = {item["canonical_name"]: item for item in preview.batch_payload["source_package_preview"]["person_review_candidates"]}
    _assert("Brett Murphy" in people, str(people))
    _assert("Thomas Gregory Moffitt (Young Bob)" in people, str(people))
    _assert("Calvin Robinson" in people, str(people))
    _assert("Doug Wilson" not in people, str(people))
    brett_notes = str(people["Brett Murphy"].get("notes") or "")
    _assert("Related preserved comments for transcript person" in brett_notes, brett_notes)
    _assert("Section: transcript, comments" in brett_notes, brett_notes)
    _assert(people["Brett Murphy"].get("source_context_section_label") == "Section: transcript, comments", str(people["Brett Murphy"]))
    _assert(people["Brett Murphy"].get("source_context_sections") == ["transcript", "comments"], str(people["Brett Murphy"]))
    _assert("@RevBrettMurphy" in brett_notes, brett_notes)
    _assert(people["Thomas Gregory Moffitt (Young Bob)"].get("source_context_sections") == ["transcript"], str(people["Thomas Gregory Moffitt (Young Bob)"]))
    _assert(people["Thomas Gregory Moffitt (Young Bob)"].get("source_context_section_label") == "Section: transcript", str(people["Thomas Gregory Moffitt (Young Bob)"]))
    _assert(people["Calvin Robinson"].get("source_context_sections") == ["transcript"], str(people["Calvin Robinson"]))
    _assert(people["Calvin Robinson"].get("source_context_section_label") == "Section: transcript", str(people["Calvin Robinson"]))
    claim_preview = preview.batch_payload["source_package_preview"]["claim_role_classification_preview"]
    comments = claim_preview["related_comment_review_sections"]
    _assert(len(comments) == 1, str(comments))
    _assert(comments[0]["section_label"] == "comments", str(comments))
    _assert(comments[0]["author_handle"] == "@RevBrettMurphy", str(comments))
    _assert("A fair criticism but I would contend" in comments[0]["text"], str(comments))
    _assert(comments[0]["merged_into_canonical_transcript"] is False, str(comments))
    _assert(comments[0]["affects_transcript_claim_span_counts"] is False, str(comments))
    comment_spans = comments[0].get("claim_role_spans")
    _assert(isinstance(comment_spans, list) and comment_spans, str(comments[0]))
    _assert(comments[0]["comment_semantic_roles_use_claim_role_classifier"] is True, str(comments[0]))
    _assert(comments[0]["semantic_role_is_separate_from_source_role"] is True, str(comments[0]))
    _assert(all(span.get("section") == "comments" for span in comment_spans), str(comment_spans))
    _assert(all(span.get("affects_transcript_claim_span_counts") is False for span in comment_spans), str(comment_spans))
    _assert(not all(span.get("role") == "SECONDARY" for span in comment_spans), str(comment_spans))
    comment_source_roles = preview.batch_payload["source_package_preview"]["youtube_comment_source_role_records"]
    _assert(len(comment_source_roles) == 2, str(comment_source_roles))
    parent_role = next(item for item in comment_source_roles if item["source_kind"] == "youtube_comment_context")
    _assert(parent_role["source_role_status"] == "RESOLVED_SECONDARY_SOURCE", str(parent_role))
    _assert(parent_role["source_role_label"] == "Secondary — preserved YouTube comment context", str(parent_role))
    _assert(parent_role["linked_persons"] == [], str(parent_role))
    _assert(parent_role["does_not_create_person"] is True, str(parent_role))
    reply_role = next(item for item in comment_source_roles if item["source_kind"] == "youtube_comment_reply")
    _assert(reply_role["source_role_status"] == "RESOLVED_SECONDARY_SOURCE", str(reply_role))
    _assert(reply_role["source_role_label"] == "Secondary — preserved YouTube comment by transcript/source person", str(reply_role))
    _assert(reply_role["canonical_person"] == "Brett Murphy", str(reply_role))
    _assert(reply_role["linked_persons"] == ["Brett Murphy"], str(reply_role))
    _assert(reply_role["does_not_create_new_person"] is True, str(reply_role))
    breakdown = preview.batch_payload["source_package_preview"]["source_record_count_breakdown"]
    _assert(breakdown["primary_media_sources"] == 1, str(breakdown))
    _assert(breakdown["secondary_transcript_records"] == 1, str(breakdown))
    _assert(breakdown["resolved_tertiary_references"] == 0, str(breakdown))
    _assert(breakdown["unresolved_source_reference_candidates"] == 0, str(breakdown))
    _assert(breakdown["youtube_comment_source_role_threads"] == 1, str(breakdown))
    _assert(breakdown["youtube_comment_source_role_records"] == 2, str(breakdown))
    summary_text = render_profile_media_source_package_preview_text(preview)
    _assert("YouTube comment source roles" in summary_text, summary_text)
    _assert("Secondary — preserved YouTube comment by transcript/source person" in summary_text, summary_text)
    canonical_text = claim_preview["transcript_streams"][0]["canonical_transcript_text"]
    _assert("@RevBrettMurphy" not in canonical_text, canonical_text)
    _assert("A fair criticism but I would contend" not in canonical_text, canonical_text)
    state = build_import_review_decision_state(preview.batch_payload)
    brett_row = next(row for row in state.person_rows if row.canonical_name == "Brett Murphy")
    _assert(brett_row.source_context_section_label == "Section: transcript, comments", str(brett_row))
    young_row = next(row for row in state.person_rows if row.canonical_name == "Thomas Gregory Moffitt (Young Bob)")
    calvin_row = next(row for row in state.person_rows if row.canonical_name == "Calvin Robinson")
    _assert(young_row.source_context_section_label == "Section: transcript", str(young_row))
    _assert(calvin_row.source_context_section_label == "Section: transcript", str(calvin_row))

def test_source_package_preview_emits_claim_role_spans_for_full_transcript() -> None:
    source_text = """Title: 04 07 source
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=0407

Transcript:
So we moved to the Diocese of Leicester, which is super woke.
5:44 - 6:01 [Brett Murphy]
We need to end the sodomite parades.
15:08 - 16:33 [Brett Murphy]
----
Transcript:
So we moved to the Diocese of Leicester, which is super woke.
5:44 - 6:01 [Brett Murphy]
We need to end the sodomite parades.
15:08 - 16:33 [Brett Murphy]
"""
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp) / "04 07 source.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Claim role transcript preview",
            source_url="https://metro.co.uk/example-article",
            source_title="Metro source evidence review",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
    claim_preview = preview.batch_payload["source_package_preview"]["claim_role_classification_preview"]
    _assert(claim_preview["classifier_module"] == "profile_media_claim_role_classifier", str(claim_preview))
    _assert(claim_preview["media_source_role_separate_from_claim_span_role"] is True, str(claim_preview))
    _assert(claim_preview["canonical_transcript_stream_used"] is True, str(claim_preview))
    _assert(claim_preview["transcript_streams"][0]["duplicate_transcript_representations_detected"] is True, str(claim_preview))
    spans = claim_preview["spans"]
    texts = [span["text"] for span in spans]
    roles = [(span["role"], span["designation"]) for span in spans]
    normalized_first_two = [texts[0].strip(), texts[1].strip().lstrip(", ").strip()]
    _assert(
        normalized_first_two == ["So we moved to the Diocese of Leicester", "which is super woke."],
        str(texts),
    )
    _assert(all("----" not in text for text in texts), str(texts))
    _assert(("PRIMARY", "self-action") in roles, str(roles))
    _assert(("UNKNOWN", "institution-claim") in roles, str(roles))
    _assert(("PRIMARY", "speaker-owned-imperative") in roles, str(roles))
    _assert(("UNKNOWN", "slur-label") in roles, str(roles))
    _assert(all(span["review_state"] == "assigned" for span in spans), str(spans))
    _assert(all(span["media_source_role"] == "PRIMARY_SOURCE_EVIDENCE" for span in spans), str(spans))
    tag_plan = claim_preview["tag_plan"]
    _assert(tag_plan["full_transcript_order_preserved"] is True, str(tag_plan))
    _assert(tag_plan["clause_level_tags"] is True, str(tag_plan))
    _assert(len(tag_plan["tag_ranges"]) == len(spans), str(tag_plan))


def test_source_package_preview_separates_provenance_references_and_claim_counts() -> None:
    source_text = """Title: Source reference test
Channel: Project Britannia
Source: https://www.youtube.com/watch?v=source-ref
Transcript provenance: YouTube transcript

Transcript:
X measured Y.
1:00 - 1:02 [Brett Murphy]
which is super woke.
1:03 - 1:04 [Brett Murphy]
Right?
1:05 - 1:06 [Brett Murphy]
"""
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp) / "source-reference.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Source reference preview",
            source_url="https://metro.co.uk/example",
            source_title="Metro source evidence review",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
    preview_section = preview.batch_payload["source_package_preview"]
    transcript_provenance = preview_section["transcript_provenance_preview"]
    _assert(transcript_provenance["records"][0]["media_source_display"] == "Media source: Primary [Original video/audio URL]", str(transcript_provenance))
    _assert(transcript_provenance["records"][0]["transcript_provenance_display"] == "Transcript: Secondary [YouTube transcript]", str(transcript_provenance))
    source_rows = preview.batch_payload["sources"]
    source_text_rows = [row for row in source_rows if "source_text_evidence=True" in row.get("confidence_or_verification_notes", "")]
    _assert(len(source_text_rows) == 1, str(source_rows))
    _assert("X measured Y" not in source_text_rows[0].get("confidence_or_verification_notes", ""), str(source_text_rows[0]))
    refs = preview_section["source_reference_candidate_preview"]
    _assert(refs["main_sourcing_card_candidate_count"] == 1, str(refs))
    _assert(refs["main_sourcing_card_candidates"][0]["source_pointer_type"] in {"measurement_or_dataset", "statistical_claim_no_attached_source"}, str(refs))
    _assert("which is super woke" not in " ".join(item["text"] for item in refs["main_sourcing_card_candidates"]), str(refs))
    counts = preview_section["claim_span_counts"]
    _assert(counts["UNKNOWN"] >= 2, str(counts))
    _assert("BLANK" not in counts, str(counts))
    source_ref_segments = [item for item in preview_section["source_role_segments"] if item.get("source_reference_candidate")]
    _assert(len(source_ref_segments) == 1, str(preview_section["source_role_segments"]))
    _assert(source_ref_segments[0]["goes_to_main_sourcing_card"] is True, str(source_ref_segments))
    breakdown = preview_section["source_record_count_breakdown"]
    _assert(breakdown["primary_media_sources"] == 1, str(breakdown))
    _assert(breakdown["transcript_provenance_records"] == 1, str(breakdown))
    _assert(breakdown.get("review_source_reference_candidates", breakdown.get("unresolved_source_reference_candidates")) in {0, 1}, str(breakdown))
    _assert(breakdown.get("unknown_media_source_statements", 0) >= 1, str(breakdown))
    _assert(breakdown["generated_excerpts_suppressed"] == 1, str(breakdown))


def test_source_package_preview_unknown_transcript_and_metadata_only_source_card() -> None:
    source_text = """Title: Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy
Channel: Project Britannia
Subscribers: 18.9K
Views: 11,082
Date: July 4, 2026
Description: Former Church of England priest Father Brett Murphy speaks out against what he sees as wokery and heresy within the Church. A wide-ranging interview on Anglicanism, faith, theology, and the future of Christianity in Britain.

Support our mission - projectbritannia.org/donate
Source: https://www.youtube.com/watch?v=kQGOEJb76rU

Transcript
Thomas Gregory Moffitt - "Young Bob"
People talk about demographic replacement.
1:00 - 1:03 [Brett Murphy]
We need to end the sodomite parades.
1:04 - 1:06 [Brett Murphy]
----
Transcript
51:50 - 51:52 [Brent Murphy]
Hello, this is another episode that must not be canonical.
"""
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp) / "04 07 source.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="04 07 source",
            source_url="https://www.youtube.com/watch?v=kQGOEJb76rU",
            source_title="Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
    preview_section = preview.batch_payload["source_package_preview"]
    provenance = preview_section["transcript_provenance_preview"]["records"][0]
    _assert(provenance["transcript_provenance_display"] == "Transcript: Secondary [Transcript text file; provenance not recorded]", str(provenance))
    source_text_rows = [row for row in preview.batch_payload["sources"] if "source_text_evidence=True" in row.get("confidence_or_verification_notes", "")]
    _assert(len(source_text_rows) == 1, str(source_text_rows))
    notes = source_text_rows[0]["confidence_or_verification_notes"]
    _assert("Project Britannia / Muslims quote passage" not in notes, notes)
    _assert("Pride/adoption passage" not in notes, notes)
    _assert("Title: Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy" in notes, notes)
    _assert("Channel: Project Britannia" in notes, notes)
    _assert("Support: projectbritannia.org/donate" in notes, notes)
    _assert("Source: https://www.youtube.com/watch?v=kQGOEJb76rU" in notes, notes)
    source_link_candidates = preview_section["source_link_role_candidates"]
    _assert(any(item["display_label"] == "Source" and item["source_role_status"] == "RESOLVED_PRIMARY_SOURCE" and item["section"] == "metadata" for item in source_link_candidates), str(source_link_candidates))
    _assert(any(item["display_label"] == "Support" and item["source_role_status"] == "NOT_A_SOURCE_REFERENCE" and item["section"] == "metadata" for item in source_link_candidates), str(source_link_candidates))
    state = build_import_review_decision_state(preview.batch_payload)
    source_text_state_rows = [row for row in state.source_record_rows if row.artifact_kind == "source_text_evidence"]
    _assert(len(source_text_state_rows) == 1, str(state.source_record_rows))
    _assert("\nChannel: Project Britannia\n" in source_text_state_rows[0].excerpt, source_text_state_rows[0].excerpt)
    _assert("\nSupport: projectbritannia.org/donate\n" in source_text_state_rows[0].excerpt, source_text_state_rows[0].excerpt)
    spans = preview_section["claim_role_classification_preview"]["spans"]
    joined = " ".join(span["text"] for span in spans)
    _assert("Thomas Gregory Moffitt" not in joined, joined)
    _assert("----" not in joined, joined)
    _assert("Hello, this is another episode" not in joined, joined)
    breakdown = preview_section["source_record_count_breakdown"]
    _assert(breakdown["primary_media_sources"] == 1, str(breakdown))
    _assert(breakdown["transcript_provenance_records"] == 1, str(breakdown))
    _assert(breakdown["secondary_transcript_records"] == 1, str(breakdown))
    _assert(breakdown["unknown_transcript_provenance_records"] == 0, str(breakdown))
    _assert(breakdown["generated_excerpts_suppressed"] == 1, str(breakdown))


def test_source_package_preview_adds_link_source_preview_without_inflating_source_counts() -> None:
    source_text = """Title: Synthetic link layer source
Channel: Neutral Channel
Source: https://www.youtube.com/watch?v=linklayer
Transcript provenance: YouTube transcript

Transcript
This is a neutral transcript line.
00:01 - 00:03 [Speaker]

### [15] Ian Paul — Premier Christianity critical article
[Premier article](https://www.premierchristianity.com/opinion/example)

Live:
https://www.archbishopofcanterbury.org/node/32/example
Wayback capture list:
https://web.archive.org/web/*/https://www.archbishopofcanterbury.org/node/32/example
"""
    tmp_ctx = tempfile.TemporaryDirectory()
    try:
        tmp = tmp_ctx.name
        source_path = Path(tmp) / "links.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Link layer preview",
            source_url="https://www.youtube.com/watch?v=linklayer",
            source_title="Synthetic link layer source",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
        preview_section = preview.batch_payload["source_package_preview"]
        link_preview = preview_section["link_source_preview"]
        _assert(link_preview["link_count"] >= 4, str(link_preview))
        _assert(link_preview["role_counts"]["LOCATOR"] >= 1, str(link_preview))
        _assert("LOCATOR" not in link_preview["visible_role_counts"], str(link_preview))
        _assert(any(item["source_object_type"] == "archive_locator" for item in link_preview["objects"]), str(link_preview))
        _assert(any(item["source_object_type"] == "official_page" and item["claim_specific_role"] == "PRIMARY" for item in link_preview["objects"]), str(link_preview))
        _assert(preview_section["link_source_objects_separate_from_claim_spans"] is True, str(preview_section))
        _assert(all("claim_role_spans" not in item for item in link_preview["objects"]), str(link_preview))
        breakdown = preview_section["source_record_count_breakdown"]
        _assert(breakdown["primary_media_sources"] == 1, str(breakdown))
        _assert(breakdown["transcript_provenance_records"] == 1, str(breakdown))
        _assert(link_preview["link_objects_do_not_inflate_media_source_counts"] is True, str(link_preview))
        summary_text = render_profile_media_source_package_preview_text(preview)
        _assert("LINK SOURCE OBJECTS:" in summary_text, summary_text)
        _assert("Separate from claim spans: True" in summary_text, summary_text)

        official = next(item for item in link_preview["objects"] if item.get("source_object_type") == "official_page")
        decisions_path = Path(preview_section["link_source_decisions_path"])
        append_link_source_decision(
            decisions_path,
            {
                "link_object_key": link_source_object_key(official),
                "url": official["url"],
                "normalised_url": official["normalised_url"],
                "selected_role": "UNKNOWN",
                "decision_status": "changed_role",
                "decision_note": "synthetic override",
                "previous_role": official["claim_specific_role"],
                "previous_reason": official["role_reason"],
            },
        )
        preview_with_decision = build_profile_media_source_package_preview(
            database_root=str(decisions_path.parent),
            case_title="Link layer preview",
            source_url="https://www.youtube.com/watch?v=linklayer",
            source_title="Synthetic link layer source",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
        decided_section = preview_with_decision.batch_payload["source_package_preview"]
        decided_link_preview = decided_section["link_source_preview"]
        _assert(decided_link_preview["link_source_decisions_count"] == 1, str(decided_link_preview))
        decided_official = next(item for item in decided_link_preview["objects"] if item.get("url") == official["url"])
        _assert(decided_official["claim_specific_role"] == "UNKNOWN", str(decided_official))
        _assert(decided_official["original_claim_specific_role"] == "PRIMARY", str(decided_official))
        _assert(decided_official["classifier_default_link_role"] == "PRIMARY", str(decided_official))
        _assert(decided_official["visible_link_role"] == "UNKNOWN", str(decided_official))
        _assert(decided_section["source_record_count_breakdown"] == breakdown, str(decided_section["source_record_count_breakdown"]))
    finally:
        tmp_ctx.cleanup()


def test_metro_article_text_and_links_feed_repair1_review_payload() -> None:
    article_text = """Title: People shout seagull eater in street after far-right lies
Source URL: https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/
Barney Davis
Senior news reporter
Nora Mubarak told Metro she had rescued the bird.
Oliver Freeston shared the video on Facebook with the caption: 'Grimsby in 2026'.
Tommy Robinson also shared the video. He wrote: 'Get these backwards people out!'
Wayback archived copy:
https://web.archive.org/web/20260717224516/https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/
https://archive.ph/6mr3C
"""
    with tempfile.TemporaryDirectory() as tmp:
        article_path = Path(tmp) / "metro_article.txt"
        article_path.write_text(article_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Metro repair1",
            source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
            source_title="People shout seagull eater",
            artifacts=[{"kind": "article_text", "display_name": article_path.name, "local_path": str(article_path)}],
        )
    preview_section = preview.batch_payload["source_package_preview"]
    link_preview = preview_section["link_source_preview"]
    metro = next(
        item for item in link_preview["objects"]
        if "metro.co.uk/2026/07/17/people-shout-seagull-eater" in str(item.get("normalised_url") or item.get("url") or "")
        and item.get("claim_specific_role") != "LOCATOR"
    )
    _assert(metro["source_object_type"] == "news_article", str(metro))
    _assert(metro["claim_specific_role"] == "SECONDARY", str(metro))
    archive_rows = [item for item in link_preview["objects"] if item.get("claim_specific_role") == "LOCATOR"]
    _assert(archive_rows, str(link_preview))
    _assert(all(item.get("visible_link_role") == "SECONDARY" for item in archive_rows), str(archive_rows))
    _assert(all(item.get("visible_link_source_row_label") == "Archive URL" for item in archive_rows), str(archive_rows))
    _assert(link_preview["visible_role_counts"]["SECONDARY"] >= 3, str(link_preview))
    _assert("LOCATOR" not in link_preview["visible_role_counts"], str(link_preview))
    _assert(link_preview["link_objects_do_not_inflate_media_source_counts"] is True, str(link_preview))
    claim_preview = preview_section["claim_role_classification_preview"]
    _assert(claim_preview["article_text_source_roles_enabled"] is True, str(claim_preview))
    _assert(claim_preview["article_text_stream_count"] == 1, str(claim_preview))
    _assert(any(span.get("section_label") == "article_text" for span in claim_preview["spans"]), str(claim_preview))
    people = {person["canonical_name"] for person in preview_section["person_review_candidates"]}
    _assert({"Nora Mubarak", "Oliver Freeston", "Tommy Robinson", "Barney Davis"} <= people, str(people))
    breakdown = preview_section["source_record_count_breakdown"]
    _assert(breakdown["primary_media_sources"] == 0, str(breakdown))
    _assert(breakdown["transcript_provenance_records"] == 0, str(breakdown))


def test_mixed_top_link_preamble_and_article_body_both_feed_review_layers() -> None:
    article_text = """https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/
https://web.archive.org/web/20260717224516/https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/
https://archive.ph/6mr3C

People shout seagull eater in street after far-right lies
Barney Davis
Senior news reporter
Nora Mubarak told Metro she had rescued the bird.
The secretly filmed clip went viral after Oliver Freeston shared the video on Facebook with the caption: 'Grimsby in 2026'.
Picture: @ActivePatriotUK
Picture: Supplied
Picture: Supplied
Tommy Robinson also shared the video. He wrote: 'Get these backwards people out!'
"""
    with tempfile.TemporaryDirectory() as tmp:
        article_path = Path(tmp) / "mixed_links_article.txt"
        article_path.write_text(article_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="Mixed link article",
            source_url="https://metro.co.uk/2026/07/17/people-shout-seagull-eater-street-far-right-lies-29157396/",
            source_title="People shout seagull eater",
            artifacts=[{"kind": "article_text", "display_name": article_path.name, "local_path": str(article_path)}],
        )
    preview_section = preview.batch_payload["source_package_preview"]
    link_preview = preview_section["link_source_preview"]
    _assert(link_preview["visible_role_counts"]["SECONDARY"] >= 3, str(link_preview))
    _assert("LOCATOR" not in link_preview["visible_role_counts"], str(link_preview))
    claim_preview = preview_section["claim_role_classification_preview"]
    joined_spans = " ".join(str(span.get("text") or "") for span in claim_preview["spans"])
    _assert("People shout seagull eater" in joined_spans, joined_spans)
    _assert("https://metro.co.uk" not in joined_spans, joined_spans)
    _assert(claim_preview["article_text_stream_count"] == 1, str(claim_preview))
    people = {person["canonical_name"] for person in preview_section["person_review_candidates"]}
    _assert({"Barney Davis", "Nora Mubarak", "Oliver Freeston", "Tommy Robinson"} <= people, str(people))
    article_media = preview_section["article_media_details"]
    _assert(any(item["label"] == "Media" and item["role"] == "Unknown" for item in article_media), str(article_media))
    _assert(any(item["label"] == "Image 1" and item["role"] == "Unknown" for item in article_media), str(article_media))
    _assert(sum(1 for item in article_media if item["role"] == "Secondary" and "Supplied" in item["reason"]) == 2, str(article_media))
    _assert(all(item.get("article_media_details_derived_from_text") is True for item in link_preview["objects"]), str(link_preview))
    segments = preview_section["source_role_segments"]
    oliver = next(item for item in segments if item.get("segment_id") == "oliver_freeston_reported_post_primary_gap_candidate")
    tommy = next(item for item in segments if item.get("segment_id") == "tommy_robinson_reported_post_primary_gap_candidate")
    _assert(oliver["candidate_source_role"] == "UNKNOWN_SOURCE_ROLE", str(oliver))
    _assert(tommy["candidate_source_role"] == "UNKNOWN_SOURCE_ROLE", str(tommy))




def test_0407_metadata_separator_does_not_replace_canonical_transcript() -> None:
    source_text = """Title: Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy
Channel: Project Britannia
Subscribers: 18.9K
Views: 11,082
Date: July 4, 2026
Description: Former Church of England priest Father Brett Murphy speaks out against what he sees as wokery and heresy within the Church.
Source: https://www.youtube.com/watch?v=kQGOEJb76rU
----
Transcript
Thomas Gregory Moffitt - "Young Bob"

So we moved to the Diocese of Leicester, which is super woke.
5:44 - 6:01 [Brett Murphy]
My best mate, Father Calvin Robinson, was then a member of the FCE.
22:21 - 22:28 [Brett Murphy]
51:50 - 51:52 [Brent Murphy]
----
Hello, this is duplicate/raw transcript material that must not be canonical.

Comments
@viewer
Pastor Doug Wilson is mentioned here.
"""
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp) / "04 07 source.txt"
        source_path.write_text(source_text, encoding="utf-8")
        preview = build_profile_media_source_package_preview(
            database_root=tmp,
            case_title="04 07 source",
            source_url="https://www.youtube.com/watch?v=kQGOEJb76rU",
            source_title="Former Church of England Priest Speaks Out Against Wokery and Heresy ft Father Brett Murphy",
            artifacts=[{"kind": "source_txt", "display_name": source_path.name, "local_path": str(source_path)}],
        )
    preview_section = preview.batch_payload["source_package_preview"]
    claim_preview = preview_section["claim_role_classification_preview"]
    spans = claim_preview["spans"]
    joined = " ".join(span["text"] for span in spans)
    _assert(spans, str(claim_preview))
    _assert(spans[0]["text"].startswith("So we moved to the Diocese of Leicester"), str(spans[:3]))
    _assert("Title: Former Church" not in joined, joined)
    _assert("Thomas Gregory Moffitt" not in joined, joined)
    _assert("----" not in joined, joined)
    _assert("duplicate/raw transcript material" not in joined, joined)
    stream = claim_preview["transcript_streams"][0]
    _assert(stream["duplicate_raw_transcript_section_label"] == "duplicate_raw_transcript", str(stream))
    _assert("duplicate/raw transcript material" in stream["duplicate_raw_transcript_text"], str(stream))
    people = {item["canonical_name"]: item for item in preview_section["person_review_candidates"]}
    _assert("Thomas Gregory Moffitt (Young Bob)" in people, str(people))
    _assert("Calvin Robinson" in people, str(people))
    _assert("Doug Wilson" not in people, str(people))
    breakdown = preview_section["source_record_count_breakdown"]
    _assert(breakdown["primary_media_sources"] == 1, str(breakdown))
    _assert(breakdown["secondary_transcript_records"] == 1, str(breakdown))
    _assert(breakdown["unknown_transcript_provenance_records"] == 0, str(breakdown))

if __name__ == "__main__":
    test_preserved_youtube_comment_thread_extractor_handles_brett_authored_replies_only()
    test_preserved_brett_comment_sections_have_semantic_claim_spans()
    test_metro_source_artifacts_build_importable_batch_payload()
    test_preview_json_write_is_confirmation_gated_and_import_validator_accepts_it()
    test_kind_and_bucket_mapping_are_review_conservative()
    test_source_package_preview_adds_mixed_role_segment_candidates_from_article_text()
    test_internal_media_artifact_is_primary_media_source()
    test_payload_includes_text_without_mutation_flags()
    test_section_aware_source_txt_person_contexts_for_metro_sources()
    test_metro_article_and_0407_0408_source_txt_acceptance()
    test_source_transcript_scope_excludes_comment_only_persons()
    test_transcript_people_can_carry_related_comment_user_context_without_comment_only_people()
    test_source_package_preview_emits_claim_role_spans_for_full_transcript()
    test_source_package_preview_separates_provenance_references_and_claim_counts()
    test_source_package_preview_unknown_transcript_and_metadata_only_source_card()
    test_source_package_preview_adds_link_source_preview_without_inflating_source_counts()
    test_metro_article_text_and_links_feed_repair1_review_payload()
    test_mixed_top_link_preamble_and_article_body_both_feed_review_layers()
    test_0407_metadata_separator_does_not_replace_canonical_transcript()
    print("profile_media_source_package_preview v82a OK")
