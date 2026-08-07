from __future__ import annotations

from pathlib import Path


DOC_EXPECTATIONS = {
    "ACCESS_KEYS_MANAGER_SPEC.md": (
        "Sidebar button: `KEYS/ACCOUNTS`",
        "Implemented Online ASR KEYS/ACCOUNTS Review Chain",
        "Search inside `Add a provider` searches the full catalogue.",
    ),
    "CURRENT_DEV_STATE.md": (
        "Online ASR KEYS/ACCOUNTS Release-Section Closeout",
        "635b3a1 Add Online ASR Keys Accounts release section closeout",
        "continue roadmap work through section-level mega patches",
    ),
    "PROJECT_CURRENT_STATE_HANDOFF.md": (
        "Online ASR KEYS/ACCOUNTS Review-Release Section Closeout",
        "larger section-level mega patches",
        "No provider/API calls, background key tests, media uploads",
    ),
    "SOURCE_EVIDENCE_ROADMAP.md": (
        "Online ASR KEYS/ACCOUNTS Review Release-Section Closeout",
        "metadata-only Online ASR KEYS/ACCOUNTS review-release section is closed at `635b3a1`",
        "Stored report results return safe filenames, hashes, byte counts",
    ),
    "SOURCE_EVIDENCE_ROADMAP_COVERAGE_AUDIT.md": (
        "Online ASR KEYS/ACCOUNTS review-release section closeout",
        "Online ASR KEYS/ACCOUNTS metadata-only release-section closeout through `635b3a1` are complete",
        "no-secrets, no-provider-calls, no-raw-media, no-full-paths",
    ),
    "ONLINE_ASR_KEYS_ACCOUNTS_RELEASE_SECTION_CLOSEOUT.md": (
        "Commit checkpoint: `635b3a1 Add Online ASR Keys Accounts release section closeout`",
        "Main sidebar label: `KEYS/ACCOUNTS`",
        "Future roadmap work should proceed in larger section-level mega patches",
    ),
}


def _read_doc(name: str) -> str:
    return Path(name).read_text(encoding="utf-8")


def test_online_asr_keys_accounts_release_docs_closeout_markers() -> None:
    for filename, markers in DOC_EXPECTATIONS.items():
        text = _read_doc(filename)
        for marker in markers:
            assert marker in text, f"missing marker in {filename}: {marker}"


def test_online_asr_keys_accounts_docs_do_not_claim_new_runtime_execution() -> None:
    combined = "\n".join(_read_doc(filename) for filename in DOC_EXPECTATIONS)
    required_boundaries = (
        "does not add runtime provider calls",
        "does not read credential values",
        "Provider/API calls are not performed",
        "Completed or verified transcription is not claimed",
        "not approval for broader provider/API behavior",
    )
    for boundary in required_boundaries:
        assert boundary in combined


if __name__ == "__main__":
    test_online_asr_keys_accounts_release_docs_closeout_markers()
    test_online_asr_keys_accounts_docs_do_not_claim_new_runtime_execution()
    print("Online ASR KEYS/ACCOUNTS release docs closeout self-test passed.")
