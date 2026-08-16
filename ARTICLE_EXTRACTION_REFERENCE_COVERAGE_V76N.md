# Article Extraction Reference Coverage V76N

Audit date: 2026-08-16

This file compares current V76L article extraction adapter code with article/page extraction references.

## Current V76L Adapter

- `IMPLEMENTED`, `TESTED`: `profile_media_article_extraction_adapter.py` accepts supplied HTML text or a local HTML file.
- `IMPLEMENTED`, `TESTED`: It produces title, byline, date, site name, description, main text, outbound links, image URLs, attribution markings, source-basis candidates, source-role candidate, and review lanes where available.
- `IMPLEMENTED`, `TESTED`: It never downloads pages, crawls websites, copies media, final-classifies source roles, or infers sensitive identifiers.
- `IMPLEMENTED`, `TESTED`: It can write a source preview JSON only with `WRITE_ARTICLE_EXTRACTION_SOURCE_PREVIEW`.
- `PARTIAL`, `BLOCKED_BY_DEPENDENCY`: `metadata_parser`, `trafilatura`, and `newspaper4k` are optional imports. If unavailable, the stdlib HTML parser path remains deterministic.
- `REFERENCE_ONLY`, `DO_NOT_VENDOR`: `external_reference_sources_20260816_article_extraction/metadata_parser`, `/trafilatura`, and `/newspaper4k` are downloaded references, not app code.

## Reference Comparison

| Reference | Useful functions | Current app equivalent | Status | Missing |
| --- | --- | --- | --- | --- |
| `metadata_parser` | OpenGraph/Twitter/schema metadata, canonical/URL helpers | optional import `_run_metadata_parser`; stdlib meta fallback | `PARTIAL`, `BLOCKED_BY_DEPENDENCY`, `REFERENCE_ONLY` | full MetadataParser API surface; richer URL validation/normalization; redirect/history handling; absolute/relative metadata URL strategy |
| `trafilatura` | `extract`, metadata, language/date/site extraction, dedupe, fetch/crawl modules | optional import `_run_trafilatura`; no default fetch/crawl | `PARTIAL`, `BLOCKED_BY_DEPENDENCY`, `REFERENCE_ONLY` | `bare_extraction`; `extract_with_metadata`; richer metadata; deduplication; language/date/site depth; richer link/image handling; controlled fetch/crawl modules |
| `newspaper4k` | Article lifecycle, title/date/author/image/video/feed/category parser/config | optional import `_run_newspaper4k` | `PARTIAL`, `BLOCKED_BY_DEPENDENCY`, `REFERENCE_ONLY` | full Article lifecycle; parser/config object usage; top image; movies; source/category/feed logic; richer metadata fallback |
| `annismckenzie__x-article-exporter` | X article ID parsing, extraction, rendering, HTML/PDF/Typst output | V76L generic article extraction plus Twitter capture modules | `PARTIAL`, `REFERENCE_ONLY` | X article rendering pipeline, PDF/Typst, server/MCP/translate pieces |
| `eight04__web-exporter` | generic web-extension export | app-owned source capture/export modules | `PARTIAL`, `REFERENCE_ONLY` | extension parity and browser-extension export UX |
| `prinsss__twitter-web-exporter` | X/Twitter web export and output shape | Twitter importer/capture modules | `PARTIAL`, `REFERENCE_ONLY` | full Twitter web-exporter parity |

## Missed-Logic Checklist

### metadata_parser

| Item | Status | Notes |
| --- | --- | --- |
| URL validation / URL normalization | `PARTIAL` | basic URL handling exists elsewhere and V76L stores source/canonical URL; full metadata_parser URL strategy is not implemented. |
| richer OpenGraph/Twitter/schema metadata | `PARTIAL` | optional metadata_parser fields are attempted when installed; full schema coverage is not guaranteed. |
| redirect/history handling | `NOT_IMPLEMENTED` | no web fetch/redirect chain is performed by V76L. |
| absolute/relative metadata URL strategy | `PARTIAL` | stdlib parser uses `urljoin` for links/images; full metadata URL strategy is incomplete. |
| full MetadataParser API surface | `NOT_IMPLEMENTED` | only selected calls are used. |

### trafilatura

| Item | Status | Notes |
| --- | --- | --- |
| `bare_extraction` / `extract_with_metadata` | `NOT_IMPLEMENTED` | V76L calls selected extraction paths only. |
| richer metadata extraction | `PARTIAL` | selected metadata fields are collected when available. |
| deduplication | `PARTIAL` | simple field merging/deduping exists; not trafilatura parity. |
| language/date/site extraction depth | `PARTIAL` | some fields exist; full depth is not guaranteed. |
| link/image handling beyond basic JSON | `PARTIAL` | basic output fields exist; no full trafilatura graph. |
| controlled fetch/crawl modules | `NOT_IMPLEMENTED` | deliberately not run by default. |

### newspaper4k

| Item | Status | Notes |
| --- | --- | --- |
| Article lifecycle | `PARTIAL` | optional import path exists; full lifecycle is not modelled. |
| title/date/author extractors | `PARTIAL` | selected fields are captured when available. |
| image/video extractors | `PARTIAL` | image URLs exist; video/movie extractor parity absent. |
| source/category/feed logic | `NOT_IMPLEMENTED` | not integrated. |
| top image / movies / metadata fallbacks | `PARTIAL` | top image may land in image URLs; movie/media fallback parity absent. |
| parser/config object usage | `NOT_IMPLEMENTED` | no full config surface. |

## App-Level Workflow Gaps

| Gap | Status | Notes |
| --- | --- | --- |
| HOME folder source ingestion | `PARTIAL`, `NOT_IMPLEMENTED` for full direct ingestion | Current workflows use explicit tree text / batch previews / guarded writes. |
| `source.txt` + article file + screenshot/media folder reading | `NOT_IMPLEMENTED` as a complete path | Needs V76O or later. |
| RTF/text article support | `PARTIAL` | supplied text/HTML can be handled; RTF extraction not proven. |
| social-media post/video provenance model | `PARTIAL` | source-role and media-chain fields exist in several areas; no complete HOME bridge. |
| segment-level source role logic | `PARTIAL` | source criticism review lanes exist; not final segment classifier. |
| first-person “I” author/self-claim logic | `NOT_IMPLEMENTED` as final logic | Should be review-lane/candidate-only when added. |
| witness-connectivity logic | `PARTIAL` | policy language and source criticism exist; no full automated resolver. |
| automatic source preview generation inside HOME | `PARTIAL` | V76L CLI/source preview exists; full GUI Add/Import integration is incomplete. |
| GUI Add / Import integration | `PARTIAL` | workbench actions/state exist; full user flow remains incomplete. |

## Policy Boundary

Article extraction libraries gather metadata/content. They do not decide final Primary/Secondary/Tertiary/Internal role. FEVER, AVeriTeC, MICE, benchmark verdicts, and dataset scoring are excluded from product classification logic.

