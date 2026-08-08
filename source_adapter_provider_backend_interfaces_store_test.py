from __future__ import annotations

import tempfile

from source_adapter_provider_backend_interfaces import build_source_adapter_provider_backend_interfaces
from source_adapter_provider_backend_interfaces_store import store_source_adapter_provider_backend_interfaces


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        package = build_source_adapter_provider_backend_interfaces(output_dir=tmpdir).as_dict()
        result = store_source_adapter_provider_backend_interfaces(package, tmpdir)
    assert result["store_status"] == "STORED"
    assert result["verification"]["verified"] is True
    assert result["provider_backend_request_row_count"] == 25
    assert result["provider_backend_execution_receipt_row_count"] == 25
    assert result["output_file_count"] == 6
    print("Source Adapter Provider Backend Interfaces store self-test passed.")


if __name__ == "__main__":
    main()
