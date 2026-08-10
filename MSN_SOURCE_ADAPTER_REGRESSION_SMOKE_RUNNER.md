# MSN Source Adapter Regression Smoke Runner

This document describes the regression smoke runner added for the MSN adapter.

The runner indexes or executes the MSN adapter's no-network self-tests and writes a small report. It is useful after future roadmap patches, because it gives an operator a quick way to detect whether core MSN adapter files/tests have been removed or broken.

## Dry-run / index mode

```cmd
python source_msn_adapter_regression_smoke_runner.py --repo "T:\References\to go\Media\tools\Modified YouTube comment extractor" --output "%USERPROFILE%\Downloads\msn_smoke_report"
```

This does not execute tests. It lists which tests are present and which are missing.

## Execute mode

```cmd
python source_msn_adapter_regression_smoke_runner.py --repo "T:\References\to go\Media\tools\Modified YouTube comment extractor" --output "%USERPROFILE%\Downloads\msn_smoke_report" --execute
```

This runs the selected self-tests with the current Python interpreter.

## Output files

- `MSN_SOURCE_ADAPTER_REGRESSION_SMOKE_REPORT.json`
- `MSN_SOURCE_ADAPTER_REGRESSION_SMOKE_REPORT.md`
- `MSN_SOURCE_ADAPTER_REGRESSION_SMOKE_REPORT.csv`

## Statuses

- `PASS`
- `FAIL`
- `READY_TO_EXECUTE`
- `PARTIAL_MISSING_TESTS`

The regression smoke runner is not a live MSN completion proof. It is a maintenance and safety check.
