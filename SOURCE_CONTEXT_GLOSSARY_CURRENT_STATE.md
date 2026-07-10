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
| Source adapter metadata | `source_adapters.py`, `source_adapters_test.py` | Local adapter capability metadata and URL support checks. |
| Context/glossary skeleton | `context_glossary.py`, `context_glossary_test.py` | Local glossary normalization, deduplication, user-term handling, and context hint resolution. |
| Source capture planning | `source_capture_plan.py`, `source_capture_plan_test.py` | Local source URL + adapter + capture option + context hint plan assembly. |
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

## Verification

Run from Windows CMD with the project virtual environment active:

```cmd
python -m py_compile source_adapters.py source_adapters_test.py source_capture_plan.py source_capture_plan_test.py source_plan_provenance.py source_plan_provenance_test.py context_glossary.py context_glossary_test.py youtube_url_utils.py youtube_url_utils_test.py & python source_adapters_test.py & python source_capture_plan_test.py & python source_plan_provenance_test.py & python context_glossary_test.py & python youtube_url_utils_test.py & git diff --check & git status --short
```

Expected result: all five local self-tests pass and the working tree is clean after committed changes.

## Safe Next Milestones

1. Source/context/glossary documentation alignment:
   - remove stale wording that says skeletons do not exist if helper files now exist,
   - keep no fetch/capture/network/GUI behavior.
2. Local-only CLI for source capture plan inspection:
   - read manually supplied JSON,
   - render plan summary as text/Markdown/JSON,
   - explicit-output-only,
   - no fetch/capture/network/GUI behavior.
3. Local-only context glossary report CLI:
   - read user-entered context hints and glossary terms,
   - render normalized/deduped glossary candidates,
   - explicit-output-only,
   - no provider prompt/keyterm integration.
4. New source adapters:
   - only as metadata/capability skeletons first,
   - no generic scraper,
   - no site fetching until separately approved with mocked/local tests.
5. GUI/runtime integration:
   - deferred until separately approved.
