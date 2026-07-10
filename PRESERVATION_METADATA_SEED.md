# Preservation Metadata Seed

Date: 2026-07-10

## Purpose

`PRESERVATION_METADATA_SEED.json` provides small deterministic example data for local-only Total Export/source-preservation workflows.

The seed can be used with `total_export_preservation_plan_cli.py` to render a preservation plan from example manual archive URL metadata and example local media registration metadata.

## Local-Only Scope

The seed is example data only. It does not fetch sources, check archive services, submit archive URLs, download media, inspect real local media paths, scrape pages, capture screenshots, transcribe, call providers, store credentials, or wire into the GUI.

Fake local paths in the seed must not be treated as existing files. Fake hashes and archive URLs are user-supplied example metadata only.

## Example Command

```cmd
python total_export_preservation_plan_cli.py --input PRESERVATION_METADATA_SEED.json --format markdown
```

To write an explicit local report:

```cmd
python total_export_preservation_plan_cli.py --input PRESERVATION_METADATA_SEED.json --format markdown --output PRESERVATION_METADATA_SEED_REPORT.md --overwrite
```

## Included Example Cases

- A YouTube-style source with both manual archive metadata and local media metadata.
- A non-YouTube source with an archive URL but no local media registration.
- A non-YouTube source with local media registration but no archive URL.
- A non-YouTube source with `manually_checked_not_found` archive status.
- A non-YouTube source with `missing_local_file` local media status.

## Safety Notes

- Archive metadata is local/user-entered example data only.
- `manually_checked_not_found` is not proof that no archive exists.
- Local media metadata records local/user-entered example file state only.
- No archive checks/submission, downloads, fetching, scraping, screenshots, transcription, provider calls, or GUI integration are performed.
