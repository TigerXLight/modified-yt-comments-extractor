# Local Preservation Plan Report

Date: 2026-07-10

## Purpose

`total_export_preservation_plan.py` defines a local-only report helper that compares source URLs with:

- Manually supplied archive URL metadata records from `total_export_manual_archive.py`.
- User-supplied local media registration records from `total_export_local_media.py`.

The report identifies manual preservation follow-up items, such as missing archive metadata, missing local media metadata, archive statuses that need review, missing local media files, and local media hash/status review cases.

## Scope

This helper consumes in-memory records only. It does not fetch sources, check archive services, submit URLs to archives, download media, scrape pages, capture screenshots, run browser automation, transcribe audio/video, call ASR providers, call network APIs, store credentials, or wire anything into the GUI.

Missing metadata means unknown. It is not proof that an archive, source page, media file, or external copy does not exist.

## Inputs

- `source_urls`: Source URLs to include in the plan.
- `manual_archive_records`: Local/user-entered archive metadata records.
- `local_media_records`: Local/user-entered media registration records.

YouTube URLs are normalized with the existing local YouTube URL utility, so common forms such as `youtu.be/...` and canonical watch URLs can match the same source. Non-YouTube URLs are compared as cleaned local strings.

## Output Counts And Actions

The plan reports:

- Source count.
- Sources with or missing archive metadata.
- Sources with or missing local media metadata.
- Sources needing manual follow-up.
- Per-source archive/local media status summaries.
- Per-source warnings.
- Per-source recommended manual actions.

Recommended actions are user guidance only. They do not trigger archive checks, downloads, fetching, scraping, screenshots, transcription, or provider calls.

## Status Notes

Archive statuses are user-entered local notes. A status such as `manually_checked_not_found` records only that the user says they checked manually and did not find an archive. It is not proof that no archive exists.

Local media statuses are local filesystem/user-entered notes. A status such as `missing_local_file` records local file state at registration/check time. It is not proof that a remote source is unavailable.

## Future Integration

Future CLI/report integration can be considered only after a separate approval. Any future integration must preserve the local-only boundary unless explicit network/archive/download/capture behavior is approved later.

## Local CLI Usage

`total_export_preservation_plan_cli.py` renders user-supplied local JSON metadata as text, Markdown, or JSON.

Example commands:

```cmd
python total_export_preservation_plan_cli.py --input PRESERVATION_PLAN_INPUT.json
python total_export_preservation_plan_cli.py --input PRESERVATION_PLAN_INPUT.json --format text
python total_export_preservation_plan_cli.py --input PRESERVATION_PLAN_INPUT.json --format markdown
python total_export_preservation_plan_cli.py --input PRESERVATION_PLAN_INPUT.json --format json
python total_export_preservation_plan_cli.py --input PRESERVATION_PLAN_INPUT.json --format markdown --output PRESERVATION_PLAN_REPORT_OUTPUT.md --overwrite
```

The CLI writes a file only when `--output` is explicitly provided. Existing output files are preserved unless `--overwrite` is passed.

The CLI reads local JSON only. It does not check archive services, submit archive URLs, download media, fetch sources, scrape pages, capture screenshots, transcribe, call providers, store credentials, or wire into the GUI.
