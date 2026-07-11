import argparse

from preservation_backend_plan_cli_test import run_self_test as run_backend_plan_cli_test
from preservation_evidence_bundle_cli_test import run_self_test as run_evidence_bundle_cli_test
from preservation_evidence_bundle_json_input_validation_test import (
    run_self_test as run_evidence_bundle_json_input_validation_test,
)
from preservation_evidence_bundle_regression_runner_test import (
    run_self_test as run_evidence_bundle_regression_runner_test,
)
from preservation_evidence_bundle_scope_invariant_test import (
    run_self_test as run_evidence_bundle_scope_invariant_test,
)
from preservation_evidence_bundle_test import run_self_test as run_evidence_bundle_test
from total_export_prepare_cli_test import run_self_test as run_total_export_prepare_cli_test


REGRESSION_TESTS = (
    ("evidence bundle model/rendering", run_evidence_bundle_test),
    ("evidence bundle JSON helper validation", run_evidence_bundle_json_input_validation_test),
    ("evidence bundle local-only scope invariants", run_evidence_bundle_scope_invariant_test),
    ("standalone evidence bundle CLI", run_evidence_bundle_cli_test),
    ("preservation backend plan CLI integration", run_backend_plan_cli_test),
    ("Total Export prepare CLI integration", run_total_export_prepare_cli_test),
    ("evidence bundle regression runner behavior", run_evidence_bundle_regression_runner_test),
)


def _selected_tests(selected_labels: tuple[str, ...]):
    if not selected_labels:
        return REGRESSION_TESTS

    known_labels = {label for label, _test_func in REGRESSION_TESTS}
    unknown_labels = tuple(
        label for label in selected_labels if label not in known_labels
    )
    if unknown_labels:
        raise ValueError(
            "unknown regression test label(s): "
            + ", ".join(unknown_labels)
            + "; expected one of "
            + ", ".join(label for label, _test_func in REGRESSION_TESTS)
        )

    selected = set(selected_labels)
    return tuple(
        (label, test_func)
        for label, test_func in REGRESSION_TESTS
        if label in selected
    )


def run_self_test(*, selected_labels: tuple[str, ...] = ()) -> None:
    for label, test_func in _selected_tests(selected_labels):
        test_func()
        print(f"{label}: passed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local preservation evidence bundle regression tests.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available regression test labels without running them.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="LABEL",
        help="Run only the selected regression test label. Repeat to select multiple labels.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    labels = tuple(label for label, _test_func in REGRESSION_TESTS)

    if args.list:
        for label in labels:
            print(label)
        return 0

    try:
        run_self_test(selected_labels=tuple(args.only))
    except ValueError as exc:
        parser.error(str(exc))
    print("Preservation evidence bundle regression self-test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
