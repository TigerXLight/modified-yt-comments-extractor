# Source Evidence Roadmap

This is planning only. The local `reference_feature_notes/` files are private reference material and must stay ignored. Reference tools/files are inspiration only, not implementation source.

Do not copy code, wasm, assets, license blocks, or large text from `reference_feature_notes/`. Future third-party dependencies such as ffmpeg/libav/Playwright/etc. require dependency and license documentation before integration.

## Access And Capture Policy

- The app may support evidence preservation and citation workflows for content the user can normally access.
- Supported purposes include research, quotation, criticism/review, current-events reference, academic analysis, and preservation.
- The app records provenance and access/capture method; it should not make final legal conclusions for the user.
- Media capture/download should not be framed as categorically banned, but public access does not automatically settle every later redistribution question.
- Do not build bypass/circumvention features for DRM, private access controls, paywalls, login restrictions, meters, anti-copy controls, or site protections.
- Capture should be user-triggered and evidence-oriented.

Planned access mode labels:

- `PUBLIC_ACCESS`
- `USER_AUTHENTICATED_ACCESS`
- `METERED_OR_PREVIEW_ACCESS`
- `BLOCKED_OR_PAYWALLED`
- `ARCHIVED_COPY`
- `MANUAL_IMPORT`

## Mixed-Access Websites

- Access mode should be recorded per URL/page/session, not assumed for an entire domain.
- News sites may have a mix of free articles, metered articles, subscriber-only articles, public previews, and separately accessible comment sections.
- Users should be able to capture comments without forcing article-body extraction.
- Users should be able to capture visible headline/snippet/preview text where it is rendered.
- If article text is not selected, do not extract/store the full article just because comments were captured.
- If access is blocked, stop and offer archive check, manual import, or full-page screenshot of only what is visible.
- Browser-assisted capture may support user-authenticated pages later.
- Prefer a dedicated capture browser profile; do not harvest passwords/cookies.
- A future advanced option may allow a user-selected existing browser profile only where technically safe and clearly user-approved.

## Track A: Source / Comment Adapters

- YouTube remains the only currently implemented adapter.
- Preserve existing YouTube comments/livechat behavior while adding future source support.
- Future platforms to consider:
  - Reddit.
  - TikTok.
  - Twitch live chat.
  - Bluesky.
  - Threads.
  - Twitter/X.
  - Instagram.
  - Facebook.
  - Pinterest.
  - Medium.
  - Tumblr.
  - LinkedIn.
  - Quora.
  - News websites such as Telegraph/MSN-style pages.
  - Forums.
  - Other video/social platforms.
- Each platform needs site-specific rules, auth/API/browser strategy, and visible limitations.
- Do not assume one generic scraper can capture every comments section.
- Comments should preserve when the comment was posted when the platform provides it.
- Small reference IDs and permalinks should be included in exports where possible so evidence is traceable.

## Track B: Web Evidence Capture

- Capture screenshot.
- Capture full-page screenshot.
- Extract visible page text.
- Extract readable/article text where possible.
- Save HTML/source snapshot where allowed.
- Save metadata.
- Save source URL/canonical URL.
- Let user choose save folder.
- Save screenshot and extracted text paths in evidence metadata.
- Keep capture user-triggered, not automatic background scraping.
- User options should make capture scope clear before anything is saved.

## Track C: Archive / Check Backup

- Archive Check should be planned as automatic/default-on for Total Export because it is a read-only evidence lookup.
- Check existing Wayback Machine captures.
- Report latest available capture date/status where possible.
- Archive Submit/Save should remain explicit/user-selected because it sends a URL to an external archive service.
- Optionally submit URL to archive services later.
- Save archive result, timestamp, service, status, and archive URL where available.
- Do not treat archive failure as proof content did not exist.
- Treat archive.ph/archive.today-style services as optional and separate from Wayback because behavior may differ.

## Track D: Optional Media-Download Inspiration

- Use Video DownloadHelper/JDownloader-style tools only as feature inspiration.
- Potential future ideas:
  - Detect media assets.
  - Show available media streams/options.
  - Let user choose download folder.
  - Save source URL and metadata.
  - Create an evidence manifest for downloaded media.
- Do not implement downloading now.
- Do not bypass DRM, paywalls, login restrictions, or site protections.
- Keep legal, ToS, and copyright risk visible to the user.

## Source-Role / Evidence Hierarchy

These are project evidence roles, not universal academic definitions.

- Primary/original authored source:
  - Original author, uploader, participant, direct witness, original post, original raw media, or direct statement connected to the event, claim, media, or direct perspective.
- Secondary/outside perspective source:
  - A person, outlet, reporter, commentator, translator, clipper, editor, or publisher giving an outside perspective, interpretation, framing, or report.
  - Secondary sources are authored for their own perspective, but must not be silently substituted for the primary/original source.
- Tertiary/propagated source:
  - An authority, agency, family statement, database, aggregator, or repeated media account that propagates or summarizes a claim without itself being the original authored source.

Rules:

- Preserve source roles separately in exports.
- Source role should be tracked per claim, not only per URL/file.
- A source can be primary/original only for its own authored statement, direct experience, witnessed observation, original upload, or original media.
- A bystander/witness can be primary for what they personally observed, but must not be substituted for another participant's own statement or experience.
- Source role must be scoped to the exact claim being supported.
- The same captured item may be primary/original for one claim but secondary, tertiary, irrelevant, or temporally limited for another.
- Do not let repeated media reports or agency loops silently become primary sourcing.
- Do not treat authority, agency, family, or publisher repetition as automatic replacement for the primary/original source.

Source status labels:

- `PRIMARY_SOURCE_LOCATED`
- `PRIMARY_SOURCE_NOT_LOCATED`
- `PRIMARY_SOURCE_CLAIMED_BUT_UNVERIFIED`
- `PRIMARY_SOURCE_DISPUTED`
- `SECONDARY_FRAMING_ONLY`
- `TERTIARY_PROPAGATED_CLAIM`
- `MANUAL_SOURCE_NOTE`

## Claim-Level And Temporal Source-Role Planning

- Self-authored social posts can be primary/original authored sources for what they directly show or state, such as appearance, hairstyle, clothing, tattoos, self-presentation, location claims, or authored statements.
- Their value must be qualified by timing/currentness: post date, capture date, whether the post is old, reposted, edited, undated, or close/far from the event being assessed.
- Do not downgrade a self-authored appearance source just because it does not prove unrelated claims. Preserve its exact claim scope.
- Support source-chain gaps where the original uploader, first poster, original file, or primary authored source cannot be located.
- Support closed-loop reporting detection where multiple reports repeat the same unattributed agency/family/authority claim.
- Support timeline gaps such as media files acquired days after the event or after widespread reposting.
- Support notes where context is missing, removed, cropped, translated, reframed, or disputed.

Planned fields:

- `claim_text`
- `claim_type`
- `claim_source_role`
- `source_role_scope`
- `source_role_limitation`
- `authored_or_posted_at`
- `captured_at_utc`
- `event_time_or_claim_time`
- `temporal_gap_note`
- `currentness_status`: `CURRENT` / `HISTORICAL` / `UNKNOWN` / `REPOSTED` / `UNDATED`
- `primary_source_status`
- `source_chain_gap`
- `closed_loop_reporting_flag`
- `first_uploader_known`
- `first_uploader_url`
- `first_seen_by_user_utc`
- `media_acquired_at_utc`
- `file_obtained_delay_note`
- `publisher_framing_summary`
- `removed_or_missing_context_note`
- `identity_claim_basis`
- `appearance_claim_basis`
- `forensic_claim_basis`
- `family_or_authority_claim_basis`
- `open_source_media_available`
- `corroborating_sources`
- `contradicting_sources`
- `verification_notes`

## Media Source-Chain And Disputed-Framing Tracking

- Media files can appear across multiple news outlets/social platforms and may originate from a different primary source.
- Reposts may appear on TikTok, X/Twitter, Facebook, Instagram, YouTube, Reddit, Telegram-style mirrors, news websites, and other platforms.
- Do not assume the captured publisher page is the original source of the media.
- Preserve publisher framing and visible source credits.
- Preserve claimed original source where visible.
- Preserve social/source URL where visible.
- Track reposts/duplicates of the same media across platforms.
- Allow notes where the original author/uploader disputes, corrects, or clarifies the publisher's framing/context.
- Preserve evidence of competing claims without deciding who is correct.
- Support source-chain gap recording where the original source is not cited or cannot be located.

Planned fields:

- `media_observed_on_url`
- `publisher_page_url`
- `publisher_name`
- `publisher_headline_or_caption`
- `publisher_framing_summary`
- `visible_source_credit`
- `claimed_original_source`
- `original_source_url` if visible
- `original_author_or_uploader` if visible
- `primary_source_status`
- `source_role`
- `source_chain_gap`
- `social_source_url` if visible
- `wire_agency_source_credit` if visible
- Caption/context around media.
- `first_seen_by_user_utc`
- `capture_time_utc`
- `media_hash/checksum`
- `perceptual_hash/fingerprint`, future only
- `same_media_seen_on_other_urls`
- `repost_platform`
- `repost_uploader/account` if visible
- `repost_timestamp` if visible
- `source_author_correction_url` if available
- `source_author_correction_text/path` if manually imported
- `notes_on_context_dispute`
- `confidence/verification_notes`

## YouTube-Specific Planning Note

- Public YouTube evidence workflows can include:
  - Metadata.
  - Comments.
  - Replies.
  - Live chat where available.
  - Captions/transcripts where available.
  - Full-page screenshot.
  - Archive check.
  - Future optional video/media evidence.
- Public YouTube video/media evidence should be a future selectable capture option.
- Private, unavailable, restricted, or inaccessible videos should not be treated as downloadable targets.
- Existing YouTube comments/livechat behavior must remain unchanged.

## Capture Checkbox Roadmap

- Posts.
- Comments.
- Replies.
- Live chat.
- Captions/transcripts.
- Full-page screenshot.
- Visible page text.
- Readable/article text.
- HTML snapshot.
- Archive check.
- Archive submit.
- Video/media evidence, future only.
- Media source-chain fields, future only.
- Disputed framing/source-author correction notes, future only.
- Source-role labels, future only.

## Provenance / Purpose Fields To Plan

- `source_url`
- `canonical_url`
- `source_platform`
- `adapter_name`
- `access_mode`
- `capture_method`
- `capture_purpose`
- `source_role`
- `primary_source_status`
- `source_chain_gap`
- `capture_time_utc`
- `item_id`, `comment_id`, or `post_id` where available
- `parent_id` for replies
- Author/display name.
- Author profile/channel ID where available.
- Comment/post timestamp.
- Like/reaction count where available.
- Reply count where available.
- Permalink.
- `archive_url` if available
- `archive_service`
- `archive_checked_at_utc`
- `archive_status`
- `media_url` where available
- Local media path where captured.
- Local file hash/checksum where useful.
- Screenshot path where captured.
- Extracted text path where captured.
- Raw JSON/HTML sidecar where available.
- Capture/session ID or reference code.
- Media source-chain fields where available.
- Disputed framing/correction fields where available.

## UI Wording Note

- Consider renaming "Package" to "Total Export" or "Export Package".
- Prefer "Total Export" for clarity.
- Total Export means create a folder/package containing all selected evidence outputs.
- Keep TXT/CSV/Excel as individual quick exports.
- Consider making Total Export visually distinct from quick exports.
- Consider placing Total Export near the Source URLs/evidence capture controls rather than burying it with quick exports.
- Archive Check can be default-on inside Total Export; Archive Submit should stay explicit.

## ASR Note

- There is no known truly infinite free hosted ASR API.
- Local/offline ASR remains the only practical unlimited option.
- Cloud ASR remains optional and quota/cost/API-key dependent.
