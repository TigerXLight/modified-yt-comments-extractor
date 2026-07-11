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


def run_self_test() -> None:
    list_result = _run_runner("--list")
    assert list_result.returncode == 0, list_result.stderr
    assert _listed_labels(list_result.stdout) == EXPECTED_LABELS
    assert list_result.stderr == ""

    only_result = _run_runner("--only", "evidence bundle JSON helper validation")
    assert only_result.returncode == 0, only_result.stderr
    assert "evidence bundle JSON helper validation: passed" in only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in only_result.stdout
    assert "evidence bundle regression runner behavior: passed" not in only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in only_result.stdout
    assert only_result.stderr == ""

    scope_only_result = _run_runner("--only", "evidence bundle local-only scope invariants")
    assert scope_only_result.returncode == 0, scope_only_result.stderr
    assert "evidence bundle local-only scope invariants: passed" in scope_only_result.stdout
    assert "evidence bundle JSON helper validation: passed" not in scope_only_result.stdout
    assert "standalone evidence bundle CLI: passed" not in scope_only_result.stdout
    assert "evidence bundle regression runner behavior: passed" not in scope_only_result.stdout
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
    assert "evidence bundle regression runner behavior: passed" not in multi_only_result.stdout
    assert "Preservation evidence bundle regression self-test passed." in multi_only_result.stdout
    assert multi_only_result.stderr == ""

    unknown_result = _run_runner("--only", "missing regression group")
    assert unknown_result.returncode == 2
    assert unknown_result.stdout == ""
    assert "unknown regression test label(s): missing regression group" in unknown_result.stderr


if __name__ == "__main__":
    run_self_test()
    print("Preservation evidence bundle regression runner self-test passed.")
