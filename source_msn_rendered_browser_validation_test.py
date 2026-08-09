from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

from warcio.archiveiterator import ArchiveIterator

import source_msn_rendered_browser_validation as msn_rendered
from source_msn_rendered_browser_validation import (
    LOCAL_PACKAGE_STRUCTURALLY_VERIFIED,
    RENDERED_BROWSER_LIVE_TESTED,
    CapturedResponse,
    MOBILE_PROFILE,
    _collect_incremental_comments,
    _download_from_captured_response,
    _merge_provider_comment_rows,
    _reconcile_comments,
    _write_comments_derived_artifacts,
    verify_wacz_structure,
    write_standard_wacz,
    write_standard_warc,
)


def _response(url: str, body: bytes, content_type: str = "text/html") -> CapturedResponse:
    return CapturedResponse(
        url=url,
        status=200,
        headers={
            "Content-Type": content_type,
            "Cookie": "should-not-export=true",
            "Set-Cookie": "should-not-export=true",
            "Authorization": "Bearer should-not-export",
        },
        body=body,
        resource_type="document",
        method="GET",
        from_profile="fixture",
    )


def test_rendered_warc_is_readable_and_redacts_secret_headers() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        warc_path = Path(temp_dir) / "archive" / "data.warc"
        result = write_standard_warc(
            output_warc_path=warc_path,
            responses=(
                _response("https://www.msn.com/story", b"<html><body>story</body></html>"),
                _response("https://www.msn.com/story/image.jpg", b"image bytes", "image/jpeg"),
            ),
            timestamp_utc="2026-08-09T00:00:00Z",
        )

        assert result["conformant_read_record_count"] == 4
        assert result["index_rows"][0]["filename"] == "archive/data.warc"
        raw_warc = warc_path.read_text(encoding="latin-1")
        assert "should-not-export" not in raw_warc
        assert "Bearer should-not-export" not in raw_warc
        assert "should-not-export=true" not in raw_warc
        with warc_path.open("rb") as stream:
            records = list(ArchiveIterator(stream))
        assert [record.rec_type for record in records] == ["request", "response", "request", "response"]


def test_rendered_wacz_has_expected_standard_entries_and_index() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        warc = write_standard_warc(
            output_warc_path=root / "archive" / "data.warc",
            responses=(_response("https://www.msn.com/story", b"<html><body>story</body></html>"),),
            timestamp_utc="2026-08-09T00:00:00Z",
        )
        wacz = write_standard_wacz(
            output_wacz_path=root / "archive.wacz",
            warc_path=warc["path"],
            index_rows=warc["index_rows"],
            source_url="https://www.msn.com/story",
            title="Story",
            text="Story text",
            timestamp_utc="2026-08-09T00:00:00Z",
        )

        assert wacz["status"] == LOCAL_PACKAGE_STRUCTURALLY_VERIFIED
        assert wacz["missing_required_entries"] == []
        assert wacz["index_line_count"] == 1
        with zipfile.ZipFile(root / "archive.wacz", "r") as bundle:
            names = set(bundle.namelist())
            assert "archive/data.warc" in names
            assert "indexes/index.cdx.gz" in names
            assert "pages/pages.jsonl" in names
            assert "datapackage.json" in names
            package = json.loads(bundle.read("datapackage.json").decode("utf-8"))
            assert package["wacz_version"] == "1.2.0"

        verified = verify_wacz_structure(root / "archive.wacz")
        assert verified["status"] == LOCAL_PACKAGE_STRUCTURALLY_VERIFIED


def test_representative_download_uses_part_then_final_and_hashes() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        response = _response(
            "https://img-s-msn-com.akamaized.net/example/AA292lx3.img",
            b"\xff\xd8\xffrepresentative image",
            "image/jpeg",
        )

        result = _download_from_captured_response(output_directory=root, responses=(response,))

        assert result["status"] == RENDERED_BROWSER_LIVE_TESTED
        assert result["download_performed"] is True
        assert result["source_url"] == response.url
        assert result["mime_type"] == "image/jpeg"
        assert Path(result["output_path"]).is_file()
        assert Path(result["output_path"]).suffix == ".jpg"
        assert not Path(result["output_path"] + ".part").exists()


def test_incremental_comments_collects_nested_shadow_comment_items() -> None:
    msn_rendered.COMMENT_STABLE_PASS_TARGET = 2
    msn_rendered.COMMENT_PASS_WAIT_MS = 25
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path(".playwright-browsers").resolve()))
    from playwright.sync_api import sync_playwright

    html = """
    <html><body>
      <social-comment-wc></social-comment-wc>
      <script>
        class CommentItem extends HTMLElement {
          connectedCallback() {
            if (this.shadowRoot) return;
            const root = this.attachShadow({mode: 'open'});
            root.innerHTML = `
              <div class="comment-item-container">
                <comment-item-header></comment-item-header>
                <div class="message"><div class="comment-body">${this.getAttribute('body')}</div></div>
                <reply-list></reply-list>
              </div>`;
            const header = root.querySelector('comment-item-header');
            const headerRoot = header.attachShadow({mode: 'open'});
            headerRoot.innerHTML = `<header><a class="item-user-name" href="/community/profile/${this.getAttribute('id')}">${this.getAttribute('author')}</a><span class="posted-at">${this.getAttribute('date')}</span></header>`;
          }
        }
        class CommentList extends HTMLElement {
          connectedCallback() {
            if (this.shadowRoot) return;
            const root = this.attachShadow({mode: 'open'});
            root.innerHTML = `<div style="overflow-y:auto;max-height:120px"><div>4 comments</div><ul class="comment-list"></ul><div class="load-more-comments-container"><a class="load-more-comments-button" role="button">See more comments</a></div></div>`;
            const ul = root.querySelector('ul');
            const first = this.makeItem('c1', 'Fixture Author', '30 Jul', 'First fixture comment');
            ul.appendChild(first);
            const replyList = first.querySelector('comment-item').shadowRoot.querySelector('reply-list');
            const replyRoot = replyList.attachShadow({mode: 'open'});
            replyRoot.innerHTML = `<button class="show-more-replies">See 1 more reply</button><div id="replyTarget"></div>`;
            replyRoot.querySelector('button').addEventListener('click', () => {
              if (!replyRoot.querySelector('#r1')) replyRoot.querySelector('#replyTarget').appendChild(this.makeItem('r1', 'Reply Author', '30 Jul', 'Reply fixture comment').querySelector('comment-item'));
            });
            root.querySelector('a').addEventListener('click', () => {
              if (!root.querySelector('#c2')) ul.appendChild(this.makeItem('c2', 'Second Author', '31 Jul', 'Second fixture comment'));
            });
          }
          makeItem(id, author, date, body) {
            const li = document.createElement('li');
            const item = document.createElement('comment-item');
            item.id = id;
            item.setAttribute('data-t', JSON.stringify({'n': 'CommentItem', 'c.i': id}));
            item.setAttribute('author', author);
            item.setAttribute('date', date);
            item.setAttribute('body', body);
            li.appendChild(item);
            return li;
          }
        }
        class SocialComment extends HTMLElement {
          connectedCallback() {
            if (this.shadowRoot) return;
            const root = this.attachShadow({mode: 'open'});
            root.innerHTML = `<fluent-design-system-provider><div class="overlay-container" style="overflow-y:auto;max-height:160px"><comment-list></comment-list></div></fluent-design-system-provider>`;
          }
        }
        customElements.define('comment-item', CommentItem);
        customElements.define('comment-list', CommentList);
        customElements.define('social-comment-wc', SocialComment);
      </script>
    </body></html>
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport=MOBILE_PROFILE["viewport"])
            page = context.new_page()
            page.set_content(html)
            comments, artifact = _collect_incremental_comments(page, Path(temp_dir), "fixture_profile")
            context.close()
            browser.close()

        assert comments["social_comment_wc_found"] is True
        assert comments["social_comment_wc_shadow_open"] is True
        assert comments["row_count"] == 3
        assert [row["comment_id"] for row in comments["rows"]] == ["c1", "r1", "c2"]
        assert comments["rows"][0]["author"] == "Fixture Author"
        assert comments["rows"][0]["posted_at"] == "30 Jul"
        assert comments["rows"][1]["depth"] == 1
        assert comments["rows"][2]["first_seen_step"] >= 0
        assert comments["completeness"] == "visible_rows_partial_declared_count_unreached"
        assert comments["incremental_stable_pass_target"] == 2
        assert Path(artifact.path).read_text(encoding="utf-8").count("\n") == 3


def test_comment_provider_reconciliation_marks_complete_for_roots_plus_replies() -> None:
    rows = [
        {"comment_id": "r1", "stable_identifier": "r1", "depth": 0},
        {"comment_id": "r2", "stable_identifier": "r2", "depth": 0},
        {"comment_id": "q1", "stable_identifier": "q1", "depth": 1},
    ]

    result = _reconcile_comments(rows=rows, declared_total=3, provider_root_count=2, provider_reply_count=1)

    assert result["comments_complete"] is True
    assert result["completeness"] == "COMMENTS_COMPLETE"
    assert result["reconciliation"] == "2 top-level + 1 replies = 3; provider declared 3"


def test_provider_merge_uses_stable_api_ids_and_keeps_identical_text_distinct() -> None:
    comments = {"declared_comment_count": 2, "rows": [{"comment_id": "dom-only", "stable_identifier": "dom-only", "text": "Same"}]}
    api_result = {
        "api_followup_performed": True,
        "declared_total_count": 2,
        "records": [
            {"comment_id": "api-1", "stable_identifier": "api-1", "depth": 0, "text": "Same"},
            {"comment_id": "api-2", "stable_identifier": "api-2", "depth": 0, "text": "Same"},
        ],
        "reply_record_count": 0,
        "root_record_count": 2,
    }

    merged = _merge_provider_comment_rows(comments, api_result)

    assert merged["row_count"] == 2
    assert [row["comment_id"] for row in merged["rows"]] == ["api-1", "api-2"]
    assert merged["provider_reconciliation"]["comments_complete"] is True


def test_derived_comments_artifact_is_separate_from_faithful_capture() -> None:
    msn_rendered.COMMENT_STABLE_PASS_TARGET = 2
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path(".playwright-browsers").resolve()))
    from playwright.sync_api import sync_playwright

    with tempfile.TemporaryDirectory() as temp_dir:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport=MOBILE_PROFILE["viewport"])
            page = context.new_page()
            page.set_content("<html><body><p>faithful page</p></body></html>")
            artifacts = _write_comments_derived_artifacts(
                Path(temp_dir),
                "fixture_profile",
                page,
                {"rows": [{"comment_id": "c1", "depth": 0, "author": "A", "posted_at": "now", "text": "Comment"}]},
            )
            context.close()
            browser.close()

        labels = {artifact.label for artifact in artifacts}
        assert "fixture_profile_comments_derived_layout_transformations" in labels
        assert "fixture_profile_derived_comments_full_thread_html" in labels
        assert any("derived_comments_full_thread_screenshot" in label for label in labels)
        transform = Path(temp_dir) / "fixture_profile" / "comments_derived_layout_transformations.json"
        payload = json.loads(transform.read_text(encoding="utf-8"))
        assert payload["label"] == "DERIVED_MSN_COMMENTS_EXPANDED_LAYOUT"
        assert payload["faithful_screenshot_unmodified"] is True


def run_self_test() -> None:
    test_rendered_warc_is_readable_and_redacts_secret_headers()
    test_rendered_wacz_has_expected_standard_entries_and_index()
    test_representative_download_uses_part_then_final_and_hashes()
    test_incremental_comments_collects_nested_shadow_comment_items()
    test_comment_provider_reconciliation_marks_complete_for_roots_plus_replies()
    test_provider_merge_uses_stable_api_ids_and_keeps_identical_text_distinct()
    test_derived_comments_artifact_is_separate_from_faithful_capture()


if __name__ == "__main__":
    run_self_test()
    print("source_msn_rendered_browser_validation.py: OK")
