from __future__ import annotations

from pathlib import Path
import json
import tempfile

from profile_media_semantic_media_logic_matrix_r42ed import (
    SOURCE,
    build_semantic_media_logic_adapter_matrix,
    find_latest_role_payload,
    run_self_test,
)


def test_bounded_payload_scan_no_rglob_failure() -> None:
    run_self_test()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        payload_dir = root / "profile_media_live_captures" / "r42ec_archive_role_closeout_no_gui" / "20260907_fixture"
        payload_dir.mkdir(parents=True)
        payload = payload_dir / "archive_role_overlay_payload_r42dw.json"
        payload.write_text(json.dumps({
            "selected_url": SOURCE,
            "rows_by_mode": {
                "semantic": [{"text": "reported by article", "active_role": "SECONDARY"}],
                "media": [{"text": "video clip", "active_role": "SECONDARY"}],
            },
            "counts_by_mode": {
                "semantic": {"PRIMARY": 0, "SECONDARY": 1, "TERTIARY": 0, "UNKNOWN": 0},
                "media": {"PRIMARY": 0, "SECONDARY": 1, "TERTIARY": 0, "UNKNOWN": 0},
            },
        }), encoding="utf-8")
        # Best-effort loop fixture.  It may fail on Windows without Developer Mode/admin;
        # the test still proves the normal bounded search path.
        loop = root / "profile_media_live_captures" / "r42ec_archive_role_closeout_no_gui" / "loop"
        try:
            loop.symlink_to(root / "profile_media_live_captures", target_is_directory=True)
        except Exception:
            pass
        found = find_latest_role_payload(root, SOURCE)
        assert found is not None
        assert found.name == "archive_role_overlay_payload_r42dw.json"
        result = build_semantic_media_logic_adapter_matrix(project_root=root, output_root=root / "out")
        verdict = result.get("verdict", {})
        assert verdict.get("payload_found") is True
        assert verdict.get("semantic_counts_nonzero") is True
        assert verdict.get("media_counts_nonzero") is True


if __name__ == "__main__":
    test_bounded_payload_scan_no_rglob_failure()
    print("R42EE bounded payload scan hotfix tests passed.")
