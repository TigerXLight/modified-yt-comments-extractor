from __future__ import annotations

from pathlib import Path


def test_main_registers_r43r_materializer_without_browser_side_effects() -> None:
    source = Path("main.py").read_text(encoding="utf-8")
    assert "twitter_x_live_evidence_to_account_ledger_r43r" in source
    assert "materialize_live_twitter_x_evidence_to_account_ledger_r43r" in source
    assert "does not launch browsers" in source


def test_r43r_does_not_create_parallel_control_plane() -> None:
    source = Path("profile_media_twitter_x_live_evidence_to_account_ledger_r43r.py").read_text(encoding="utf-8")
    assert "write_twitter_x_account_media_ledger_r43a" in source
    assert "remote_media_downloads_performed_by_r43r" in source
    assert "browser_session_started_by_r43r" in source


if __name__ == "__main__":
    test_main_registers_r43r_materializer_without_browser_side_effects()
    test_r43r_does_not_create_parallel_control_plane()
    print("main R43R tests passed")
