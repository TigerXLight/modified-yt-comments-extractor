import subprocess
import sys

from preservation_evidence_bundle_regression_test import (
    REGRESSION_TESTS,
    _selected_tests,
)


def _run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "preservation_evidence_bundle_regression_test.py", *args],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def run_self_test() -> None:
    labels = tuple(label for label, _test_func in REGRESSION_TESTS)
    assert labels
    assert tuple(_selected_tests(())) == REGRESSION_TESTS

    selected = tuple(_selected_tests(("evidence bundle JSON helper validation",)))
    assert tuple(label for label, _test_func in selected) == (
        "evidence bundle JSON helper validation",
    )

    try:
        _selected_tests(("missing regression group",))
    except ValueError as exc:
        message = str(exc)
        assert "unknown regression test label(s): missing regression group" in message
        assert "evidence bundle JSON helper validation" in message
    else:
        raise AssertionError("Expected unknown regression label to raise ValueError")

    list_result = _run_runner("--list")
    assert list_result.returncode == 0, list_result.stderr
    listed_labels = tuple(
        line.strip()
        for line in list_result.stdout.splitlines()
        if line.strip()
    )
    assert listed_labels == labels
    assert list_result.stderr == ""

    only_result = _run_runner("--only", "evidence bundle JSON helper validation")
    assert only_result.returncode == 0, only_result.stderr
    assert "evidence bundle JSON helper validation: passed" in only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in only_result.stdout
    assert only_result.stderr == ""

    scope_only_result = _run_runner("--only", "evidence bundle local-only scope invariants")
    assert scope_only_result.returncode == 0, scope_only_result.stderr
    assert "evidence bundle local-only scope invariants: passed" in scope_only_result.stdout
    assert "evidence bundle JSON helper validation: passed" not in scope_only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in scope_only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in scope_only_result.stdout
    assert scope_only_result.stderr == ""

    multi_only_result = _run_runner(
        "--only",
        "evidence bundle JSON helper validation",
        "--only",
        "evidence bundle local-only scope invariants",
    )
    assert multi_only_result.returncode == 0, multi_only_result.stderr
    assert "evidence bundle JSON helper validation: passed" in multi_only_result.stdout
    assert "evidence bundle local-only scope invariants: passed" in multi_only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in multi_only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in multi_only_result.stdout
    assert multi_only_result.stderr == ""

    unknown_result = _run_runner("--only", "missing regression group")
    assert unknown_result.returncode == 2
    assert unknown_result.stdout == ""
    assert "unknown regression test label(s): missing regression group" in unknown_result.stderr


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle regression runner self-test passed.")
