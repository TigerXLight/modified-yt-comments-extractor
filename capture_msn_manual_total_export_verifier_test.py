from __future__ import annotations

from capture_msn_manual_total_export_verifier import verify_msn_manual_total_export_cli_result


def test_verifier_accepts_safe_cli_shape() -> None:
    report = verify_msn_manual_total_export_cli_result(
        {
            "packet": {
                "package_id": "msn_pkg",
                "comment_count": 2,
                "total_export_manifest_implemented": True,
                "ready_for_total_export_review": True,
                "completed_capture_claimed": False,
                "verified_capture_claimed": False,
            },
            "store_result": {
                "files": [
                    {"file_name": "metadata/msn_pkg_manifest.json", "role": "total_export_manifest_json"},
                    {"file_name": "page_capture/msn_pkg_article_text.txt", "role": "article_text"},
                    {"file_name": "metadata/msn_pkg_msn_manual_capture_bundle.json", "role": "capture_bundle_json"},
                ]
            },
        }
    )
    assert report.verdict == "MSN_MANUAL_TOTAL_EXPORT_READY_FOR_REVIEW"
    assert report.total_export_manifest_present is True
    assert report.full_local_path_serialized is False


def test_verifier_rejects_full_path_leak() -> None:
    report = verify_msn_manual_total_export_cli_result(
        {
            "packet": {"package_id": "bad", "total_export_manifest_implemented": True, "ready_for_total_export_review": True},
            "store_result": {"files": [{"file_name": "C:\\Users\\fahad\\secret.json"}]},
        }
    )
    assert report.verdict == "MSN_MANUAL_TOTAL_EXPORT_NEEDS_REVIEW"
    assert report.full_local_path_serialized is True


if __name__ == "__main__":
    test_verifier_accepts_safe_cli_shape()
    test_verifier_rejects_full_path_leak()
    print("MSN manual Total Export verifier self-test passed.")
