from __future__ import annotations

from pathlib import Path


def main() -> None:
    doc = Path("SOURCE_ADAPTER_PRIORITY_FIXTURE_PACK_IMPLEMENTATION.md").read_text(encoding="utf-8")
    assert "Priority Fixture Pack Implementation" in doc
    assert "KEYS/ACCOUNTS" in doc
    assert "operator-approved" in doc
    print("Source Adapter Priority Fixture Pack Implementation docs self-test passed.")


if __name__ == "__main__":
    main()
