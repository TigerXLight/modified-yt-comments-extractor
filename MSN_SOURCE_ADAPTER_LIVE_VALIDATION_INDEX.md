# MSN Source Adapter Live Validation Index

This document describes the final live-validation index layer for the MSN source adapter.

The index scans a completed MSN output folder and reports whether the folder has the expected live-run evidence across:

- article extraction
- comments export
- profile export
- offline viewer / rendered page
- WARC / archive outputs
- WACZ / ReplayWeb-labelled outputs
- media / image / video outputs
- source-chain and provenance outputs
- final reports, acceptance, certification, and live evidence

The live-validation index deliberately keeps the same boundary used across the MSN adapter chain:

> No no-network self-test can promote the adapter to a real MSN COMPLETE state. A positive manual/live evidence file is required.

## Main command

```cmd
python source_msn_adapter_live_validation_index.py --input "C:\path\to\MSN_OUTPUT_FOLDER"
```

Optional explicit output directory:

```cmd
python source_msn_adapter_live_validation_index.py --input "C:\path\to\MSN_OUTPUT_FOLDER" --output "C:\path\to\MSN_OUTPUT_FOLDER\reports"
```

## Output files

- `MSN_SOURCE_ADAPTER_LIVE_VALIDATION_INDEX.json`
- `MSN_SOURCE_ADAPTER_LIVE_VALIDATION_INDEX.md`
- `MSN_SOURCE_ADAPTER_LIVE_VALIDATION_INDEX.csv`

## Final states

- `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`
- `READY_FOR_LIVE_EVIDENCE`
- `PROMOTION_BLOCKED`
- `INSUFFICIENT_OUTPUT`

## Required positive live evidence keys

A filled live evidence JSON must positively show:

- `article_extracted`
- `comments_exported`
- `profiles_exported`
- `offline_viewer_verified`
- `archive_verified`
- `media_reviewed`
- `source_chain_reviewed`

This keeps the MSN adapter honest: structural readiness and repo tests are not the same as a successful live MSN run.
