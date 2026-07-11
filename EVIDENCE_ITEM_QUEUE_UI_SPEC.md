# Evidence Item Queue UI/Data-Flow Spec

Date: 2026-07-11

## Purpose

This document expands the roadmap-only Add Media / evidence item queue into a future UI and data-flow specification.

It is planning only. It does not implement UI, storage, media parsing, subtitle editing, ASR changes, source fetching, media downloading, archive checks, browser automation, database scanning, file movement, or Total Export GUI wiring.

The goal is to preserve the existing local ASR/reference workflows while giving future source-evidence and Total Export work a clearer item model.

## Current Workflow Compatibility

Older local ASR/reference testing workflows must remain possible and understandable:

- YouTube URL.
- TXT reference file.
- Source MP4/media file.
- Subtitle/transcript output file.
- Provider/engine metadata.
- Scoring window.
- Reference accuracy result.

The queue must not blur these roles. A TXT reference file is not the same thing as a transcript output. A source media file is not the same thing as a source URL. A YouTube URL used for context is not automatically proof that the local media file came from that URL unless the user or metadata links them.

## Queue Concept

The future Add Media flow should become a selectable evidence/work item queue, usually shown as a short list on the left or right side of the workspace.

Each added object becomes one explicit queue item:

- Source URL.
- Local media file.
- TXT reference file.
- Subtitle file.
- Transcript file.
- Screenshot.
- HTML/text snapshot.
- Archive URL.
- Manual evidence note.
- Total Export package.
- ASR result.
- Database/category suggestion.

Selecting a queue item should show:

- Its role.
- Display name.
- Source URL if linked.
- Local path if applicable.
- Item status.
- Linked items.
- Available actions.
- Provenance/capture notes.
- Whether it is included in Total Export.

## Item Roles

Planned item roles:

- `SOURCE_URL`
- `LOCAL_MEDIA`
- `REFERENCE_TEXT`
- `SUBTITLE_FILE`
- `TRANSCRIPT_FILE`
- `SCREENSHOT`
- `HTML_SNAPSHOT`
- `VISIBLE_TEXT_SNAPSHOT`
- `ARCHIVE_URL`
- `MANUAL_EVIDENCE_NOTE`
- `ASR_RESULT`
- `TOTAL_EXPORT_PACKAGE`
- `DATABASE_CATEGORY_SUGGESTION`

Roles should be explicit and user-visible. The same physical file should not silently change role without user confirmation.

## Item Lifecycle

Planned lifecycle statuses:

- `ADDED`
- `LINKED`
- `READY`
- `NEEDS_REVIEW`
- `MISSING_LOCAL_FILE`
- `DUPLICATE_CANDIDATE`
- `EXCLUDED_FROM_EXPORT`
- `INCLUDED_IN_EXPORT`
- `REMOVED_FROM_WORKING_SET`

Removing an item from the working set should not imply deleting the original local file.

## Linking Rules

Queue items may be linked, but linking must be explicit or strongly derived from existing app state.

Examples:

- A `SOURCE_URL` may link to comments, screenshots, archive URLs, media, or text snapshots.
- A `LOCAL_MEDIA` item may link to a `REFERENCE_TEXT`, `SUBTITLE_FILE`, `TRANSCRIPT_FILE`, or `ASR_RESULT`.
- A `REFERENCE_TEXT` may link to the media/scoring window it was used to evaluate.
- A `SUBTITLE_FILE` may link to the media and ASR result that produced it.
- A `TOTAL_EXPORT_PACKAGE` may link to all selected evidence items included in that package.
- A `DATABASE_CATEGORY_SUGGESTION` may link to the article/export/source items it would classify.

The queue should make unlinked or ambiguously linked items visible rather than guessing.

## Selection Behavior

Selecting an item should expose actions appropriate to its role.

Examples:

- Edit subtitle file.
- Inspect transcript/text file.
- Attach media to a source URL.
- Attach screenshot or HTML/text snapshot to a source URL.
- Mark item as manual import.
- Assign or correct item role.
- Include/exclude from Total Export.
- View linked source, archive, or local file.
- View ASR/reference scoring details.
- View database classification suggestion.
- Remove from working set.

Destructive actions and filesystem moves should require explicit confirmation.

## ASR Reference Pairing

ASR reference work should preserve a clear pairing between:

- Media item.
- Reference text item.
- Candidate transcript/subtitle item.
- ASR engine/provider metadata.
- Scoring window.
- Accuracy result.
- Term/keyphrase hit/miss result where available.

Future UI should show when a score is incomplete because a pair is missing, a scoring window is unknown, or the candidate transcript is not linked.

The ASR pairing model should remain usable without any source URL. Local file-only testing must continue to work.

## Total Export Inclusion

The queue should make Total Export selection explicit.

Each item should be able to show:

- Included or excluded.
- Reason if excluded.
- Output type/path if included.
- Capture/access method if known.
- Source role if applicable.
- Archive status if applicable.
- Hash/checksum if applicable.

Total Export should consume the selected queue items and their metadata rather than assuming every item in the workspace should be packaged.

## Relationship To Database Taxonomy

A database category suggestion should be a queue item or linked review record, not an automatic file move.

The queue should show:

- Suggested category path.
- Previous category path if any.
- Evidence basis for the suggestion.
- Sensitive classification warning if relevant.
- User review state.
- Accepted/rejected/deferred decision.

Unknown/not identified must remain a valid status.

## Relationship To Behavior / Activity Log

Future activity logging may record queue actions such as:

- Item added.
- Item role changed.
- Item linked/unlinked.
- Subtitle/transcript edited.
- Source URL added.
- Total Export inclusion toggled.
- Database suggestion accepted/rejected.

The activity log is future local logging only. It must not store secrets, cookies, passwords, API keys, private session tokens, or unrelated private text.

## Planned Item Fields

- `item_id`
- `item_role`
- `display_name`
- `source_url`
- `linked_source_id`
- `local_path`
- `media_type`
- `mime_type`
- `file_size_bytes`
- `file_hash`
- `is_manual_import`
- `linked_item_ids`
- `linked_reference_text_path`
- `linked_subtitle_path`
- `linked_transcript_path`
- `linked_screenshot_path`
- `linked_archive_url`
- `asr_engine_or_provider`
- `asr_result_path`
- `reference_score_path`
- `scoring_window`
- `term_coverage_path`
- `total_export_include`
- `total_export_output_kind`
- `item_status`
- `created_at_utc`
- `updated_at_utc`
- `user_notes`

## Explicit Non-Goals For This Spec

This spec does not add:

- GUI widgets.
- File watching.
- Subtitle editing.
- ASR provider calls.
- Transcription.
- Media download/capture.
- Source fetching.
- Archive checks/submission.
- Browser automation.
- Scraping.
- Database scanning/indexing.
- File movement.
- Credential storage.
- Total Export runtime wiring.
