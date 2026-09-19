
from __future__ import annotations

import tempfile
from pathlib import Path

import profile_media_reddit_source_adapter_layer_closeout_r44n as r44n


def test_build_closeout_contract():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name in r44n.REQUIRED_LAYER_FILES:
            (root / name).write_text("# fixture\n", encoding="utf-8")
        out = root / "out"
        result = r44n.build_closeout(root, out)
        assert result["status"] == r44n.STATUS
        assert result["contract"]["primary_method"] == "signed_in_en_reddit_target_then_branch_link_queue"
        assert result["contract"]["cookie_or_token_extraction_enabled"] is False
        assert result["contract"]["login_automation_enabled"] is False
        assert "R44L current www.reddit.com link queue remains secondary fallback only." in result["contract"]["secondary_fallback"]
        assert Path(result["receipt_path"]).exists()
        assert Path(result["summary_markdown_path"]).exists()


def test_missing_layer_files_block():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        try:
            r44n.build_closeout(root, root / "out")
        except SystemExit as exc:
            assert "MISSING_FILES" in str(exc)
        else:
            raise AssertionError("expected SystemExit for missing files")


if __name__ == "__main__":
    test_build_closeout_contract()
    test_missing_layer_files_block()
    print("profile_media_reddit_source_adapter_layer_closeout_r44n_test: PASS")
