from __future__ import annotations

from source_adapter_priority_fixture_pack_implementation import example_priority_fixture_pack_implementation_package
from source_adapter_priority_fixture_pack_implementation_verifier import verify_source_adapter_priority_fixture_pack_implementation


def main() -> None:
    verification = verify_source_adapter_priority_fixture_pack_implementation(example_priority_fixture_pack_implementation_package())
    assert verification["verified"] is True
    assert verification["fixture_pack_count"] == 5
    assert verification["dispatch_receipt_count"] >= 20
    print("Source Adapter Priority Fixture Pack Implementation verifier self-test passed.")


if __name__ == "__main__":
    main()
