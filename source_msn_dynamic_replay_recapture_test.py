from __future__ import annotations

import gzip
import json
import tempfile
import zipfile
from pathlib import Path

from source_msn_dynamic_replay_recapture import (
    CapturedResponse,
    MAIN_URL_FALLBACK,
    article_terms_verified,
    build_materialized_article_html,
    build_warc,
    cdx_timestamp_from_iso,
    desktop_article_url,
    find_article_detail,
    gzip_warc_members,
    materialize_body_html,
    surt_key,
    text_from_html,
    write_wacz,
)


ARTICLE = {
    "title": "Arrest made after shot fired outside York mosque",
    "abstract": "Arrest made after shot fired outside York mosque -",
    "sourceHref": "https://www.independent.co.uk/bulletin/news/york-mosque-north-yorkshire-police-b3024401.html",
    "authors": [{"name": "Tom Wilkinson"}],
    "provider": {"name": "The Independent"},
    "imageResources": [{"url": "https://img-s-msn-com.akamaized.net/tenant/amp/entityid/AA292lx3.img", "cmsId": "cms/api/amp/image/AA292lx3", "caption": "Mosque image", "attribution": "Google Street View"}],
    "body": "<img data-reference='image' data-document-id='cms/api/amp/image/AA292lx3' /><ul><li>A 44-year-old man has been arrested after a firearm was discharged outside York Mosque and Islamic Centre on Bull Lane at 2.19am on Thursday.</li></ul>",
}


def test_article_terms() -> None:
    assert article_terms_verified(text_from_html(ARTICLE["body"]))
    assert not article_terms_verified("Advertisement More for You")


def test_desktop_article_url_strips_fragment() -> None:
    assert "#" not in desktop_article_url(MAIN_URL_FALLBACK + "#comments")


def test_materialize_body_html_replaces_image() -> None:
    out = materialize_body_html(ARTICLE)
    assert "article-image" in out
    assert "AA292lx3.img" in out


def test_find_article_detail() -> None:
    response = CapturedResponse(
        url="https://assets.msn.com/content/view/v2/Detail/en-gb/AA29207o",
        status=200,
        content_type="application/json; charset=utf-8",
        resource_type="fetch",
        body=json.dumps(ARTICLE).encode("utf-8"),
        captured_at_utc="2026-08-12T05:56:34Z",
    )
    article, source = find_article_detail([response])
    assert article is not None
    assert source is response


def test_build_html_warc_wacz() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        article_response = CapturedResponse(
            url="https://assets.msn.com/content/view/v2/Detail/en-gb/AA29207o",
            status=200,
            content_type="application/json; charset=utf-8",
            resource_type="fetch",
            body=json.dumps(ARTICLE).encode("utf-8"),
            captured_at_utc="2026-08-12T05:56:34Z",
        )
        html, comment_total, actual_comment_text = build_materialized_article_html(
            source_url=MAIN_URL_FALLBACK,
            article=ARTICLE,
            article_response=article_response,
            social_summary={"commentSummary": {"totalCount": 25, "subCommentSummaries": [{"type": "Comment", "totalCount": 16}, {"type": "Reply", "totalCount": 9}]}},
            social_response=None,
            visible_body_text="Advertisement More for You",
            visible_dom_verified=False,
        )
        assert "desktop JSON-first dynamic recapture V5" in html
        assert "article only" in html or "article-only" in html
        assert "A 44-year-old man" in html
        assert comment_total == 25
        assert actual_comment_text is False
        warc = build_warc(MAIN_URL_FALLBACK, html, [article_response], "2026-08-12T05:56:34Z")
        warc_gz, members = gzip_warc_members(warc)
        assert gzip.decompress(warc_gz).startswith(b"WARC/1.0")
        wacz = root / "x.wacz"
        result = write_wacz(wacz, MAIN_URL_FALLBACK, ARTICLE["title"], warc_gz, members, "2026-08-12T05:56:34Z")
        assert result["cdx_timestamp"] == "20260812055634"
        assert result["main_surt_key"].startswith("com,msn,www,)/")
        with zipfile.ZipFile(wacz, "r") as z:
            assert "archive/data.warc.gz" in z.namelist()
            assert "indexes/index.cdxj" in z.namelist()


def test_surt_and_timestamp() -> None:
    assert surt_key("https://www.msn.com/en-gb/news/x?PC=EMMX01") == "com,msn,www,)/en-gb/news/x?pc=emmx01"
    assert cdx_timestamp_from_iso("2026-08-12T05:56:34Z") == "20260812055634"


if __name__ == "__main__":
    test_article_terms()
    test_desktop_article_url_strips_fragment()
    test_materialize_body_html_replaces_image()
    test_find_article_detail()
    test_build_html_warc_wacz()
    test_surt_and_timestamp()
    print("source_msn_dynamic_replay_recapture_test OK")
