from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.run_external_reference_coverage_audit_cli_v76n import build_audit_payload


ROOT = Path(__file__).resolve().parent
REQUIRED_DOCS = (
    "EXTERNAL_REFERENCE_SOURCE_COVERAGE_AUDIT_V76N.md",
    "SCREENSHOT_ARCHIVE_REFERENCE_COVERAGE_V76N.md",
    "TWITTER_X_REFERENCE_COVERAGE_V76N.md",
    "ARTICLE_EXTRACTION_REFERENCE_COVERAGE_V76N.md",
    "PROFILE_MEDIA_SOURCE_WORKFLOW_REFERENCE_GAPS_V76N.md",
    "PROJECT_REFERENCE_COVERAGE_COMMAND_INDEX_V76N.md",
)


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_required_docs_exist_and_include_status_tags() -> None:
    combined = []
    for name in REQUIRED_DOCS:
        path = ROOT / name
        assert path.is_file(), name
        text = path.read_text(encoding="utf-8")
        assert "# " in text, name
        combined.append(text)
    all_text = "\n".join(combined)
    for phrase in (
        "IMPLEMENTED",
        "NOT_IMPLEMENTED",
        "REFERENCE_ONLY",
        "UNSAFE_OUT_OF_SCOPE",
        "DO_NOT_VENDOR",
        "DO_NOT_IMPLEMENT_WRITE_ACTION",
    ):
        assert phrase in all_text, phrase


def test_workflow_gap_phrases_are_present() -> None:
    text = _read("PROFILE_MEDIA_SOURCE_WORKFLOW_REFERENCE_GAPS_V76N.md")
    for phrase in (
        "HOME source folder",
        "witness connectivity",
        "first-person",
        "claim-subject affiliation",
    ):
        assert phrase in text, phrase


def test_article_and_twitter_policy_phrases_are_present() -> None:
    article = _read("ARTICLE_EXTRACTION_REFERENCE_COVERAGE_V76N.md")
    for phrase in ("metadata_parser", "trafilatura", "newspaper4k"):
        assert phrase in article, phrase
    twitter = _read("TWITTER_X_REFERENCE_COVERAGE_V76N.md")
    assert "DO_NOT_IMPLEMENT_WRITE_ACTION" in twitter
    assert "posting" in twitter and "deleting" in twitter and "following" in twitter


def test_acceptance_matrix_and_cli_safety_flags() -> None:
    matrix = json.loads((ROOT / "testdata" / "external_reference_coverage_v76n_acceptance_matrix.json").read_text(encoding="utf-8"))
    assert matrix["schema_version"] == "external-reference-coverage-v76n-acceptance-matrix"
    payload = build_audit_payload()
    assert payload["repo_reference_inventory_scan"] is True
    assert payload["folder_scan_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["web_download_performed"] is False
    assert payload["crawling_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False
    assert payload["references_found"] > 0
    assert payload["unsafe_out_of_scope"] > 0


def test_external_reference_folders_not_tracked() -> None:
    completed = subprocess.run(
        [
            "git",
            "ls-files",
            "external_reference_sources_20260814_234822",
            "external_reference_sources_20260816_article_extraction",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == ""


if __name__ == "__main__":
    test_required_docs_exist_and_include_status_tags()
    test_workflow_gap_phrases_are_present()
    test_article_and_twitter_policy_phrases_are_present()
    test_acceptance_matrix_and_cli_safety_flags()
    test_external_reference_folders_not_tracked()
    print("external_reference_coverage_audit_v76n_test: OK")

