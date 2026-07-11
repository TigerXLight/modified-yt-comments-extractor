import subprocess
import sys


SUCCESS_BANNER = "Preservation evidence bundle regression self-test passed."
RUNNER_BEHAVIOR_LABEL = "evidence bundle regression runner behavior"

EXPECTED_LABELS = (
    "evidence bundle model/rendering",
    "evidence bundle JSON helper validation",
    "evidence bundle local-only scope invariants",
    "standalone evidence bundle CLI",
    "preservation backend plan CLI integration",
    "Total Export prepare CLI integration",
    RUNNER_BEHAVIOR_LABEL,
)


def _run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "preservation_evidence_bundle_regression_test.py", *args],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def _listed_labels(stdout: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in stdout.splitlines() if line.strip())


def _only_args(*labels: str) -> tuple[str, ...]:
    return tuple(
        argument
        for label in labels
        for argument in ("--only", label)
    )


def _assert_list_output_shape(output: str) -> None:
    lines = tuple(output.splitlines())
    assert lines == EXPECTED_LABELS, output
    assert output.endswith("\n"), output


def _passed_labels(stdout: str) -> tuple[str, ...]:
    suffix = ": passed"
    return tuple(
        line.removesuffix(suffix)
        for line in stdout.splitlines()
        if line.endswith(suffix)
    )


def _assert_success_banner_once(result: subprocess.CompletedProcess[str]) -> None:
    assert result.stdout.count(SUCCESS_BANNER) == 1, result.stdout


def _assert_success_result(
    result: subprocess.CompletedProcess[str],
    expected_labels: tuple[str, ...],
) -> None:
    assert result.returncode == 0, result.stderr
    assert SUCCESS_BANNER in result.stdout
    _assert_success_banner_once(result)
    assert _passed_labels(result.stdout) == expected_labels
    assert result.stderr == ""


def _assert_no_success_output(result: subprocess.CompletedProcess[str]) -> None:
    assert result.stdout == "", result.stdout
    assert SUCCESS_BANNER not in result.stderr, result.stderr
    assert ": passed" not in result.stderr, result.stderr


def _assert_unknown_label_failure(
    result: subprocess.CompletedProcess[str],
    *missing_labels: str,
) -> None:
    assert result.returncode == 2
    _assert_no_success_output(result)
    assert "unknown regression test label(s):" in result.stderr
    for missing_label in missing_labels:
        assert missing_label in result.stderr
    assert "expected one of" in result.stderr
    for expected_label in EXPECTED_LABELS:
        assert expected_label in result.stderr


def run_self_test() -> None:
    assert _only_args("a", "b") == ("--only", "a", "--only", "b")

    list_result = _run_runner("--list")
    assert list_result.returncode == 0, list_result.stderr
    assert _listed_labels(list_result.stdout) == EXPECTED_LABELS
    _assert_list_output_shape(list_result.stdout)
    assert len(set(EXPECTED_LABELS)) == len(EXPECTED_LABELS)
    assert EXPECTED_LABELS[-1] == RUNNER_BEHAVIOR_LABEL
    assert len(set(_listed_labels(list_result.stdout))) == len(EXPECTED_LABELS)
    assert list_result.stderr == ""
    assert _passed_labels(list_result.stdout) == ()
    assert "passed" not in list_result.stdout
    assert SUCCESS_BANNER not in list_result.stdout

    only_result = _run_runner("--only", "evidence bundle JSON helper validation")
    assert "evidence bundle JSON helper validation: passed" in only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in only_result.stdout
    assert f"{RUNNER_BEHAVIOR_LABEL}: passed" not in only_result.stdout
    _assert_success_result(only_result, ("evidence bundle JSON helper validation",))

    scope_only_result = _run_runner("--only", "evidence bundle local-only scope invariants")
    assert "evidence bundle local-only scope invariants: passed" in scope_only_result.stdout
    assert "evidence bundle JSON helper validation: passed" not in scope_only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in scope_only_result.stdout
    assert f"{RUNNER_BEHAVIOR_LABEL}: passed" not in scope_only_result.stdout
    _assert_success_result(
        scope_only_result,
        ("evidence bundle local-only scope invariants",),
    )

    multi_only_result = _run_runner(
        *_only_args(
            "evidence bundle JSON helper validation",
            "evidence bundle local-only scope invariants",
        )
    )
    assert "evidence bundle JSON helper validation: passed" in multi_only_result.stdout
    assert "evidence bundle local-only scope invariants: passed" in multi_only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in multi_only_result.stdout
    assert f"{RUNNER_BEHAVIOR_LABEL}: passed" not in multi_only_result.stdout
    _assert_success_result(
        multi_only_result,
        (
            "evidence bundle JSON helper validation",
            "evidence bundle local-only scope invariants",
        ),
    )

    duplicate_only_result = _run_runner(
        *_only_args(
            "evidence bundle JSON helper validation",
            "evidence bundle JSON helper validation",
        )
    )
    assert duplicate_only_result.stdout.count(
        "evidence bundle JSON helper validation: passed"
    ) == 1
    assert "standalone evidence bundle CLI: passed" not in duplicate_only_result.stdout
    _assert_success_result(
        duplicate_only_result,
        ("evidence bundle JSON helper validation",),
    )

    reverse_order_result = _run_runner(
        *_only_args(
            "evidence bundle local-only scope invariants",
            "evidence bundle JSON helper validation",
        )
    )
    _assert_success_result(
        reverse_order_result,
        (
            "evidence bundle JSON helper validation",
            "evidence bundle local-only scope invariants",
        ),
    )

    # Do not call the aggregate runner without --only here: that would recursively
    # select this runner-behavior test group.
    non_self_labels = tuple(
        label for label in EXPECTED_LABELS
        if label != RUNNER_BEHAVIOR_LABEL
    )
    assert non_self_labels == EXPECTED_LABELS[:-1]
    non_self_args = _only_args(*non_self_labels)
    assert RUNNER_BEHAVIOR_LABEL not in non_self_labels
    assert RUNNER_BEHAVIOR_LABEL not in non_self_args
    for expected_label in non_self_labels:
        assert expected_label in non_self_args
    assert non_self_args.count("--only") == len(non_self_labels)
    non_self_result = _run_runner(*non_self_args)
    assert f"{RUNNER_BEHAVIOR_LABEL}: passed" not in non_self_result.stdout
    _assert_success_result(non_self_result, non_self_labels)

    missing_only_value_result = _run_runner("--only")
    assert missing_only_value_result.returncode == 2
    _assert_no_success_output(missing_only_value_result)
    assert "--only" in missing_only_value_result.stderr
    missing_only_error = missing_only_value_result.stderr.lower()
    assert "expected" in missing_only_error or "argument" in missing_only_error

    unknown_result = _run_runner("--only", "missing regression group")
    _assert_unknown_label_failure(unknown_result, "missing regression group")

    multiple_unknown_result = _run_runner(
        *_only_args(
            "missing regression group",
            "missing second regression group",
        )
    )
    _assert_unknown_label_failure(
        multiple_unknown_result,
        "missing regression group",
        "missing second regression group",
    )

    mixed_unknown_result = _run_runner(
        *_only_args(
            "evidence bundle JSON helper validation",
            "missing regression group",
        )
    )
    _assert_unknown_label_failure(mixed_unknown_result, "missing regression group")
    assert "evidence bundle JSON helper validation" in mixed_unknown_result.stderr

    duplicate_known_unknown_result = _run_runner(
        *_only_args(
            "evidence bundle JSON helper validation",
            "evidence bundle JSON helper validation",
            "missing regression group",
        )
    )
    _assert_unknown_label_failure(
        duplicate_known_unknown_result,
        "missing regression group",
    )
    assert (
        "evidence bundle JSON helper validation: passed"
        not in duplicate_known_unknown_result.stdout
    )


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle regression runner self-test passed.")
