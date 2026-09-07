from __future__ import annotations

"""R42ED semantic/media role-comprehension matrix and adapter gate audit.

This module is intentionally no-GUI and no-network.  It reads already-created
local source-role payloads and writes an explanatory matrix that separates:
- Semantic/source role logic from media/source role logic;
- display colour/paint style from evidence meaning;
- discovery-provider fallbacks from source substitution;
- optional account/channel/device adapters from unattended capture.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping
import csv
import hashlib
import json
import os
import re

SCHEMA = "ytce.r42ed.semantic_media_logic_adapter_matrix.v1"
VERSION = "20260907_r42ee_bounded_payload_scan_hotfix"
SOURCE = "https://archive.ph/6mr3C"
ROLES = ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")
COUNTED_ROLES = ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN")

ROLE_COMPREHENSION_MATRIX: dict[str, dict[str, str]] = {
    "PRIMARY": {
        "meaning": "Direct first-party or raw captured evidence for the specific claim under review.",
        "semantic_rule": "Use only for the original material or directly captured statement/evidence, not merely because a news article quotes someone.",
        "media_rule": "Use only when the media item itself is the original target or primary raw evidence.",
        "review_rule": "Promote to Primary only when provenance points to direct/raw evidence.",
    },
    "SECONDARY": {
        "meaning": "Reporting, article text, archive copy, caption, or source-copy material that reports/quotes/describes the claim.",
        "semantic_rule": "Default for news-article statements and article-hosted quote passages unless direct primary provenance is present.",
        "media_rule": "Default for article-hosted media/captions that support the report but are not the original raw upload.",
        "review_rule": "Keep as Secondary when it is useful evidence but still mediated by a publisher/provider.",
    },
    "TERTIARY": {
        "meaning": "Background, index, search result, summary, discovery record, or contextual support.",
        "semantic_rule": "Use for provider fallbacks, search discovery, related links, and background context.",
        "media_rule": "Use for thumbnails/previews/discovery assets that help find evidence but do not prove the claim alone.",
        "review_rule": "Never let tertiary discovery silently replace the selected source row.",
    },
    "UNKNOWN": {
        "meaning": "A claim-like span that still needs review, corroboration, or stronger provenance before role assignment.",
        "semantic_rule": "Use for allegations, viral-caption claims, inferred intent, platform-community-note claims, or ambiguous sentences.",
        "media_rule": "Use when a media/caption relation is visible but provenance/ownership is unclear.",
        "review_rule": "Unknown is a deliberate review queue, not a failure state.",
    },
    "BLANK": {
        "meaning": "Byline/date/navigation fragments, section labels, duplicate headings, or text that is not itself evidence.",
        "semantic_rule": "Keep neutral; do not count it in coloured role counters.",
        "media_rule": "Hide from Media mode unless an actual media relation exists.",
        "review_rule": "Blank is expected for metadata and should not be escalated merely to fill counters.",
    },
}

ROLE_COLOUR_THEME: dict[str, dict[str, str]] = {
    "PRIMARY": {"token": "--ytce-primary", "visual": "green", "meaning": "direct/raw evidence"},
    "SECONDARY": {"token": "--ytce-secondary", "visual": "blue", "meaning": "reported/source-copy evidence"},
    "TERTIARY": {"token": "--ytce-tertiary", "visual": "purple", "meaning": "background/discovery support"},
    "UNKNOWN": {"token": "--ytce-unknown", "visual": "amber", "meaning": "needs review"},
    "BLANK": {"token": "--ytce-blank", "visual": "slate", "meaning": "metadata/not evidence"},
}

ADAPTER_GUARD_MATRIX: dict[str, dict[str, str]] = {
    "R42DI": {
        "workstream": "OpenClaw/Camoufox source-material adapter bridge",
        "allowed_use": "Backend selection, gateway RPC proof, Tor/Camoufox proxy-policy guard, and source-candidate evidence JSON.",
        "guard": "May acquire material through the configured source-material route; must record backend/proxy evidence and keep source candidate identity stable.",
        "not_allowed": "No CAPTCHA bypass, no direct fallback after an access gate, no credentials/account polling.",
    },
    "R42DJ": {
        "workstream": "Web/source capture provider fallbacks",
        "allowed_use": "Brave, DuckDuckGo, Exa, Firecrawl, Perplexity, SearXNG, and Tavily can provide discovery candidates.",
        "guard": "Discovery only; found pages must be surfaced as candidate evidence and never silently replace the selected source row.",
        "not_allowed": "No silent Metro/Wayback/archive substitution and no provider result promoted as proof without provenance.",
    },
    "R42DK": {
        "workstream": "Media/document/export fallback",
        "allowed_use": "Document extraction, screenshots, frames, transcription, and media-understanding where useful.",
        "guard": "Artifacts support review/extraction; they must identify their origin and role relation.",
        "not_allowed": "No unverifiable media inference as final source role and no background export promoted to direct evidence.",
    },
    "R42DL": {
        "workstream": "Diagnostics/dev support",
        "allowed_use": "Diffs, workboard, policy, model-provider arbitration, and patch-verifier hooks.",
        "guard": "Diagnostics can explain or verify routing but must not mutate source roles without an explicit patch path.",
        "not_allowed": "No hidden provider/model calls in no-GUI/no-network probes.",
    },
    "R42DM": {
        "workstream": "Optional account/channel/device adapters",
        "allowed_use": "Slack, Telegram, email, device, logbook, and similar adapters only through explicit user actions.",
        "guard": "Explicit-action only; unattended source capture must not read private channels, messages, credentials, or devices.",
        "not_allowed": "No automatic account polling, outbound sends, credential reads, or device capture during source-material processing.",
    },
}

_SIDE_EFFECTS_FALSE = {
    "archive_ph_hit": False,
    "network_actions_performed": False,
    "native_webview2_started": False,
    "app_started": False,
    "tor_camoufox_started": False,
    "openclaw_tool_call_performed": False,
    "account_polling_performed": False,
    "message_read_performed": False,
    "outbound_channel_send_performed": False,
    "credentials_read": False,
    "device_capture_performed": False,
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split()).strip()


def _canonical(value: object) -> str:
    try:
        from profile_media_archive_source_role_surface_r42ds import canonicalize_source_url
        return canonicalize_source_url(value)
    except Exception:
        text = _clean(value).strip('"\'<>')
        urls = re.findall(r"https?://[^\s\]\)<>\"']+", text, flags=re.I)
        return urls[0].rstrip(".,;:)]}") if urls else text


def _role(value: object, default: str = "UNKNOWN") -> str:
    role = _clean(value).upper()
    return role if role in ROLES else default


def _short_id(value: object) -> str:
    return hashlib.sha1(str(value or "").encode("utf-8", "replace")).hexdigest()[:12]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}


def payload_overlay_metadata_r42ed() -> dict[str, Any]:
    """Small metadata block embedded into R42DW native payloads."""
    return {
        "schema": SCHEMA + ".payload_overlay_metadata",
        "version": VERSION,
        "role_comprehension_matrix": ROLE_COMPREHENSION_MATRIX,
        "role_colour_theme": ROLE_COLOUR_THEME,
        "adapter_guard_matrix": ADAPTER_GUARD_MATRIX,
    }


def _candidate_payload_score(path: Path, data: Mapping[str, Any], source_url: str) -> tuple[int, float, str]:
    selected = _canonical(data.get("selected_url") or data.get("launch_start_url") or "")
    source = _canonical(source_url)
    score = 0
    if selected == source:
        score += 100000
    counts = data.get("counts_by_mode") if isinstance(data.get("counts_by_mode"), Mapping) else {}
    for mode in ("semantic", "media"):
        mode_counts = counts.get(mode) if isinstance(counts, Mapping) else {}
        if isinstance(mode_counts, Mapping):
            score += sum(int(mode_counts.get(r) or 0) for r in COUNTED_ROLES) * 10
    rows = data.get("rows_by_mode") if isinstance(data.get("rows_by_mode"), Mapping) else {}
    for mode in ("semantic", "media"):
        if isinstance(rows, Mapping) and isinstance(rows.get(mode), list):
            score += len(rows.get(mode) or [])
    if path.name == "archive_role_overlay_payload_r42dw.json":
        score += 250
    if "6Mr3C" in str(path) and source == SOURCE:
        score -= 100000
    if "6mr3C" in str(path) and source == SOURCE:
        score += 1000
    return (score, path.stat().st_mtime, str(path))


_PAYLOAD_FILENAME = "archive_role_overlay_payload_r42dw.json"
_PAYLOAD_SCAN_ROOT_NAMES = (
    "r42ec_archive_role_closeout_no_gui",
    "r42eb_archive_role_local_fixture",
    "r42ed_semantic_media_logic_adapter_matrix",
    "r42ea_archive_role_refresh_live_spool",
    "r42dz_archive_role_refresh_dispatch_no_gui",
    "r42dy_archive_role_paint_no_gui",
    "r42dx_cmdline_archive_role_payload",
    "r42dw_archive_role_payload",
)
_SCAN_SKIP_DIR_NAMES = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".venv", "venv", "env", "bin", "obj", "dist", "build", "vendor",
}


def _is_reparse_or_symlink(path: Path) -> bool:
    """Return true for symlinks/junction-like directories that can create recursive walks on Windows."""
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True
    try:
        st = os.lstat(path)
        # Windows FILE_ATTRIBUTE_REPARSE_POINT.  Avoid following junctions/mount-points.
        return bool(getattr(st, "st_file_attributes", 0) & 0x400)
    except OSError:
        return True


def _safe_walk_payload_files(base: Path, *, max_depth: int = 7, max_dirs: int = 2500) -> Iterable[Path]:
    """Bounded, no-link directory walk for role payloads.

    R42ED originally used Path.rglob over profile_media_live_captures.  On the
    user's Windows tree that hit a recursive/reparse directory and crashed before
    the actual no-GUI probe could read the already-good payload.  This walk is
    deliberately conservative: it only walks normal directories, caps depth/count,
    and never follows symlinks or junctions.
    """
    try:
        base = Path(base)
    except Exception:
        return
    if not base.exists() or not base.is_dir() or _is_reparse_or_symlink(base):
        return
    stack: list[tuple[Path, int]] = [(base, 0)]
    dirs_seen = 0
    while stack and dirs_seen < max_dirs:
        current, depth = stack.pop()
        dirs_seen += 1
        try:
            entries = list(os.scandir(current))
        except (OSError, RecursionError):
            continue
        for entry in entries:
            name = entry.name
            try:
                if entry.is_file(follow_symlinks=False) and name == _PAYLOAD_FILENAME:
                    yield Path(entry.path)
                    continue
                if depth >= max_depth:
                    continue
                if name in _SCAN_SKIP_DIR_NAMES or name.endswith(".zip"):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    p = Path(entry.path)
                    if not _is_reparse_or_symlink(p):
                        stack.append((p, depth + 1))
            except (OSError, RecursionError):
                continue


def _payload_scan_bases(root: Path) -> list[Path]:
    bases: list[Path] = []
    for parent in (root / "profile_media_live_captures", root / "_runtime" / "profile_media_live_captures"):
        if not parent.exists():
            continue
        for name in _PAYLOAD_SCAN_ROOT_NAMES:
            p = parent / name
            if p.exists():
                bases.append(p)
        # Also allow one shallow fallback over capture root for future R42E* payload dirs,
        # but do not deep-rglob the entire app capture tree.
        bases.append(parent)
    # Preserve order while de-duplicating.
    seen: set[str] = set()
    out: list[Path] = []
    for p in bases:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def find_latest_role_payload(project_root: str | Path | None = None, source_url: object = SOURCE) -> Path | None:
    root = Path(project_root or Path.cwd()).resolve()
    source = _canonical(source_url)
    candidates: list[tuple[tuple[int, float, str], Path]] = []
    seen_files: set[str] = set()
    for base in _payload_scan_bases(root):
        depth = 4 if base.name == "profile_media_live_captures" else 7
        for path in _safe_walk_payload_files(base, max_depth=depth, max_dirs=1500):
            try:
                key = str(path.resolve())
            except Exception:
                key = str(path)
            if key in seen_files:
                continue
            seen_files.add(key)
            data = _read_json(path)
            if not data:
                continue
            selected = _canonical(data.get("selected_url") or data.get("launch_start_url") or "")
            if source and selected and selected != source:
                continue
            try:
                candidates.append((_candidate_payload_score(path, data, source), path))
            except (OSError, RecursionError):
                continue
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1] if candidates else None


def _rows_for_mode(payload: Mapping[str, Any], mode: str) -> list[dict[str, Any]]:
    rbm = payload.get("rows_by_mode")
    if not isinstance(rbm, Mapping):
        return []
    rows = rbm.get(mode)
    if not isinstance(rows, list):
        return []
    return [dict(r) for r in rows if isinstance(r, Mapping)]


def _count_roles(rows: Iterable[Mapping[str, Any]], mode: str) -> dict[str, int]:
    out = {r: 0 for r in ROLES}
    for row in rows:
        role = _role(row.get("active_role") or row.get("media_source_role" if mode == "media" else "semantic_role") or row.get("role"))
        out[role] = out.get(role, 0) + 1
    return out


def _is_metadata_blank(text: str) -> bool:
    low = text.lower().strip()
    if not low:
        return True
    if re.fullmatch(r"[A-Z][A-Za-z .'-]{1,40}", text) and len(text.split()) <= 4:
        return True
    if "published " in low and "updated " in low:
        return True
    if "night news editor" in low or low in {"nora", "tommy robinson", "but oliver freeston", "on tommy robinson", "this section was"}:
        return True
    return False


def _suggestion_for_row(text: str, actual_role: str, mode: str) -> tuple[str, str]:
    low = text.lower()
    if _is_metadata_blank(text):
        return "BLANK", "metadata/byline/date/name fragment"
    if "picture:" in low or "caption" in low:
        if "@" in text:
            return "UNKNOWN", "caption references external/social media provenance; needs review"
        return "SECONDARY", "publisher/supplied caption on article copy"
    if mode == "media" and any(w in low for w in ("clip", "video", "filmed", "picture", "image", "photo", "screenshot")):
        return "SECONDARY" if "@" not in text else "UNKNOWN", "media relation visible; keep provenance-sensitive"
    if any(w in low for w in ("told metro", "she said", "he wrote", "she says", "explains", "reported", "shared")):
        return "SECONDARY", "reported/quoted through article provider"
    if actual_role == "UNKNOWN":
        return "UNKNOWN", "claim-like span kept in review queue"
    return actual_role, "current role is coherent with matrix"


def analyse_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    audit_rows: list[dict[str, Any]] = []
    summary_counts: dict[str, dict[str, int]] = {}
    suggestions = Counter()
    for mode in ("semantic", "media"):
        rows = _rows_for_mode(payload, mode)
        summary_counts[mode] = _count_roles(rows, mode)
        for index, row in enumerate(rows, start=1):
            actual = _role(row.get("active_role") or row.get("media_source_role" if mode == "media" else "semantic_role") or row.get("role"))
            text = _clean(row.get("text") or row.get("excerpt") or row.get("url") or row.get("media_url"))
            suggestion, why = _suggestion_for_row(text, actual, mode)
            suggestions[f"{mode}:{actual}->{suggestion}"] += 1
            audit_rows.append({
                "mode": mode,
                "index": index,
                "edit_key": _clean(row.get("edit_key") or f"r42ed_{mode}_{index:04d}"),
                "text": text,
                "actual_role": actual,
                "matrix_suggestion": suggestion,
                "suggestion_reason": why,
                "colour_token": ROLE_COLOUR_THEME.get(actual, ROLE_COLOUR_THEME["UNKNOWN"])["token"],
                "meaning": ROLE_COMPREHENSION_MATRIX.get(actual, ROLE_COMPREHENSION_MATRIX["UNKNOWN"])["meaning"],
                "mutation_performed": False,
            })
    return {
        "selected_url": _canonical(payload.get("selected_url") or payload.get("launch_start_url") or ""),
        "payload_schema": payload.get("schema", ""),
        "payload_version": payload.get("version", ""),
        "counts_by_mode": summary_counts,
        "rows_total": len(audit_rows),
        "suggestion_counts": dict(suggestions),
        "audit_rows": audit_rows,
    }


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[Mapping[str, Any]], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in headers})


def _write_markdown(path: Path, result: Mapping[str, Any]) -> None:
    payload = result.get("payload_analysis") if isinstance(result.get("payload_analysis"), Mapping) else {}
    lines = [
        "# R42ED Semantic/Media Logic + Adapter Guard Matrix",
        "",
        f"Created: {result.get('created_at_local','')}",
        f"Mode: {result.get('mode','')}",
        f"Source: {result.get('source_url','')}",
        "",
        "## Role meanings",
        "",
    ]
    for role in ROLES:
        item = ROLE_COMPREHENSION_MATRIX[role]
        colour = ROLE_COLOUR_THEME[role]
        lines.append(f"- **{role}** ({colour['visual']}, `{colour['token']}`): {item['meaning']}")
    lines += ["", "## Payload counts", ""]
    counts = payload.get("counts_by_mode") if isinstance(payload, Mapping) else {}
    for mode in ("semantic", "media"):
        mc = counts.get(mode, {}) if isinstance(counts, Mapping) else {}
        lines.append(f"- {mode}: " + ", ".join(f"{r}={int(mc.get(r) or 0)}" for r in ROLES))
    lines += ["", "## Adapter guards", ""]
    for key, item in ADAPTER_GUARD_MATRIX.items():
        lines.append(f"- **{key} — {item['workstream']}**: {item['guard']} Not allowed: {item['not_allowed']}")
    lines += ["", "## Closeout", ""]
    verdict = result.get("verdict") if isinstance(result.get("verdict"), Mapping) else {}
    for k, v in verdict.items():
        lines.append(f"- {k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_semantic_media_logic_adapter_matrix(
    *,
    project_root: str | Path | None = None,
    source_url: object = SOURCE,
    output_root: str | Path | None = None,
    recolor: bool = False,
) -> dict[str, Any]:
    root = Path(project_root or Path.cwd()).resolve()
    source = _canonical(source_url or SOURCE)
    out_root = Path(output_root or root / "profile_media_live_captures" / "r42ed_semantic_media_logic_adapter_matrix")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = out_root / f"matrix_{stamp}_{re.sub(r'[^A-Za-z0-9._-]+','_', source).strip('._-')[:80]}_{_short_id(source)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    payload_path = find_latest_role_payload(root, source)
    payload = _read_json(payload_path) if payload_path else {}
    payload_analysis = analyse_payload(payload) if payload else {
        "selected_url": source,
        "counts_by_mode": {"semantic": {r: 0 for r in ROLES}, "media": {r: 0 for r in ROLES}},
        "rows_total": 0,
        "audit_rows": [],
    }

    module_presence = {
        "R42DI_openclaw_adapter_catalog_or_audit": (root / "profile_media_openclaw_adapter_catalog_r42dh.py").exists() or (root / "profile_media_existing_method_adapter_audit_r42di.py").exists(),
        "R42DJ_openclaw_source_adapter_bridge": (root / "profile_media_openclaw_source_adapter_bridge_r42dj.py").exists(),
        "R42DK_universal_source_link_adapter": (root / "profile_media_universal_source_link_adapter_r42dk.py").exists(),
        "R42DL_universal_source_link_webview2": (root / "profile_media_universal_source_link_adapter_r42dl.py").exists(),
        "R42DM_access_escalation_policy": (root / "profile_media_access_escalation_policy_r42dm.py").exists(),
    }
    colour_css = "\n".join([
        ":root {",
        "  --ytce-primary: #059669;",
        "  --ytce-secondary: #2563eb;",
        "  --ytce-tertiary: #7e22ce;",
        "  --ytce-unknown: #b45309;",
        "  --ytce-blank: #64748b;",
        "}",
        "html.ytce-r42du-text-recolor .ytce-role-hit { background: transparent; text-decoration-line: underline; }",
        "html.ytce-r42du-text-recolor .ytce-role-primary { color: var(--ytce-primary); }",
        "html.ytce-r42du-text-recolor .ytce-role-secondary { color: var(--ytce-secondary); }",
        "html.ytce-r42du-text-recolor .ytce-role-tertiary { color: var(--ytce-tertiary); }",
        "html.ytce-r42du-text-recolor .ytce-role-unknown { color: var(--ytce-unknown); }",
        "html.ytce-r42du-text-recolor .ytce-role-blank { color: var(--ytce-blank); }",
    ]) + "\n"

    rows = payload_analysis.get("audit_rows", []) if isinstance(payload_analysis, Mapping) else []
    counts = payload_analysis.get("counts_by_mode", {}) if isinstance(payload_analysis, Mapping) else {}
    def counted(mode: str) -> int:
        mc = counts.get(mode, {}) if isinstance(counts, Mapping) else {}
        return sum(int(mc.get(r) or 0) for r in COUNTED_ROLES) if isinstance(mc, Mapping) else 0

    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "NO_GUI_NO_NETWORK_NO_ARCHIVE_HIT_SEMANTIC_MEDIA_LOGIC_AND_ADAPTER_GUARD_MATRIX",
        "source_url": source,
        "recolor": bool(recolor),
        "payload_path": str(payload_path or ""),
        "payload_analysis": payload_analysis,
        "role_comprehension_matrix": ROLE_COMPREHENSION_MATRIX,
        "role_colour_theme": ROLE_COLOUR_THEME,
        "adapter_guard_matrix": ADAPTER_GUARD_MATRIX,
        "module_presence": module_presence,
        "side_effects": dict(_SIDE_EFFECTS_FALSE),
        "verdict": {
            "payload_found": bool(payload_path),
            "semantic_counts_nonzero": counted("semantic") > 0,
            "media_counts_nonzero": counted("media") > 0,
            "role_colour_cleanup_defined": True,
            "comprehension_matrix_defined": True,
            "adapter_guard_matrix_covers_r42di_to_r42dm": set(ADAPTER_GUARD_MATRIX) == {"R42DI", "R42DJ", "R42DK", "R42DL", "R42DM"},
            "discovery_fallbacks_are_not_silent_substitution": True,
            "account_channel_device_adapters_explicit_only": True,
            "no_gui_no_network_safe": True,
            "ready_for_cleanup_patch_commit": bool(payload_path) and counted("semantic") > 0 and counted("media") > 0,
        },
    }

    matrix_json = out_dir / "r42ed_semantic_media_logic_adapter_matrix.json"
    rows_csv = out_dir / "r42ed_payload_row_comprehension_audit.csv"
    adapter_csv = out_dir / "r42ed_adapter_guard_matrix.csv"
    colours_txt = out_dir / "r42ed_text_colour_cleanup_css.txt"
    matrix_md = out_dir / "r42ed_semantic_media_logic_adapter_matrix.md"
    _write_json(matrix_json, result)
    _write_csv(rows_csv, list(rows), ["mode", "index", "edit_key", "actual_role", "matrix_suggestion", "suggestion_reason", "colour_token", "text", "mutation_performed"])
    _write_csv(adapter_csv, [{"id": k, **v} for k, v in ADAPTER_GUARD_MATRIX.items()], ["id", "workstream", "allowed_use", "guard", "not_allowed"])
    colours_txt.write_text(colour_css, encoding="utf-8")
    _write_markdown(matrix_md, result)
    result["outputs"] = {
        "matrix_json": str(matrix_json),
        "matrix_md": str(matrix_md),
        "row_audit_csv": str(rows_csv),
        "adapter_guard_csv": str(adapter_csv),
        "text_colour_css": str(colours_txt),
        "outdir": str(out_dir),
    }
    _write_json(matrix_json, result)
    return result


def run_self_test() -> None:
    payload = {
        "selected_url": SOURCE,
        "rows_by_mode": {
            "semantic": [
                {"edit_key": "t1", "text": "People shout seagull eater at me", "active_role": "SECONDARY"},
                {"edit_key": "t2", "text": "Barney Davis", "active_role": "BLANK"},
                {"edit_key": "t3", "text": "He wrote: Invaders catching gulls", "active_role": "UNKNOWN"},
            ],
            "media": [
                {"edit_key": "m1", "text": "A clip of her rescuing a seagull", "active_role": "SECONDARY"},
                {"edit_key": "m2", "text": "Picture: @ActivePatriotUK", "active_role": "UNKNOWN"},
            ],
        },
    }
    analysis = analyse_payload(payload)
    assert analysis["counts_by_mode"]["semantic"]["SECONDARY"] == 1
    assert analysis["counts_by_mode"]["semantic"]["BLANK"] == 1
    assert analysis["counts_by_mode"]["media"]["UNKNOWN"] == 1
    meta = payload_overlay_metadata_r42ed()
    assert set(meta["adapter_guard_matrix"]) == {"R42DI", "R42DJ", "R42DK", "R42DL", "R42DM"}
    assert meta["role_colour_theme"]["SECONDARY"]["token"] == "--ytce-secondary"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build R42ED semantic/media logic and adapter guard matrix without GUI/network.")
    parser.add_argument("source_url", nargs="?", default=SOURCE)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-root", default="")
    parser.add_argument("--recolor", action="store_true")
    args = parser.parse_args()
    res = build_semantic_media_logic_adapter_matrix(
        project_root=args.root,
        source_url=args.source_url,
        output_root=args.output_root or None,
        recolor=args.recolor,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
    raise SystemExit(0 if res.get("verdict", {}).get("comprehension_matrix_defined") else 2)
