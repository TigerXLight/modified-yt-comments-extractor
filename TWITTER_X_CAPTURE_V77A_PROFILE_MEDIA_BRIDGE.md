# Twitter/X Capture V77A Profile/Media Bridge

Status: `IMPLEMENTED`, `TESTED`, `REVIEW_REQUIRED`

V76P made Profile/Media source-folder ingestion and source criticism current. V77A makes Twitter/X capture output compatible with that workflow by adding a Profile/Media provenance record builder.

## Required Fields Preserved

`twitter_capture_profile_media_provenance.py` preserves:

- `source_url`
- `canonical_url`
- `platform`
- `account_handle`
- `display_name`
- `post_id`
- `status_id`
- `post_text`
- `created_at`
- `captured_at`
- `archive_url`
- `screenshot_references`
- `media_references`
- `rendered_dom_status`
- `cursor_state`
- `rate_limit_or_cooldown_state`
- `uploader_account`
- `speaker`
- `clip_holder`
- `original_programme_channel_source`
- `transcripted_statement`
- `claim_subject_affiliation_review`
- `social_media_video_provenance_review`
- `source_role_candidate`
- `final_source_role_decision`
- `warnings`

For Twitter/X posts, the source-role candidate can mark the post as primary/original only for the poster's own authored post text when account, status ID, and post text are present. `final_source_role_decision` remains `false`.

Screenshots/media/DOM captures are review material for V76P HOME source workflows. They do not by themselves prove claim-subject affiliation, source authorship, or incident facts.

## Not Claimed

V77A does not claim full X account export, official X API access, media-download completion, live screenshot capture, or final Primary/Secondary/Tertiary classification.
