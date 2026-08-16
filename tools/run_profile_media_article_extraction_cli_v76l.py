from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_article_extraction_adapter import (
    WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW,
    extract_article_from_file,
    extract_article_from_html,
    render_article_extraction_text,
    write_article_source_preview,
)

DEMO_HTML = """<!doctype html>
<html>
<head>
<title>Demo Article</title>
<link rel="canonical" href="https://example.test/news/2026/jun/21/demo" />
<meta property="og:title" content="21 Jun - Demo article folder - White" />
<meta property="og:site_name" content="Belfast Telegraph" />
<meta name="author" content="Demo Reporter" />
<meta property="article:published_time" content="2026-06-21T10:00:00Z" />
<meta name="description" content="Demo article for HOME repository extraction." />
<meta property="og:image" content="https://example.test/images/demo-person.jpg" />
</head>
<body>
<article>
<h1>21 Jun - Demo article folder - White</h1>
<p>Police said the report repeated a court claim about the incident.</p>
<p>A witness told the newspaper that they saw part of the event.</p>
<p>The image is recorded as an image URL only; the app must not treat the person shown as affiliated without marking.</p>
<p><a href="/court-document">court document</a></p>
</article>
</body>
</html>"""


def _write_demo_html(path_text: str | None) -> Path:
    if path_text:
        path = Path(path_text)
    else:
        path = Path(tempfile.gettempdir()) / "ytce_profile_media_article_v76l_demo.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEMO_HTML, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="V76L Profile/Media article extraction adapter proof")
    parser.add_argument("--html-file", default="", help="Local HTML file to parse. No web download is performed.")
    parser.add_argument("--source-url", default="https://example.test/news/2026/jun/21/demo", help="Original/canonical article URL label.")
    parser.add_argument("--reference-root", default="", help="Optional external_reference_sources_... folder for local optional imports.")
    parser.add_argument("--extractor-order", nargs="*", default=None, help="Optional extractor order, e.g. metadata_parser trafilatura newspaper4k stdlib_html")
    parser.add_argument("--write-demo-html", default="", help="Write and use a small demo HTML file at this path.")
    parser.add_argument("--print-text", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    parser.add_argument("--output-json", default="", help="Write source preview JSON only with the confirmation phrase.")
    parser.add_argument("--confirm-write", default="")
    args = parser.parse_args()

    html_file = args.html_file
    if args.write_demo_html or not html_file:
        html_file = str(_write_demo_html(args.write_demo_html or None))

    result = extract_article_from_file(
        html_file,
        source_url=args.source_url,
        reference_root=args.reference_root,
        extractor_order=args.extractor_order,
    )
    payload = result.to_dict()

    write_result = None
    if args.output_json:
        write_result = write_article_source_preview(result, args.output_json, confirmation=args.confirm_write)
        payload["write_result"] = write_result

    if args.print_text:
        print(render_article_extraction_text(result))
        if write_result is not None:
            print("")
            print("Write result:")
            print(json.dumps(write_result, ensure_ascii=False, indent=2))
    if args.print_json or not args.print_text:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.status in {"success", "needs_review_empty_extraction"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
