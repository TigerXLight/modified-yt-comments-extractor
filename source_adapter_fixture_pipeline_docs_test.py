from __future__ import annotations

from pathlib import Path


def test_fixture_pipeline_docs_cover_local_safety_and_outputs() -> None:
    text = Path("SOURCE_ADAPTER_FIXTURE_PIPELINE.md").read_text(encoding="utf-8")
    required = [
        "Source Adapter Fixture Pipeline",
        "local-only",
        "does not fetch URLs",
        "source_adapter_fixture_pipeline.py",
        "source_adapter_fixture_pipeline_cli.py",
        "source_adapter_fixture_pipeline_verifier.py",
        "fixture pipeline closeout handoff",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_fixture_pipeline_docs_cover_local_safety_and_outputs()
    print("Source Adapter Fixture Pipeline docs self-test passed.")
