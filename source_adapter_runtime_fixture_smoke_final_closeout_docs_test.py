from __future__ import annotations

from pathlib import Path


def test_docs_cover_fixture_smoke_closeout_terms() -> None:
    text = Path("SOURCE_ADAPTER_RUNTIME_FIXTURE_SMOKE_FINAL_CLOSEOUT.md").read_text(encoding="utf-8")
    required = [
        "Runtime Fixture Smoke Final Closeout",
        "dry-run runtime receipts",
        "priority fixture execution matrix",
        "manual/live smoke runbook",
        "runtime roadmap coverage closeout",
        "KEYS/ACCOUNTS",
        "operator-approved manual/live smoke",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


if __name__ == "__main__":
    test_docs_cover_fixture_smoke_closeout_terms()
    print("Source Adapter Runtime Fixture Smoke Final Closeout docs self-test passed.")
