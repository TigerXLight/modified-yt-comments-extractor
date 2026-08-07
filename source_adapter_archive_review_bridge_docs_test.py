from __future__ import annotations

from pathlib import Path


def main() -> None:
    text = Path("SOURCE_ADAPTER_ARCHIVE_REVIEW_BRIDGE.md").read_text(encoding="utf-8")
    assert "source_adapter_archive_review_bridge.py" in text
    assert "source_archive_review" in text
    assert "source_pipeline_closeout" in text
    assert "per-archive-result-intake decisions" in text


if __name__ == "__main__":
    main()
    print("Source Adapter Archive Review Bridge docs self-test passed.")
