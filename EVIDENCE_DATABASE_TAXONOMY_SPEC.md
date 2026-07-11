# Evidence Database Taxonomy And Reclassification Spec

Date: 2026-07-11

## Purpose

This document expands the roadmap-only evidence database taxonomy into a future data-flow and safety specification.

It is planning only. It does not implement database scanning, folder creation, file movement, reclassification, storage, indexing, source fetching, media downloading, archive checks, browser automation, GUI wiring, or automatic classification.

The goal is to let the project later recognise and work with a user-defined evidence database root without forcing one fixed built-in taxonomy.

## Core Principle

The database taxonomy must be user-defined, data-driven, and reviewable.

The app should recognise and describe existing folder structures first. It should not assume that every user stores evidence in the same order or that a folder name always means the same classification dimension.

Examples of dimensions a user may encode in folders:

- Topic or domain.
- Case type.
- Action/type.
- Direct or indirect.
- Domestic or international.
- Adult or child.
- Sex/gender relationship category.
- Religious/ethnic/identity known or unknown.
- Source outlet.
- Month or year.
- Article/case/export title.
- User-specific research bucket.

These dimensions should be represented as configurable taxonomy metadata, not hard-coded rules.

## Example Structure Patterns

The app should be able to describe structures like these without requiring them.

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

A future database setup wizard should be able to ask the user what each level means rather than guessing.

## Database Root Registration

A future user flow may allow the user to register one or more database roots.

Planned registration metadata:

- `database_root`
- `database_label`
- `taxonomy_version`
- `registered_at_utc`
- `last_indexed_at_utc`
- `last_updated_at_utc`
- `default_date_bucket_format`
- `path_separator_policy`
- `case_title_policy`
- `unknown_label_policy`
- `sensitive_classification_policy`
- `dry_run_required`

Registering a database root should not immediately move, rename, or rewrite folders.

## Read-Only Indexing First

The first implementation milestone should be a read-only index/dry-run report.

Read-only indexing may later:

- Walk a user-approved database root.
- Detect folder paths.
- Identify likely article/export folders.
- Find existing Total Export manifests where present.
- Record source URLs, archive URLs, and local evidence paths when already represented in manifests.
- Produce a local index file or report.

Read-only indexing must not:

- Delete files.
- Move files.
- Rename folders.
- Infer sensitive classifications from weak clues.
- Fetch remote pages.
- Call archive services.
- Download media.
- Open private browser sessions.
- Submit URLs externally.

## Taxonomy Mapping

The app should support a user-reviewed mapping between folder levels and classification dimensions.

Example mapping concepts:

- Level 1 -> topic/domain.
- Level 2 -> action/type.
- Level 3 -> direct/indirect.
- Level 4 -> source classification.
- Level 5 -> month bucket.
- Level 6 -> source outlet.
- Leaf folder -> article/case/export title.

The mapping should be editable because different branches of the same database may use different structures.

Planned mapping fields:

- `taxonomy_map_id`
- `database_root`
- `path_pattern`
- `dimension_order`
- `dimension_name`
- `dimension_value`
- `normalization_rule_id`
- `required_review`
- `notes`

## Classification Dimensions

Planned dimensions may include:

- `topic_domain`
- `case_type`
- `action_type`
- `directness`
- `domestic_or_international`
- `adult_or_child`
- `relationship_category`
- `sex_or_gender_category`
- `religion_identity_status`
- `ethnicity_identity_status`
- `source_outlet`
- `month_bucket`
- `article_or_export_title`
- `manual_tags`

Sensitive dimensions must require stronger review controls.

## Unknown / Not Identified

`Unknown`, `not identified`, `not stated`, and similar labels are valid states.

They should not be treated as errors or missing data.

A later source may change a classification from unknown/not identified to known, but only through a reviewable update path.

## Unknown-To-Known Reclassification

When a new source or manually entered evidence records a classification that may affect older database placement, the app should flag a review item rather than move files automatically.

Example:

- Existing path: `Non-religious or not identified / June 2026 / Source Outlet / Article Folder`
- New evidence: a later source explicitly records a relevant religious identity.
- App action: create a dry-run reclassification suggestion.
- User decision: accept, reject, or defer.

The suggestion should preserve:

- Previous path.
- Suggested path.
- Evidence/source basis.
- Source role.
- Source status.
- Whether the source is primary, secondary, tertiary, propagated, disputed, or manually noted.
- Timestamp.
- User decision.
- Notes.

## Sensitive Classification Safeguards

Sensitive or protected classifications must not be inferred from weak clues.

Examples requiring explicit evidence or user confirmation:

- Religion.
- Ethnicity.
- Sex/gender relationship category.
- Identity category.
- Adult/child where unclear.
- Relationship-based category where unclear.

Rules:

- Do not infer religion or ethnicity from names, locations, photos, clothing, or stereotypes.
- Do not infer sex/gender relationship category unless the source evidence or user note explicitly supports it.
- Keep `unknown/not identified` valid.
- Show sensitive classification warnings in any suggestion.
- Require user approval before writing a sensitive classification into database metadata or suggesting a folder move based on it.
- Preserve source role and source status for the classification.

## Alias And Normalization Suggestions

The app may suggest spelling or naming normalization, but only with user approval.

Examples:

- `religous` -> `religious`
- `incitment` -> `incitement`
- outlet-name consistency
- month/date normalization
- case-title formatting
- punctuation cleanup

Normalization should be logged and reversible where possible.

## Dry-Run Report

Before any change, the app should produce a dry-run report.

Dry-run report sections may include:

- Existing path.
- Parsed dimensions.
- Suggested destination path.
- Reason for suggestion.
- Evidence basis.
- Sensitive classification warning.
- Conflicts.
- Missing metadata.
- Unknown/not identified state.
- User action required.
- No-op items.

The dry-run report should be clear enough for the user to approve or reject individual changes.

## Reclassification History

The database should preserve reclassification history rather than overwrite the past.

Planned history fields:

- `history_id`
- `item_id`
- `previous_category_path`
- `new_category_path`
- `suggested_category_path`
- `change_type`
- `change_reason`
- `classification_basis`
- `classification_source_url`
- `classification_source_role`
- `classification_source_status`
- `user_review_status`
- `user_reviewed_at_utc`
- `changed_at_utc`
- `notes`

Original evidence and manifests should remain intact.

## Relationship To Total Export

Total Export packages may become database items.

The database index should preserve:

- Package ID.
- Manifest path.
- Source URLs.
- Archive URLs.
- Local evidence paths.
- Capture/session IDs.
- Queue item IDs where available.
- Created/updated timestamps.
- Reclassification history.

Moving or relabeling a database folder should not invalidate package IDs or erase original manifest provenance.

## Relationship To Evidence Item Queue

Database category suggestions can appear as queue items or linked review records.

The queue should show:

- Suggested category path.
- Previous path.
- Evidence basis.
- Sensitive classification warning.
- Review state.
- Accept/reject/defer action.

The queue should not silently move files.

## Relationship To Activity Log

Future activity logging may record:

- Database root registered.
- Folder indexed.
- Taxonomy mapping edited.
- Classification suggestion created.
- Suggestion accepted/rejected/deferred.
- Folder moved/renamed after approval.
- Alias normalization approved.
- Conflict resolved.

Activity logs should avoid storing secrets or unrelated private text.

## Planned Database Fields

- `database_root`
- `database_label`
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

## Possible Future Actions

- Register database root.
- Scan/index folders in read-only mode.
- Detect existing taxonomy paths.
- Let the user map folder levels to dimensions.
- Generate dry-run suggested destination paths.
- Flag classification conflicts.
- Flag unknown-to-known classification updates.
- Record user approval/rejection/defer decisions.
- Move or relabel only after explicit approval.
- Preserve original manifests and evidence files.
- Write reclassification notes/history.

## Explicit Non-Goals For This Spec

This spec does not add:

- Folder scanning.
- File movement.
- Folder creation.
- Automatic classification.
- Sensitive classification inference.
- Source fetching.
- Archive checks/submission.
- Media downloading.
- Browser automation.
- Scraping.
- GUI wiring.
- Storage/database implementation.
- Background monitoring.
