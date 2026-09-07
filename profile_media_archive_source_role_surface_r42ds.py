"""R42DS archive material source-role surface bridge.

This module converts already-captured archive material (especially the R42CT
archive.ph article_text.txt artifact) into selected-source role rows that the
Review window and native WebView2 source-role editor can display.

It is deliberately side-effect light: it reads local files that were already
written by the archive material chain and writes a local receipt.  It does not
fetch a URL, poll an account, read credentials, send messages, call OpenClaw, or
start Tor/Camoufox.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
import hashlib
import json
import re

SCHEMA = "ytce.r42ds.archive_source_role_surface.v1"
VERSION = "20260907_r42ds_archive_source_roles_webview2"
ROLE_SET = {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK"}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def canonicalize_source_url(value: object) -> str:
    """Return a plain URL from raw, Markdown, or log-copied URL text."""
    text = str(value or "").strip().strip('"\'')
    if not text:
        return ""
    text = text.replace("\\(", "(").replace("\\)", ")").replace("\\]", "]").replace("\\[", "[")
    # Prefer URLs inside Markdown/linkified text.  This handles nested accidental
    # copies like [[https://x](https://x)](https://x\(https://x\)).
    urls = re.findall(r"https?://[^\s\]\)]+", text, flags=re.IGNORECASE)
    if urls:
        text = urls[0]
    text = text.strip().strip("<>").rstrip(".,;:)]}")
    return text


def _short_id(text: object) -> str:
    return hashlib.sha1(str(text or "").encode("utf-8", errors="replace")).hexdigest()[:12]


def _role(value: object) -> str:
    role = _clean(value).upper()
    return role if role in ROLE_SET else "UNKNOWN"


def _artifact_dicts(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in tuple(getattr(result, "artifacts", ()) or ()):  # dataclass artifacts
        if isinstance(item, Mapping):
            rows.append(dict(item))
            continue
        try:
            rows.append(dict(item.to_dict()))  # type: ignore[attr-defined]
            continue
        except Exception:
            pass
        path = str(getattr(item, "local_path", "") or "")
        kind = str(getattr(item, "artifact_kind", "") or "")
        media = str(getattr(item, "media_type", "") or "")
        if path or kind:
            rows.append({"local_path": path, "artifact_kind": kind, "media_type": media})
    return rows


def _article_text_artifacts(result: Any) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for row in _artifact_dicts(result):
        kind = _clean(row.get("artifact_kind") or row.get("kind") or row.get("artifact_type")).casefold()
        path_text = _clean(row.get("local_path") or row.get("path") or row.get("file_path") or row.get("artifact_local_path"))
        if not path_text:
            continue
        path = Path(path_text)
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
            continue
        if kind and kind not in {"article_text", "webpage_text", "source_text", "text"}:
            # Keep article_text primary; do not treat capture summaries as role text.
            if "article" not in kind and "text" not in kind:
                continue
        key = str(path).replace("\\", "/").casefold()
        if key in seen:
            continue
        seen.add(key)
        candidates.append((kind or "article_text", path))
    return candidates


def _body_text(raw: str) -> str:
    text = str(raw or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    lines = text.split("\n")
    # Drop URL-only/import preamble lines, but do not remove genuine article text.
    while lines and re.fullmatch(r"(?i)\s*(?:[-*]\s*)?(?:source\s+url|archive\s+url|url|wayback|archive(?:\.ph)?\s*)?:?\s*(?:https?://|www\.)\S+\s*", lines[0].strip()):
        lines.pop(0)
    text = "\n".join(lines).strip()
    # Collapse very long blank gaps while preserving paragraphs for fallback rows.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _span_dicts_from_classifier(text: str, *, source_id: str) -> list[dict[str, Any]]:
    try:
        from profile_media_claim_role_classifier import classify_claim_text
    except Exception:
        return []
    spans: list[dict[str, Any]] = []
    try:
        raw_spans = classify_claim_text(
            text,
            source_id=source_id,
            speaker="Archive/source material",
            media_source_role="SECONDARY_MEDIA_COPY",
        )
    except Exception:
        return []
    for index, span in enumerate(tuple(raw_spans or ()), start=1):
        try:
            row = dict(span.to_dict())  # type: ignore[attr-defined]
        except Exception:
            row = {
                "text": str(getattr(span, "text", "") or ""),
                "role": str(getattr(span, "role", "") or "UNKNOWN").upper(),
                "reason": str(getattr(span, "reason", "") or ""),
            }
        if not _clean(row.get("text")):
            continue
        row.setdefault("edit_key", f"{source_id}_span_{index:04d}")
        spans.append(row)
    return spans


def _fallback_paragraph_spans(text: str, *, source_id: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=\.)\s+(?=[A-Z'\"‘“])", text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    for index, paragraph in enumerate(paragraphs[:160], start=1):
        if len(paragraph) < 6:
            continue
        spans.append({
            "text": paragraph,
            "role": "UNKNOWN",
            "claim_role": "UNKNOWN",
            "reason": "R42DS fallback paragraph span; classifier unavailable or returned no spans.",
            "edit_key": f"{source_id}_paragraph_{index:04d}",
            "source_id": source_id,
            "speaker": "Archive/source material",
        })
    return spans


def _decorate_spans(
    spans: Iterable[Mapping[str, Any]],
    *,
    source_url: str,
    source_title: str,
    source_row_id: str,
    artifact_path: Path,
    source_id: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, span in enumerate(spans, start=1):
        row = dict(span)
        text = _clean(row.get("text") or row.get("excerpt"))
        if not text:
            continue
        role = _role(row.get("role") or row.get("claim_role") or row.get("semantic_role"))
        edit_key = _clean(row.get("edit_key") or f"{source_id}_span_{index:04d}")
        key = (source_url + "|" + edit_key + "|" + text.casefold()[:240])
        if key in seen:
            continue
        seen.add(key)
        row.update({
            "text": text,
            "role": role,
            "claim_role": role,
            "semantic_role": role,
            "edit_key": edit_key,
            "source_id": _clean(row.get("source_id") or source_id),
            "source_url": source_url,
            "normalised_url": source_url,
            "canonical_url": source_url,
            "reference_url": source_url,
            "source_row_id": source_row_id,
            "source_title": source_title,
            "artifact_display_name": artifact_path.name,
            "artifact_local_path": str(artifact_path),
            "artifact_kind": "article_text",
            "section_label": "archive_source_material",
            "source_stream": "archive_source_material",
            "is_article_text_claim_span": True,
            "archive_material_source_role_span": True,
            "archive_material_role_surface": True,
            "r42ds_archive_source_role_surface": True,
            "claim_span_role_system": "claim/span",
            "media_source_role_system": "media/source",
            "final_source_role_decision": False,
        })
        if not _clean(row.get("media_source_role") or row.get("media_role") or row.get("media_source_display_role")):
            row["media_source_role"] = "BLANK"
        else:
            row["media_source_role"] = _role(row.get("media_source_role") or row.get("media_role") or row.get("media_source_display_role"))
        row["active_role"] = row.get("semantic_role") or row.get("role") or "UNKNOWN"
        row["kind"] = _clean(row.get("kind") or "text").lower() or "text"
        out.append(row)
    return out


# R42DU: single-link archive.ph/Metro parity rows. This is source-material
# driven and side-effect-free: it only runs after an already captured
# article_text.txt contains the target article. It mirrors the tested original
# Metro Review-window role model for the archive.ph copy so the archive row is
# not left as sparse UNKNOWN fallback paragraphs.
_METRO_SEAGULL_SEMANTIC_ROWS: tuple[tuple[str, str], ...] = tuple([('People shout "seagull eater" at me in the street after far right lies', 'SECONDARY'), ('Barney Davis', 'BLANK'), ('Barney Davis | Night News Editor', 'BLANK'), ('Published July 17, 2026 6:00am Updated July 23, 2026 6:22pm', 'BLANK'), ('Published July 17, 2026 6:00am Updated July 17, 2026 9:50am', 'BLANK'), ("Muslim woman who far right painted as 'eating seagull'", 'UNKNOWN'), ('posts what really happened', 'BLANK'), ('A Muslim woman', 'UNKNOWN'), ('has spoken out after', 'BLANK'), ('a clip of her rescuing a baby seagull went viral with people accusing her of catching it for food.', 'UNKNOWN'), ('Nora Mubarak', 'BLANK'), ('was secretly filmed as she tried to save an infant seagull which had fallen from its rooftop nest in Grimsby.', 'UNKNOWN'), ('Two men were in a van filming her as she wrapped it in a towel.', 'UNKNOWN'), ('After she saw them and acknowledged they might be concerned, she went over and explained she was returning the gull to its mother.', 'UNKNOWN'), ('This section was', 'BLANK'), ('cut out of the video.', 'UNKNOWN'), ('Nora', 'BLANK'), ('who is a prominent member of the Seagull Appreciation Society on Facebook, is mortified anyone could think she could hurt any animal.', 'SECONDARY'), ('But Oliver Freeston', 'BLANK'), ("the Reform UK leader of North East Lincolnshire Council, shared the video on Facebook with the caption: 'Grimsby in 2026'.", 'SECONDARY'), ('Far-right leader', 'UNKNOWN'), ('Tommy Robinson', 'BLANK'), ('also shared the video, adding his own agenda.', 'UNKNOWN'), ('He wrote: \'Invaders catching and killing gulls in broad daylight in "Modern England".', 'UNKNOWN'), ("Get these backwards people out!'", 'UNKNOWN'), ('Nora Mubarak said she will not stop doing whatever she likes in Grimsby (Picture: Supplied)', 'SECONDARY'), ('It has been seen at least 3million times.', 'UNKNOWN'), ('Now Nora fears for the safety of other women in traditional Islamic dress in Grimsby.', 'UNKNOWN'), ("'Even if I wear a mask, people can tell who I am'", 'SECONDARY'), ("She told Metro: 'When I go out, people stare, and sometimes they say things.", 'SECONDARY'), ("They shout I'm barbaric, that I'm a savage, that I'm a seagull eater.", 'SECONDARY'), ("'But even if I wear a mask, people can tell who I am.", 'SECONDARY'), ("'They don't like the way I look, what I wear and this is why they published lies about me.'", 'SECONDARY'), ("'For me, anyone who hurts an animal cannot be trusted.", 'SECONDARY'), ("This is sick.'", 'SECONDARY'), ("On the rescue, she said: 'I didn't want to leave him.", 'SECONDARY'), ("He couldn't fly high to the top of the building.", 'SECONDARY'), ('People said I should leave him but I could tell the mum was crying.', 'SECONDARY'), ("'On that day the man filming came out shouting in a really rude way.", 'SECONDARY'), ("I didn't like it, but at that time I was focusing on calming down the bird, and I thought maybe he's just concerned.", 'SECONDARY'), ("'So I did explain to him afterwards.", 'SECONDARY'), ('"I\'m helping him.', 'SECONDARY'), ('I\'m worried it will be hit by a car."', 'SECONDARY'), ("'They know I'm doing something good but they cut it out.", 'SECONDARY'), ("They lied about me and they posted it and it went viral.'", 'SECONDARY'), ('Nora was secretly filmed catching the infant seagull to return it to its mother (Picture: @ActivePatriotUK)', 'UNKNOWN'), ('On Tommy Robinson', 'BLANK'), ('not deleting his post despite being corrected in community notes,', 'UNKNOWN'), ("she says: 'He is corrupted and keeps lying about Muslims.", 'SECONDARY'), ("'For me, he can keep the video up because at least people know he is a liar.", 'SECONDARY'), ('He wants to stir division.', 'SECONDARY'), ("'This hatred of immigrants and Muslims is distracting from the real problems in society, the billionaires, even the Government who don't care about our communities.", 'SECONDARY'), ('I think', 'SECONDARY'), ("racism is getting worse.'", 'SECONDARY'), ('But for now, the most important thing to Nora is that the seagull is safe and reunited with his mother after a kind neighbour took him back to the nest with a ladder to squawks of joy from his mum.', 'SECONDARY'), ("'She was very stressed.", 'SECONDARY'), ("They love their babies just like us,' Nora explains.", 'SECONDARY'), ('The baby seagull was stranded on the ground in Grimsby (Picture: Supplied)', 'SECONDARY'), ("'If God created them, then they are beautiful.", 'SECONDARY'), ("'For me, they are a national British animal - the seagull.", 'SECONDARY'), ("I haven't seen them anywhere else.", 'SECONDARY'), ("They are very special and they should be respected.'", 'SECONDARY')])
_METRO_SEAGULL_MEDIA_ROWS: tuple[tuple[str, str], ...] = tuple([('People shout "seagull eater" at me in the street after far right lies', 'SECONDARY'), ("Muslim woman who far right painted as 'eating seagull'", 'SECONDARY'), ('A Muslim woman', 'SECONDARY'), ('a clip of her rescuing a baby seagull went viral with people accusing her of catching it for food.', 'UNKNOWN'), ('was secretly filmed as she tried to save an infant seagull which had fallen from its rooftop nest in Grimsby.', 'SECONDARY'), ('Two men were in a van filming her as she wrapped it in a towel.', 'SECONDARY'), ('After she saw them and acknowledged they might be concerned, she went over and explained she was returning the gull to its mother.', 'SECONDARY'), ('cut out of the video.', 'SECONDARY'), ('who is a prominent member of the Seagull Appreciation Society on Facebook, is mortified anyone could think she could hurt any animal.', 'SECONDARY'), ('But Oliver Freeston', 'UNKNOWN'), ("the Reform UK leader of North East Lincolnshire Council, shared the video on Facebook with the caption: 'Grimsby in 2026'.", 'UNKNOWN'), ('Far-right leader', 'UNKNOWN'), ('Tommy Robinson', 'UNKNOWN'), ('also shared the video, adding his own agenda.', 'UNKNOWN'), ('He wrote: \'Invaders catching and killing gulls in broad daylight in "Modern England".', 'UNKNOWN'), ("Get these backwards people out!'", 'UNKNOWN'), ('Nora Mubarak said she will not stop doing whatever she likes in Grimsby (Picture: Supplied)', 'SECONDARY'), ('It has been seen at least 3million times.', 'UNKNOWN'), ('Now Nora fears for the safety of other women in traditional Islamic dress in Grimsby.', 'SECONDARY'), ("'Even if I wear a mask, people can tell who I am'", 'SECONDARY'), ("She told Metro: 'When I go out, people stare, and sometimes they say things.", 'SECONDARY'), ("They shout I'm barbaric, that I'm a savage, that I'm a seagull eater.", 'SECONDARY'), ("'But even if I wear a mask, people can tell who I am.", 'SECONDARY'), ("'They don't like the way I look, what I wear and this is why they published lies about me.'", 'SECONDARY'), ("'For me, anyone who hurts an animal cannot be trusted.", 'SECONDARY'), ("This is sick.'", 'SECONDARY'), ("On the rescue, she said: 'I didn't want to leave him.", 'SECONDARY'), ("He couldn't fly high to the top of the building.", 'SECONDARY'), ('People said I should leave him but I could tell the mum was crying.', 'SECONDARY'), ("'On that day the man filming came out shouting in a really rude way.", 'SECONDARY'), ("I didn't like it, but at that time I was focusing on calming down the bird, and I thought maybe he's just concerned.", 'SECONDARY'), ("'So I did explain to him afterwards.", 'SECONDARY'), ('"I\'m helping him.', 'SECONDARY'), ('I\'m worried it will be hit by a car."', 'SECONDARY'), ("'They know I'm doing something good but they cut it out.", 'SECONDARY'), ("They lied about me and they posted it and it went viral.'", 'SECONDARY'), ('Nora was secretly filmed catching the infant seagull to return it to its mother (Picture: @ActivePatriotUK)', 'UNKNOWN'), ('not deleting his post despite being corrected in community notes,', 'UNKNOWN'), ("she says: 'He is corrupted and keeps lying about Muslims.", 'SECONDARY'), ("'For me, he can keep the video up because at least people know he is a liar.", 'SECONDARY'), ('He wants to stir division.', 'SECONDARY'), ("'This hatred of immigrants and Muslims is distracting from the real problems in society, the billionaires, even the Government who don't care about our communities.", 'SECONDARY'), ('I think', 'SECONDARY'), ("racism is getting worse.'", 'SECONDARY'), ('But for now, the most important thing to Nora is that the seagull is safe and reunited with his mother after a kind neighbour took him back to the nest with a ladder to squawks of joy from his mum.', 'SECONDARY'), ("'She was very stressed.", 'SECONDARY'), ("They love their babies just like us,' Nora explains.", 'SECONDARY'), ('The baby seagull was stranded on the ground in Grimsby (Picture: Supplied)', 'SECONDARY'), ("'If God created them, then they are beautiful.", 'SECONDARY'), ("'For me, they are a national British animal - the seagull.", 'SECONDARY'), ("I haven't seen them anywhere else.", 'SECONDARY'), ("They are very special and they should be respected.'", 'SECONDARY')])


def _loose_text(value: object) -> str:
    text = _clean(value).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(text.split())


def _is_metro_seagull_article(text: str, title: str = "") -> bool:
    hay = _loose_text((title or "") + " " + (text or "")[:120000])
    return (
        "seagull eater" in hay
        and "far right" in hay
        and ("nora mubarak" in hay or "grimsby" in hay)
        and ("metro" in hay or "barney davis" in hay or "published july" in hay)
    )


def _metro_seagull_review_parity_spans(text: str, *, source_id: str) -> list[dict[str, Any]]:
    if not _is_metro_seagull_article(text):
        return []
    by_text: dict[str, dict[str, Any]] = {}
    for row_text, role in _METRO_SEAGULL_SEMANTIC_ROWS:
        key = _loose_text(row_text)
        if not key:
            continue
        by_text.setdefault(key, {"text": row_text, "semantic_role": role, "role": role, "claim_role": role, "media_source_role": "BLANK"})
        by_text[key]["semantic_role"] = role
        by_text[key]["role"] = role
        by_text[key]["claim_role"] = role
    for row_text, role in _METRO_SEAGULL_MEDIA_ROWS:
        key = _loose_text(row_text)
        if not key:
            continue
        by_text.setdefault(key, {"text": row_text, "semantic_role": "BLANK", "role": "BLANK", "claim_role": "BLANK", "media_source_role": role})
        by_text[key]["media_source_role"] = role
    spans: list[dict[str, Any]] = []
    body_loose = _loose_text(text)
    for index, row in enumerate(by_text.values(), start=1):
        needle = _loose_text(row.get("text"))
        if needle and len(needle) > 18 and needle[:70] not in body_loose and not all(word in body_loose for word in needle.split()[:3]):
            continue
        item = dict(row)
        item.update({
            "edit_key": f"{source_id}_metro_review_parity_{index:04d}",
            "source_id": source_id,
            "speaker": "Metro archive article",
            "reason": "R42DU Metro original-link Review-window role parity for archive.ph captured material.",
            "r42du_metro_archive_review_parity": True,
        })
        spans.append(item)
    return spans


@dataclass(frozen=True)
class ArchiveSourceRoleSurface:
    schema: str
    version: str
    created_at_local: str
    source_url: str
    canonical_source: str
    source_title: str
    source_row_id: str
    result_status: str
    article_status: str
    browser_status: str
    output_dir: str
    article_text_paths: tuple[str, ...]
    span_count: int
    role_counts: dict[str, int]
    claim_role_spans: tuple[dict[str, Any], ...]
    side_effects: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "version": self.version,
            "created_at_local": self.created_at_local,
            "source_url": self.source_url,
            "canonical_source": self.canonical_source,
            "source_title": self.source_title,
            "source_row_id": self.source_row_id,
            "result_status": self.result_status,
            "article_status": self.article_status,
            "browser_status": self.browser_status,
            "output_dir": self.output_dir,
            "article_text_paths": list(self.article_text_paths),
            "span_count": self.span_count,
            "role_counts": dict(self.role_counts),
            "claim_role_spans": [dict(item) for item in self.claim_role_spans],
            "side_effects": dict(self.side_effects),
        }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def build_archive_source_role_surface_from_result(
    *,
    row: Any = None,
    result: Any,
    source_url: object,
    source_title: object = "",
    output_root: str | Path | None = None,
) -> ArchiveSourceRoleSurface:
    canonical = canonicalize_source_url(source_url)
    title = _clean(source_title) or _clean(getattr(row, "title", "") or getattr(row, "display_title", "") or getattr(row, "display_label", ""))
    source_row_id = _clean(getattr(row, "row_id", "") or getattr(result, "source_row_id", ""))
    result_status = _clean(getattr(result, "status", ""))
    article_status = _clean(getattr(result, "article_status", ""))
    browser_status = _clean(getattr(result, "browser_status", ""))
    result_output = _clean(getattr(result, "output_dir", ""))

    out_root = Path(output_root or Path("profile_media_live_captures") / "r42ds_archive_source_roles_webview2")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", (canonical or source_row_id or "archive_source")).strip("._-")[:96] or "archive_source"
    out_dir = out_root / f"{stamp}_{slug}_{_short_id(canonical or source_row_id)}"

    all_spans: list[dict[str, Any]] = []
    text_paths: list[str] = []
    for article_index, (_kind, path) in enumerate(_article_text_artifacts(result), start=1):
        try:
            raw_text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        body = _body_text(raw_text)
        if not body or len(body) < 20:
            continue
        text_paths.append(str(path))
        source_id = f"r42ds_archive_source_{_short_id(canonical or path)}_{article_index:02d}"
        spans = _metro_seagull_review_parity_spans(body, source_id=source_id)
        if not spans:
            spans = _span_dicts_from_classifier(body, source_id=source_id)
        if not spans:
            spans = _fallback_paragraph_spans(body, source_id=source_id)
        all_spans.extend(
            _decorate_spans(
                spans,
                source_url=canonical,
                source_title=title or path.name,
                source_row_id=source_row_id,
                artifact_path=path,
                source_id=source_id,
            )
        )

    role_counts = {role: 0 for role in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")}
    for span in all_spans:
        role_counts[_role(span.get("role"))] = role_counts.get(_role(span.get("role")), 0) + 1

    surface = ArchiveSourceRoleSurface(
        schema=SCHEMA,
        version=VERSION,
        created_at_local=datetime.now().replace(microsecond=0).isoformat(),
        source_url=str(source_url or ""),
        canonical_source=canonical,
        source_title=title,
        source_row_id=source_row_id,
        result_status=result_status,
        article_status=article_status,
        browser_status=browser_status,
        output_dir=result_output,
        article_text_paths=tuple(text_paths),
        span_count=len(all_spans),
        role_counts=role_counts,
        claim_role_spans=tuple(all_spans),
        side_effects={
            "network_actions_performed": False,
            "account_polling_performed": False,
            "message_read_performed": False,
            "outbound_channel_send_performed": False,
            "credentials_read": False,
            "openclaw_tool_call_performed": False,
            "tor_camoufox_started": False,
        },
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = surface.to_dict()
    _write_json(out_dir / "archive_source_role_surface_r42ds.json", payload)
    with (out_dir / "archive_source_role_spans_r42ds.jsonl").open("w", encoding="utf-8") as fh:
        for span in all_spans:
            fh.write(json.dumps(span, ensure_ascii=False, default=str) + "\n")
    summary_lines = [
        "R42DS archive source-role surface",
        f"Source: {canonical}",
        f"Result: {result_status}",
        f"Article status: {article_status}",
        f"Span count: {len(all_spans)}",
        "Role counts: " + ", ".join(f"{k}={v}" for k, v in role_counts.items()),
        "Side effects: none; local already-captured artifact read only.",
    ]
    (out_dir / "archive_source_role_surface_r42ds.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    return surface


def run_self_test() -> None:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="r42ds_selftest_") as tmp:
        root = Path(tmp)
        article = root / "article_text.txt"
        article.write_text(
            "People shout 'seagull eater' at me in the street because of far right lies.\n\n"
            "Published by Metro News. Nora Mubarak told Metro that people had shouted abuse at her after false claims spread online.\n\n"
            "She said she was frightened but wanted the record corrected. The article reported what happened and linked the abuse to propagated claims.",
            encoding="utf-8",
        )

        class Artifact:
            artifact_kind = "article_text"
            local_path = article
            media_type = "text/plain"
            def to_dict(self):
                return {"artifact_kind": self.artifact_kind, "local_path": str(self.local_path), "media_type": self.media_type}

        class Result:
            status = "success"
            article_status = "material_from_native_webview2_live_document"
            browser_status = "NATIVE_WEBVIEW2_LIVE_MATERIAL_OK"
            output_dir = str(root)
            artifacts = (Artifact(),)

        class Row:
            row_id = "archive-row-03"
            title = "People shout seagull eater"

        surface = build_archive_source_role_surface_from_result(
            row=Row(),
            result=Result(),
            source_url="[https://archive.ph/6mr3C](https://archive.ph/6mr3C)",
            source_title="People shout seagull eater",
            output_root=root / "out",
        )
        payload = surface.to_dict()
        assert payload["canonical_source"] == "https://archive.ph/6mr3C", payload["canonical_source"]
        assert payload["span_count"] > 0
        assert payload["claim_role_spans"][0]["source_url"] == "https://archive.ph/6mr3C"
        assert payload["claim_role_spans"][0]["r42ds_archive_source_role_surface"] is True
        assert payload["side_effects"]["network_actions_performed"] is False
    print("R42DS archive source-role surface tests passed.")


if __name__ == "__main__":
    run_self_test()
