from __future__ import annotations

import json
import tempfile
from pathlib import Path

from capture_msn_manual_evidence_review_package import build_msn_manual_evidence_review_package
from capture_msn_manual_evidence_review_package_store import (
    store_msn_manual_evidence_review_package,
    msn_manual_evidence_review_package_store_report_to_json,
)


def main() -> None:
    queue_report = {
        "queue_item": {
            "queue_item_id": "msn-review-store",
            "source_url": "https://www.msn.com/example",
            "article_title": "Store example",
            "assets": [
                {"role": "article_text", "filename": "article.txt", "sha256": "a" * 64, "byte_count": 1},
                {"role": "total_export_manifest", "filename": "manifest.json", "sha256": "b" * 64, "byte_count": 2},
            ],
        }
    }
    package = build_msn_manual_evidence_review_package(queue_report)
    with tempfile.TemporaryDirectory() as tmp:
        report = store_msn_manual_evidence_review_package(package, tmp)
        assert report.output_file_count == 2
        for stored in report.stored_files:
            assert Path(tmp, stored.filename).exists()
            assert stored.byte_count == len(Path(tmp, stored.filename).read_bytes())
        encoded = msn_manual_evidence_review_package_store_report_to_json(report)
        decoded = json.loads(encoded)
        assert decoded["queue_item_id"] == "msn-review-store"
        assert str(tmp) not in encoded
    print("MSN manual Evidence Review package store self-test passed.")


if __name__ == "__main__":
    main()
