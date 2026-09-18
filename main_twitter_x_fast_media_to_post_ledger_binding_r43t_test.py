from __future__ import annotations

import tempfile
from pathlib import Path

from profile_media_twitter_x_fast_media_to_post_ledger_binding_r43t import (
    R43T_PASS_STATUS,
    build_report,
)


def test_main_r43t_fast_media_binding_report_surface() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = build_report(Path(tmp) / "r43t_report")
        assert result.status == R43T_PASS_STATUS
        assert result.summary["bound_media_count"] >= 1
        assert result.summary["unbound_media_count"] >= 1


if __name__ == "__main__":
    test_main_r43t_fast_media_binding_report_surface()
    print("main R43T test passed")
