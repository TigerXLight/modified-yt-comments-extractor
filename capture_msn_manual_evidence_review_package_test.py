from __future__ import annotations

import json

from capture_msn_manual_evidence_review_package import (
    MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION,
    MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING,
    build_msn_manual_evidence_review_package,
    msn_manual_evidence_review_package_to_json,
)


def _sample_queue_report() -> dict:
    return {
        "queue_item": {
            "queue_item_id": "msn-example-001",
            "source_url": "https://www.msn.com/en-gb/news/example",
            "named_site": "msn",
            "named_action": "msn_article_and_comments",
            "article_title": "Example MSN story",
            "assets": [
                {"role": "article_text", "filename": r"T:\\unsafe\\article.txt", "sha256": "a" * 64, "byte_count": 44},
                {"role": "comments_json", "filename": "comments.json", "sha256": "b" * 64, "byte_count": 55},
                {"role": "total_export_manifest", "filename": "manifest.json", "sha256": "c" * 64, "byte_count": 66},
            ],
        },
        "issue_count": 0,
    }


def main() -> None:
    package = build_msn_manual_evidence_review_package(_sample_queue_report(), reviewer_id="reviewer 1", notes=["ready"])
    assert package.schema_version == MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_SCHEMA_VERSION
    assert package.review_status == MSN_MANUAL_EVIDENCE_REVIEW_PACKAGE_STATUS_PENDING
    assert package.queue_item_id == "msn-example-001"
    assert package.assets[0].filename == "article.txt"
    assert package.safety_flags["no_full_local_paths"] is True
    assert package.safety_flags["required_asset_roles_present"] is True
    assert len(package.review_actions) >= 6
    encoded = msn_manual_evidence_review_package_to_json(package)
    decoded = json.loads(encoded)
    assert decoded["package_hash"] == package.package_hash
    assert "T:\\" not in encoded
    print("MSN manual Evidence Review package self-test passed.")


if __name__ == "__main__":
    main()
