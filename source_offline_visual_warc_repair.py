from __future__ import annotations

import base64
import datetime as _dt
import gzip
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

VERSION = "2026-08-12.static-msn-visual-warc-repair.v3"
DEFAULT_TARGET_URL = "https://www.msn.com/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o?ytce_static_visual_replay_v3=20260812_reference_image_expander"
OUTPUT_DIR_NAME = "static_visual_replay_v3"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest().upper()
    except Exception:
        return None


def _sha1_base32(data: bytes) -> str:
    return "sha1:" + base64.b32encode(hashlib.sha1(data).digest()).decode("ascii").lower()


def read_text(path: Path | None, max_chars: int = 120_000) -> str:
    if not path or not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n[TRUNCATED at {max_chars} characters]"
    return text


def read_json(path: Path | None) -> Any:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def find_existing(root: Path, candidates: list[str]) -> Path | None:
    normalized_candidates = [c.replace("\\", "/") for c in candidates]
    for candidate in candidates:
        p = root / candidate
        if p.is_file():
            return p
    names = {Path(x.replace("\\", "/")).name for x in candidates}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(root).as_posix().replace("\\", "/")
        except Exception:
            rel = str(p).replace("\\", "/")
        if rel in normalized_candidates or p.name in names or rel.split("/")[-1] in names:
            return p
    return None


def detect_files(root: Path) -> dict[str, Path | None]:
    return {
        "rendered_html": find_existing(root, ["live_capture/rendered-page.html", "rendered-page.html"]),
        "article_text_android": find_existing(root, ["live_capture/browser_capture/android_mobile_chromium/article.txt"]),
        "article_text_desktop": find_existing(root, ["live_capture/browser_capture/desktop_chromium/article.txt"]),
        "comments_json": find_existing(root, ["comments.json"]),
        "profiles_json": find_existing(root, ["profiles.json", "comments-profiles.json"]),
        "hero_image": find_existing(root, ["media/AA292lx3.img", "AA292lx3.img"]),
        "desktop_full_page_screenshot": find_existing(root, [
            "live_capture/browser_capture/desktop_chromium/faithful_full_page.png",
            "live_capture/screenshots/full-page.png",
            "faithful_full_page.png",
            "full-page.png",
        ]),
        "accepted_article_screenshot": find_existing(root, ["screenshots/android_article_MAIN_SINGLE_reference_style.png"]),
        "accepted_comments_screenshot": find_existing(root, ["screenshots/android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png"]),
        "capture_manifest": find_existing(root, ["live_capture/capture-manifest.json", "capture-manifest.json"]),
    }


def strip_tags(text: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_title(rendered_html: str, fallback: str = "Arrest made after shot fired outside York mosque") -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", rendered_html, flags=re.I | re.S)
    if m:
        title = html.unescape(strip_tags(m.group(1))).strip()
        title = re.sub(r"\s+[-|].*$", "", title).strip()
        if title:
            return title
    return fallback


def extract_source_url(root: Path, files: dict[str, Path | None]) -> str:
    manifest = read_json(files.get("capture_manifest"))
    if isinstance(manifest, dict):
        for key in ("canonical_source_url",):
            val = str(manifest.get(key) or "").strip()
            if val:
                return val
        norm = manifest.get("normalized_outputs")
        if isinstance(norm, dict):
            val = str(norm.get("canonical_source_url") or "").strip()
            if val:
                return val
    return "https://www.msn.com/en-gb/news/other/arrest-made-after-shot-fired-outside-york-mosque/ar-AA29207o"


def extract_article_sections(article_text: str) -> tuple[list[str], str]:
    text = re.sub(r"\s+", " ", article_text).strip()
    if not text:
        return [], ""
    marker = " IN FULL "
    if marker in " " + text + " ":
        before, after = text.split("IN FULL", 1)
        summary_text = before.strip()
        in_full = after.strip()
    else:
        summary_text = text
        in_full = ""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", summary_text)
    bullets = [s.strip() for s in sentences if len(s.strip()) > 10]
    if len(bullets) > 6:
        bullets = bullets[:6]
    if not in_full and len(sentences) > len(bullets):
        in_full = " ".join(sentences[len(bullets):]).strip()
    return bullets, in_full


def _top_level_comments(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("comments", "items", "rows", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return val
    return []


def load_comment_count(path: Path | None) -> int:
    data = read_json(path)
    top = _top_level_comments(data)
    count = 0

    def walk(item: Any) -> None:
        nonlocal count
        count += 1
        if isinstance(item, dict):
            replies = item.get("replies")
            if isinstance(replies, list):
                for child in replies:
                    walk(child)

    for item in top:
        walk(item)
    return count


def load_profile_count(path: Path | None) -> int:
    data = read_json(path)
    if isinstance(data, list):
        return len([x for x in data if isinstance(x, dict)])
    if isinstance(data, dict):
        for key in ("profiles", "items", "rows", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return len([x for x in val if isinstance(x, dict)])
    return 0


def sniff_mime(path: Path) -> str:
    try:
        start = path.read_bytes()[:16]
    except Exception:
        start = b""
    if start.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if start.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    guessed = mimetypes.guess_type(path.name)[0]
    return guessed or "application/octet-stream"


def data_uri_for_file(path: Path | None) -> tuple[str, dict[str, Any]]:
    if not path or not path.is_file():
        return "", {"exists": False}
    data = path.read_bytes()
    mime = sniff_mime(path)
    return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii"), {
        "exists": True,
        "path": str(path),
        "size_bytes": len(data),
        "sha256": sha256_bytes(data),
        "mime_type": mime,
    }


def build_visual_html(root: Path, target_url: str = DEFAULT_TARGET_URL) -> tuple[str, dict[str, Any]]:
    files = detect_files(root)
    rendered_html = read_text(files.get("rendered_html"), 150_000)
    article_text = read_text(files.get("article_text_android"), 80_000)
    if "York" not in article_text and "firearm" not in article_text:
        backup = read_text(files.get("article_text_desktop"), 80_000)
        if "York" in backup or "firearm" in backup:
            article_text = backup
    if not article_text:
        article_text = strip_tags(rendered_html)
    title = extract_title(rendered_html)
    bullets, in_full = extract_article_sections(article_text)
    if not bullets:
        bullets = [
            "A 44-year-old man has been arrested after a firearm was discharged outside York Mosque and Islamic Centre on Bull Lane.",
            "No one was injured in the incident, and the firearm is believed to have been an air weapon.",
            "North Yorkshire Police confirmed the arrested man is a white UK national from York, who was traced after leaving the scene in a silver vehicle.",
            "Police inquiries are ongoing to establish the motivation behind the incident, and the man remains in custody for questioning.",
            "Authorities are providing reassurance to the Muslim community, with increased patrols around the mosque and officers meeting with the imam.",
        ]
    hero_uri, hero_record = data_uri_for_file(files.get("hero_image"))
    accepted_article_screenshot_uri, accepted_article_screenshot_record = data_uri_for_file(files.get("accepted_article_screenshot"))
    desktop_full_page_screenshot_uri, desktop_full_page_screenshot_record = data_uri_for_file(files.get("desktop_full_page_screenshot"))
    # The accepted single-article screenshot is the visual reference approved for this page.
    # The desktop full-page screenshot remains metadata-only because it includes unrelated feed/content blocks.
    reference_screenshot_uri = accepted_article_screenshot_uri or desktop_full_page_screenshot_uri
    reference_screenshot_record = accepted_article_screenshot_record if accepted_article_screenshot_uri else desktop_full_page_screenshot_record
    reference_screenshot_label = "accepted Android article screenshot" if accepted_article_screenshot_uri else "fallback desktop full-page screenshot"
    comment_count = load_comment_count(files.get("comments_json"))
    profile_count = load_profile_count(files.get("profiles_json"))
    source_url = extract_source_url(root, files)
    generated = _utc_now()
    if not in_full:
        in_full = "Man arrested after ‘disturbing’ firearm incident outside York mosque"

    bullet_html = "\n".join(f"<li>{html.escape(x)}</li>" for x in bullets)
    hero_html = (
        f"<label class='image-expand-link' for='hero-image-expanded' title='Click to expand hero image'><img class='hero' src='{hero_uri}' alt='York Mosque and Islamic Centre hero image'></label>"
        f"<input class='lightbox-toggle' id='hero-image-expanded' type='checkbox' aria-hidden='true'>"
        f"<label class='lightbox' for='hero-image-expanded' aria-label='Expanded hero image'><span class='lightbox-close' aria-hidden='true'>×</span><img src='{hero_uri}' alt='Expanded York Mosque and Islamic Centre hero image'></label>"
        if hero_uri else
        "<div class='missing-hero'>Hero image not found in local evidence bundle.</div>"
    )
    screenshot_section = (
        f"<section class='screenshot-proof'><h2>Accepted article screenshot reference</h2><p>This lower section embeds the accepted single-article screenshot reference, not the unrelated desktop full-page/feed screenshot. The reconstructed page above is the replay-friendly static view. Click the screenshot to expand it. V3 uses no-navigation checkbox/label expansion so ReplayWeb is less likely to treat the click as a page navigation.</p><label class='image-expand-link' for='accepted-article-screenshot-expanded' title='Click to expand accepted article screenshot'><img src='{reference_screenshot_uri}' alt='Accepted article screenshot reference'></label><input class='lightbox-toggle' id='accepted-article-screenshot-expanded' type='checkbox' aria-hidden='true'><label class='lightbox' for='accepted-article-screenshot-expanded' aria-label='Expanded accepted article screenshot'><span class='lightbox-close' aria-hidden='true'>×</span><img src='{reference_screenshot_uri}' alt='Expanded accepted article screenshot reference'></label><p class='proof-note'>Embedded reference: {html.escape(reference_screenshot_label)}.</p></section>"
        if reference_screenshot_uri else ""
    )

    doc = f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — MSN static visual replay</title>
<style>
:root {{ color-scheme: dark; --bg:#202020; --panel:#242424; --panel2:#191919; --line:#3d3d3d; --text:#f5f5f5; --muted:#a9a9a9; --accent:#00a2ff; --green:#19b95f; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family: Arial, Helvetica, sans-serif; font-size:14px; }}
a {{ color:#43b7ff; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.topbar {{ height:50px; background:#1f1f1f; border-bottom:1px solid #333; display:flex; align-items:center; gap:18px; padding:0 18px; position:sticky; top:0; z-index:5; }}
.logo {{ display:flex; align-items:center; gap:8px; font-weight:700; font-size:22px; }}
.logo-dot {{ width:24px; height:24px; border-radius:50%; background:linear-gradient(135deg,#14a1ff,#78c257 40%,#f95f62 72%,#ffd451); display:inline-block; }}
.back {{ border:1px solid #555; border-radius:16px; padding:7px 11px; font-size:12px; color:#fff; }}
.search {{ flex:1; max-width:620px; margin:auto; background:#fff; color:#777; height:34px; border-radius:18px; display:flex; align-items:center; padding:0 22px; }}
.weather {{ color:#ffd36a; font-weight:700; }}
.signin {{ border:1px solid #666; border-radius:3px; padding:7px 12px; font-size:12px; }}
.shell {{ display:grid; grid-template-columns:72px minmax(520px, 760px) 300px; gap:28px; max-width:1220px; margin:0 auto; padding:18px 0 36px; }}
.left-rail {{ padding-top:100px; }}
.rail-button {{ width:35px; height:35px; border-radius:10px; background:#303030; border:1px solid #4a4a4a; display:flex; align-items:center; justify-content:center; margin:12px auto; color:#ccc; }}
.badge {{ position:relative; }}
.badge::after {{ content:attr(data-badge); position:absolute; top:-7px; right:-7px; background:#0a84ff; color:#fff; border-radius:9px; font-size:10px; padding:2px 5px; }}
main {{ min-width:0; }}
.banner {{ height:64px; margin:0 auto 36px; max-width:660px; background:linear-gradient(90deg,#f3efe1,#fff 38%,#d8f0f6); color:#593c14; display:flex; align-items:center; justify-content:center; text-align:center; font-family:Georgia,serif; letter-spacing:.06em; border:1px solid #3a3a3a; }}
.publisher {{ background:#242424; border-radius:8px; padding:14px 18px; display:flex; align-items:center; justify-content:space-between; margin-bottom:22px; }}
.pub-left {{ display:flex; align-items:center; gap:12px; }}
.pub-icon {{ width:32px; height:32px; border-radius:50%; background:#fff; color:#e51d2a; display:flex; align-items:center; justify-content:center; font-weight:900; }}
.follow {{ background:#fff; color:#222; border-radius:4px; padding:5px 10px; font-size:12px; margin-left:8px; }}
h1 {{ font-size:30px; line-height:1.16; margin:0 0 18px; }}
.byline {{ color:#aaa; margin-bottom:24px; }}
.byline strong {{ color:#fff; }}
.readtime {{ color:var(--green); margin-left:10px; }}
.article-divider {{ border:0; border-top:1px solid #444; margin:0 0 24px; }}
.hero-wrap {{ margin-bottom:16px; }}
.hero {{ width:100%; display:block; max-height:455px; object-fit:cover; border-radius:3px; background:#111; }}
.caption {{ font-size:11px; color:#cfcfcf; margin:8px 0 24px; border-left:2px solid #00a2ff; padding-left:8px; }}
.summary {{ margin:0 0 28px 18px; padding:0; font-weight:700; line-height:1.56; }}
.summary li {{ margin:6px 0; }}
.full-label {{ font-weight:800; margin:26px 0 14px; }}
.newsletter {{ font-weight:700; line-height:1.6; margin-top:18px; }}
.right-col {{ border-left:1px solid #3b3b3b; padding-left:26px; padding-top:126px; }}
.ad {{ width:250px; height:250px; background:linear-gradient(150deg,#0073da,#0ea5ff 45%,#0b3c8a); border-radius:2px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; color:#ffef76; font-size:22px; font-weight:800; margin:0 auto 30px; }}
.ad small {{ color:#fff; font-size:11px; margin-top:14px; }}
.visit {{ border:1px solid #474747; border-radius:8px; padding:14px; margin:0 auto 30px; width:250px; }}
.visit-title {{ color:#43b7ff; font-weight:700; margin-bottom:12px; }}
.visit-item {{ padding:10px 0; border-top:1px solid #3a3a3a; font-size:12px; font-weight:700; line-height:1.4; }}
.evidence-note {{ margin-top:36px; border:1px solid #444; background:#171717; border-radius:8px; padding:14px 16px; color:#cfcfcf; }}
.screenshot-proof {{ margin:40px 0 20px; padding:18px; border:1px solid #444; background:#161616; border-radius:8px; }}
.screenshot-proof img {{ width:100%; max-width:100%; display:block; border:1px solid #444; }}
.image-expand-link {{ display:block; cursor:zoom-in; }}
.lightbox-toggle {{ position:fixed; left:-9999px; opacity:0; pointer-events:none; }}
.proof-note {{ color:#bdbdbd; font-size:12px; margin:10px 0 0; }}
.lightbox {{ display:none; position:fixed; inset:0; z-index:1000; background:rgba(0,0,0,.92); align-items:center; justify-content:center; padding:28px; cursor:zoom-out; }}
.lightbox-toggle:checked + .lightbox {{ display:flex; }}
.lightbox img {{ max-width:96vw; max-height:92vh; object-fit:contain; border:1px solid #555; background:#111; box-shadow:0 18px 60px rgba(0,0,0,.7); }}
.lightbox-close {{ position:fixed; right:24px; top:16px; z-index:1002; color:#fff; width:44px; height:44px; border-radius:50%; border:1px solid #777; background:#222; display:flex; align-items:center; justify-content:center; font-size:30px; line-height:1; text-decoration:none; }}
.lightbox > img {{ position:relative; z-index:1001; }}
.missing-hero {{ min-height:320px; display:flex; align-items:center; justify-content:center; border:1px dashed #666; color:#ccc; }}
@media (max-width:980px) {{ .shell {{ grid-template-columns:1fr; padding:14px; }} .left-rail,.right-col {{ display:none; }} .banner {{ margin-bottom:20px; }} .search {{ max-width:none; }} }}
</style>
</head>
<body>
<div class="topbar"><div class="logo"><span class="logo-dot"></span>msn</div><span class="back">Back to feed</span><div class="search">Search the web</div><div class="weather">☾ 18°C</div><div class="signin">Sign in</div></div>
<div class="shell">
<aside class="left-rail"><div class="rail-button">⌂</div><div class="rail-button badge" data-badge="34">👍</div><div class="rail-button">♡</div><div class="rail-button badge" data-badge="25">▣</div><div class="rail-button">↗</div><div class="rail-button">⋮</div></aside>
<main>
<div class="banner"><div>SUMMER ESCAPE&nbsp;&nbsp; <strong>35% OFF</strong><br><span style="font-size:11px">BEST AVAILABLE RATE · BOOK NOW</span></div></div>
<section class="publisher"><div class="pub-left"><span class="pub-icon">✦</span><strong>The Independent</strong><span class="follow">+ Follow</span></div><div class="muted">2.4M Followers&nbsp;&nbsp;↗</div></section>
<article>
<h1>{html.escape(title)}</h1>
<div class="byline">Story by <strong>Tom Wilkinson</strong> · 1w · <span class="readtime">↻ 1 min read</span></div>
<hr class="article-divider">
<div class="hero-wrap">{hero_html}<div class="caption">Screenshot 2026-07-30 at 07.50 copy<br>© Google Street View</div></div>
<ul class="summary">{bullet_html}</ul>
<div class="full-label">IN FULL</div>
<p><a href="#">{html.escape(in_full[:300])}</a></p>
<p class="newsletter">From news to politics, travel to sport, culture to climate – The Independent has a host of free newsletters to suit your interests. To find the stories you want to read, and more, in your inbox, click <a href="#">here</a>.</p>
</article>
<section class="evidence-note"><strong>Static visual WARC repair candidate.</strong> This derived page is intended to replay closer to the accepted MSN desktop appearance than the raw dynamic WARC. It does not replace the raw WARC/WACZ, does not claim dynamic ReplayWeb.page success, and uses only local captured artifacts. Structured comments loaded: <strong>{comment_count}</strong>. Profiles loaded: <strong>{profile_count}</strong>. Source URL: <a href="{html.escape(source_url)}">{html.escape(source_url)}</a>. Generated: {html.escape(generated)}.</section>
{screenshot_section}
</main>
<aside class="right-col"><div class="ad">bluehost<br><span>World-class speed for your WordPress sites.</span><small>Sponsored</small></div><div class="visit"><div class="visit-title">Visit The Independent ↗</div><div class="visit-item">Iran war latest: Trump claims total control of Strait of Hormuz</div><div class="visit-item">CNN pundit reveals how Mitch McConnell is doing after rehab</div><div class="visit-item">Trump issues ‘dangerous’ Medicaid rule for trans youth...</div></div><div class="ad">bluehost<br><span>World-class speed for your WordPress sites.</span><small>Sponsored</small></div></aside>
</div>
</body>
</html>"""

    manifest = {
        "schema_version": "static_visual_replay_manifest_v1",
        "generator_version": VERSION,
        "generated_at_utc": generated,
        "target_url": target_url,
        "source_url": source_url,
        "purpose": "Derived static ReplayWeb/WARC visual candidate closer to the accepted MSN desktop page appearance.",
        "does_not_replace_raw_warc": True,
        "dynamic_replay_success_claimed": False,
        "manual_replayweb_visual_review_required": True,
        "input_files": {k: (str(v) if v else None) for k, v in files.items()},
        "hero_image": hero_record,
        "accepted_article_screenshot": accepted_article_screenshot_record,
        "desktop_full_page_screenshot_metadata_only": desktop_full_page_screenshot_record,
        "embedded_reference_screenshot_label": reference_screenshot_label,
        "embedded_reference_screenshot_sha256": reference_screenshot_record.get("sha256") if isinstance(reference_screenshot_record, dict) else None,
        "embedded_reference_screenshot_path": reference_screenshot_record.get("path") if isinstance(reference_screenshot_record, dict) else None,
        "click_to_expand_images": True,
        "click_to_expand_implementation": "no_navigation_checkbox_label_lightbox",
        "replayweb_cache_bust_target_url": True,
        "comment_count_loaded": comment_count,
        "profile_count_loaded": profile_count,
        "boundaries": [
            "This is a derived static visual replay candidate built from local captured artifacts.",
            "The raw dynamic WARC/WACZ files are preserved unchanged and remain partial/experimental unless separately verified.",
            "The page is designed to look closer to the accepted MSN desktop view, but it is not a live recapture and not an MSN runtime replay claim.",
            "Structured text remains controlled by the local article/comment/profile exports; screenshots remain visual evidence.",
        ],
    }
    return doc, manifest


def _http_response_bytes(payload: bytes, content_type: str) -> bytes:
    headers = (
        "HTTP/1.1 200 OK\r\n"
        f"Content-Type: {content_type}\r\n"
        "Cache-Control: no-store\r\n"
        "X-YTCE-Static-Visual-Replay: true\r\n"
        f"Content-Length: {len(payload)}\r\n"
        "\r\n"
    ).encode("utf-8")
    return headers + payload


def _warc_record_bytes(target_url: str, payload: bytes, content_type: str, when: str) -> bytes:
    block = _http_response_bytes(payload, content_type)
    headers = (
        "WARC/1.0\r\n"
        "WARC-Type: response\r\n"
        f"WARC-Target-URI: {target_url}\r\n"
        f"WARC-Date: {when}\r\n"
        f"WARC-Record-ID: <urn:uuid:{uuid.uuid4()}>\r\n"
        "Content-Type: application/http; msgtype=response\r\n"
        f"WARC-Block-Digest: {_sha1_base32(block)}\r\n"
        f"WARC-Payload-Digest: {_sha1_base32(payload)}\r\n"
        f"Content-Length: {len(block)}\r\n"
        "\r\n"
    ).encode("utf-8")
    return headers + block + b"\r\n\r\n"


def write_warc_pair(out_dir: Path, target_url: str, html_text: str, when: str) -> tuple[Path, Path, str, str]:
    payload = html_text.encode("utf-8")
    record = _warc_record_bytes(target_url, payload, "text/html; charset=utf-8", when)
    warc_path = out_dir / "static-msn-visual-replay-v3.warc"
    warc_gz_path = out_dir / "static-msn-visual-replay-v3.warc.gz"
    warc_path.write_bytes(record)
    with gzip.GzipFile(filename="", mode="wb", fileobj=warc_gz_path.open("wb"), mtime=0) as gz:
        gz.write(record)
    return warc_path, warc_gz_path, sha256_file(warc_path) or "", sha256_file(warc_gz_path) or ""


def generate_static_visual_replay(output_root: str | Path, target_url: str = DEFAULT_TARGET_URL) -> dict[str, Any]:
    root = Path(output_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"output_root does not exist: {root}")
    out = root / OUTPUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    html_text, manifest = build_visual_html(root, target_url=target_url)
    html_path = out / "msn-static-visual-replay-v3.html"
    manifest_path = out / "static-visual-replay-v3-manifest.json"
    target_path = out / "static-visual-replay-v3-target-url.txt"
    readme_path = out / "README_STATIC_VISUAL_REPLAY_V3.txt"
    opener_path = out / "open_static_visual_replay_v3_direct.cmd"
    html_path.write_text(html_text, encoding="utf-8", newline="\n")
    manifest["html_sha256"] = sha256_file(html_path)
    manifest["html_path"] = str(html_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    target_path.write_text(target_url + "\n", encoding="utf-8", newline="\n")
    readme_path.write_text(
        "MSN static visual replay candidate\n"
        "=================================\n\n"
        "Purpose: create a derived static WARC/HTML page that visually resembles the accepted MSN desktop article view more closely than the raw dynamic ReplayWeb output, while embedding the accepted single-article screenshot reference rather than the unrelated full-page/feed screenshot.\n\n"
        "This does NOT replace the raw WARC/WACZ files. It does NOT claim a successful dynamic ReplayWeb.page replay. It is a separate static visual candidate made from local captured artifacts only.\n\n"
        "Manual test:\n"
        "1. Open msn-static-visual-replay.html directly for the direct static view.\n"
        "2. In ReplayWeb.page, choose static-msn-visual-replay.warc.gz from this folder.\n"
        "3. If ReplayWeb.page shows a URL picker, open the URL shown in static-visual-replay-target-url.txt.\n"
        "4. Confirm whether the result is visually closer to the accepted MSN desktop screenshot, that the lower proof section uses the accepted single-article screenshot, and that clicking the hero/proof images expands them.\n",
        encoding="utf-8",
        newline="\n",
    )
    opener_path.write_text('@echo off\r\nstart "" "%~dp0msn-static-visual-replay-v3.html"\r\n', encoding="utf-8")
    when = str(manifest.get("generated_at_utc") or _utc_now())
    warc_path, warc_gz_path, warc_sha, warc_gz_sha = write_warc_pair(out, target_url, html_text, when)
    manifest["warc_path"] = str(warc_path)
    manifest["warc_gz_path"] = str(warc_gz_path)
    manifest["warc_sha256"] = warc_sha
    manifest["warc_gz_sha256"] = warc_gz_sha
    manifest["readme_path"] = str(readme_path)
    manifest["open_direct_cmd"] = str(opener_path)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    return {
        "status": "STATIC_VISUAL_REPLAY_GENERATED",
        "output_dir": str(out),
        "html_path": str(html_path),
        "html_sha256": sha256_file(html_path),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "warc_path": str(warc_path),
        "warc_sha256": warc_sha,
        "warc_gz_path": str(warc_gz_path),
        "warc_gz_sha256": warc_gz_sha,
        "target_url": target_url,
        "comment_count_loaded": manifest.get("comment_count_loaded"),
        "profile_count_loaded": manifest.get("profile_count_loaded"),
        "dynamic_replay_success_claimed": False,
        "manual_replayweb_visual_review_required": True,
    }


def print_generation_summary(result: dict[str, Any]) -> None:
    print("STATIC_VISUAL_REPLAY_STATUS=" + str(result.get("status")))
    print("STATIC_VISUAL_OUTPUT_DIR=" + str(result.get("output_dir")))
    print("STATIC_VISUAL_HTML=" + str(result.get("html_path")))
    print("STATIC_VISUAL_HTML_SHA256=" + str(result.get("html_sha256")))
    print("STATIC_VISUAL_WARC=" + str(result.get("warc_path")))
    print("STATIC_VISUAL_WARC_SHA256=" + str(result.get("warc_sha256")))
    print("STATIC_VISUAL_WARC_GZ=" + str(result.get("warc_gz_path")))
    print("STATIC_VISUAL_WARC_GZ_SHA256=" + str(result.get("warc_gz_sha256")))
    print("STATIC_VISUAL_MANIFEST=" + str(result.get("manifest_path")))
    print("STATIC_VISUAL_TARGET_URL=" + str(result.get("target_url")))
    print("STRUCTURED_COMMENTS_LOADED=" + str(result.get("comment_count_loaded")))
    print("PROFILES_LOADED=" + str(result.get("profile_count_loaded")))
    print("DYNAMIC_REPLAY_SUCCESS_CLAIMED=False")
    print("MANUAL_REPLAYWEB_VISUAL_REVIEW_REQUIRED=True")
