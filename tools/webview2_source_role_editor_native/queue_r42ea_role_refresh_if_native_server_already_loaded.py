from __future__ import annotations
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_archive_role_payload_r42dw import build_latest_archive_role_payload
from profile_media_archive_role_refresh_live_spool_r42ea import spool_live_role_overlay_refresh_if_server_ready

if __name__ == "__main__":
    out_root = ROOT / "profile_media_live_captures" / "r42ea_archive_role_refresh_live_spool"
    payload = build_latest_archive_role_payload(
        project_root=ROOT,
        source_url="https://archive.ph/6mr3C",
        output_root=out_root,
        text_paint_style="recolor" if "--recolor" in sys.argv else "",
    )
    result = spool_live_role_overlay_refresh_if_server_ready(
        project_root=ROOT,
        payload_path=payload.get("payload_path") or "",
        changes_path=payload.get("changes_path") or str(out_root / "archive_role_overlay_changes_r42ea.jsonl"),
        selected_url=payload.get("source_url") or "https://archive.ph/6mr3C",
        dry_run=False,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
