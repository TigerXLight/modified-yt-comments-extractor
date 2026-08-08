from __future__ import annotations

import tempfile

from source_adapter_runtime_gui_provider_implementation import example_runtime_gui_provider_implementation_package
from source_adapter_runtime_gui_provider_implementation_store import store_source_adapter_runtime_gui_provider_implementation


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = store_source_adapter_runtime_gui_provider_implementation(example_runtime_gui_provider_implementation_package(), tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 8
    assert result["verification"]["verified"] is True
    assert result["route_count"] >= 4
    assert result["provider_count"] >= 4
    print("Source Adapter Runtime GUI Provider Implementation store self-test passed.")


if __name__ == "__main__":
    main()
