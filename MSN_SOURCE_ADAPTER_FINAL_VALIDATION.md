# MSN Source Adapter Final Validation

This module is the final no-network confidence gate for MSN source-adapter output folders.
It does not run live capture, browser automation, network downloads, WARC replay, WACZ
replay, archive submission, or external verification. It validates the structure and
honesty of an already-created MSN output folder.

## Required areas

The validator reports each area as `PASS`, `PARTIAL`, `FAIL`, or `NOT_APPLICABLE`:

1. `article_extraction` — rendered HTML exists and exposes title, publisher/source,
   article text, hero media, visible credits, and article links where available.
2. `comments_profile_extraction` — comments JSON plus profile export files exist and
   contain comments/replies/profile records.
3. `offline_webpage_viewer` — rendered HTML, local viewer launcher/index, WARC.GZ,
   strict WACZ status, and optional ReplayWeb-compatible WACZ are labelled honestly.
4. `media_discovery_download_registration` — media candidates and local downloaded
   media files are registered separately. Video/HLS/DASH candidates remain
   metadata-only unless local files and hashes exist.
5. `source_role_and_media_source_chain` — MSN, reposted publisher, visible media
   credit, and original primary source status remain separated.
6. `total_export_manifest_and_release_outputs` — bundle/readiness/release manifest
   outputs exist for the adapter handoff.

## MSN reposting rule

MSN is often a republishing surface for another outlet, such as The Independent. A
visible credit such as Google Street View is also not automatically the original
source for all claims. The final validator preserves these layers separately:

- MSN page: captured platform / republishing surface.
- Reposted outlet: publisher/source or secondary framing source.
- Visible image/video credit: media credit or claimed/visible source context.
- Original primary source: only located when the original authored source, raw media,
  uploader, direct witness, or direct statement is actually identified.

## Outputs

Running the validator writes:

- `MSN_ADAPTER_FINAL_VALIDATION_REPORT.json`
- `MSN_ADAPTER_FINAL_VALIDATION_REPORT.md`

The overall status is `CONFIDENT_WITH_MANUAL_REVIEW` only when the required areas pass.
Manual review still remains required for real MSN pages because MSN markup, comments,
media delivery, WARC replay, and WACZ compatibility can change.
