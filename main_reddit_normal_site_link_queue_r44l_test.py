#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def run_self_test() -> None:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R44L_REDDIT_NORMAL_SITE_LINK_QUEUE_FALLBACK" in text
    assert "reddit_normal_site_link_queue_fallback_r44l" in text
    assert "build_reddit_normal_site_link_queue_contract_r44l" in text
    print("main_reddit_normal_site_link_queue_r44l_test: PASS")


if __name__ == "__main__":
    run_self_test()
