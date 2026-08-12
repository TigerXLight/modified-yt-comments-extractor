from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_offline_viewer_for_closeout(output_root: str | Path) -> dict[str, Any]:
    from source_offline_evidence_viewer import generate_offline_backup_viewer
    return generate_offline_backup_viewer(output_root)


def patch_result_with_offline_viewer(result: Any, output_root: str | Path | None = None) -> Any:
    if output_root is None:
        if isinstance(result, dict):
            output_root = result.get("output_root") or result.get("OUTPUT_ROOT") or result.get("output_dir") or result.get("OUTPUT_DIR")
        else:
            output_root = getattr(result, "output_root", None) or getattr(result, "OUTPUT_ROOT", None)
    if not output_root:
        return result
    try:
        generated = generate_offline_viewer_for_closeout(output_root)
        print("OFFLINE_BACKUP_VIEWER_HTML:", generated.get("offline_backup_viewer_html"))
        print("OFFLINE_BACKUP_MANIFEST_JSON:", generated.get("offline_backup_manifest_json"))
        print("OPEN_OFFLINE_BACKUP_VIEWER_CMD:", generated.get("open_offline_backup_viewer_cmd"))
        if isinstance(result, dict):
            result["OFFLINE_BACKUP_VIEWER_HTML"] = generated.get("offline_backup_viewer_html")
            result["OFFLINE_BACKUP_MANIFEST_JSON"] = generated.get("offline_backup_manifest_json")
            result["OPEN_OFFLINE_BACKUP_VIEWER_CMD"] = generated.get("open_offline_backup_viewer_cmd")
    except Exception as exc:
        print("OFFLINE_BACKUP_VIEWER_WARNING:", repr(exc))
        if isinstance(result, dict):
            warnings = result.setdefault("warnings", [])
            if isinstance(warnings, list):
                warnings.append(f"offline_backup_viewer_failed:{exc!r}")
    return result
