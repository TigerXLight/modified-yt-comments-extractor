# MSN source adapter release validation

This file defines the final offline/manual confidence gate for the MSN source adapter.
It does not run live capture and must not be used to claim that a specific live MSN page was fully captured unless the operator records the manual result.

## Required adapter layers

1. Article extraction: title, publisher/source, author/date/read time where visible, rendered body, links, source/original URL, completeness status.
2. Comments/profile extraction: parent comments, nested replies, deleted placeholders, likes/dislikes, profile URLs/CIDs, account comment/like/follower stats, and export files.
3. Offline webpage viewer: rendered HTML, WARC.GZ partial replay, strict WACZ label, compatible WACZ candidate when present, local viewer index/launcher.
4. Media discovery/download registration: hero images, inline images, OpenGraph/Twitter card media, JSON-LD image/video candidates, posters, manifests, direct video candidates, local path/hash only when selected and captured.
5. Source-role/provenance: MSN/page surface, republishing outlet, visible source credit, claimed original source, original source URL, and source-chain gap must remain separate.

## MSN repost rule

MSN often republishes articles from other outlets, such as The Independent. In those cases:

- MSN is the observed/captured platform surface.
- The outlet shown on the page is the visible publisher or republishing source.
- A visible media credit such as Google Street View is a claimed/visible source credit, not automatically the original primary source.
- The original author/uploader/file must be recorded separately when located.
- If it is not located, the adapter must preserve `PRIMARY_SOURCE_NOT_LOCATED` or `PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED` and `source_chain_gap=true` as appropriate.

## Confidence rule

The adapter can be structurally ready while still requiring manual live validation. A complete structural report means the system can assemble the article, comments, viewer, media, and provenance layers into a coherent evidence bundle. It does not prove that a particular future MSN page will expose every field or allow every media file to be downloaded.
