# MSN Source Adapter Final State Lock

This document records the intended final state for the MSN adapter completion slice.

## Goal statement

The MSN adapter is considered done only when the workflow can produce or validate an evidence package that covers:

- article extraction,
- comments and nested replies,
- profile links and profile account statistics where available,
- offline rendered article view,
- WARC/WACZ/archive outputs with honest status labels,
- image/media/video candidate registration,
- downloaded media hashes when downloaded media is present,
- source-role and primary-source-status metadata,
- clear separation between MSN as the captured surface, visible publisher/source, visible media credit, and the original source when not located,
- final reports that say PASS/PARTIAL/FAIL instead of relying on assumptions.

## Non-negotiable source role rules

1. MSN is a captured platform or republisher surface unless the article is actually authored by MSN.
2. A visible publisher such as `The Independent` is not automatically the original source for every claim or media item.
3. A visible image credit such as `Google Street View` is media-credit evidence, not proof that MSN is the primary source.
4. Repeated media reports, agency loops, authority claims, family claims, or database summaries do not become primary merely through repetition.
5. Primary-source status is claim-level/item-level, not just URL-level.
6. Missing original source evidence must be marked as a gap, not silently filled.

## Completion vocabulary

Use these final states consistently:

- `COMPLETE`
- `CONFIDENT_WITH_MANUAL_REVIEW`
- `PARTIAL`
- `BLOCKED`
- `INSUFFICIENT_EVIDENCE`

Use these check states consistently:

- `PASS`
- `PARTIAL`
- `FAIL`
- `NOT_APPLICABLE`
- `UNKNOWN`

## Current confidence target

The repo should be allowed to say the MSN adapter is structurally confident when fixture/no-network tests pass and the output folder contains reports from the final validator, acceptance suite, done gate, operator final runner, and live-result reconciler.

The repo should only say live MSN is complete when a filled manual/live acceptance result is present and does not report a blocking failure.
