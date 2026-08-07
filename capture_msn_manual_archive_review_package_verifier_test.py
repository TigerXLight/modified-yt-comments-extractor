from capture_msn_manual_archive_review_package import build_msn_manual_archive_review_package
from capture_msn_manual_archive_review_package_cli import _fixture_intake
from capture_msn_manual_archive_review_package_verifier import verify_msn_manual_archive_review_package


def test_verifier_accepts_ready_archive_review_package():
    package = build_msn_manual_archive_review_package(_fixture_intake())
    result = verify_msn_manual_archive_review_package(package)
    assert result["verified"] is True
    assert result["issue_count"] == 0


def test_verifier_rejects_package_with_readiness_issues():
    package = build_msn_manual_archive_review_package(_fixture_intake())
    package["readiness_issues"] = ["manual_issue"]
    result = verify_msn_manual_archive_review_package(package)
    assert result["verified"] is False
    assert "readiness_issues_present" in result["issues"]


if __name__ == "__main__":
    test_verifier_accepts_ready_archive_review_package()
    test_verifier_rejects_package_with_readiness_issues()
    print("MSN manual archive review package verifier self-test passed.")
