# R42GN Source Row Display, Archive Policy, and Public Audio Title Audit

Status target: `PASS_R42GN_SOURCE_ROW_DISPLAY_ARCHIVE_AUDIO_TITLE_AUDIT`

## Scope

R42GN is a source-row display and metadata-policy pass. It does not run live capture, browser/CDP/WebView, yt-dlp, JDownloader, media download, archive submission, credential/cookie access, source-role assignment, counter mutation, no-jump mutation, or review-window rewrites.

## Implemented

- X/Twitter source rows keep the existing Post/Thread/Media settings model but use a compact row title treatment for long quoted post text.
- X/Twitter archive policy now surfaces archive.ph and Local backup controls only. Wayback remains hidden for X/Twitter because the existing policy does not prove it as a useful/default row action.
- X/Twitter archive.ph is approval/human-chain guarded metadata only; no archive submission runs from row intake.
- Global Player/LBC public catch-up audio rows use cached/static title hints for the fixture URL so the row shows `Tuesday, 08 September - Nick Ferrari` instead of the opaque episode ID.
- Global Player/LBC row provenance preserves R42GH method identity as plan metadata: `yt_dlp_python_module`, `py -m yt_dlp`, native format `0`, native M4A preservation, and sidecars. No yt-dlp execution or audio download runs.
- Existing Metro/news webpage archive controls remain unchanged.

## Compatibility

The existing source-row intake and package-preview path remains in place. R42GN adds a read-only audit helper and tiny row-state/UI presentation changes only.

## Guardrails

- Source roles: unchanged.
- Counters/no-jump: unchanged.
- Saved decisions: unchanged.
- Archive inheritance: unchanged.
- Metadata promotion: none.
- Review-window logic: unchanged.
