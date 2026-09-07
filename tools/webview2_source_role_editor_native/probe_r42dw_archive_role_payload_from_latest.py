from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_archive_role_payload_r42dw import build_latest_archive_role_payload

OUTROOT = ROOT / "profile_media_live_captures" / "r42dw_archive_role_payload"
OUTROOT.mkdir(parents=True, exist_ok=True)
SOURCE = "https://archive.ph/6mr3C"


def _latest_file(base: Path, name: str) -> Path | None:
    if not base.exists():
        return None
    items = [p for p in base.rglob(name) if p.is_file()]
    items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return items[0] if items else None


def _payload_counts(path: Path | None) -> dict[str, object]:
    if not path or not path.is_file():
        return {"present": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        rows = data.get("rows_by_mode") if isinstance(data, dict) else {}
        sem = rows.get("semantic") if isinstance(rows, dict) else []
        med = rows.get("media") if isinstance(rows, dict) else []
        return {
            "present": True,
            "path": str(path),
            "bytes": path.stat().st_size,
            "semantic_rows": len(sem) if isinstance(sem, list) else 0,
            "media_rows": len(med) if isinstance(med, list) else 0,
            "text_paint_style": str(data.get("text_paint_style") or "") if isinstance(data, dict) else "",
        }
    except Exception as exc:
        return {"present": True, "path": str(path), "error": repr(exc)}


def main() -> int:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = OUTROOT / ("probe_" + stamp)
    outdir.mkdir(parents=True, exist_ok=True)

    latest_material_payload = _latest_file(ROOT / "profile_media_live_captures" / "r42ct_archive_source_material", "native_webview2_material_payload.json")
    latest_material_capture = _latest_file(ROOT / "profile_media_live_captures" / "r42ct_archive_source_material", "native_webview2_material_capture.json")
    latest_surface = _latest_file(ROOT / "profile_media_live_captures" / "r42ds_archive_source_roles_webview2", "archive_source_role_surface_r42ds.json")

    result = build_latest_archive_role_payload(
        project_root=ROOT,
        source_url=SOURCE,
        output_root=OUTROOT,
        text_paint_style=os.environ.get("YTCE_R42DU_TEXT_PAINT_STYLE", "").strip(),
    )
    summary = {
        "mode": "probe",
        "schema": "ytce.r42dw.archive_role_payload_probe.v1",
        "outdir": str(outdir),
        "source_url": SOURCE,
        "archive_ph_hit": False,
        "native_webview2_started": False,
        "material_capture_path": str(latest_material_capture) if latest_material_capture else "",
        "material_capture_payload_before_role_refresh": _payload_counts(latest_material_payload),
        "latest_r42ds_surface_path": str(latest_surface) if latest_surface else "",
        "r42dw_role_ready_payload": result,
        "diagnosis": {
            "material_capture_payload_can_be_empty": True,
            "role_ready_payload_should_not_be_empty": bool(result.get("semantic_rows", 0) > 0),
            "safe_for_cmd_only_testing": True,
        },
    }
    out = outdir / "r42dw_archive_role_payload_probe_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        return 2
    if int(result.get("semantic_rows") or 0) <= 0:
        return 3
    if int(result.get("media_rows") or 0) <= 0:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
