# MSN Source Adapter Done Gate

The MSN source adapter is considered structurally complete only when the done gate can evaluate the current output bundle across all project goals:

1. Article extraction.
2. Comments/profile extraction.
3. Offline webpage/archive viewer.
4. Media discovery/download registration.
5. Source-role and media source-chain provenance.
6. Release/final validation reporting.
7. Manual/live validation evidence.

The done gate is intentionally conservative. It does not run live capture, does not download media, and does not pretend that no-network fixtures prove every future MSN page.

## Source-role rule

MSN pages are captured surfaces. They are not automatically primary/original sources. For reposted articles, preserve these separately:

- MSN captured platform / republisher surface.
- Visible publisher/source, such as The Independent.
- Visible media credit, such as Google Street View.
- Claimed original source, when visible.
- Original source URL, when visible.
- Source-chain gap when the original authored source or first media source is not located.

## Overall statuses

- `READY_FOR_MSN_OPERATOR_USE`: all core systems pass and manual validation exists.
- `CONFIDENT_WITH_MANUAL_REVIEW`: adapter structure is strong, but live review remains needed.
- `PARTIAL_NEEDS_FOLLOW_UP`: some major pieces are present but gaps remain.
- `NOT_READY`: core evidence is missing.

## Command

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_done_gate.py --bundle-dir "<MSN_OUTPUT_FOLDER>"
```

Generated outputs:

- `MSN_ADAPTER_DONE_GATE_REPORT.json`
- `MSN_ADAPTER_DONE_GATE_REPORT.md`
