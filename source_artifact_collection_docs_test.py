from __future__ import annotations

from pathlib import Path


def test_docs_state_shared_adapter_direction() -> None:
    text = Path("SOURCE_ARTIFACT_COLLECTION.md").read_text(encoding="utf-8")
    required = [
        "shared artifact-collection boundary",
        "adapter-neutral",
        "explicit operator-supplied files",
        "does not scan folders",
        "does not fetch URLs",
    ]
    missing = [item for item in required if item not in text]
    assert not missing, missing


def main() -> None:
    test_docs_state_shared_adapter_direction()
    print("Source artifact collection docs self-test passed.")


if __name__ == "__main__":
    main()
