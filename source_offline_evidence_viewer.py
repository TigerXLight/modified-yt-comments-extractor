from __future__ import annotations

import datetime as _dt
import hashlib
import html
import json
from pathlib import Path
from typing import Any, Iterable

VIEWER_VERSION = "2026-08-12.offline-backup-viewer.v4"
TEXT_MAX_CHARS = 120_000
COMMENTS_MAX = 500
MSN_PROFILE_BASE = "https://www.msn.com/en-gb/community/profile/"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest().upper()
    except Exception:
        return None


def read_text(path: Path | None, max_chars: int = TEXT_MAX_CHARS) -> str:
    if not path or not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n[TRUNCATED at {max_chars} characters; open the source file for full text.]"
    return text


def read_json(path: Path | None) -> Any:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def file_record(path: Path, root: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "path": str(path),
        "relative_path": relpath(path, root),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256_file(path) if path.exists() else None,
    }


def first_existing(root: Path, candidates: Iterable[str]) -> Path | None:
    for c in candidates:
        p = root / c
        if p.exists():
            return p
    return None


def find_first(root: Path, names: Iterable[str]) -> Path | None:
    wanted = set(names)
    for p in root.rglob("*"):
        if p.is_file() and p.name in wanted:
            return p
    return None


def find_all(root: Path, patterns: Iterable[str], limit: int = 300) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for p in root.rglob(pattern):
            if p.is_file() and p not in seen:
                seen.add(p)
                out.append(p)
                if len(out) >= limit:
                    return out
    return out


def detect_output_files(output_root: Path) -> dict[str, Path | None]:
    return {
        "article_screenshot": first_existing(output_root, [
            "screenshots/android_article_MAIN_SINGLE_reference_style.png",
            "android_article_MAIN_SINGLE_reference_style.png",
        ]) or find_first(output_root, ["android_article_MAIN_SINGLE_reference_style.png"]),
        "comments_screenshot": first_existing(output_root, [
            "screenshots/android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png",
            "android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png",
        ]) or find_first(output_root, ["android_comments_all_expanded_SINGLE_INTERNAL_STITCH.png"]),
        "comments_json": first_existing(output_root, ["comments.json"]),
        "comments_txt": first_existing(output_root, ["comments.txt"]),
        "comments_html": first_existing(output_root, ["comments.html"]),
        "profiles_json": first_existing(output_root, ["profiles.json", "comments-profiles.json"]),
        "profiles_txt": first_existing(output_root, ["profiles.txt", "comments-profiles.txt"]),
        "viewer_input_receipt_json": first_existing(output_root, ["offline_backup_viewer_input_receipt.json"]),
        "source_role_claims_json": first_existing(output_root, ["source-role-claims.json"]),
        "media_source_chain_json": first_existing(output_root, ["media-source-chain.json"]),
        "memento_json": first_existing(output_root, ["memento_archive_discovery.json"]),
        "memento_txt": first_existing(output_root, ["memento_archive_discovery.txt"]),
        "warcreate_json": first_existing(output_root, ["warcreate_style_interaction_metadata.json"]),
        "warcreate_txt": first_existing(output_root, ["warcreate_style_interaction_metadata.txt"]),
        "replay_status_json": first_existing(output_root, ["archive_replay_status.json"]),
        "replay_status_txt": first_existing(output_root, ["archive_replay_status.txt"]),
        "recompression_json": first_existing(output_root, ["warc_pywb_recompression_report.json"]),
        "recompression_txt": first_existing(output_root, ["warc_pywb_recompression_report.txt"]),
        "rendered_html": first_existing(output_root, ["live_capture/rendered-page.html", "rendered-page.html"]),
        "warc_gz": first_existing(output_root, ["live_capture/rendered-page.warc.gz", "rendered-page.warc.gz"]),
        "pywb_indexable_warc_gz": first_existing(output_root, ["live_capture/rendered-page.pywb-indexable.warc.gz", "rendered-page.pywb-indexable.warc.gz"]),
        "wacz": first_existing(output_root, ["live_capture/archive.viewable-live-capture.wacz", "archive.viewable-live-capture.wacz"]),
        "local_viewer": first_existing(output_root, ["live_capture/local_viewer/local-viewer-index.html", "local_viewer/local-viewer-index.html"]),
        "article_txt_android": first_existing(output_root, ["live_capture/browser_capture/android_mobile_chromium/article.txt"]),
        "article_txt_desktop": first_existing(output_root, ["live_capture/browser_capture/desktop_chromium/article.txt"]),
    }


def _top_level_comments(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("comments", "items", "rows", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return val
    return []


def load_comments(path: Path | None) -> list[dict[str, Any]]:
    """Return parent comments and nested replies as a single ordered viewer list."""
    data = read_json(path)
    top = _top_level_comments(data)
    out: list[dict[str, Any]] = []

    def walk(item: Any, depth: int = 0, parent_human_id: str = "") -> None:
        if len(out) >= COMMENTS_MAX:
            return
        if not isinstance(item, dict):
            out.append({
                "text": str(item),
                "_viewer_depth": depth,
                "_viewer_parent_human_id": parent_human_id,
            })
            return
        row = dict(item)
        replies = row.pop("replies", None)
        row["_viewer_depth"] = depth
        row["_viewer_parent_human_id"] = parent_human_id
        out.append(row)
        this_id = str(item.get("human_id") or item.get("comment_id") or item.get("id") or "")
        if isinstance(replies, list):
            for child in replies:
                if len(out) >= COMMENTS_MAX:
                    break
                walk(child, depth + 1, this_id)

    for item in top:
        if len(out) >= COMMENTS_MAX:
            break
        walk(item)
    return out


def load_profiles(path: Path | None) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, list):
        return [dict(x) for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("profiles", "items", "rows", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return [dict(x) for x in val if isinstance(x, dict)]
    return []


def flatten_comment_text(item: Any) -> dict[str, str]:
    if not isinstance(item, dict):
        return {"author": "", "text": str(item), "meta": "", "depth": "0"}
    author = ""
    for key in ("author", "display_name", "user_name", "username", "profile_name", "name"):
        val = item.get(key)
        if val:
            author = str(val)
            break
    text = ""
    for key in ("text", "comment", "body", "content", "comment_text", "message"):
        val = item.get(key)
        if val:
            text = str(val)
            break
    if not text:
        text = json.dumps(item, ensure_ascii=False)[:2000]
    meta_bits = []
    for key in (
        "human_id", "type", "date", "created_at", "timestamp", "time", "likes",
        "reaction_count", "reply_count", "parent_human_id", "parent_id", "comment_id", "id",
    ):
        if key in item and item.get(key) not in (None, ""):
            meta_bits.append(f"{key}={item.get(key)}")
    parent = item.get("_viewer_parent_human_id")
    if parent and "parent_human_id" not in item:
        meta_bits.append(f"parent={parent}")
    return {
        "author": author,
        "text": text,
        "meta": "; ".join(meta_bits),
        "depth": str(int(item.get("_viewer_depth") or 0)),
    }


def html_escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def json_summary(data: Any, max_chars: int = 60_000) -> str:
    if data is None:
        return ""
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... [TRUNCATED at {max_chars} characters]"
    return text


def _profile_url(profile: dict[str, Any]) -> tuple[str, str]:
    canonical = str(profile.get("canonical_url") or "").strip()
    if canonical:
        return canonical, "captured"
    raw_urls = profile.get("raw_urls")
    if isinstance(raw_urls, list):
        for value in raw_urls:
            value = str(value or "").strip()
            if value:
                return value, "captured_raw"
    for key in ("author_profile_url", "profile_url"):
        value = str(profile.get(key) or "").strip()
        if value:
            return value, "captured"
    cid = str(profile.get("profile_cid") or profile.get("author_profile_cid") or "").strip()
    if cid.startswith("cid-"):
        return MSN_PROFILE_BASE + cid, "reconstructed_from_stored_cid"
    return "", "not_available"


def _profile_value(profile: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = profile.get(key)
        if value not in (None, ""):
            return str(value)
    return "Not captured"


def render_profiles_table(profiles: list[dict[str, Any]]) -> tuple[str, int]:
    if not profiles:
        return "<p class='missing'>No profile records loaded from profiles.json.</p>", 0
    rows: list[str] = []
    stats_found = 0
    for p in profiles:
        comments = _profile_value(p, "account_comments", "comments_count", "comment_count")
        likes = _profile_value(p, "account_likes", "likes_count", "like_count")
        followers = _profile_value(p, "account_followers", "followers_count", "follower_count")
        if "Not captured" not in (comments, likes, followers):
            stats_found += 1
        url, url_basis = _profile_url(p)
        url_html = (
            f"<a href='{html_escape(url)}'>{html_escape(url)}</a>"
            if url
            else "<span class='missing'>Not captured</span>"
        )
        status = str(p.get("profile_stats_status") or "unknown")
        method = str(p.get("profile_stats_method") or "")
        status_text = status + (f" / {method}" if method else "")
        if url_basis == "reconstructed_from_stored_cid":
            status_text += " / URL reconstructed from stored CID"
        rows.append(
            "<tr>"
            f"<td>{html_escape(p.get('author') or '')}</td>"
            f"<td>{html_escape(comments)}</td>"
            f"<td>{html_escape(likes)}</td>"
            f"<td>{html_escape(followers)}</td>"
            f"<td class='url-cell'>{url_html}</td>"
            f"<td>{html_escape(status_text)}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap'><table><thead><tr>"
        "<th>Author</th><th>Comments</th><th>Likes</th><th>Followers</th>"
        "<th>MSN community profile</th><th>Capture status</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>",
        stats_found,
    )


def render_file_link(record: dict[str, Any]) -> str:
    if not record.get("exists"):
        return f"<li><span class='missing'>MISSING</span> {html_escape(record.get('role'))}</li>"
    rp = html_escape(record.get("relative_path"))
    role = html_escape(record.get("role"))
    size = html_escape(record.get("size_bytes"))
    sha = html_escape(record.get("sha256"))
    return f"<li><a href='{rp}'>{role}</a> <span class='muted'>({size} bytes, SHA256 {sha})</span></li>"


def build_manifest(output_root: Path) -> dict[str, Any]:
    output_root = output_root.resolve()
    files = detect_output_files(output_root)
    records = {k: file_record(v, output_root, k) if v else {"role": k, "exists": False} for k, v in files.items()}
    extra_records = []
    existing_rps = {rec.get("relative_path") for rec in records.values() if isinstance(rec, dict)}
    for p in find_all(output_root, ["*.warc", "*.warc.gz", "*.wacz", "*.html", "*.json", "*.txt", "*.png", "*.jpg", "*.jpeg"], limit=300):
        rp = relpath(p, output_root)
        if rp in existing_rps:
            continue
        suffix = p.suffix.lower()
        role = "artifact"
        if p.name.endswith(".warc.gz") or suffix in {".warc", ".wacz"}:
            role = "archive_or_replay_artifact"
        elif suffix in {".png", ".jpg", ".jpeg"}:
            role = "image_or_screenshot"
        elif suffix == ".json":
            role = "json_metadata_or_export"
        elif suffix in {".txt", ".html"}:
            role = "text_or_html_export"
        extra_records.append(file_record(p, output_root, role))
    comments = load_comments(files.get("comments_json"))
    profiles = load_profiles(files.get("profiles_json"))
    memento = read_json(files.get("memento_json"))
    replay = read_json(files.get("replay_status_json"))
    recompression = read_json(files.get("recompression_json"))
    viewer_inputs = read_json(files.get("viewer_input_receipt_json"))
    stats_found = 0
    for p in profiles:
        if all(str(p.get(k) or "").strip() for k in ("account_comments", "account_likes", "account_followers")):
            stats_found += 1
    return {
        "viewer_version": VIEWER_VERSION,
        "generated_at_utc": _utc_now(),
        "output_root": str(output_root),
        "files": records,
        "extra_artifacts": extra_records,
        "comment_count_loaded": len(comments),
        "profile_count_loaded": len(profiles),
        "profile_stats_found_count": stats_found,
        "viewer_input_receipt": viewer_inputs,
        "memento_status": (memento or {}).get("status") if isinstance(memento, dict) else None,
        "memento_count": (memento or {}).get("memento_count") if isinstance(memento, dict) else None,
        "first_memento": (memento or {}).get("first_memento") if isinstance(memento, dict) else None,
        "latest_memento": (memento or {}).get("latest_memento") if isinstance(memento, dict) else None,
        "replay_status": replay,
        "recompression_report": recompression,
        "boundaries": [
            "This offline viewer is the human-readable static evidence backup.",
            "Structured comments text is canonical. Comment screenshots are visual evidence only.",
            "The viewer does not claim WACZ, WARC, ReplayWeb.page, or pywb visual replay success.",
            "WARC/WACZ/pywb artifacts remain preserved and hashed as partial/experimental archive-replay candidates.",
            "Profile counts are shown only when captured; missing values are explicitly marked Not captured.",
            "A community profile URL reconstructed from a stored MSN CID is labelled as reconstructed and is not a live-verification claim.",
        ],
    }


def build_viewer_html(output_root: Path, manifest: dict[str, Any]) -> str:
    output_root = output_root.resolve()
    files = detect_output_files(output_root)
    comments = load_comments(files.get("comments_json"))
    profiles = load_profiles(files.get("profiles_json"))
    memento = read_json(files.get("memento_json"))
    replay = read_json(files.get("replay_status_json"))
    recompression = read_json(files.get("recompression_json"))
    source_role = read_json(files.get("source_role_claims_json"))
    media_chain = read_json(files.get("media_source_chain_json"))
    viewer_inputs = read_json(files.get("viewer_input_receipt_json"))

    article_text = ""
    for p in (files.get("article_txt_android"), files.get("article_txt_desktop")):
        t = read_text(p, 40_000)
        if t.strip():
            article_text = t
            break
    if not article_text:
        article_text = read_text(files.get("rendered_html"), 50_000)

    records = [r for r in manifest["files"].values() if isinstance(r, dict)] + manifest.get("extra_artifacts", [])
    seen: set[str] = set()
    unique_records = []
    for r in records:
        rp = r.get("relative_path")
        if not rp or rp in seen:
            continue
        seen.add(rp)
        unique_records.append(r)

    article_img = manifest["files"].get("article_screenshot", {})
    comments_img = manifest["files"].get("comments_screenshot", {})
    article_img_src = html_escape(article_img.get("relative_path")) if article_img.get("exists") else ""
    comments_img_src = html_escape(comments_img.get("relative_path")) if comments_img.get("exists") else ""

    memento_first = manifest.get("first_memento") or {}
    memento_latest = manifest.get("latest_memento") or {}
    if not isinstance(memento_first, dict):
        memento_first = {}
    if not isinstance(memento_latest, dict):
        memento_latest = {}

    comment_cards = []
    for i, c in enumerate(comments[:COMMENTS_MAX], 1):
        fc = flatten_comment_text(c)
        depth = max(0, min(int(fc["depth"]), 8))
        comment_cards.append(
            "<article class='comment' style='margin-left:{}px'><div class='comment-head'><h4>#{} {}</h4>"
            "<span>{}</span></div><pre class='comment-text'>{}</pre></article>".format(
                depth * 22, i, html_escape(fc["author"]), html_escape(fc["meta"]), html_escape(fc["text"])
            )
        )
    if not comment_cards:
        comment_cards.append("<p class='missing'>No comments loaded from comments.json.</p>")

    profiles_html, profile_stats_found = render_profiles_table(profiles)
    replay_txt = read_text(files.get("replay_status_txt"), 40_000)
    memento_txt = read_text(files.get("memento_txt"), 40_000)
    warcreate_txt = read_text(files.get("warcreate_txt"), 50_000)
    artifacts_html = "".join(render_file_link(r) for r in unique_records if r.get("exists"))
    boundaries_html = "".join("<li>" + html_escape(x) + "</li>" for x in manifest.get("boundaries", []))
    comments_html = "".join(comment_cards)
    article_img_html = f"<img src='{article_img_src}' alt='Accepted article screenshot'>" if article_img_src else "<p class='missing'>Missing article screenshot.</p>"
    comments_img_html = f"<img src='{comments_img_src}' alt='Accepted comments screenshot'>" if comments_img_src else "<p class='missing'>Missing comments screenshot.</p>"

    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MSN Offline Evidence Backup Viewer</title>
<style>
:root { color-scheme: light dark; --bg:#111827; --panel:#1f2937; --text:#f9fafb; --muted:#9ca3af; --border:#374151; --accent:#f59e0b; --good:#10b981; --bad:#ef4444; }
@media (prefers-color-scheme: light) { :root { --bg:#f8fafc; --panel:#ffffff; --text:#111827; --muted:#6b7280; --border:#d1d5db; } }
body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:var(--bg); color:var(--text); line-height:1.45; }
header { padding:24px; border-bottom:1px solid var(--border); background:var(--panel); position:sticky; top:0; z-index:10; }
main { padding:24px; max-width:1280px; margin:auto; }
h1,h2,h3 { margin-top:0; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:16px; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:16px; overflow:auto; margin-bottom:16px; }
.image-card img { max-width:100%; border:1px solid var(--border); border-radius:10px; background:#000; }
.muted { color:var(--muted); font-size:0.92rem; }
.ok { color:var(--good); font-weight:700; } .missing { color:var(--bad); font-weight:700; }
pre { white-space:pre-wrap; word-break:break-word; background:rgba(127,127,127,.12); padding:12px; border-radius:10px; max-height:520px; overflow:auto; }
code { background:rgba(127,127,127,.15); padding:1px 4px; border-radius:4px; }
a { color:var(--accent); }
.comment { border-top:1px solid var(--border); padding:12px 0; }
.comment-head { display:flex; gap:16px; align-items:baseline; justify-content:space-between; flex-wrap:wrap; }
.comment h4 { margin:0 0 6px; }
.comment-text { max-height:none; margin:6px 0 0; }
ul { padding-left:20px; }
nav a { margin-right:12px; white-space:nowrap; }
.notice { border-left:4px solid var(--accent); padding:10px 12px; background:rgba(127,127,127,.10); border-radius:8px; }
.table-wrap { overflow:auto; }
table { width:100%; border-collapse:collapse; min-width:900px; }
th,td { text-align:left; vertical-align:top; padding:9px 10px; border-bottom:1px solid var(--border); }
th { position:sticky; top:0; background:var(--panel); }
.url-cell { word-break:break-all; }
</style>
</head>
<body>
<header>
<h1>MSN Offline Evidence Backup Viewer</h1>
<p class="muted">Generated __GENERATED__. Stable human-readable backup. WARC/WACZ/ReplayWeb.page/pywb remain partial or experimental replay artifacts unless separately verified.</p>
<nav><a href="#screenshots">Screenshots</a><a href="#comments">Comments</a><a href="#profiles">Profiles</a><a href="#time">Memento time data</a><a href="#replay">Replay status</a><a href="#artifacts">Artifacts</a></nav>
</header>
<main>
<section class="grid">
<article class="card"><h2>Evidence status</h2><p>Structured comments loaded: <strong>__COMMENT_COUNT__</strong></p><p>Profiles loaded: <strong>__PROFILE_COUNT__</strong></p><p>Profiles with all three account stats captured: <strong>__PROFILE_STATS_FOUND__</strong></p><p>Memento status: <strong>__MEMENTO_STATUS__</strong></p><p>Memento count: <strong>__MEMENTO_COUNT__</strong></p><p>Output root: <code>__OUTPUT_ROOT__</code></p></article>
<article class="card"><h2>Boundary</h2><ul>__BOUNDARIES__</ul></article>
</section>
<section id="screenshots"><h2>Accepted primary screenshots</h2><p class="notice"><strong>Visual evidence only.</strong> The structured article/comments exports control readable text where a screenshot wraps, clips, overlaps, or visually distorts content.</p><div class="grid"><article class="card image-card"><h3>Article screenshot</h3>__ARTICLE_IMG__<p class="muted">SHA256 __ARTICLE_SHA__</p></article><article class="card image-card"><h3>Comments screenshot</h3>__COMMENTS_IMG__<p class="muted">SHA256 __COMMENTS_SHA__</p></article></div></section>
<section id="article" class="card"><h2>Article/text backup</h2><pre>__ARTICLE_TEXT__</pre></section>
<section id="comments" class="card"><h2>Structured comments backup — canonical text</h2><p class="notice">This section is canonical for comment wording. It is built from the structured comments export, including nested replies; the stitched screenshot above is supporting visual evidence only.</p>__COMMENTS__</section>
<section id="profiles" class="card"><h2>Profiles backup — V35-style fields</h2><p class="muted">Fields: author, comments count, likes count, followers count, and MSN community profile URL. Missing statistics are shown as “Not captured”; they are not invented. A URL reconstructed from a stored profile CID is labelled in the status column.</p>__PROFILES_TABLE__</section>
<section id="time" class="card"><h2>Memento/CDX/TimeMap date tracking</h2><p>First memento: <strong>__FIRST_TS__</strong> <a href="__FIRST_URL__">__FIRST_URL__</a></p><p>Latest memento: <strong>__LATEST_TS__</strong> <a href="__LATEST_URL__">__LATEST_URL__</a></p><pre>__MEMENTO_TEXT__</pre></section>
<section id="replay" class="card"><h2>Partial / experimental archive-replay artifacts</h2><p class="notice">WARC, WACZ, ReplayWeb.page and pywb are preserved for archival/replay work, but this viewer does not promote them to the primary backup and does not claim successful visual replay unless the separate status evidence says so.</p><pre>__REPLAY_TEXT__</pre><h3>pywb recompression/indexability</h3><pre>__RECOMPRESSION__</pre></section>
<section class="card"><h2>Accepted-input receipt</h2><pre>__VIEWER_INPUTS__</pre></section>
<section class="card"><h2>WARCreate-style interaction metadata</h2><pre>__WARCREATE__</pre></section>
<section class="grid"><article class="card"><h2>Source-role claims</h2><pre>__SOURCE_ROLE__</pre></article><article class="card"><h2>Media source chain</h2><pre>__MEDIA_CHAIN__</pre></article></section>
<section id="artifacts" class="card"><h2>Files and preserved artifacts</h2><ul>__ARTIFACTS__</ul></section>
</main>
</body>
</html>""".replace("__GENERATED__", html_escape(manifest.get("generated_at_utc"))) \
        .replace("__COMMENT_COUNT__", html_escape(manifest.get("comment_count_loaded"))) \
        .replace("__PROFILE_COUNT__", html_escape(manifest.get("profile_count_loaded"))) \
        .replace("__PROFILE_STATS_FOUND__", html_escape(profile_stats_found)) \
        .replace("__MEMENTO_STATUS__", html_escape(manifest.get("memento_status"))) \
        .replace("__MEMENTO_COUNT__", html_escape(manifest.get("memento_count"))) \
        .replace("__OUTPUT_ROOT__", html_escape(output_root)) \
        .replace("__BOUNDARIES__", boundaries_html) \
        .replace("__ARTICLE_IMG__", article_img_html) \
        .replace("__COMMENTS_IMG__", comments_img_html) \
        .replace("__ARTICLE_SHA__", html_escape(article_img.get("sha256"))) \
        .replace("__COMMENTS_SHA__", html_escape(comments_img.get("sha256"))) \
        .replace("__ARTICLE_TEXT__", html_escape(article_text)) \
        .replace("__COMMENTS__", comments_html) \
        .replace("__PROFILES_TABLE__", profiles_html) \
        .replace("__FIRST_TS__", html_escape(memento_first.get("timestamp"))) \
        .replace("__FIRST_URL__", html_escape(memento_first.get("archive_url", ""))) \
        .replace("__LATEST_TS__", html_escape(memento_latest.get("timestamp"))) \
        .replace("__LATEST_URL__", html_escape(memento_latest.get("archive_url", ""))) \
        .replace("__MEMENTO_TEXT__", html_escape(memento_txt or json_summary(memento))) \
        .replace("__REPLAY_TEXT__", html_escape(replay_txt or json_summary(replay))) \
        .replace("__RECOMPRESSION__", html_escape(json_summary(recompression))) \
        .replace("__VIEWER_INPUTS__", html_escape(json_summary(viewer_inputs))) \
        .replace("__WARCREATE__", html_escape(warcreate_txt)) \
        .replace("__SOURCE_ROLE__", html_escape(json_summary(source_role))) \
        .replace("__MEDIA_CHAIN__", html_escape(json_summary(media_chain))) \
        .replace("__ARTIFACTS__", artifacts_html)


def generate_offline_backup_viewer(output_root: str | Path) -> dict[str, Any]:
    root = Path(output_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"output_root does not exist: {root}")
    manifest = build_manifest(root)
    viewer_html = build_viewer_html(root, manifest)
    manifest_path = root / "offline_backup_manifest.json"
    viewer_path = root / "offline_backup_viewer.html"
    opener_path = root / "open_offline_backup_viewer.cmd"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    viewer_path.write_text(viewer_html, encoding="utf-8")
    opener_path.write_text('@echo off\r\nstart "" "%~dp0offline_backup_viewer.html"\r\n', encoding="utf-8")
    return {
        "offline_backup_viewer_html": str(viewer_path),
        "offline_backup_manifest_json": str(manifest_path),
        "open_offline_backup_viewer_cmd": str(opener_path),
        "viewer_sha256": sha256_file(viewer_path),
        "manifest_sha256": sha256_file(manifest_path),
        "status": "OFFLINE_BACKUP_VIEWER_GENERATED",
    }


def print_generation_summary(result: dict[str, Any]) -> None:
    print("OFFLINE_BACKUP_VIEWER_HTML:", result.get("offline_backup_viewer_html"))
    print("OFFLINE_BACKUP_MANIFEST_JSON:", result.get("offline_backup_manifest_json"))
    print("OPEN_OFFLINE_BACKUP_VIEWER_CMD:", result.get("open_offline_backup_viewer_cmd"))
    print("OFFLINE_BACKUP_VIEWER_SHA256:", result.get("viewer_sha256"))
    print("OFFLINE_BACKUP_MANIFEST_SHA256:", result.get("manifest_sha256"))
    print("OFFLINE_BACKUP_VIEWER_STATUS:", result.get("status"))
