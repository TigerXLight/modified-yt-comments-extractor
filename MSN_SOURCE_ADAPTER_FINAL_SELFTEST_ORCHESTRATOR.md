# MSN Source Adapter Final Self-Test Orchestrator

This file documents the final self-test orchestration layer for the MSN source adapter work.

The orchestrator is intentionally conservative. It does not certify live MSN extraction by itself. It only proves that the repository self-test layer is passing and that a failing self-test produces a non-zero process exit code.

## Why this exists

A previous patch-kit command reached commit/push even though a newly added self-test had printed an `AssertionError`. This layer exists to prevent that class of workflow mistake from being treated as clean.

The tool added by this layer is:

```text
source_msn_adapter_final_selftest_orchestrator.py
```

It discovers matching self-test files, runs them with Python, writes JSON/Markdown/CSV reports, and exits non-zero if any test fails.

## Standard command

From the repository root:

```cmd
python source_msn_adapter_final_selftest_orchestrator.py --repo . --out reports\msn_final_selftests --fail-fast
```

For the user's Windows layout:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_final_selftest_orchestrator.py --repo . --out reports\msn_final_selftests --fail-fast
```

## Expected states

```text
ALL_SELFTESTS_PASSED
SELFTEST_FAILURES_DETECTED
NO_SELFTESTS_FOUND
```

`ALL_SELFTESTS_PASSED` is still not equal to live MSN completion. Final MSN completion remains blocked until positive manual/live evidence is present.
