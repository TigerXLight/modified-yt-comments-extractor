from __future__ import annotations

from pathlib import Path


def test_docs_record_safety_boundary() -> None:
    text = Path("SOURCE_ADAPTER_ARTIFACT_INTAKE.md").read_text(encoding="utf-8")
    assert "explicit local artifact file bindings" in text
    assert "does not fetch URLs" in text
    assert "does not" in text and "scan folders" in text
    assert "only reads explicit operator-supplied local artifact paths" in text


if __name__ == "__main__":
    test_docs_record_safety_boundary()
    print("Source Adapter Artifact Intake docs self-test passed.")
