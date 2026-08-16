from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.run_project_capabilities_audit_cli_v76m import build_audit_payload


ROOT = Path(__file__).resolve().parent
REQUIRED_DOCS = (
    "PROJECT_CURRENT_CAPABILITIES_AND_FUNCTIONS_V76M.md",
    "PROJECT_FUNCTION_INDEX_V76M.md",
    "PROJECT_SCREENSHOT_ARCHIVE_CAPABILITIES_V76M.md",
    "PROFILE_MEDIA_DATABASE_CURRENT_CAPABILITIES_V76M.md",
    "PROJECT_CAPABILITY_GAPS_AND_NEXT_STEPS_V76M.md",
)
REQUIRED_TAGS = (
    "IMPLEMENTED",
    "PARTIAL",
    "TESTED",
    "REFERENCE_ONLY",
    "BLOCKED_BY_DEPENDENCY",
    "NEEDS_MANUAL_REVIEW",
)


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_required_docs_exist_and_have_major_sections() -> None:
    for name in REQUIRED_DOCS:
        path = ROOT / name
        assert path.is_file(), name
        text = path.read_text(encoding="utf-8")
        assert "# " in text, name
        assert "IMPLEMENTED" in text, name

    overview = _read("PROJECT_CURRENT_CAPABILITIES_AND_FUNCTIONS_V76M.md")
    for section in (
        "YouTube",
        "ASR",
        "Screenshots",
        "Offline Archive",
        "Twitter",
        "Total Export",
        "Profile / Media Database",
        "Article Extraction Adapter",
        "Confirmation Gates",
    ):
        assert section in overview, section


def test_docs_distinguish_implemented_from_reference_only() -> None:
    combined = "\n".join(_read(name) for name in REQUIRED_DOCS)
    for tag in REQUIRED_TAGS:
        assert tag in combined, tag
    assert "external_reference_sources_20260816_article_extraction/" in combined
    assert "REFERENCE_ONLY" in combined
    assert "Do not vendor" not in combined or "not vendored" in combined


def test_profile_media_wording_corrections_are_present() -> None:
    text = _read("PROFILE_MEDIA_DATABASE_CURRENT_CAPABILITIES_V76M.md")
    assert "Save to HOME" in text
    assert "Batch JSON exists as an internal/intermediate format" in text
    assert "A case is action/event/type/time/source-context driven" in text
    assert "Extraction libraries gather metadata/content" in text
    assert "FEVER" in text and "not product classification logic" in text


def test_acceptance_matrix_and_cli_safety_flags() -> None:
    matrix_path = ROOT / "testdata" / "project_capabilities_v76m_acceptance_matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    assert matrix["schema_version"] == "project-capabilities-v76m-acceptance-matrix"
    assert "capability_areas" in matrix
    payload = build_audit_payload()
    assert payload["repo_source_inventory_scan"] is True
    assert payload["folder_scan_performed"] is False
    assert payload["media_download_performed"] is False
    assert payload["web_download_performed"] is False
    assert payload["automatic_classification_performed"] is False
    assert payload["sensitive_identifier_inference_performed"] is False


def test_external_reference_folder_not_tracked() -> None:
    completed = subprocess.run(
        ["git", "ls-files", "external_reference_sources_20260816_article_extraction"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == ""


if __name__ == "__main__":
    test_required_docs_exist_and_have_major_sections()
    test_docs_distinguish_implemented_from_reference_only()
    test_profile_media_wording_corrections_are_present()
    test_acceptance_matrix_and_cli_safety_flags()
    test_external_reference_folder_not_tracked()
    print("project_capabilities_audit_v76m_test: OK")

