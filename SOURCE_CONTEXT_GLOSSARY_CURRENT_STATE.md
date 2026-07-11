# Source Context / Glossary Current State

Date: 2026-07-10

Branch: `v2.6.0-asr-engines`

Latest known checkpoint when this document was added:

```text
35c6829 Refresh project handoff checkpoint
```

## Purpose

This document is the local current-state handoff for the source URL, source adapter, source capture plan, provenance, and context/glossary skeleton.

It records what exists now, what is intentionally not implemented, how to verify the local helpers, and what safe future milestones look like.

## Hard Boundaries

The current source/context/glossary helpers are local planning and metadata helpers only.

They must not:

- fetch source URLs,
- download media,
- fetch comments, live chat, captions, transcripts, metadata, oEmbed, or webpage content,
- call ASR providers,
- call topic resolver, Common Crawl, Serper, Exa, archive services, or any network/API service,
- scrape pages,
- capture screenshots,
- store credentials, cookies, tokens, or sessions,
- inspect or extract ZIPs,
- wire into the GUI,
- change runtime extractor/export/ASR behavior.

Current helpers validate, normalize, classify, and assemble local metadata only.

## Current Local Helpers

| Area | Files | Purpose |
| --- | --- | --- |
| YouTube URL parsing | `youtube_url_utils.py`, `youtube_url_utils_test.py` | Strict local YouTube video-ID extraction/normalization. |
| Source adapter metadata | `source_adapters.py`, `source_adapters_test.py`, `source_adapters_registry_test.py` | Local adapter capability metadata, YouTube URL support, metadata-only News Website known-host URL support, `source_name` registry helpers, and name lookup. |
| Source adapter capability report | `source_adapter_capability_report.py`, `source_adapter_capability_report_test.py`, `source_adapter_capability_report_cli.py`, `source_adapter_capability_report_cli_test.py` | Local registered-adapter capability/credential/privacy/setup report rendering. |
| Source adapter gap analysis | `source_adapter_gap_analysis.py`, `source_adapter_gap_analysis_test.py`, `source_adapter_gap_analysis_cli.py`, `source_adapter_gap_analysis_cli_test.py` | Local current-vs-future adapter and preservation backend gap analysis. |
| Capture method metadata | `capture_method_metadata.py`, `capture_method_metadata_test.py` | Local metadata catalog for visible/full-page/container/stitched screenshots, selected/raw HTML, and manual evidence bundles; no capture execution. |
| Context/glossary skeleton | `context_glossary.py`, `context_glossary_test.py` | Local glossary normalization, deduplication, user-term handling, and context hint resolution. |
| Context glossary CLI | `context_glossary_cli.py`, `context_glossary_cli_test.py` | Explicit-output-only CLI for manually supplied context/glossary JSON normalization and reporting. |
| Source capture planning | `source_capture_plan.py`, `source_capture_plan_test.py` | Local source URL + adapter + capture option + context hint plan assembly. |
| Source capture plan CLI | `source_capture_plan_cli.py`, `source_capture_plan_cli_test.py` | Explicit-output-only inspection CLI for manually supplied source URL/context/glossary JSON. |
| Source plan provenance | `source_plan_provenance.py`, `source_plan_provenance_test.py` | Local provenance records derived from Source Capture Plans without fetch/capture behavior. |

## Current Verified State

The focused inspection before this file was added found these relevant files present:

```text
source_adapters.py
source_adapters_test.py
source_capture_plan.py
source_capture_plan_test.py
source_plan_provenance.py
source_plan_provenance_test.py
context_glossary.py
context_glossary_test.py
youtube_url_utils.py
youtube_url_utils_test.py
```

Local verification passed for:

- Source adapter self-test.
- Source capture plan self-test.
- Source plan provenance self-test.
- Context glossary self-test.
- YouTube URL utility self-test.

## Pipeline Position

The planned pipeline remains:

1. Source URL.
2. Source adapter capability check.
3. Local capture plan options.
4. Context hint and user glossary term normalization.
5. Candidate glossary/entity handling.
6. User review/edit before any ASR prompt/keyterm use.
7. Optional future provider-specific keyterms.
8. Term QA after transcription.

Only local planning and metadata layers exist here. Fetching, capture, ASR use, provider keyterms, and GUI integration are not implemented by this layer.

## Context / Glossary Policy

- Metadata/comments/context are for glossary discovery and QA only.
- They are not a replacement for transcription.
- External/background context is optional.
- External/background context must be strict-filtered.
- External/background context must never block local transcript/ASR work.
- External/background context must never be trusted as ground truth.
- The user must be able to review/edit glossary terms before they affect ASR prompts, provider keyterms, QA checks, or final transcript decisions.
- If a provider has no glossary/keyterm support, glossary terms can still feed Term QA after transcription.

## Scrollable Container Capture Notes

Social platforms can display comments inside nested scrollable containers or modals. A browser page screenshot or Page Up/Page Down workflow may only capture the visible portion of the comments container, not the full comment thread.

Future preservation/capture metadata should distinguish:

- visible screenshot only,
- full-page screenshot,
- scrollable-container screenshot,
- stitched/multi-image capture,
- selected-DOM or print-cleaned HTML,
- raw saved HTML,
- manually supplied evidence bundle.

Manual tools such as Print Edit WE, FireShot, GoFullPage, browser DevTools, or saved-page HTML can be useful evidence sources, but their outputs should be recorded with capture limitations. Do not treat any one visual/DOM capture method as a universal social-comment extractor. Future automation should be site-specific or site-family-specific, opt-in, and tested locally/mocked before any fetch/capture/browser behavior is added.

`capture_method_metadata.py` now formalizes these seven methods as local metadata with output kinds, current manual-only status, future-automation candidacy, limitations, and recommended next steps. It does not fetch, browse, capture screenshots, scrape, download, or wire into the GUI.

Preservation backend plans now also record media preservation intent as `none`, `select`, or explicit `all`. This local metadata neither discovers nor downloads media; any future automation must remain opt-in, site-specific, and locally/mocked tested.

The same preservation plan reports can now include multiple selected IDs from `capture_method_metadata.py`, with display names and limitations. Selection remains metadata only: no screenshot, DOM capture, scrolling, scraping, browser execution, or download occurs, and nested scrollable containers remain a known evidence limitation.

`preservation_evidence_bundle.py` and its stdout-only CLI now describe empty/planned or manual/external artifact bundles, fixed preservation formats, capture-method links, path hints, and limitations. They do not open, scan, hash, validate, create, upload, or capture files; nested scrollable-container completeness remains an explicit limitation.

Future webpage media preservation should also record whether media capture is `all` or `select`: `all` means every discovered image/video/media asset is intended for preservation, while `select` means the user chooses individual assets. Media download must remain opt-in and must not default to downloading everything from a webpage.

## Preservation Backend Plan CLI Usage

`preservation_backend_plan_cli.py` renders a local preservation backend plan for manually supplied source URLs, backend choices, and desired output formats.

```cmd
python preservation_backend_plan_cli.py
python preservation_backend_plan_cli.py --format text
python preservation_backend_plan_cli.py --format json
python preservation_backend_plan_cli.py --input preservation_plan.json --output PRESERVATION_BACKEND_PLAN.md --overwrite
```

Example input JSON:

```json
{
  "source_url": "https://www.telegraph.co.uk/news/example/",
  "selected_backend_ids": ["manual_local_files", "archivebox_self_hosted"],
  "selected_format_ids": ["html", "pdf", "warc", "json"],
  "notes": "User wants a local backup plan."
}
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network/archive services, test credentials, scrape pages, run ArchiveBox, capture screenshots, or wire into the GUI.

## Source Adapter Gap Analysis CLI Usage

`source_adapter_gap_analysis_cli.py` renders a local adapter and preservation gap analysis comparing the current adapter inventory with future platform/backend categories.

```cmd
python source_adapter_gap_analysis_cli.py
python source_adapter_gap_analysis_cli.py --format text
python source_adapter_gap_analysis_cli.py --format json
python source_adapter_gap_analysis_cli.py --output SOURCE_ADAPTER_GAP_ANALYSIS.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network/archive services, test credentials, scrape pages, run ArchiveBox, capture screenshots, or wire into the GUI.

## Source Adapter Capability Report CLI Usage

`source_adapter_capability_report_cli.py` renders local source adapter metadata from the registered adapter list as Markdown, text, or JSON.

```cmd
python source_adapter_capability_report_cli.py
python source_adapter_capability_report_cli.py --format text
python source_adapter_capability_report_cli.py --format json
python source_adapter_capability_report_cli.py --adapter youtube --output SOURCE_ADAPTER_CAPABILITIES.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network/archive services, test credentials, scrape pages, capture screenshots, or wire into the GUI.

## Context Glossary CLI Usage

`context_glossary_cli.py` reads a manually supplied JSON object and renders normalized context hints, deduped glossary terms, and phrase-prompt terms as Markdown, text, or JSON.

Example input shape:

```json
{
  "source_label": "YouTube clip",
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "Example title",
  "user_terms": ["Nyxara", "Freckelston"]
}
```

```cmd
python context_glossary_cli.py --input context_glossary_input.json
python context_glossary_cli.py --input context_glossary_input.json --format text
python context_glossary_cli.py --input context_glossary_input.json --format json
python context_glossary_cli.py --input context_glossary_input.json --output CONTEXT_GLOSSARY_REPORT.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything, call providers/network services, or feed ASR prompts/keyterms.

## Source Capture Plan CLI Usage

`source_capture_plan_cli.py` reads a manually supplied JSON object and renders a local Source Capture Plan as Markdown, text, or JSON.

Example input shape:

```json
{
  "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
  "source_label": "YouTube clip",
  "title": "Example title",
  "selected_capture_options": ["comments", "archive_check"],
  "user_terms": ["Nyxara", "Freckelston"]
}
```

```cmd
python source_capture_plan_cli.py --input source_capture_plan_input.json
python source_capture_plan_cli.py --input source_capture_plan_input.json --format text
python source_capture_plan_cli.py --input source_capture_plan_input.json --format json
python source_capture_plan_cli.py --input source_capture_plan_input.json --output SOURCE_CAPTURE_PLAN_REPORT.md --overwrite
```

The CLI prints to stdout by default, writes only when `--output` is explicitly supplied, and preserves existing files unless `--overwrite` is used. It does not fetch/capture/download anything or call providers/network services.

## Verification

Run from Windows CMD with the project virtual environment active:

```cmd
python -m py_compile source_adapters.py source_adapters_test.py source_adapters_registry_test.py source_adapter_capability_report.py source_adapter_capability_report_test.py source_adapter_capability_report_cli.py source_adapter_capability_report_cli_test.py source_adapter_gap_analysis.py source_adapter_gap_analysis_test.py source_adapter_gap_analysis_cli.py source_adapter_gap_analysis_cli_test.py source_capture_plan.py source_capture_plan_test.py source_capture_plan_cli.py source_capture_plan_cli_test.py source_plan_provenance.py source_plan_provenance_test.py context_glossary.py context_glossary_test.py context_glossary_cli.py context_glossary_cli_test.py youtube_url_utils.py youtube_url_utils_test.py & python source_adapters_test.py & python source_adapters_registry_test.py & python source_adapter_capability_report_test.py & python source_adapter_capability_report_cli_test.py & python source_adapter_gap_analysis_test.py & python source_adapter_gap_analysis_cli_test.py & python source_capture_plan_test.py & python source_capture_plan_cli_test.py & python source_plan_provenance_test.py & python context_glossary_test.py & python context_glossary_cli_test.py & python youtube_url_utils_test.py & git diff --check & git status --short
```

Expected result: all listed local self-tests pass and the working tree is clean after committed changes.

## Safe Next Milestones

1. Source/context/glossary documentation alignment:
   - remove stale wording that says skeletons do not exist if helper files now exist,
   - keep no fetch/capture/network/GUI behavior.
2. Future source adapters:
   - only as metadata/capability skeletons first,
   - no generic scraper,
   - no site fetching until separately approved with mocked/local tests.
3. GUI/runtime integration:
   - deferred until separately approved.

## Preservation Evidence Bundle Plan Integration

Preservation plans may include evidence bundle metadata for manual/planned/external artifacts. Path hints are descriptive labels only. The helpers do not open, scan, hash, create, upload, download, capture, scrape, or fetch files/URLs.


Evidence bundle item details can record role, origin, path hint labels, and notes in preservation plan reporting. Path hints are descriptive only and are not opened, scanned, hashed, or validated.


The preservation evidence bundle CLI can record item role, origin, path hint labels, and notes. These remain metadata strings only and do not trigger file inspection or capture behavior.


Evidence item detail parsing now uses shared preservation evidence bundle helpers across the local CLI entry points, keeping role/origin/path-hint/notes validation consistent without file or network operations.


Evidence item detail metadata now has local regression checks for malformed specs, duplicate details, and unknown artifact IDs across the shared helper and CLI entry points.


Preservation backend plan input JSON can include evidence bundle metadata for local reporting. The evidence bundle fields remain descriptive metadata and do not cause source fetching, file opening, capture, or network behavior.


Standalone preservation evidence bundle CLI can render explicit local JSON bundle metadata through `--input`; evidence path hints remain descriptive strings and do not trigger file inspection or capture behavior.


Evidence bundle CLI JSON input errors are covered for missing files and malformed JSON, with explicit local failures and no evidence path inspection.


Total Export preservation-plan explanations can render explicit evidence bundle JSON input. The JSON is local metadata only; path hints inside it are labels and do not trigger file inspection or capture behavior.


Total Export evidence bundle JSON input error handling is covered for malformed JSON and non-object roots, while continuing to avoid evidence path inspection.
