from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_priority_fixture_pack_implementation import example_priority_fixture_pack_implementation_package
from source_adapter_priority_fixture_pack_implementation_store import store_source_adapter_priority_fixture_pack_implementation


def main() -> None:
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_priority_fixture_pack_implementation(example_priority_fixture_pack_implementation_package(), tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 8
    assert result["verification"]["verified"] is True
    assert result["fixture_pack_count"] == 5
    print("Source Adapter Priority Fixture Pack Implementation store self-test passed.")


if __name__ == "__main__":
    main()
