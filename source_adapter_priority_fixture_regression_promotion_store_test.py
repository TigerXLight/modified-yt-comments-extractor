from __future__ import annotations

from tempfile import TemporaryDirectory

from source_adapter_priority_fixture_regression_promotion import example_priority_fixture_regression_promotion_package
from source_adapter_priority_fixture_regression_promotion_store import store_source_adapter_priority_fixture_regression_promotion


def main() -> None:
    with TemporaryDirectory() as tmp:
        result = store_source_adapter_priority_fixture_regression_promotion(example_priority_fixture_regression_promotion_package(), tmp)
    assert result["store_status"] == "STORED"
    assert result["output_file_count"] == 6
    assert result["verification"]["verified"] is True
    assert result["fixture_pack_count"] == 5
    assert result["promoted_regression_queue_row_count"] == 20
    assert result["named_site_smoke_gate_row_count"] == 5
    print("Source Adapter Priority Fixture Regression Promotion store self-test passed.")


if __name__ == "__main__":
    main()
