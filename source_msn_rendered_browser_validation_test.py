from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

from warcio.archiveiterator import ArchiveIterator

from source_msn_rendered_browser_validation import (
    LOCAL_PACKAGE_STRUCTURALLY_VERIFIED,
    RENDERED_BROWSER_LIVE_TESTED,
    CapturedResponse,
    MOBILE_PROFILE,
    _collect_incremental_comments,
    _download_from_captured_response,
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
            root.innerHTML = `<div><ul class="comment-list"></ul><div class="load-more-comments-container"><a class="load-more-comments-button" role="button">See more comments</a></div></div>`;
            const ul = root.querySelector('ul');
            ul.appendChild(this.makeItem('c1', 'Fixture Author', '30 Jul', 'First fixture comment'));
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
        assert comments["row_count"] == 2
        assert [row["comment_id"] for row in comments["rows"]] == ["c1", "c2"]
        assert comments["rows"][0]["author"] == "Fixture Author"
        assert comments["rows"][0]["posted_at"] == "30 Jul"
        assert comments["rows"][1]["first_seen_step"] > 0
        assert comments["completeness"] == "incremental_visible_rows_captured_partial"
        assert Path(artifact.path).read_text(encoding="utf-8").count("\n") == 2


def run_self_test() -> None:
    test_rendered_warc_is_readable_and_redacts_secret_headers()
    test_rendered_wacz_has_expected_standard_entries_and_index()
    test_representative_download_uses_part_then_final_and_hashes()
    test_incremental_comments_collects_nested_shadow_comment_items()


if __name__ == "__main__":
    run_self_test()
    print("source_msn_rendered_browser_validation.py: OK")
