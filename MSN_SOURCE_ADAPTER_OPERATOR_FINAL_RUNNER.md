# MSN Source Adapter Operator Final Runner

Status: implementation support added.

This document describes the final operator runner for the MSN source adapter. The runner is designed for the final confidence stage after an MSN article has already been captured/exported into a local output folder.

It does **not** start live capture and it does **not** browse the web. It only chains the existing local/no-network MSN adapter report tools against an existing output folder.

## Why this exists

The MSN adapter is considered complete only when the following areas can be checked together:

1. Article extraction.
2. Comments/profile extraction.
3. Offline webpage/archive viewer.
4. Media discovery/download registration.
5. Source-role and media source-chain provenance.
6. Done-gate and acceptance reports.
7. Manual operator validation pack.

Earlier patches added each layer separately. This runner joins the layers into one operator-facing final summary so that a real MSN capture folder can be validated without manually remembering all commands.

## Command

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_operator_final_runner.py "C:\path\to\msn-output-folder" --source-url "https://www.msn.com/..." --output-dir "C:\path\to\reports"
```

The output directory defaults to:

```text
<msn-output-folder>\msn_source_adapter_operator_final
```

## Outputs

The runner writes:

```text
MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.json
MSN_SOURCE_ADAPTER_OPERATOR_FINAL_SUMMARY.md
```

It also delegates to existing tools which may write their own reports under the same output tree:

```text
completion\
final_validation\
done_gate\
acceptance\
live_acceptance_pack\
operator_smoke_pack\
```

## Status levels

The final summary uses:

```text
PASS
WARN
FAIL
SKIPPED
```

The overall status is:

```text
CONFIDENT_WITH_MANUAL_REVIEW
PARTIAL_REVIEW_NEEDED
BLOCKED
```

`CONFIDENT_WITH_MANUAL_REVIEW` means the code/report chain ran locally and the remaining uncertainty is about real MSN behaviour and operator observation, not missing adapter plumbing.

## Source-role rule preserved

The runner does not collapse MSN, visible publisher, visible credit, and original media source into one source. It expects the lower-level manifest, acceptance, and done-gate reports to preserve:

- MSN as captured platform / republisher surface where applicable.
- visible publisher/source such as The Independent where visible.
- visible media credit such as Google Street View where visible.
- original source gap when the original uploader/raw media source is not located.

## No automatic live/manual smoke

This runner may generate operator packs and templates, but it does not perform a live capture. Manual/live validation remains explicitly operator-gated.

## Practical use

Run this against the best available MSN capture/export folder after:

- rendered-page.html exists,
- archive/viewer artifacts exist,
- comments/profile exports exist where the article has comments,
- media inventory/download sidecars exist or are intentionally dry-run, and
- source-role provenance has been generated.

The final summary then tells whether the adapter output folder is ready to treat as complete, partial, or blocked.
