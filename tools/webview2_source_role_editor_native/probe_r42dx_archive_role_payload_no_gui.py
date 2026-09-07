from __future__ import annotations

from pathlib import Path
from datetime import datetime
from collections import Counter
import json
import os
import re
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_archive_role_payload_r42dw import (
    build_latest_archive_role_payload,
    find_latest_archive_surface,
)

SOURCE = "https://archive.ph/6mr3C"
OUTROOT = ROOT / "profile_media_live_captures" / "r42dx_cmdline_archive_role_payload"
OUTROOT.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"_error": repr(exc), "_path": str(path)}


def _canonical(v: object) -> str:
    s = " ".join(str(v or "").split())
    m = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)$", s)
    if m:
        s = m.group(2)
    return s.strip().strip('"').strip("'")


def _candidate_files(base: Path, name: str) -> list[Path]:
    if not base.exists():
        return []
    files = [p for p in base.rglob(name) if p.is_file()]
    # Prefer semantic creation/folder names over extraction mtime.
    files.sort(key=lambda p: (p.parent.name, p.name), reverse=True)
    return files


def _summarize_material_captures() -> dict[str, Any]:
    base = ROOT / "profile_media_live_captures" / "r42ct_archive_source_material"
    out: dict[str, Any] = {
        "base": str(base),
        "present": base.exists(),
        "good_lowercase_success_count": 0,
        "bad_or_failed_mixed_case_count": 0,
        "latest_good_lowercase_capture": {},
        "all_seen_count": 0,
    }
    latest_good: tuple[str, Path, Mapping[str, Any]] | None = None
    for p in _candidate_files(base, "native_webview2_material_capture.json"):
        data = _read_json(p)
        src = _canonical(data.get("source_url") or data.get("visible_url") or "")
        status = str(data.get("status") or "").lower()
        text_len = int(data.get("text_length") or data.get("text_len") or 0)
        out["all_seen_count"] += 1
        key = p.parent.name
        is_lower = src == SOURCE or "6mr3C" in key
        is_mixed = src == "https://archive.ph/6Mr3C" or "6Mr3C" in key
        if is_lower and status == "success" and text_len > 1000:
            out["good_lowercase_success_count"] += 1
            if latest_good is None or key > latest_good[0]:
                latest_good = (key, p, data)
        if is_mixed or status in {"material_unavailable_access_gate", "access_blocked_challenge"}:
            out["bad_or_failed_mixed_case_count"] += 1
    if latest_good:
        key, p, data = latest_good
        article_path = data.get("article_text_path") or ""
        article = Path(article_path)
        out["latest_good_lowercase_capture"] = {
            "folder": key,
            "path": str(p),
            "status": data.get("status"),
            "source_url": data.get("source_url"),
            "page_title": data.get("page_title"),
            "text_length": data.get("text_length"),
            "html_length": data.get("html_length"),
            "article_text_path": article_path,
            "article_text_exists": article.is_file(),
            "article_text_bytes": article.stat().st_size if article.is_file() else 0,
        }
    return out


def _summarize_payload(path: Path | None) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {"present": False}
    rows = data.get("rows_by_mode") if isinstance(data.get("rows_by_mode"), dict) else {}
    sem = rows.get("semantic") if isinstance(rows, dict) and isinstance(rows.get("semantic"), list) else []
    med = rows.get("media") if isinstance(rows, dict) and isinstance(rows.get("media"), list) else []
    def counts(rs):
        c = Counter(str((r or {}).get("active_role") or (r or {}).get("role") or "UNKNOWN").upper() for r in rs)
        return {k: int(c.get(k, 0)) for k in ("PRIMARY", "SECONDARY", "TERTIARY", "UNKNOWN", "BLANK")}
    return {
        "present": True,
        "path": str(path),
        "bytes": path.stat().st_size if path else 0,
        "selected_url": data.get("selected_url"),
        "launch_start_url": data.get("launch_start_url"),
        "semantic_rows": len(sem),
        "media_rows": len(med),
        "semantic_counts": counts(sem),
        "media_counts": counts(med),
        "text_paint_style": data.get("text_paint_style") or "",
        "first_semantic_text": (sem[0].get("text") if sem else ""),
    }


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = OUTROOT / ("probe_" + stamp)
    outdir.mkdir(parents=True, exist_ok=True)

    material_summary = _summarize_material_captures()
    surface_path = find_latest_archive_surface(project_root=ROOT, source_url=SOURCE)
    surface = _read_json(surface_path)
    result = build_latest_archive_role_payload(
        project_root=ROOT,
        source_url=SOURCE,
        output_root=OUTROOT,
        text_paint_style=os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", "").strip(),
    )
    generated_payload = _summarize_payload(Path(result.get("payload_path", "")) if result.get("payload_path") else None)

    # Find the empty material-capture payloads that were opening WebView2 first.
    base = ROOT / "profile_media_live_captures" / "r42ct_archive_source_material"
    material_payloads = _candidate_files(base, "native_webview2_material_payload.json")
    latest_material_payload = material_payloads[0] if material_payloads else None

    summary = {
        "schema": "ytce.r42dx.cmdline_archive_role_payload_no_gui_probe.v1",
        "created_at_local": datetime.now().replace(microsecond=0).isoformat(),
        "mode": "NO_GUI_NO_NETWORK_REPLAY",
        "source": SOURCE,
        "do_not_open_app_for_this_probe": True,
        "network_actions_performed": False,
        "native_webview2_started": False,
        "archive_ph_hit": False,
        "material_capture_summary": material_summary,
        "selected_r42ds_surface": {
            "path": str(surface_path) if surface_path else "",
            "span_count": surface.get("span_count"),
            "role_counts": surface.get("role_counts"),
            "source_url": surface.get("source_url"),
            "canonical_source": surface.get("canonical_source"),
            "article_status": surface.get("article_status"),
            "browser_status": surface.get("browser_status"),
        },
        "material_capture_payload_before_role_refresh": _summarize_payload(latest_material_payload),
        "r42dx_generated_role_ready_payload": generated_payload,
        "r42dw_build_result": result,
        "cmdline_verdict": {
            "import_path_fixed": True,
            "has_good_archive_material": bool(material_summary.get("good_lowercase_success_count", 0) > 0),
            "surface_has_spans": bool(int(surface.get("span_count") or 0) > 0),
            "role_ready_payload_has_rows": bool(generated_payload.get("semantic_rows", 0) > 0 and generated_payload.get("media_rows", 0) > 0),
            "safe_to_continue_without_archive_hits": True,
            "avoid_mixed_case_test_url": "https://archive.ph/6Mr3C",
            "use_only_raw_lowercase_test_url": SOURCE,
        },
    }
    out = outdir / "r42dx_cmdline_archive_role_payload_no_gui_probe_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Compact display: full JSON still written to disk.
    display = {
        "mode": summary["mode"],
        "source": SOURCE,
        "good_lowercase_success_count": material_summary.get("good_lowercase_success_count"),
        "latest_good_capture_status": (material_summary.get("latest_good_lowercase_capture") or {}).get("status"),
        "latest_good_text_length": (material_summary.get("latest_good_lowercase_capture") or {}).get("text_length"),
        "selected_surface_span_count": surface.get("span_count"),
        "selected_surface_role_counts": surface.get("role_counts"),
        "generated_semantic_rows": generated_payload.get("semantic_rows"),
        "generated_media_rows": generated_payload.get("media_rows"),
        "generated_semantic_counts": generated_payload.get("semantic_counts"),
        "generated_media_counts": generated_payload.get("media_counts"),
        "payload_path": generated_payload.get("path"),
        "outdir": str(outdir),
        "archive_ph_hit": False,
        "native_webview2_started": False,
    }
    print(json.dumps(display, ensure_ascii=False, indent=2))

    if not result.get("ok"):
        return 2
    if int(generated_payload.get("semantic_rows") or 0) <= 0:
        return 3
    if int(generated_payload.get("media_rows") or 0) <= 0:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
