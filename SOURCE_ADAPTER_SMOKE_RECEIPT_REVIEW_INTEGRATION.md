# Source Adapter Smoke Receipt Review Integration

This milestone implements receipt-review integration after named-site smoke
execution.  It consumes named-site provider action receipts, verifies provider
receipt files, records review decisions, and projects accepted receipts into the
source evidence / total export handoff surfaces.

## Implemented surfaces

- Review decision rows for all named-site provider action receipts.
- Per-site evidence integration rows for capture, archive, release, file-library,
  and KEYS/ACCOUNTS receipt families.
- Store, CLI, verifier, and docs tests.
- Release/export gate showing reviewed receipt readiness.

## Status strings

- `SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_INTEGRATION_BUILT`
- `SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_DECISIONS_READY`
- `SOURCE_ADAPTER_SMOKE_RECEIPTS_INTEGRATED_FOR_SOURCE_EVIDENCE_REVIEW`
- `SOURCE_ADAPTER_SMOKE_RECEIPT_REVIEW_READY_FOR_RELEASE_EXPORT_INTEGRATION`

## Operator contract

This stage is the review/import side of the smoke execution workflow.  It does
not discard provider receipts; it records decision rows, evidence integration
rows, and release/export readiness metadata while preserving `KEYS/ACCOUNTS`
redacted credential-reference hashes.
