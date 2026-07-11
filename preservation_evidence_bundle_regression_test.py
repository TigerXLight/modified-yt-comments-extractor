from preservation_backend_plan_cli_test import run_self_test as run_backend_plan_cli_test
from preservation_evidence_bundle_cli_test import run_self_test as run_evidence_bundle_cli_test
from preservation_evidence_bundle_json_input_validation_test import (
    run_self_test as run_evidence_bundle_json_input_validation_test,
)
from preservation_evidence_bundle_test import run_self_test as run_evidence_bundle_test
from total_export_prepare_cli_test import run_self_test as run_total_export_prepare_cli_test


REGRESSION_TESTS = (
    ("evidence bundle model/rendering", run_evidence_bundle_test),
    ("evidence bundle JSON helper validation", run_evidence_bundle_json_input_validation_test),
    ("standalone evidence bundle CLI", run_evidence_bundle_cli_test),
    ("preservation backend plan CLI integration", run_backend_plan_cli_test),
    ("Total Export prepare CLI integration", run_total_export_prepare_cli_test),
)


def run_self_test() -> None:
    for label, test_func in REGRESSION_TESTS:
        test_func()
        print(f"{label}: passed")


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle regression self-test passed.")
