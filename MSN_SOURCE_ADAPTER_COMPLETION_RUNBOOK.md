# MSN Source Adapter Completion Runbook

This runbook is the operator-facing finish step for an existing MSN capture/export folder. It joins the already implemented MSN adapter pieces into one completion output:

- rendered article extraction and article/archive metadata
- V34/V35-style comments/profile exports
- offline viewer/archive artifacts, including WARC/WACZ status labels
- media inventory/download sidecars
- source-role, primary-source-status, source-chain, and republisher provenance
- readiness, release, final validation, and total package reports

The command is intentionally safe by default. It registers media candidates in dry-run mode unless media download is explicitly requested with resource selection and allowed hostnames.

## Example dry-run completion command

```cmd
git -C "T:\References\to go\Media\tools\Modified YouTube comment extractor" status --short
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe "T:\References\to go\Media\tools\Modified YouTube comment extractor\source_msn_adapter_completion_cli.py" "C:\Path\To\MSN\Capture\Folder" --source-url "https://www.msn.com/..." --select-all-images
```

Dry-run media registration writes inventory and status files but does not download external assets. Use this first for real MSN output folders.

## Explicit media download rule

Only use `--download-media` after reviewing the media inventory. Direct image/video assets still require selected IDs or selection flags plus allowed hostnames. HLS/DASH manifests, blob URLs, frames, and playback-only resources are recorded as metadata/status unless a separate approved video workflow captures them.

## Manual source-role reminder

MSN may republish material from another outlet such as The Independent. A visible image credit such as Google Street View is another separate source-chain fact. The adapter must not silently treat MSN, the republisher, the visible credit, an agency line, a family/authority claim, or an unknown original uploader as the primary/original authored source.
