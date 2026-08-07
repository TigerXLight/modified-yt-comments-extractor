from pathlib import Path


def test_docs_cover_release_pipeline_closeout():
    text = Path("CAPTURE_MSN_MANUAL_RELEASE_PIPELINE_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "MSN manual release pipeline closeout",
        "Total Export package creation",
        "Evidence Queue handoff",
        "approved release package",
        "release section closeout",
        "does not perform browser automation",
        "credential access",
    ]
    for phrase in required:
        assert phrase in text


if __name__ == "__main__":
    test_docs_cover_release_pipeline_closeout()
    print("MSN manual release pipeline closeout docs self-test passed.")
