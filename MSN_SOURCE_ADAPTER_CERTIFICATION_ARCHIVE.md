# MSN Source Adapter Certification Archive

This module builds a compact, hash-indexed archive folder for final MSN adapter evidence. It is intended for handoff, regression preservation, and future roadmap work.

The archive helper:

- copies final MSN adapter reports when present;
- records SHA256, size, and relative path for every archived file;
- writes JSON and Markdown indexes;
- can create a `.zip` archive of the collected evidence;
- keeps local generated reports separate from live-source claims.

The archive does not download from MSN and does not validate a live page by itself. It only packages evidence already produced by the adapter tools and manual/live validation flow.

## Typical command

```cmd
python source_msn_adapter_certification_archive.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\certification_archive" --zip
```
