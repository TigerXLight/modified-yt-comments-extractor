from __future__ import annotations

from pathlib import Path


def test_docs_cover_release_export_bundle_boundary() -> None:
    text = Path("CAPTURE_MSN_MANUAL_RELEASE_EXPORT_BUNDLE.md").read_text(encoding="utf-8")
    required = [
        "explicit JSON files only",
        "export bundle",
        "export manifest",
        "no live HTTP",
        "no browser automation",
        "no file moves",
        "no full local path serialization",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_cover_release_export_bundle_boundary()
    print("MSN manual release export bundle docs self-test passed.")
