# Profile/Media Database V76P Implementation Closeout

Status: `IMPLEMENTED`, `CLI_ONLY`, `GUI_STATE`, `TESTED`, `REVIEW_REQUIRED`

V76P closes out the local Profile/Media Database source workflow enough to support:

`HOME source folder -> source.txt + local article TXT/RTF/HTML + screenshot/media references -> segment-level source criticism -> source evaluation JSON preview -> guarded HOME/SAVE preview write -> GUI Add / Import preview state`

## Implemented Code

- `profile_media_source_segment_analysis.py`
- `profile_media_social_video_provenance.py`
- `profile_media_home_source_folder_ingestion.py`
- `profile_media_database_workbench_panel.py`
- `tools/run_profile_media_home_source_folder_ingestion_cli_v76o.py`

## Segment-Level Source-Role Review

`profile_media_source_segment_analysis.py` splits supplied local text into reviewable segments. Each segment includes:

- `segment_id`
- `segment_text_preview`
- `segment_type`
- `speaker_or_author_candidate`
- `source_role_candidate`
- `role_scope`
- `basis`
- `warnings`
- `review_lanes`

It also records:

- `first_person_author_self_claim_review`
- `author_identity_needed`
- `author_scope_only`
- `witness_connectivity_status`
- `direct_witness_basis`
- `direct_interviewer_basis`
- `direct_recorder_basis`
- `court_observer_basis`
- `direct_holder_basis`
- `no_witness_connectivity_found`
- quoted social post preservation fields

The module does not finalize source roles, infer sensitive identifiers, or classify people.

## First-Person Scope

First-person claims such as "I received threats" are marked as possible `PRIMARY_SELF_AUTHORED_SCOPE_REVIEW` only for the author/speaker's own claimed experience. They are not primary for claims about other people. The output keeps `author_identity_needed` and `author_scope_only` so an operator can review the scope.

## Witness Connectivity

Secondary depends on a direct witness, direct interviewer, direct recorder, court observer, or direct holder basis. Ordinary police/court/family/agency repetition becomes tertiary/review-required unless a direct basis is structurally preserved.

## Quoted Social Post Handling

Quoted social-media posts are primary for the poster only when the account and source URL are preserved enough to connect the post to the poster. Otherwise the segment records `quoted_post_connection_review`.

## Social-Media/Video Provenance

`profile_media_social_video_provenance.py` separates:

- uploader/account
- speaker
- original programme/channel/source
- clip holder
- transcripted statement
- archive URL
- source URL
- platform logo/watermark

Logos and watermarks can support platform provenance but do not prove claim affiliation. Missing affiliation creates `claim_subject_affiliation_gap`.

## HOME Source Evaluation JSON

The V76O preview JSON now includes:

- `source_role_segments`
- `social_video_provenance`
- expanded review lanes
- all existing safety flags

Writing remains guarded by:

`WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW`

## GUI Add / Import State

`profile_media_database_workbench_panel.py` now accepts a `source_folder_preview` payload. The panel state exposes:

- `Add / Import source folder`
- source-folder URL count
- source-role segment count
- media-reference count
- preview summary in rendered panel text

This is a GUI-safe state bridge. It does not open a picker, scan HOME, write files, download media, classify automatically, or move/copy user evidence.

## Article Extraction Backend Status

Optional article extraction backends are still not vendored:

- `metadata_parser`
- `trafilatura`
- `newspaper4k`

When missing, previews expose backend-missing warnings. The stdlib fallback remains a diagnostic/emergency local preview path, not full product extraction parity.

## Safety Boundary

V76P does not:

- download web pages
- crawl
- download media
- scan the whole HOME database
- move/copy evidence files
- infer sensitive identifiers
- finalize Primary/Secondary/Tertiary/Internal roles
- implement Twitter/X extraction expansion
- vendor third-party reference source

External reference folders remain `REFERENCE_ONLY`.
