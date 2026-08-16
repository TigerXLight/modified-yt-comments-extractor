# Profile Media Source Workflow Reference Gaps V76N

Audit date: 2026-08-16

This file is the implementation roadmap for the real workflow:

`HOME source folder -> source.txt + RTF/TXT/HTML + screenshots/media -> source evaluation JSON`

It should guide V76O or V76N+1 work. It is documentation/audit-only.

## Current Implemented Foundations

- `IMPLEMENTED`, `TESTED`: HOME path parsing and case/event classification structure in `profile_media_home_repository_model.py`.
- `IMPLEMENTED`, `TESTED`: Source-role normalization in `profile_media_source_role_policy.py`.
- `IMPLEMENTED`, `TESTED`: Source criticism model and `claim-subject affiliation` review lane in `profile_media_source_criticism_model.py`.
- `IMPLEMENTED`, `TESTED`: Explicit existing-folder tree text to batch-preview planner in `profile_media_existing_folder_batch_planner.py`.
- `IMPLEMENTED`, `TESTED`: Controlled Save-to-HOME backend in `profile_media_database_materialize_workflow.py`; backend confirmation token: `MATERIALIZE_PROFILE_MEDIA_DATABASE_SELECTION`.
- `IMPLEMENTED`, `TESTED`: Reviewed folder move/rename operations in `profile_media_database_folder_operations.py`; confirmation token: `APPLY_PROFILE_MEDIA_REVIEWED_FOLDER_OPERATIONS`.
- `IMPLEMENTED`, `TESTED`: Article extraction from supplied HTML/local HTML in `profile_media_article_extraction_adapter.py`; write token: `WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW`.

## HOME Source Folder Ingestion Gap

| Requirement | Current status | Missing code | Suggested implementation |
| --- | --- | --- | --- |
| Select HOME source folder | `PARTIAL` | explicit source-folder selector and dry-run inventory | `profile_media_home_source_ingestion.py` |
| Read `source.txt` | `NOT_IMPLEMENTED` as full workflow | parser for source notes and expected metadata | `profile_media_home_source_ingestion.py` |
| Read RTF/TXT/HTML article files | `PARTIAL` | RTF/text extraction and article-file routing | `profile_media_article_extraction_adapter.py` plus ingestion adapter |
| Read screenshot/media folder | `PARTIAL` | media/screenshot inventory and source-chain link records | `profile_media_media_source_chain.py` |
| Produce source evaluation JSON | `PARTIAL` | unified JSON combining article extraction, source roles, screenshots/media, manual notes | `profile_media_source_evaluation.py` |
| GUI Add/Import integration | `PARTIAL`, `GUI_ONLY` | user-friendly Add/Import flow that hides batch JSON | `profile_media_database_gui_controller.py`, `main.py` |

## Source Role Logic Needed

| Logic | Current status | Required next behavior |
| --- | --- | --- |
| Primary/Secondary/Tertiary/Internal role fields | `IMPLEMENTED`, `PARTIAL` | Preserve fields on source, claim, media, and segment records. |
| first-person authored/self-claim logic | `NOT_IMPLEMENTED` as final logic | Detect first-person as review signal only; do not infer identity or truth. |
| witness connectivity | `PARTIAL` | Record whether the source is direct witness/holder/participant/interviewer or repeated/outside framing. |
| claim-subject affiliation | `IMPLEMENTED`, `PARTIAL` | Preserve `claim_subject_affiliation_gap` and review lane when claim subject is not linked to source basis. |
| internal media | `PARTIAL` | Distinguish internally created/owned files from publisher-observed or reposted media. |
| social-media/video provenance | `PARTIAL` | Bridge Twitter/MSN/YouTube media provenance into HOME source evaluation JSON. |
| closed-loop reporting | `PARTIAL` | Record repeated-source loops and source-chain gaps without promoting repeated reporting to primary. |

## Source Evaluation JSON Draft Requirements

The future source evaluation JSON should include:

- source folder path selected by user
- source URL and canonical URL
- source.txt parsed fields
- article extraction result
- screenshot/media inventory
- source role candidates and review lanes
- first-person review signals
- witness connectivity notes
- claim-subject affiliation gaps
- media source-chain fields
- internal media flags
- disputed framing/source-author correction notes
- manual source notes
- safety flags: no automatic classification, no sensitive identifier inference, no unapproved file movement

## User-Facing Wording Rules

- `SUPERSEDED`: do not use "materialize" as common user-facing wording. Use "Save to HOME" or "controlled folder/index creation."
- `SUPERSEDED`: do not present batch JSON as the normal user workflow. It is an internal/intermediate implementation detail.
- `IMPLEMENTED`: case/event classification is action/event/type/time/source-context driven, not simply "person = case."
- `PARTIAL`: article extraction libraries gather metadata/content; they do not decide final Primary/Secondary/Tertiary/Internal role.

## Safety Notes

- `DO_NOT_IMPLEMENT_WRITE_ACTION`: do not add social-media posting, deleting, liking, following, DMs, or botting.
- `NEEDS_MANUAL_REVIEW`: source role is claim-level and may differ for the same source item across different claims.
- `UNSAFE_OUT_OF_SCOPE`: no CAPTCHA bypass, credential automation, or aggressive scraping/rate-limit bypass.

