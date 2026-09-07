from __future__ import annotations

"""R42DW archive role-payload bridge.

The archive material worker first opens the native WebView2 helper with an
empty material-capture payload because article_text.txt does not exist yet.
After R42CT/R42DU captures the rendered article and R42DS builds source-role
spans, this module writes a second, role-ready WebView2 payload from those local
spans.  It performs no fetch, account polling, credential lookup, outbound send,
OpenClaw call, or Tor/Camoufox action.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from collections import Counter
import json
import os
import re
from typing import Any, Iterable, Mapping

VERSION = "20260907_r42dx_archive_role_payload_after_material_cmdline_safe"
SCHEMA = "ytce.r42dw.archive_role_overlay_payload.v1"
VALID_ROLES = {"PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK"}


def _r42ed_payload_overlay_metadata() -> dict[str, Any]:
    """Optional R42ED role logic/colour metadata for native overlays.

    This import is deliberately optional so older workers can still build archive
    role payloads if the R42ED matrix module has not been installed yet.
    """
    try:
        from profile_media_semantic_media_logic_matrix_r42ed import payload_overlay_metadata_r42ed

        meta = payload_overlay_metadata_r42ed()
        return dict(meta) if isinstance(meta, Mapping) else {}
    except Exception:
        return {}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _role(value: object, *, default: str = "UNKNOWN") -> str:
    role = str(value or "").strip().upper()
    return role if role in VALID_ROLES else default


def _canonical(value: object) -> str:
    try:
        from profile_media_archive_source_role_surface_r42ds import canonicalize_source_url
        return canonicalize_source_url(value)
    except Exception:
        s = _clean(value)
        m = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", s)
        if m:
            s = m.group(2)
        return s.strip().strip('"').strip("'")


def _short_id(value: object) -> str:
    import hashlib
    text = str(value or "").encode("utf-8", "replace")
    return hashlib.sha1(text).hexdigest()[:12]


def _count(rows: Iterable[Mapping[str, Any]], key: str = "active_role") -> dict[str, int]:
    out = {role: 0 for role in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN")}
    for row in rows:
        role = _role(row.get(key), default="UNKNOWN")
        if role in out:
            out[role] += 1
    return out


def _role_markup(rows: Iterable[Mapping[str, Any]], *, key: str = "active_role") -> str:
    parts: list[str] = []
    for row in rows:
        text = _clean(row.get("text") or row.get("excerpt") or "")
        if not text:
            continue
        role = _role(row.get(key), default="UNKNOWN")
        parts.append(f"[{text} | {role.title()}]")
    return "\n".join(parts)


def _row_from_span(span: Mapping[str, Any], *, mode: str, index: int, canonical_source: str) -> dict[str, Any] | None:
    text = _clean(span.get("text") or span.get("excerpt") or "")
    if not text:
        return None
    semantic_role = _role(span.get("semantic_role") or span.get("claim_role") or span.get("role"), default="UNKNOWN")
    media_role = _role(span.get("media_source_role") or span.get("media_role"), default="BLANK")
    active_role = media_role if mode == "media" else semantic_role
    if mode == "media" and active_role == "BLANK":
        return None
    edit_key = _clean(span.get("edit_key") or span.get("span_id") or f"r42dw_archive_role_payload_{index:04d}")
    return {
        "edit_key": edit_key,
        "text": text,
        "kind": "text",
        "semantic_role": semantic_role,
        "media_source_role": media_role,
        "active_role": active_role,
        "role": active_role,
        "url": canonical_source,
        "source_url": _canonical(span.get("source_url") or canonical_source),
        "normalised_url": _canonical(span.get("normalised_url") or canonical_source),
        "canonical_url": _canonical(span.get("canonical_url") or canonical_source),
        "reference_url": _canonical(span.get("reference_url") or canonical_source),
        "source_row_id": _clean(span.get("source_row_id") or ""),
        "source_title": _clean(span.get("source_title") or ""),
        "artifact_local_path": str(span.get("artifact_local_path") or ""),
        "artifact_kind": _clean(span.get("artifact_kind") or "article_text"),
        "source_stream": _clean(span.get("source_stream") or "archive_source_material"),
        "section_label": _clean(span.get("section_label") or "archive_source_material"),
        "archive_material_role_surface": True,
        "r42ds_archive_source_role_surface": bool(span.get("r42ds_archive_source_role_surface") or True),
        "r42dw_archive_role_payload_row": True,
    }


def rows_by_mode_from_surface(surface: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    canonical_source = _canonical(surface.get("canonical_source") or surface.get("source_url") or "https://archive.ph/6mr3C")
    spans = surface.get("claim_role_spans") or surface.get("spans") or []
    if not isinstance(spans, list):
        spans = []
    semantic_rows: list[dict[str, Any]] = []
    media_rows: list[dict[str, Any]] = []
    seen_sem: set[str] = set()
    seen_med: set[str] = set()
    for index, item in enumerate(spans, start=1):
        if not isinstance(item, Mapping):
            continue
        sem = _row_from_span(item, mode="semantic", index=index, canonical_source=canonical_source)
        med = _row_from_span(item, mode="media", index=index, canonical_source=canonical_source)
        if sem:
            key = (_clean(sem.get("edit_key")), _clean(sem.get("text")).casefold())
            sk = json.dumps(key, ensure_ascii=False)
            if sk not in seen_sem:
                seen_sem.add(sk)
                semantic_rows.append(sem)
        if med:
            key = (_clean(med.get("edit_key")), _clean(med.get("text")).casefold())
            mk = json.dumps(key, ensure_ascii=False)
            if mk not in seen_med:
                seen_med.add(mk)
                media_rows.append(med)
    return {"semantic": semantic_rows, "media": media_rows}


def _plain_text(rows_by_mode: Mapping[str, list[dict[str, Any]]]) -> str:
    texts: list[str] = []
    seen: set[str] = set()
    for row in list(rows_by_mode.get("semantic") or []) + list(rows_by_mode.get("media") or []):
        text = _clean(row.get("text") or "")
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            texts.append(text)
    return "\n".join(texts)


def build_native_role_overlay_payload_from_surface(
    surface: Mapping[str, Any],
    *,
    source_url: object = "",
    title: object = "",
    text_paint_style: object = "",
) -> dict[str, Any]:
    canonical_source = _canonical(source_url or surface.get("canonical_source") or surface.get("source_url") or "https://archive.ph/6mr3C")
    rows_by_mode = rows_by_mode_from_surface({**dict(surface), "canonical_source": canonical_source})
    semantic_rows = rows_by_mode["semantic"]
    media_rows = rows_by_mode["media"]
    source_title = _clean(title or surface.get("source_title") or "Archive source material")
    paint_style = _clean(text_paint_style or os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", ""))
    r42ed_meta = _r42ed_payload_overlay_metadata()
    payload = {
        "schema": SCHEMA,
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "selected_url": canonical_source,
        "launch_start_url": canonical_source,
        "title": source_title,
        "article_title": source_title,
        "source_navigation_urls": [
            {"url": canonical_source, "label": "Archive", "kind": "archive_ph", "current": True}
        ],
        "source_navigation_count": 1,
        "rows_by_mode": rows_by_mode,
        "counts_by_mode": {
            "semantic": _count(semantic_rows),
            "media": _count(media_rows),
        },
        "plain_text": _plain_text(rows_by_mode),
        "semantic_role_text": _role_markup(semantic_rows),
        "media_role_text": _role_markup(media_rows),
        "text_paint_style": paint_style,
        "role_comprehension_matrix": r42ed_meta.get("role_comprehension_matrix", {}),
        "role_colour_theme": r42ed_meta.get("role_colour_theme", {}),
        "adapter_guard_matrix": r42ed_meta.get("adapter_guard_matrix", {}),
        "r42ed_semantic_media_logic_matrix": bool(r42ed_meta),
        "r42dw_archive_role_overlay_payload": True,
        "r42ds_source_surface_span_count": int(surface.get("span_count") or len(semantic_rows)),
        "r42ds_source_surface_role_counts": dict(surface.get("role_counts") or {}),
        "side_effects": {
            "network_actions_performed": False,
            "normal_access_attempted": False,
            "native_webview2_started": False,
            "tor_camoufox_started": False,
            "account_polling_performed": False,
            "message_read_performed": False,
            "outbound_channel_send_performed": False,
            "credentials_read": False,
            "openclaw_tool_call_performed": False,
        },
    }
    return payload


@dataclass(frozen=True)
class ArchiveRolePayloadWrite:
    payload_path: str
    changes_path: str
    summary_path: str
    selected_url: str
    semantic_count: int
    media_count: int
    counts_by_mode: dict[str, dict[str, int]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + ".write_result",
            "version": VERSION,
            "payload_path": self.payload_path,
            "changes_path": self.changes_path,
            "summary_path": self.summary_path,
            "selected_url": self.selected_url,
            "semantic_count": self.semantic_count,
            "media_count": self.media_count,
            "counts_by_mode": self.counts_by_mode,
        }


def write_native_role_overlay_payload_from_surface(
    surface: Mapping[str, Any],
    *,
    output_root: str | Path | None = None,
    source_url: object = "",
    title: object = "",
    text_paint_style: object = "",
) -> ArchiveRolePayloadWrite:
    payload = build_native_role_overlay_payload_from_surface(
        surface,
        source_url=source_url,
        title=title,
        text_paint_style=text_paint_style,
    )
    selected = _canonical(payload.get("selected_url") or source_url)
    root = Path(output_root or Path("profile_media_live_captures") / "r42dw_archive_role_payload")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", selected or "archive_role_payload").strip("._-")[:96]
    out_dir = root / f"{stamp}_{slug}_{_short_id(selected)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload_path = out_dir / "archive_role_overlay_payload_r42dw.json"
    changes_path = out_dir / "archive_role_overlay_changes_r42dw.jsonl"
    summary_path = out_dir / "archive_role_overlay_payload_r42dw_summary.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not changes_path.exists():
        changes_path.write_text("", encoding="utf-8")
    result = ArchiveRolePayloadWrite(
        payload_path=str(payload_path),
        changes_path=str(changes_path),
        summary_path=str(summary_path),
        selected_url=selected,
        semantic_count=len(payload["rows_by_mode"]["semantic"]),
        media_count=len(payload["rows_by_mode"]["media"]),
        counts_by_mode=payload["counts_by_mode"],
    )
    summary = result.to_dict()
    summary["payload_preview"] = {
        "title": payload.get("title"),
        "plain_text_chars": len(payload.get("plain_text") or ""),
        "semantic_role_text_chars": len(payload.get("semantic_role_text") or ""),
        "media_role_text_chars": len(payload.get("media_role_text") or ""),
        "text_paint_style": payload.get("text_paint_style") or "",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def find_latest_archive_surface(
    *,
    project_root: str | Path | None = None,
    source_url: object = "https://archive.ph/6mr3C",
) -> Path | None:
    """Return the best local R42DS archive role surface for source_url.

    R42DX note: do not merely choose the newest folder.  A later failed run can
    create a zero-span surface (for example a case-sensitive archive short-code
    typo such as 6Mr3C -> 404).  Prefer successful, non-empty, same-source
    surfaces so command-line replay does not touch archive.ph again.
    """
    root = Path(project_root or Path.cwd())
    canonical_source = _canonical(source_url)
    base = root / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2"
    if not base.exists():
        return None

    def _score(data: Mapping[str, Any], path: Path) -> tuple[int, str, str]:
        span_count = 0
        try:
            span_count = int(data.get("span_count") or len(data.get("claim_role_spans") or []))
        except Exception:
            span_count = 0
        browser = _clean(data.get("browser_status") or data.get("status") or "")
        article = _clean(data.get("article_status") or "")
        result = _clean(data.get("result_status") or "")
        created = _clean(data.get("created_at_local") or "")
        score = 0
        if span_count > 0:
            score += 100000
        score += min(span_count, 10000)
        good_words = (browser + " " + article + " " + result).lower()
        if any(w in good_words for w in ("ok", "success", "live_material", "material_from_native_webview2")):
            score += 10000
        if any(w in good_words for w in ("material_unavailable", "access_gate", "not_obtained", "blocked", "404", "not found")):
            score -= 50000
        if canonical_source == "https://archive.ph/6mr3C":
            # The archive short code is case-sensitive in practice; keep the
            # known-good lower-case m test target ahead of later failed 6Mr3C runs.
            folder = path.parent.name
            src = _canonical(data.get("canonical_source") or data.get("source_url") or "")
            if src == "https://archive.ph/6mr3C" or "6mr3C" in folder:
                score += 1000
            if src == "https://archive.ph/6Mr3C" or "6Mr3C" in folder:
                score -= 100000
        return (score, created, path.parent.name)

    candidates: list[tuple[tuple[int, str, str], Path]] = []
    for path in base.rglob("archive_source_role_surface_r42ds.json"):
        try:
            if path.stat().st_size <= 0:
                continue
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            src = _canonical(data.get("canonical_source") or data.get("source_url") or "")
            if canonical_source and src and src != canonical_source:
                # For the single archive.ph test, do not cross-pollinate the
                # failed mixed-case short-code folder into the good lower-case row.
                continue
            candidates.append((_score(data, path), path))
        except Exception:
            continue
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1] if candidates else None


def build_latest_archive_role_payload(
    *,
    project_root: str | Path | None = None,
    source_url: object = "https://archive.ph/6mr3C",
    output_root: str | Path | None = None,
    text_paint_style: object = "",
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd())
    surface_path = find_latest_archive_surface(project_root=root, source_url=source_url)
    if surface_path is None:
        return {
            "schema": SCHEMA + ".latest_probe",
            "version": VERSION,
            "ok": False,
            "reason": "latest_r42ds_archive_surface_not_found",
            "source_url": _canonical(source_url),
        }
    surface = json.loads(surface_path.read_text(encoding="utf-8", errors="replace"))
    write = write_native_role_overlay_payload_from_surface(
        surface,
        source_url=source_url or surface.get("canonical_source") or surface.get("source_url") or "",
        title=surface.get("source_title") or "Archive source material",
        text_paint_style=text_paint_style,
        output_root=output_root or (root / "profile_media_live_captures" / "r42dw_archive_role_payload"),
    )
    payload = json.loads(Path(write.payload_path).read_text(encoding="utf-8", errors="replace"))
    return {
        "schema": SCHEMA + ".latest_probe",
        "version": VERSION,
        "ok": True,
        "source_url": _canonical(source_url),
        "surface_path": str(surface_path),
        "payload_path": write.payload_path,
        "changes_path": write.changes_path,
        "summary_path": write.summary_path,
        "semantic_rows": write.semantic_count,
        "media_rows": write.media_count,
        "counts_by_mode": write.counts_by_mode,
        "payload_rows_empty": write.semantic_count == 0 and write.media_count == 0,
        "payload_plain_text_chars": len(payload.get("plain_text") or ""),
        "side_effects": {
            "network_actions_performed": False,
            "native_webview2_started": False,
            "tor_camoufox_started": False,
            "account_polling_performed": False,
            "message_read_performed": False,
            "outbound_channel_send_performed": False,
            "credentials_read": False,
            "openclaw_tool_call_performed": False,
        },
    }


def run_self_test() -> None:
    surface = {
        "canonical_source": "https://archive.ph/6mr3C",
        "source_title": "6Mr3C",
        "span_count": 3,
        "claim_role_spans": [
            {"edit_key": "a", "text": "People shout seagull eater at me", "semantic_role": "SECONDARY", "media_source_role": "SECONDARY"},
            {"edit_key": "b", "text": "Barney Davis", "semantic_role": "BLANK", "media_source_role": "BLANK"},
            {"edit_key": "c", "text": "unsupported viral caption", "semantic_role": "UNKNOWN", "media_source_role": "UNKNOWN"},
        ],
    }
    payload = build_native_role_overlay_payload_from_surface(surface)
    assert len(payload["rows_by_mode"]["semantic"]) == 3
    assert len(payload["rows_by_mode"]["media"]) == 2
    assert payload["counts_by_mode"]["semantic"]["SECONDARY"] == 1
    assert payload["counts_by_mode"]["semantic"]["UNKNOWN"] == 1
    assert payload["counts_by_mode"]["media"]["SECONDARY"] == 1
    assert payload["counts_by_mode"]["media"]["UNKNOWN"] == 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build R42DW archive role overlay payload from latest R42DS surface.")
    parser.add_argument("source_url", nargs="?", default="https://archive.ph/6mr3C")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-root", default="")
    parser.add_argument("--recolor", action="store_true")
    args = parser.parse_args()
    result = build_latest_archive_role_payload(
        project_root=args.root,
        source_url=args.source_url,
        output_root=args.output_root or None,
        text_paint_style="recolor" if args.recolor else "",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("ok") else 2)
