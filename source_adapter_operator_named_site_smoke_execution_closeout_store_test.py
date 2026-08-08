from __future__ import annotations

import tempfile

from source_adapter_operator_named_site_smoke_execution_closeout import example_operator_named_site_smoke_execution_closeout_package
from source_adapter_operator_named_site_smoke_execution_closeout_store import store_source_adapter_operator_named_site_smoke_execution_closeout


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        result = store_source_adapter_operator_named_site_smoke_execution_closeout(example_operator_named_site_smoke_execution_closeout_package(), temp_dir)
        assert result["store_status"] == "STORED"
        assert result["output_file_count"] == 7
        assert result["verification"]["verified"], result
        roles = {item["role"] for item in result["stored_files"]}
        assert "source_adapter_operator_named_site_manual_smoke_execution_batch" in roles
        assert "source_adapter_operator_named_site_smoke_execution_handoff" in roles
    print("Source Adapter Operator Named Site Smoke Execution Closeout store self-test passed.")


if __name__ == "__main__":
    main()
