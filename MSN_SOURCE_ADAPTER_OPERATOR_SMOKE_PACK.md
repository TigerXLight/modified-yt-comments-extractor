# MSN Source Adapter Operator Smoke Pack

This pack prepares a manual validation checklist for a real MSN article. It does not auto-start live capture.

The checklist covers:

- Article extraction.
- Comments/profile extraction.
- Offline viewer / WARC / WACZ status.
- Image/video/media registration.
- Source-role and source-chain separation.
- Total package and final validation reports.

## Command

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_operator_smoke_pack.py --target-url "<MSN_URL>" --output-dir "%USERPROFILE%\Downloads\msn_operator_smoke_pack"
```

After manually validating the generated checklist, copy the template JSON, fill statuses, and place it beside the MSN output bundle so the done gate can consume it.
