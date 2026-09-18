from __future__ import annotations

import json
import tempfile
from pathlib import Path

from profile_media_twitter_x_live_profile_lock_preflight_r43s import (
    R43S_MARKER,
    R43S_PASS_STATUS,
    build_report,
)


def test_main_import_preserves_r43s_profile_preflight_surface() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build_report(Path(tmp) / "r43s_main")
        assert report["marker"] == R43S_MARKER
        assert report["status"] == R43S_PASS_STATUS
        assert report["bad_checks"] == ()
        payload = json.loads((Path(tmp) / "r43s_main" / "R43S_TWITTER_X_LIVE_PROFILE_LOCK_PREFLIGHT_REPORT.json").read_text(encoding="utf-8"))
        assert payload["profile_preflight_summary"]["profile_preflight_status"] == "PASS_PROFILE_PREFLIGHT"
        main_source = Path("main.py").read_text(encoding="utf-8")
        assert "R43S_TWITTER_X_LIVE_PROFILE_LOCK_PREFLIGHT" in main_source
        assert "twitter_x_live_profile_lock_preflight_r43s" in main_source


if __name__ == "__main__":
    test_main_import_preserves_r43s_profile_preflight_surface()
    print("main R43S tests passed")
