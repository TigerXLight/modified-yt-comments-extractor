from __future__ import annotations

import json

from capture_msn_manual_evidence_review_package import (
    build_msn_manual_evidence_review_package,
    msn_manual_evidence_review_package_to_json,
)
from capture_msn_manual_evidence_review_package_verifier import (
    MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERDICT_READY,
    verify_msn_manual_evidence_review_package,
)


def main() -> None:
    package = build_msn_manual_evidence_review_package(
        {
            "queue_item": {
                "queue_item_id": "verify-review",
                "source_url": "https://www.msn.com/example",
                "article_title": "Verifier example",
                "assets": [
                    {"role": "article_text", "filename": "article.txt", "sha256": "a" * 64, "byte_count": 1},
                    {"role": "total_export_manifest", "filename": "manifest.json", "sha256": "b" * 64, "byte_count": 2},
                ],
            }
        }
    )
    report = verify_msn_manual_evidence_review_package(json.loads(msn_manual_evidence_review_package_to_json(package)))
    assert report.verdict == MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_VERDICT_READY
    assert report.issue_count == 0
    assert report.asset_count == 2
    print("MSN manual Evidence Review package verifier self-test passed.")


if __name__ == "__main__":
    main()
