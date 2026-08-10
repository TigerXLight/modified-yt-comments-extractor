# MSN Source Adapter Completion Snapshot

This file documents the completion-snapshot layer.

The snapshot verifies that the MSN adapter has the expected implementation and documentation surface after the MSN completion series. It is not a replacement for live validation. It is a repo-level inventory check used to prevent losing part of the adapter chain later.

## Command

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_completion_snapshot.py "T:\References\to go\Media\tools\Modified YouTube comment extractor"
```

Optional output directory:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_completion_snapshot.py "T:\References\to go\Media\tools\Modified YouTube comment extractor" --output-dir "%USERPROFILE%\Downloads\msn_completion_snapshot"
```

## Outputs

- `MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.json`
- `MSN_SOURCE_ADAPTER_COMPLETION_SNAPSHOT.md`

## Meaning

- `PASS`: all expected MSN adapter completion files are present.
- `PARTIAL`: one or more expected implementation or documentation files are missing.

The snapshot helps keep the repo honest when later roadmap work continues beyond MSN.
