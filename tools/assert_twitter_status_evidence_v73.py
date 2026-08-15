from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from twitter_status_evidence_extractor import extract_status_evidence_from_capture, render_human_readable_status


_MINIMAL_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAFgwJ/lJ/aigAAAABJRU5ErkJggg=="


def _write_fixture_capture(capture: Path) -> None:
    source_url = "https://x.com/DuvalMagic/status/2085760210359267524"
    dom = """<!DOCTYPE html><html><head>
<title>Randy Pitchford on X: "Use this SHiFT code for free Golden Keys" / X</title>
<meta property="og:url" content="https://x.com/DuvalMagic/status/2085760210359267524">
<meta property="og:title" content="Randy Pitchford (@DuvalMagic) on X">
<meta property="og:description" content="Use this SHiFT code for free Golden Keys in Borderlands 4:

THFB3-SW99B-W6JB5-JTTJ3-SKK9W

Redeem in-game or at https://t.co/Spvl73WSZt. Expires 8/28.

Good luck, and happy looting!">
<meta property="og:image" content="https://pbs.twimg.com/media/HPIb1teawAEGqVL.png:large">
<link rel="canonical" href="https://x.com/DuvalMagic/status/2085760210359267524">
<link rel="preload" as="image" imagesrcset="https://pbs.twimg.com/media/HPIb1teawAEGqVL?format=webp&amp;name=small 680w, https://pbs.twimg.com/media/HPIb1teawAEGqVL?format=webp&amp;name=large 2048w">
</head><body>
<article data-tweet-id="2085760210359267524">
<a href="https://x.com/DuvalMagic">Randy Pitchford</a>
<a href="https://x.com/DuvalMagic">@DuvalMagic</a>
<div>Use this SHiFT code for free Golden Keys in Borderlands 4:</div>
<a href="http://shift.gearbox.com">shift.gearbox.com</a>
<a href="/DuvalMagic/status/2085760210359267524">17:09 · 7 Aug 2026</a>
<a href="/DuvalMagic/status/2085760210359267524">124.9kViews</a>
<span>5</span><span>115</span><span>747</span><span>186</span>
</article>
</body></html>"""
    (capture / "rendered_dom_snapshot.html").write_text(dom, encoding="utf-8")
    (capture / "browser_session_manifest.json").write_text(json.dumps({"canonical_url": source_url, "source_url": source_url}), encoding="utf-8")
    (capture / "network_events.jsonl").write_text(json.dumps({"url": "https://pbs.twimg.com/media/HPIb1teawAEGqVL?format=webp&name=large", "status": 200}) + "\n", encoding="utf-8")
    (capture / "media_inventory.json").write_text("[]\n", encoding="utf-8")
    (capture / "screenshot.png").write_bytes(base64.b64decode(_MINIMAL_PNG_B64))


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="ytce_v73_status_evidence_") as tmp:
        capture = Path(tmp)
        _write_fixture_capture(capture)
        bundle = extract_status_evidence_from_capture(capture)
        text = render_human_readable_status(bundle)
        links = json.loads((capture / "status_links_inventory.json").read_text(encoding="utf-8"))
        counters = json.loads((capture / "status_counters_inventory.json").read_text(encoding="utf-8"))
        markers = json.loads((capture / "status_media_markers.json").read_text(encoding="utf-8"))
        screenshot_manifest = json.loads((capture / "screenshot_manifest.json").read_text(encoding="utf-8"))

        assert bundle.author_name == "Randy Pitchford"
        assert bundle.screen_name == "DuvalMagic"
        assert bundle.status_id == "2085760210359267524"
        assert "Use this SHiFT code" in bundle.post_text
        assert bundle.posted_at == "17:09 · 7 Aug 2026"
        assert bundle.views == "124.9k"
        assert any(counter["name"] == "comments" and counter["raw_value"] == "5" for counter in counters)
        assert any(counter["name"] == "retweets" and counter["raw_value"] == "115" for counter in counters)
        assert any(counter["name"] == "likes" and counter["raw_value"] == "747" for counter in counters)
        assert any(counter["name"] == "bookmarks" and counter["raw_value"] == "186" for counter in counters)
        assert any(item["url"] == "http://shift.gearbox.com" and item["link_type"] == "external" for item in links)
        assert any(item["media_id"] == "HPIb1teawAEGqVL" and item["safe_to_handoff_to_jd"] is True for item in markers)
        assert screenshot_manifest["capture_strategy"] == "go_full_page_style_full_page_or_tiled_manifest"
        assert screenshot_manifest["tiles"][0]["exists"] is True
        assert "Randy Pitchford\n@DuvalMagic" in text
        assert "124.9k Views" in text
        assert "5 comments 115 retweets 747 likes 186 bookmarks" in text

    print("assert_twitter_status_evidence_v73 OK")


if __name__ == "__main__":
    main()
