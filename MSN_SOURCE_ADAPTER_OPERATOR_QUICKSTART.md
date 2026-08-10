# MSN Source Adapter Operator Quickstart

This document is the operator-facing bridge after the MSN adapter has reached the certification/archive layer.

It does not perform a live MSN capture. It prepares deterministic, copyable commands for an existing MSN output folder and keeps the final evidence boundary honest:

- no-network self-tests can prove the adapter is release-candidate locked;
- live/manual evidence must be supplied before `COMPLETE` or `CERTIFIED_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE` is allowed;
- MSN as the republisher, the visible publisher/source credit, visible media credit, and original-source status remain separate evidence fields.

## Typical command

```cmd
python source_msn_adapter_operator_quickstart.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\operator_quickstart"
```

The command writes:

- `MSN_SOURCE_ADAPTER_OPERATOR_QUICKSTART.json`
- `MSN_SOURCE_ADAPTER_OPERATOR_QUICKSTART.md`
- `MSN_SOURCE_ADAPTER_OPERATOR_COMMANDS.cmd`

## What the generated command script covers

1. Live evidence template generation.
2. Operator final runner.
3. Live result reconciliation.
4. Release promotion gate.
5. Final promotion closeout.
6. Certification bundle.
7. Certification archive.

The generated `.cmd` file is safe by default: it does not create positive live evidence and it does not claim final completion. The operator still has to fill the live-evidence result from an actual MSN page validation run.
