# MSN manual approved release package

This section implements the final local release package boundary for approved MSN manual captures.

The flow consumes an explicit approved export handoff JSON and, when available, the MSN manual Total Export package-store JSON. It writes a metadata-only release package, release manifest, and evidence queue release update for the Total Export release path.

Safety boundary:
- no live HTTP
- no browser automation
- no archive submission
- no media downloads
- no credential reads
- no folder scans
- no full local paths in JSON payloads
- no claim that a live capture was completed outside the explicit approved handoff

CLI entry point:

```cmd
"C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe" capture_msn_manual_approved_release_package_cli.py --approved-handoff-json approved_export_handoff.json --package-store-json total_export_package_store.json --output-dir review_release
```
