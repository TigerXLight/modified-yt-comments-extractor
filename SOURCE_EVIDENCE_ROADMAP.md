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

## Operational Site-Capture REV4 Local Scaffold

- Local/mocked implementation exists for operational capture contracts, status codes, action-log hash chains, dependency/license audit metadata, a localhost fixture server, lazy browser-runner wrappers, supplied-HTML article/page/snapshot/comment/livechat/media helpers, localhost-only explicit media-download tests, mock-only archive-provider checks, ArchiveBox command planning, and source UI capture-plan wiring.
- The source UI can build a deterministic local capture plan from the selected source, Webpage/Comments/Livechat controls, and screenshot intent settings. The controller plan now includes deterministic in-memory `ACTION_LOG` artifact metadata with chained events and a sanitized JSONL hash for review, without writing files or executing capture.
- LOCALHOST_FIXTURE_TESTED article/page helpers now distinguish article semantic text from comments/chrome/ads, report confidence and contamination/exclusion signals, render a visible-page outline distinct from article text, model raw/final/MHTML/DOM/accessibility snapshot artifacts, and keep faithful screenshot metadata separate from derived screenshot transformations. These helpers consume supplied HTML/fixture bytes only and do not perform live browser capture or OCR.
- This is not approval for live website capture. It does not access real external websites, browser profiles, cookies, accounts, comments, media, archive services, or ArchiveBox instances.
- It does not run real scraping, live browser automation, screenshots, external downloads, archive checks/submissions, ArchiveBox execution, provider calls, credential use, or evidence-database work.
- The next live/manual site-smoke or real-site adapter step remains separately approval-gated and should use local fixtures/mocks first.

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

## Future Public Media Download / Evidence Capture Policy

- Future media evidence planning may include explicit, user-selected download or capture of open public media for purposes such as academic analysis, archiving, journalism/current-events reference, criticism/review, transformation, accessibility, and preservation.
- This is a future capability target, not current behavior. The current roadmap does not implement media downloading, discovery, capture execution, browser automation, scraping, archive submission, or source fetching.
- Publicly accessible media should not be treated as automatically unrestricted for later redistribution. Preserve access mode, source URL, capture purpose, author/publisher credit, visible license/usage notes where available, and any user-entered rights/context notes.
- Do not build bypass/circumvention features for DRM, private access controls, paywalls, login restrictions, meters, anti-copy controls, or site protections.
- Future media capture should remain opt-in and source-aware, with clear choices for:
  - no media capture
  - selected media only
  - all discovered public media on a source
  - a defined count/amount of media items
  - user-supplied local media registration
- Media evidence outputs should record what was selected, what was skipped, why it was skipped if known, when it was captured or registered, and the local path/hash where applicable.

## Future Behavior / Activity Log And Research Metrics

- The app should eventually support a local behavior/activity log for evidence-project actions, separate from source evidence itself.
- The log should help reconstruct what the user did inside the app, for example:
  - source URL added
  - source URL normalized or rejected
  - media item added
  - transcript/subtitle file added or edited
  - reference text attached
  - ASR provider/engine result imported or scored
  - Total Export package created or updated
  - archive URL manually added
  - database category suggested, accepted, rejected, or changed
- Log entries should include timestamps and stable item/session IDs so later review can compare what was visited, documented, captured, edited, exported, or reclassified.
- The log may later support aggregate research metrics such as frequently documented sites, source platforms, topic categories, date buckets, outlet names, capture types, or user-defined classification dimensions.
- Demographic or identity-category metrics must follow the database taxonomy safeguards: do not infer sensitive classifications from weak clues, keep unknown/not identified valid, and preserve the source/evidence basis for any classification.
- The behavior log should not store secrets, API keys, cookies, passwords, private session tokens, or hidden browser credentials.
- Transcript or subtitle edit logging should prefer version IDs, timestamps, file hashes, and optional user notes rather than silently exposing unrelated private text.
- The user should be able to review, export, clear, or disable future local activity logging where appropriate.
- This is planning-only and does not add tracking, analytics, telemetry, file watching, network access, or GUI behavior now.

Planned behavior/activity fields:

- `activity_id`
- `session_id`
- `activity_type`
- `actor_type`
- `actor_label`
- `item_id`
- `source_url`
- `local_path`
- `linked_item_ids`
- `before_state_hash`
- `after_state_hash`
- `changed_fields`
- `activity_time_utc`
- `user_note`
- `evidence_basis`
- `export_package_id`
- `database_root`
- `category_path`
- `privacy_level`

## Future Compression / External Archive Tool Guidance

- Total Export already plans local packages and deterministic ZIP-style packaging, but larger website archives and ArchiveBox-style stores may need stronger compression or user-selected external packaging tools.
- Future UI may provide prompts or guidance for third-party compression tools such as 7-Zip, WinRAR, WinZip, or platform-native archive utilities, especially for large local website archives, media bundles, and ArchiveBox-style exports.
- External compression should be explicit and user-triggered. Do not silently install, run, or depend on third-party compression software.
- Record compression provenance where useful, including tool name, tool version if available, archive format, compression settings, input folder/package ID, output path, output size, and checksum.
- Compression should preserve manifests, sidecars, source evidence, and reclassification/activity history rather than flattening evidence context.
- This is planning-only and does not add dependencies, compression execution, ArchiveBox execution, or GUI behavior now.

Planned compression fields:

- `compression_tool`
- `compression_tool_version`
- `archive_format`
- `compression_settings`
- `input_package_or_folder`
- `output_archive_path`
- `output_size_bytes`
- `output_hash`
- `compressed_at_utc`
- `compression_notes`

## Future Source Crediting / Witness And Access-Actor Accounting

- Source crediting should distinguish the source/publisher, article author, quoted or named witnesses, agencies, embedded media sources, the software user, and the capture session.
- A news article author is the credited author of that article/report and can be cited for the authored framing/reporting in that article. The author is not automatically the primary/original source for every claim inside the article.
- Named witnesses, quoted participants, authorities, family statements, agencies, embedded posts, and media credits inside an article should be represented as separate claim/source-role entries where relevant.
- Per article or source, the app should eventually support counting accountable witnesses or accountable source actors only when the evidence basis is explicit enough, for example named author, named witness, named official, visible account, linked source, or manually documented source note.
- Anonymous viewers, unverifiable social viewers, likes, reactions, and generic comment counts should not be treated as accountable witnesses.
- On YouTube and similar platforms, comments can be attributed to visible account/channel authors where available, but most viewers are not individually verifiable people and should not be counted as accountable witnesses merely because the video has views.
- The software user is an access/capture actor: the person who supplied the URL, imported the file, captured the screenshot, added an archive URL, or created the export. The user is not automatically a primary source for the underlying event unless they separately provide their own authored statement or evidence.
- Each accountable source actor or witness entry should preserve scope: what they authored, observed, claimed, repeated, translated, framed, captured, or manually supplied.
- Access/capture proof should preserve the date/time the page or source was accessed and the evidence that it was accessible then, such as screenshot path, archive URL, HTML/text snapshot path, local file hash, manifest entry, or manual source note.
- Source crediting should work per claim and per media item, not only per page.

Planned source-credit/witness fields:

- `source_actor_id`
- `source_actor_type`
- `source_actor_display_name`
- `source_actor_role`
- `account_or_profile_url`
- `article_author_name`
- `publisher_name`
- `agency_or_wire_credit`
- `quoted_witness_name`
- `quoted_witness_role`
- `claim_id`
- `claim_scope`
- `source_role`
- `source_status`
- `access_actor`
- `captured_by_user`
- `accessed_at_utc`
- `captured_at_utc`
- `access_proof_type`
- `access_proof_path_or_url`
- `evidence_hash`
- `witness_count_basis`
- `verification_notes`

## Future Add Media / Evidence Item Queue

- The current Add Media flow should evolve into a short selectable media/evidence item queue at the left or right of the workspace.
- Adding local media, source URLs, text/reference files, subtitle files, screenshots, manual imports, archive URLs, or local evidence notes should add one explicit item to the queue.
- Selecting an item should show its role, linked source URL, local path, status, and available item-specific actions.
- Planned actions include:
  - Edit a subtitle file.
  - Inspect a transcript or text file.
  - Attach media to a source URL.
  - Attach a screenshot or HTML/text snapshot to a source URL.
  - Mark an item as a manual import.
  - Assign a role such as source media, screenshot, transcript, sidecar, evidence note, archive note, or reference file.
  - Remove an item from the current working set without implying deletion of the source file.
- Source URL items and local media/reference items must retain explicit, separate roles. The queue should support both evidence/source work and ASR work without blending their meanings.
- Older local ASR/reference workflows must remain possible, including combinations of a YouTube URL, TXT reference file, source MP4/media file, and subtitle/transcript file.
- ASR reference-accuracy work should preserve a clear pairing among media, reference text, subtitle/transcript output, engine/provider metadata, scoring window, and accuracy result.
- This queue is planning-only. This roadmap item does not implement UI, storage, media parsing, subtitle editing, or ASR workflow changes.

Planned item fields:

- `item_id`
- `item_role`
- `display_name`
- `source_url`
- `linked_source_id`
- `local_path`
- `media_type`
- `is_manual_import`
- `linked_reference_text_path`
- `linked_subtitle_path`
- `linked_transcript_path`
- `linked_screenshot_path`
- `linked_archive_url`
- `asr_engine_or_provider`
- `asr_result_path`
- `reference_score_path`
- `item_status`
- `created_at_utc`
- `updated_at_utc`
- `user_notes`

## Future Evidence Database Taxonomy And Reclassification

- The app should eventually let the user register an evidence database root that can be described, indexed, and updated without imposing one built-in folder taxonomy.
- Existing folder structures should be recognised and represented rather than overwritten. The taxonomy should be data-driven and user-editable.
- The database may suggest repositories or category paths for articles, cases, evidence items, and Total Export packages using user-defined dimensions such as category, type, date, source outlet, identity known/unknown, relationship category, direct/indirect, adult/child, and other user metadata.
- Category suggestions must be dry-run output first. Moves, renames, relabelling, and reclassification require explicit user approval.
- Reclassification must never delete original evidence. Export/package IDs and original manifests should remain stable, with notes and history preserving what changed.
- The feature should support case/article/export folders, not only raw article URLs, and record when each folder was indexed and last updated.

Generic existing-tree patterns may include paths such as:

```text
Database/
  Topic/
    Action type/
      Direct or indirect/
        Identity known or not identified/
          Month and year/
            Source outlet/
              article or export folder/
```

```text
Database/
  Case type/
    Adult or child/
      Relationship category/
        Source classification/
          Date bucket/
            article, case, or Total Export package/
```

These are examples of dimensions the app may discover or suggest, not a required directory layout.

Reclassification and sensitive-data rules:

- If a later source supplies a classification that was previously unknown, flag the older item for review and optionally suggest a new path or label.
- For example, an item under `Non-religious or not identified` may be flagged when a later source explicitly records a relevant religious identity; no move should occur without review and approval.
- Do not infer protected or sensitive classifications such as religion, ethnicity, sex/gender relationship category, or identity from weak clues.
- Sensitive classifications require explicit source evidence, user confirmation, or manual tagging. `Unknown/not identified` remains a valid status, not an error.
- Preserve the previous path, suggested path, reason and source for the update, source role/status, timestamp, and user approval state.
- Alias, spelling, outlet-name, and date normalization should be suggestions requiring user approval, for example `religous` to `religious`, `incitment` to `incitement`, or a consistent outlet/month label.

Planned database fields:

- `database_root`
- `taxonomy_version`
- `category_path`
- `suggested_category_path`
- `previous_category_path`
- `classification_dimensions`
- `classification_status`
- `classification_basis`
- `classification_source_url`
- `classification_source_role`
- `classification_source_status`
- `classification_updated_at_utc`
- `user_review_status`
- `user_reviewed_at_utc`
- `source_outlet`
- `article_or_export_title`
- `event_or_article_date`
- `month_bucket`
- `export_package_id`
- `manifest_path`
- `source_urls`
- `archive_urls`
- `local_evidence_paths`
- `indexed_at_utc`
- `last_updated_at_utc`
- `notes`
- `history`

Possible future actions:

- Register a database root.
- Scan/index folders and detect existing taxonomy paths.
- Generate a dry-run suggested destination path.
- Flag classification conflicts and unknown-to-known updates.
- Record user approval or rejection.
- Move or relabel only after explicit approval.
- Preserve original manifests and evidence files.
- Write reclassification notes and history.

Current implementation status:

- MODEL_ONLY / LOCAL_FIXTURE_TESTED: `evidence_database_taxonomy.py` and `evidence_database_index.py` now provide local-only contracts for database roots, taxonomy versions, stable item IDs, path history, classification states, evidence basis, dry-run placement/reclassification proposals, index records, and index manifests.
- LOCAL_FIXTURE_TESTED: the evidence index store writes atomic JSON with temp-file plus replace semantics for a selected temp/test root, validates deterministic payload hashes, and supports append/update records. Tests use temporary directories only.
- USER_CONFIRMATION_REQUIRED: placement, classification, hierarchy-recognition, and reclassification helpers are dry-run proposal builders. They record basis/reason/confidence and preserve old/new path history, but never move files or apply a reclassification.
- MODEL_ONLY: variable hierarchy recognition handles supplied fixture path strings for renamed, nested, missing, and unknown folder parts. It does not scan a real database root.
- MODEL_ONLY: converters can create evidence index records from existing evidence queue items, source-resource rows, and Total Export manifests without mutating those source objects or validating files on disk.
- MODEL_ONLY / LOCAL_FIXTURE_TESTED: `evidence_database_review.py` now provides review/session, root-registration, preview, decision, and non-executing apply-plan controller contracts.
- LOCAL_FIXTURE_TESTED: root registration review uses explicitly supplied temp/test root paths, stores only root/config metadata, rejects missing and duplicate roots, and keeps broad scan disabled.
- LOCAL_FIXTURE_TESTED: preview generation groups only explicitly supplied `EvidenceIndexRecord` objects by `unknown`, `not_evidenced`, `proposed`, `user_confirmed`, `rejected`, and `superseded`.
- USER_CONFIRMATION_REQUIRED / DESTRUCTIVE_ACTION_NOT_IMPLEMENTED: review decisions and apply plans record intended accept/reject/unknown/not-evidenced/reclassification decisions with old/new path history, but execute no classification changes and no file moves.
- UI_SCAFFOLD_ONLY / LOCAL_FIXTURE_TESTED: `evidence_database_review_ui.py` adds a standalone review-window/controller scaffold with dry-run warnings, registered-root counts, preview row counts by state, selected decision/apply-plan summaries, and destructive-action-not-implemented status.
- UI_SCAFFOLD_ONLY: visible `main.py` placement remains deferred because the current UPDATES, KEYS/ACCOUNTS, EXPORT, FILES sidebar order and FILES/EXPORT workflows are protected; adding a button there would require broader layout/runtime work.
- SYNTHETIC_FIXTURE_ONLY / LOCAL_FIXTURE_TESTED: `evidence_database_demo_fixture.py` provides safe synthetic demo records across `unknown`, `not_evidenced`, `proposed`, `user_confirmed`, `rejected`, and `superseded`; all paths and URLs are synthetic/demo-only and no sensitive classification dimensions are assigned.
- IMPORT_EXPORT_ONLY / DESTRUCTIVE_ACTION_NOT_IMPLEMENTED: `evidence_database_review_io.py` exports review sessions as deterministic JSON with payload hashes and imports/validates them without executing imported decisions, scanning folders, moving files, or applying classification changes.
- REGRESSION_HARDENED / LOCAL_FIXTURE_TESTED: import/export validation now covers schema/hash tampering, compatible unknown top-level fields, malformed records, destructive-looking flags, and nested secret-like keys; the review scaffold now covers empty/duplicate/sparse summaries, rejected/superseded apply-plan target counts, persistent dry-run warning text, and absence of a visible `main.py` Evidence Database hook.
- Not implemented: broad folder scanning, real user-folder indexing, automatic classification execution, sensitive-attribute inference, file movement, live capture/download/archive/provider behavior, and evidence database migration.

## KEYS / Access & Keys Manager

- Replace or supplement the sidebar "API KEY" area with a "KEYS" button.
- Clicking "KEYS" opens a dedicated Access & Keys window.
- The current user-facing window is a compact My Providers surface: the main list shows only providers the user has added, grouped under headings such as ASR Providers and Video & Social Platforms, with a small add control per group.
- The add-provider catalog is lazy, searchable, and metadata-only; opening, searching, adding, removing, or selecting providers does not call providers, fetch pricing, or validate credentials. The add-provider popover closes on outside click, Escape, the same `+`, provider selection, and window close without accumulating temporary bindings.
- Details use plain language, hide raw implementation/provenance/diagnostic enum fields, show explicit official link buttons when applicable, and use "Key input" for masked secure credential entry. Official-link metadata now covers the complete current provider/platform catalog, not only ElevenLabs, with HTTPS official destinations for websites, developer docs, credential/app management, pricing, service status, repositories, and releases where applicable.
- Link buttons are informational/external navigation only: they open only after explicit click through the injected safe opener, do not scrape or fetch pricing at runtime, and omit non-applicable buttons instead of showing fake or disabled placeholders. Entries whose official website/developer/credential link could not be verified are recorded as explicit coverage gaps in the metadata/tests.
- The current provider details pane uses compact left-aligned label/value blocks and left-starting official-link buttons. The add-provider catalog now opens as a non-overlapping in-pane sidecar beside provider rows, searches cached normalized metadata only, and avoids credential reads/provider calls while typing.
- Provider rows show only provider name plus one status icon; full wording lives in the details pane/status text. Saved but unvalidated credentials are shown as `Key saved — not yet validated`, not as correct or incorrect. Green verified status is reserved for an explicit successful validation, and the amber warning state is reserved for an explicit validation failure or validation attempt that could not complete.
- `Validate key` is an explicit user action for supported cloud-ASR providers. It uses the existing connection-test coordinator and credential-consumption seam, runs off the Tk thread, persists only non-secret provider validation state, and does not run on window open/search/select/save/clear/link clicks.
- Keep the main sidebar less crowded.
- The current YouTube Data API key should become one credential/access entry in this future window.
- Do not imply every platform uses an API key.
- Access may involve API keys, OAuth-style login, app passwords, browser-assisted login/session, dedicated capture browser profiles, manual import, or no credentials.

Planned sections/tabs:

1. ASR providers:
   - ElevenLabs.
   - Groq.
   - OpenAI.
   - Other optional cloud ASR providers.
   - Local/offline ASR should remain available without cloud keys.
2. Video and social video platforms:
   - YouTube.
   - Vimeo.
   - TikTok.
   - Dailymotion.
   - Rumble.
   - PeerTube.
   - Odysee.
   - DTube.
   - Bilibili.
   - Youku.
   - Other future video/social video adapters.
3. Live streaming platforms:
   - Twitch.
   - Kick.
   - YouTube live.
   - Other future livestream/live-chat adapters.
4. Creator-owned and independent video hubs:
   - Nebula.
   - Floatplane.
   - Other creator-owned or subscription video hubs.
5. Short-form and entertainment mobile apps:
   - TikTok.
   - Triller.
   - Clapper.
   - Other short-form video apps.
6. Text/microblogging platforms:
   - X/Twitter.
   - Threads.
   - Bluesky.
   - Mastodon/Fediverse-style text platforms.
   - Other microblogging adapters.
7. Image, photography, and visual platforms:
   - Instagram.
   - Pixelfed.
   - Vero.
   - VSCO.
   - Glass.
   - Flickr.
   - BeReal.
   - Pinksky.
   - Locket.
   - Pinterest.
   - Lemon8.
   - Other visual/photo/social discovery adapters.
8. Community, forums, Q&A, and link aggregators:
   - Reddit.
   - Lemmy.
   - Kbin.
   - Discuit.
   - Squabbles.
   - Tildes.
   - Hacker News.
   - Lobsters.
   - 4chan.
   - Quora.
   - Tumblr.
   - Other forums/community platforms.
9. News websites:
   - News sites are too numerous to list exhaustively.
   - Treat them as site-specific or site-family adapters where possible.
   - Support browser-assisted capture, comments-only capture, headline/visible preview capture, article text only if selected, full-page screenshot, archive check, and future media evidence.
   - Access mode should be per URL/page/session, not per whole domain.
10. Professional, jobs, experts, and portfolio platforms:
   - LinkedIn.
   - Wellfound / AngelList-style platforms.
   - Hired-style platforms.
   - Teamblind / Blind.
   - Fishbowl.
   - Behance.
   - Dribbble.
   - GitHub.
   - ResearchGate.
   - Lunchclub.
   - Xing.
   - Alignable.
   - Other professional/expert/community adapters.
11. Workplace, chat, and collaboration platforms:
   - Microsoft Teams.
   - Google Chat.
   - Webex App.
   - Mattermost.
   - Rocket.Chat.
   - Zulip.
   - Element / Matrix.
   - Wire.
   - Guild.
   - Flock.
   - Other work/chat/community platforms.
   - These may require workspace permissions and should not be treated like public-web scraping.
12. Archive services:
   - Wayback Machine archive check/settings.
   - Archive submit/save settings.
   - archive.ph/archive.today-style services as optional/separate.
   - Archive Check can be default-on for Total Export later.
   - Archive Submit should remain explicit/user-selected.
13. Browser-assisted capture:
   - Dedicated capture browser profile path.
   - User-authenticated capture notes.
   - Do not harvest passwords/cookies.
   - Existing browser profile use should be advanced/user-approved only where technically safe.
   - Browser-assisted capture should record access mode and capture method.

Credential safety principles:

- Mask secrets by default.
- Provide reveal/copy/clear controls only where appropriate.
- Never write secrets into exports, logs, manifests, screenshots, extracted text, raw sidecars, or evidence packages.
- Never commit secrets.
- Prefer environment variables or local user settings initially.
- Consider OS keyring/encrypted local storage later.
- Make missing credentials visible per adapter/provider.
- Adapters should report whether credentials are required, optional, missing, configured, or not needed.
- Testing a key/connection should be explicit/user-triggered and should not run automatically.
- Do not run credential tests in background without user action.

Future adapter/provider metadata:

- `display_name`
- `platform_family`
- `credential_type`
- `credentials_required`
- `credentials_optional`
- `supports_browser_capture`
- `supports_manual_import`
- `setup_hint`
- `test_connection_supported`
- Privacy/cost/rate-limit notes if relevant.
- Access limitations if relevant.

UI wording notes:

- Sidebar button: "KEYS".
- Window title: "Access & Keys".
- "KEYS" is preferred over "API KEY" because future access may involve API keys, OAuth-style login, app passwords, browser profile settings, or no credentials.
- Do not imply every platform uses an API key.
- Use searchable/filterable platform sections later so the UI does not become too large.
- Do not list every possible service on the main screen; keep the main screen focused on Source URLs and selected capture options.

## ASR Note

- There is no known truly infinite free hosted ASR API.
- Local/offline ASR remains the only practical unlimited option.
- Cloud ASR remains optional and quota/cost/API-key dependent.

## Current Online ASR Action State

- ElevenLabs Scribe v2 now has a production-capable SDK transport and a separately approved one-call live verification for the narrow local-file explicit-action path.
- The live smoke call succeeded with secure keyring credential resolution, one request, `max_retries=0`, local 240-second timeout policy, provider/model `elevenlabs_scribe` / `scribe_v2`, normalized action/provider success, and no secret/raw-response output. Exact-phrase accuracy was not confirmed by the synthetic sample.
- The main transcript toolbar now includes `Online ASR` immediately next to `Local ASR`. The new control mirrors the Local ASR orange button/cog treatment and opens a local-file workflow.
- Opening Online ASR, selecting a file, or opening its cog/provider-picker surface must not contact a provider. A provider request is allowed only after an explicit user `Transcribe` action.
- The Online ASR cog opens a dedicated `Online ASR Providers` window, not the standalone `Access & Keys` manager. The current selectable production-wired provider is `ElevenLabs Scribe v2` / `elevenlabs_scribe` / `scribe_v2`; selection persists only the non-secret provider ID. The provider window uses the same public key-status wording as Access & Keys, including `Key saved — not yet validated`, and offers an explicit `Manage key` action that opens Access & Keys for the selected provider when possible.
- The Online ASR action must use the committed coordinator path: UI action -> `ASRProviderActionCoordinator` -> secure credential consumption -> ElevenLabs provider adapter -> SDK transport.
- The current first slice is local-file only, Scribe v2 only, word timestamps, diarization off by default, audio-event tagging off by default, and no keyterms by default.
- A corrective responsiveness pass moved heavy Local ASR imports and startup credential-status probing off initial window construction. Local ASR behavior remains unchanged; the heavy ASR engine modules load only when Local ASR is actually used.
- User-facing key validation is explicit-only and uses the read-only ElevenLabs models-list request (`GET /v1/models` via the installed SDK `client.models.list(...)`) with `max_retries=0` and a bounded timeout. It uploads no media, performs no transcription, discards response content, and stores only fixed non-secret validation state. No live validation request was performed in this milestone.
- Broader provider/API behavior remains approval-gated: no automatic/background checks, account/quota retention, model-list display, OAuth/browser access, credential reveal/copy/export behavior, or live validation beyond explicit user action is implied.

## Current Session Files Sidebar State

- The main sidebar now includes a session-only `FILES` section directly below `KEYS` and above `FILTERS`.
- Successful transcript/subtitle import, media linking, Online ASR media browsing, and Local ASR media selection add basename-only rows with normalized-path dedupe. Detach removes only the session row and never deletes the disk file.
- Selecting a transcript row uses the existing local transcript parser/import path and existing inline editor; parse failure preserves the current transcript. Selecting an audio/video row changes the active linked media only and does not transcribe or contact a provider.
- Switching away from unsaved transcript edits prompts Save / Discard / Cancel. The list is not persisted across restarts in this milestone.
- `FILES` now has an explicit compact `+` picker for multi-file transcript/subtitle/audio/video intake plus real TkDND-backed local drag/drop initialized against the existing CustomTkinter root. Picker and drop share one intake path, reject directories/unsupported items safely, preserve basename-only rows and normalized-path dedupe, and do not auto-transcribe media.
- Session state now separates selected row, active injected media, and active transcript. Selecting media injects it for playback with a distinct active row state, while selecting a subtitle/transcript preserves the active media and loads the inline editor for pairing.
- Media rows have compact direct full-ASR actions for the exact row path: local uses saved Local ASR defaults, and online uses the saved Online ASR provider/key state or opens configuration when not configured. The main Local/Online ASR dialogs use FILES-backed media selectors instead of reopening File Explorer.
- The latest local-only smoke verified the benchmark-backed Local ASR path with `short.mp4` using `whisper.cpp / Vulkan / large-v3`, resolved runner `asr_whispercpp`, and 28 transcript segments loaded into the inline editor with no faster-whisper fallback. Follow-up UI work corrected the fixed Local ASR footer wrapping, explicit-language completion wording, and redundant media picker visibility without adding provider/network/model-download behavior.
- The transcript/media lifecycle now supports media-only playback/timeline use, preserves active media and FILES rows when clearing or replacing transcripts, and adds transcript-section drag/drop for supported subtitles/transcripts through the shared intake/dedupe path. Dropping media on the Transcript section adds it to FILES without silently replacing transcript state. Transcript/media duration mismatch is warned explicitly; waveform data remains media-duration-bound and transcript segments beyond media end are marked out of range instead of stretching or repeating waveform data.
- The playback jitter correction now uses a fixed-centre playhead with half-viewport pre-roll/post-roll padding, one guarded scheduler, a monotonic interpolated display clock, one-shot seek on Position-scrubber release, and debug-gated tick instrumentation. Grabbing the Position scrubber pauses playback, remains paused during drag, seeks once on release, and resumes only when playback was active before the drag.
- `Detect speech intervals` now uses a real local-only WebRTC VAD workflow (`webrtcvad-wheels==2.0.14`) with FFmpeg PCM conversion, background worker/progress/cancellation, and blank editable timed segments. It performs no transcription, provider call, model download, invented text, or network behavior.
- Freeze note: the file-centric media workspace remains the checkpoint for FILES intake/DND, exact-row Local ASR, duration matching, Export, and timing-quality warning safeguards. Remaining Access & Keys visual stacking/scroll polish, sidebar sash grab/chunkiness, blue Position/playback stutter, low-quality mixed-audio subtitle timing, and near-continuous raw ASR timing cues are deferred follow-ups and are not blocking continuation of the ordered roadmap. Future URL `Get` resource-tree work remains separate.

## Current Local ASR Backend/Model State

- The Local ASR settings window now exposes a real `Engine/backend` selector for `whisper.cpp — Vulkan` and `faster-whisper — CPU / NVIDIA CUDA`, separates acceleration from model choice, and keeps `large-v3` documented as a model rather than Vulkan.
- The benchmark-backed best-tested local profile remains `whisper.cpp / Vulkan / large-v3` for the existing AMD/Vulkan workflow. The repository already contains the real whisper.cpp Vulkan sidecar runner (`asr_whispercpp.py`) with CLI/model discovery, subprocess execution, result parsing, and cleanup.
- `Best-tested local profile` is now a selectable/saved profile that sets `engine=whispercpp_vulkan`, `device=vulkan`, `compute_type` not applicable, and `model_name=large-v3`; Local ASR dispatch therefore reaches the existing whisper.cpp production runner through the established local wrapper rather than silently falling back to faster-whisper.
- The UI does not expose a fake Vulkan selector or silently downgrade the recommendation to CPU/small. `Update ASR Check` now shows a visible non-blocking readiness panel with separate whisper.cpp binary, Vulkan support, `large-v3` model, and overall best-tested profile status rows, while faster-whisper CPU/NVIDIA CUDA settings remain user-overridable separate paths.
- On AMD-style capability hints, the local guidance states that Vulkan acceleration requires the configured whisper.cpp Vulkan backend and `large-v3` model. No model/binary download, provider call, or transcription is performed by the settings check.
