
from __future__ import annotations

from pathlib import Path


def test_main_registration_marker_present():
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R44N_REDDIT_SOURCE_ADAPTER_LAYER_CLOSEOUT" in text
    assert "reddit_source_adapter_layer_closeout" in text
    assert "profile_media_reddit_source_adapter_layer_closeout_r44n" in text


if __name__ == "__main__":
    test_main_registration_marker_present()
    print("main_reddit_source_adapter_layer_closeout_r44n_test: PASS")
