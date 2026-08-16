# Profile/Media Database V76O HOME Source Folder Ingestion

Status: `IMPLEMENTED`, `CLI_ONLY`, `TESTED`, `REVIEW_REQUIRED`

V76O adds a real selected-folder ingestion preview for the Profile/Media Database HOME workflow:

`HOME source folder -> source.txt + RTF/TXT/HTML + screenshots/media references -> source evaluation preview JSON`

This is not a whole-HOME scanner and not a final classifier. It reads one explicitly selected source folder and produces an auditable preview for review.

## Implemented Files

- `profile_media_home_source_folder_ingestion.py`
- `profile_media_home_source_folder_ingestion_test.py`
- `tools/run_profile_media_home_source_folder_ingestion_cli_v76o.py`
- `testdata/profile_media_database_v76o_home_source_folder_fixture/`
- `testdata/profile_media_database_v76o_home_source_folder_ingestion_acceptance_matrix.json`

## Supported Local Inputs

- `source.txt`
- `.txt` article notes
- `.html` / `.htm` article files
- `.rtf` article notes using lightweight stdlib text extraction
- screenshot/image references as recorded local file references only
- audio/video/media references as recorded local file references only
- source/archive URL lines inside `source.txt`

Screenshot and media files are inventoried with relative path, absolute path, suffix, size, and SHA-256. They are not downloaded, opened as evidence content, copied, classified, moved, or uploaded by V76O.

## Article Extraction Backend Policy

V76O calls the existing V76L article extraction adapter for local article text/HTML previews. Optional backends remain optional:

- `metadata_parser`
- `trafilatura`
- `newspaper4k`

These are not vendored and are not required by this patch. When missing, the preview records backend-missing warnings and uses the stdlib fallback. The stdlib fallback is a diagnostic/emergency path for local previews; full product extraction should make missing backends visible to the operator.

No extractor may fetch or crawl a web page in this workflow.

## Source-Criticism Behavior

V76O records review lanes and candidates. V76P extends this path with segment-level source-role arrays and social/video provenance fields. It does not finalize source roles.

Implemented review signals:

- `first_person_author_self_claim_review`
- `witness_connectivity_review`
- `claim_subject_affiliation_review`
- `social_media_video_provenance_review`
- `source_chain_basis_review`

Rules preserved:

- A whole source folder can contain multiple role segments.
- First-person "I" claims may be primary only for the author/speaker's own claimed experience, not for claims about other people.
- A quoted social-media post is primary for the poster only when the original post/account/screenshot/source is preserved enough to connect it to that poster.
- News repeating court, police, family, or agency claims is usually tertiary for the underlying event unless direct witness/holder/interviewer/court-observer basis is preserved.
- Secondary depends on witness connectivity.
- Images and screenshots record claim-subject affiliation gaps when affiliation is not explicit.
- Logos, watermarks, filenames, and platform labels can support provenance but do not prove claim affiliation.
- Social-media/video provenance separates uploader/account, speaker, original programme/channel/source, clip holder, transcripted statement, source URL, and archive URL.
- Extraction libraries gather material; project source-criticism logic decides review status.
- FEVER, AVeriTeC, and MICE verdict/benchmark logic remain excluded from product classification logic.

## Safety Flags

Every preview includes:

- `folder_scan_performed: true` for the selected source folder only
- `home_database_scan_performed: false`
- `web_download_performed: false`
- `crawling_performed: false`
- `media_download_performed: false`
- `automatic_classification_performed: false`
- `sensitive_identifier_inference_performed: false`
- `final_source_role_decision: false`

## Write Gate

Writing preview JSON requires the exact token:

`WRITE_HOME_SOURCE_FOLDER_EVALUATION_PREVIEW`

Without the token, the CLI and writer return `blocked_confirmation_required` and do not write a file.

## Current Limitations

- This is a source evaluation preview, not a full GUI Add/Import wizard.
- It does not scan a full HOME database.
- It does not read real media/video/image content beyond recording file references and hashes.
- It does not perform web fetches, archive checks, or media downloads.
- Segment-level role review is represented as non-final segment records and review lanes, not final classification.
- Social-media/video provenance is represented structurally and still requires operator review.
