from __future__ import annotations
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from profile_media_archive_role_refresh_live_spool_r42ea import build_no_gui_probe

if __name__ == "__main__":
    recolor = "--recolor" in sys.argv
    result = build_no_gui_probe(project_root=ROOT, source_url="https://archive.ph/6mr3C", recolor=recolor)
    print(json.dumps(result, ensure_ascii=False, indent=2))
