import subprocess
import sys


EXPECTED_LABELS = (
    "evidence bundle model/rendering",
    "evidence bundle JSON helper validation",
    "evidence bundle local-only scope invariants",
    "standalone evidence bundle CLI",
    "preservation backend plan CLI integration",
    "Total Export prepare CLI integration",
    "evidence bundle regression runner behavior",
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
    assert result.stdout.count('Preservation evidence bundle regression self-test passed.') == 1, result.stdout


def _assert_no_success_output(result: subprocess.CompletedProcess[str]) -> None:
    assert result.stdout == "", result.stdout
    assert 'Preservation evidence bundle regression self-test passed.' not in result.stderr, result.stderr
    assert ": passed" not in result.stderr, result.stderr


def run_self_test() -> None:
    list_result = _run_runner("--list")
    assert list_result.returncode == 0, list_result.stderr
    assert _listed_labels(list_result.stdout) == EXPECTED_LABELS
    _assert_list_output_shape(list_result.stdout)
    assert len(set(EXPECTED_LABELS)) == len(EXPECTED_LABELS)
    assert len(set(_listed_labels(list_result.stdout))) == len(EXPECTED_LABELS)
    assert list_result.stderr == ""
    assert _passed_labels(list_result.stdout) == ()
    assert "passed" not in list_result.stdout
    assert "Preservation evidence bundle regression self-test passed." not in list_result.stdout

    only_result = _run_runner("--only", "evidence bundle JSON helper validation")
    assert only_result.returncode == 0, only_result.stderr
    assert "evidence bundle JSON helper validation: passed" in only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in only_result.stdout
    assert "evidence bundle regression runner behavior: passed" not in only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in only_result.stdout
    _assert_success_banner_once(only_result)
    assert _passed_labels(only_result.stdout) == ('evidence bundle JSON helper validation',)
    assert only_result.stderr == ""

    scope_only_result = _run_runner("--only", "evidence bundle local-only scope invariants")
    assert scope_only_result.returncode == 0, scope_only_result.stderr
    assert "evidence bundle local-only scope invariants: passed" in scope_only_result.stdout
    assert "evidence bundle JSON helper validation: passed" not in scope_only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in scope_only_result.stdout
    assert "evidence bundle regression runner behavior: passed" not in scope_only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in scope_only_result.stdout
    _assert_success_banner_once(scope_only_result)
    assert _passed_labels(scope_only_result.stdout) == ('evidence bundle local-only scope invariants',)
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
    assert "evidence bundle regression runner behavior: passed" not in multi_only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in multi_only_result.stdout
    _assert_success_banner_once(multi_only_result)
    assert _passed_labels(multi_only_result.stdout) == ('evidence bundle JSON helper validation', 'evidence bundle local-only scope invariants')
    assert multi_only_result.stderr == ""

    duplicate_only_result = _run_runner(
        "--only",
        "evidence bundle JSON helper validation",
        "--only",
        "evidence bundle JSON helper validation",
    )
    assert duplicate_only_result.returncode == 0, duplicate_only_result.stderr
    assert duplicate_only_result.stdout.count(
        "evidence bundle JSON helper validation: passed"
    ) == 1
    assert "standalone evidence bundle CLI: passed" not in duplicate_only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in duplicate_only_result.stdout
    _assert_success_banner_once(duplicate_only_result)
    assert _passed_labels(duplicate_only_result.stdout) == ('evidence bundle JSON helper validation',)
    assert duplicate_only_result.stderr == ""

    reverse_order_result = _run_runner(
        "--only",
        "evidence bundle local-only scope invariants",
        "--only",
        "evidence bundle JSON helper validation",
    )
    assert reverse_order_result.returncode == 0, reverse_order_result.stderr
    assert _passed_labels(reverse_order_result.stdout) == (
        "evidence bundle JSON helper validation",
        "evidence bundle local-only scope invariants",
    )
    assert "Preservation evidence bundle regression self-test passed." in reverse_order_result.stdout
    _assert_success_banner_once(reverse_order_result)
    assert _passed_labels(reverse_order_result.stdout) == ('evidence bundle JSON helper validation', 'evidence bundle local-only scope invariants')
    assert reverse_order_result.stderr == ""

    unknown_result = _run_runner("--only", "missing regression group")
    assert unknown_result.returncode == 2
    assert unknown_result.stdout == ""
    _assert_no_success_output(unknown_result)
    assert "unknown regression test label(s): missing regression group" in unknown_result.stderr
    assert "expected one of" in unknown_result.stderr
    for expected_label in EXPECTED_LABELS:
        assert expected_label in unknown_result.stderr

    mixed_unknown_result = _run_runner(
        "--only",
        "evidence bundle JSON helper validation",
        "--only",
        "missing regression group",
    )
    assert mixed_unknown_result.returncode == 2
    assert mixed_unknown_result.stdout == ""
    _assert_no_success_output(mixed_unknown_result)
    assert "unknown regression test label(s): missing regression group" in mixed_unknown_result.stderr
    assert "expected one of" in mixed_unknown_result.stderr
    assert "evidence bundle JSON helper validation" in mixed_unknown_result.stderr


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle regression runner self-test passed.")
