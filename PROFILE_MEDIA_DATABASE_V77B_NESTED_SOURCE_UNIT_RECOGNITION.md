# Profile/Media Database V77B Nested Source-Unit Recognition

Status: `IMPLEMENTED`, `TESTED`, `OFFLINE_LOCAL_FOLDER_ONLY`, `REVIEW_REQUIRED`

V77B adds case-root recognition for Profile/Media HOME ingestion when the selected folder contains `Sources/`. It preserves the existing V76O single-source-folder behavior and adds nested/case-root fields instead of flattening the user taxonomy.

## Implemented Workflow

`case root -> Sources/ -> parent folders of source.txt/Source.txt -> per-source-unit preview`

The recognizer treats every parent folder of `source.txt` or `Source.txt` under `Sources/` as a source unit, deduplicated case-insensitively on Windows. Each unit keeps its own URLs, archive URLs, article files, screenshots, media references, transcript references, subtitle/caption references, video description references, linkage fields, and role-axis review.

## GB NEWS Fixture Shape

The fixture under `testdata/profile_media_database_v77b_gb_news_nested_case/GB NEWS` covers:

- Belfast Telegraph article unit:
  `Sources/Articles/June 2026/Belfast Telegraph/24 June`
- PressReader repost/copy unit:
  `Sources/Articles/June 2026/Belfast Telegraph/24 June/Reposts of Article/PressReader`
- GB News YouTube source unit:
  `Sources/Social Media/Online/YouTube/December 2023/25 December/Faiths of the Nation with Arlene Foster`

## Main Article Selection

For nested case-root mode, `Article.rtf` in the primary article source unit is selected as the main article. `PressReader/source.txt`, `YouTube Description.txt`, `transcript.txt`, and `.srt` caption files are not allowed to override the main article title.

RTF cleanup now decodes cp1252 hex escapes, handles `\lquote`, `\rquote`, `\ldblquote`, and `\rdblquote`, strips font/header/control metadata, and uses the first two meaningful lines as title/deck.

## Source Unit Fields

V77B adds these JSON fields to the V76O preview:

- `case_root_detected`
- `source_units`
- `primary_article_source_unit`
- `repost_source_units`
- `social_video_source_units`
- `transcript_references`
- `subtitle_or_caption_references`
- `video_description_references`
- `source_unit_media_references`
- `role_axes`

Existing single-source fields remain for compatibility.

## Role Axes

V77B keeps role axes separate and does not finalize classification:

- `case_claim_role_candidate`
- `personhood_or_witness_verification_role_candidate`
- `media_source_role_candidate`
- `speaker_statement_role_candidate`
- `case_claim_role_is_final`

For the GB News YouTube unit, the media-source axis can be primary because GBNews captured/published the programme media, while personhood/witness and case-claim axes remain review-required.

## Safety Boundary

V77B is offline/local-folder recognition only. It does not perform web downloads, crawling, media downloads, OCR, browser automation, credential automation, automatic sensitive inference, or automatic final classification. Screenshots and media are recorded as local media references only.
