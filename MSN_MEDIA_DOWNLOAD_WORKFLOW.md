# MSN Media Download Workflow

MSN media handling has two layers:

1. Discovery/registration of image, video, poster, OpenGraph, Twitter-card, JSON-LD, request-log, HLS/DASH, frame, blob, and playback-only candidates.
2. Explicit download of selected direct media resources.

The tool must not auto-download every media URL. Direct downloads require operator selection and an allowed host. HLS/DASH manifests, blob URLs, frames, and playback-only media are recorded as metadata/status unless a separate approved video workflow captures them.

## Example dry run

```cmd
python source_msn_adapter_media_download_cli.py --rendered-html "C:\path\rendered-page.html" --source-url "https://www.msn.com/..." --output-dir "C:\path\media_review" --select-all-images --dry-run
```

## Example explicit image download

```cmd
python source_msn_adapter_media_download_cli.py --rendered-html "C:\path\rendered-page.html" --source-url "https://www.msn.com/..." --output-dir "C:\path\media_review" --select-all-images --allow-host img-s-msn-com.akamaized.net
```

## Output files

- `msn-media-inventory.json`
- `msn-media-inventory.csv`
- `msn-media-download-results.json`
- `msn-media-download-summary.md`
- `media\...` downloaded files where successful

## Evidence rule

A downloaded image or video is evidence that the media file was acquired from the selected media URL. It does not prove MSN, a reposting publisher, a news agency, a family statement, or a visible source credit is the original primary source. The media source-chain fields still need review.
