from __future__ import annotations

import json
import tempfile
from pathlib import Path

from source_offline_evidence_viewer_closeout_integration import patch_result_with_offline_viewer


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "comments.json").write_text(json.dumps([{"text":"ok"}]), encoding="utf-8")
        result = {"OUTPUT_ROOT": str(root)}
        out = patch_result_with_offline_viewer(result)
        assert (root / "offline_backup_viewer.html").exists()
        assert (root / "offline_backup_manifest.json").exists()
        assert out.get("OFFLINE_BACKUP_VIEWER_HTML")
    print("source_offline_evidence_viewer_closeout_integration_test OK")


if __name__ == "__main__":
    main()
