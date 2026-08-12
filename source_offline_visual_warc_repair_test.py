from __future__ import annotations

import gzip
import json
import tempfile
from pathlib import Path

from source_offline_visual_warc_repair import generate_static_visual_replay

TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6360000002000100ffff03000006000557bfab00000000"
    "49454e44ae426082"
)


def test_static_visual_replay_generation() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "live_capture" / "browser_capture" / "android_mobile_chromium").mkdir(parents=True)
        (root / "media").mkdir()
        (root / "screenshots").mkdir()
        (root / "live_capture" / "browser_capture" / "desktop_chromium").mkdir(parents=True)
        (root / "live_capture" / "rendered-page.html").parent.mkdir(parents=True, exist_ok=True)
        (root / "live_capture" / "rendered-page.html").write_text("<html><head><title>Arrest made after shot fired outside York mosque</title></head><body>Story by Tom Wilkinson</body></html>", encoding="utf-8")
        (root / "live_capture" / "browser_capture" / "android_mobile_chromium" / "article.txt").write_text(
            "A 44-year-old man has been arrested after a firearm was discharged outside York Mosque and Islamic Centre on Bull Lane. "
            "No one was injured in the incident, and the firearm is believed to have been an air weapon. "
            "IN FULL Man arrested after ‘disturbing’ firearm incident outside York mosque",
            encoding="utf-8",
        )
        (root / "media" / "AA292lx3.img").write_bytes(TINY_PNG)
        (root / "screenshots" / "android_article_MAIN_SINGLE_reference_style.png").write_bytes(TINY_PNG)
        (root / "live_capture" / "browser_capture" / "desktop_chromium" / "faithful_full_page.png").write_bytes(TINY_PNG)
        (root / "comments.json").write_text(json.dumps({"comments": [{"text": "one", "replies": [{"text": "two"}]}]}), encoding="utf-8")
        (root / "profiles.json").write_text(json.dumps([{"author": "a"}]), encoding="utf-8")
        result = generate_static_visual_replay(root)
        html_text = Path(result["html_path"]).read_text(encoding="utf-8")
        assert "Arrest made after shot fired outside York mosque" in html_text
        assert "Static visual WARC repair candidate" in html_text
        assert "Accepted article screenshot reference" in html_text
        assert "captured desktop full-page screenshot" not in html_text
        assert "for='hero-image-expanded'" in html_text
        assert "for='accepted-article-screenshot-expanded'" in html_text
        assert "lightbox-toggle:checked + .lightbox" in html_text
        assert "ytce_static_visual_replay_v3" in result["target_url"]
        assert Path(result["html_path"]).name == "msn-static-visual-replay-v3.html"
        assert Path(result["warc_gz_path"]).name == "static-msn-visual-replay-v3.warc.gz"
        assert "Structured comments loaded: <strong>2</strong>" in html_text
        assert Path(result["warc_gz_path"]).is_file()
        with gzip.open(result["warc_gz_path"], "rb") as f:
            raw = f.read()
        assert b"WARC/1.0" in raw
        assert b"HTTP/1.1 200 OK" in raw
        assert b"msn static visual replay" in raw.lower()
        assert result["dynamic_replay_success_claimed"] is False
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        assert manifest["embedded_reference_screenshot_label"] == "accepted Android article screenshot"
        assert manifest["click_to_expand_images"] is True
        assert manifest["click_to_expand_implementation"] == "no_navigation_checkbox_label_lightbox"
        assert manifest["replayweb_cache_bust_target_url"] is True
        assert manifest["accepted_article_screenshot"]["exists"] is True
        assert manifest["desktop_full_page_screenshot_metadata_only"]["exists"] is True


if __name__ == "__main__":
    test_static_visual_replay_generation()
    print("source_offline_visual_warc_repair_test OK")
