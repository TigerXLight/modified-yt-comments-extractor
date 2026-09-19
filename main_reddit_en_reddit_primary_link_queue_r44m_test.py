#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def run_self_test() -> None:
    text = Path("main.py").read_text(encoding="utf-8", errors="replace")
    assert "R44M_REDDIT_EN_REDDIT_PRIMARY_LINK_QUEUE" in text
    assert "reddit_en_reddit_primary_link_queue_r44m" in text
    assert "build_reddit_en_reddit_primary_link_queue_contract_r44m" in text
    assert "signed-in en.reddit.com primary route" in text
    print("main_reddit_en_reddit_primary_link_queue_r44m_test: PASS")


if __name__ == "__main__":
    run_self_test()
