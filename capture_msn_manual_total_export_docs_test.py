from __future__ import annotations

from pathlib import Path


def test_docs_describe_implemented_total_export_flow() -> None:
    text = Path("CAPTURE_MSN_MANUAL_TOTAL_EXPORT_INTEGRATION.md").read_text(encoding="utf-8")
    required = [
        "Total Export data path",
        "explicitly supplied operator artifacts",
        "article text, comments JSON, bundle JSON, and manifest JSON",
        "no folder scans",
        "not an observation-only record",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_describe_implemented_total_export_flow()
    print("MSN manual Total Export integration docs self-test passed.")
