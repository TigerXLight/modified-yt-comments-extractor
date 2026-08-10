# MSN Source Adapter Certification Bundle

This layer produces a final, operator-facing certification bundle for an existing MSN capture/output folder.

It does **not** claim that live MSN capture is complete from no-network fixtures alone. The bundle is designed to preserve the boundary used throughout the MSN adapter work:

- no-network/self-test evidence can lock the adapter as release-candidate ready;
- positive manual/live MSN evidence is required before a real MSN page can be certified as complete;
- MSN republisher surface, visible publisher/source credit, visible media credit, and original-source status remain separate.

## Outputs

The certification bundle CLI writes the following files under the requested output directory:

- `MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.json`
- `MSN_SOURCE_ADAPTER_CERTIFICATION_BUNDLE.md`
- `MSN_SOURCE_ADAPTER_CERTIFICATION_CHECKS.csv`

## Decision states

- `CERTIFIED_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`
- `RC_LOCKED_PENDING_LIVE_EVIDENCE`
- `PROMOTION_BLOCKED`
- `INSUFFICIENT_EVIDENCE`

## Required live-evidence boundary

A certification report must not promote the adapter to complete when the only evidence is fixture/no-network output. A live evidence result must explicitly pass the key checks for article extraction, comments/profile extraction, offline viewer/archive, media registration/download status, and source-chain/provenance separation.

## Typical command

```cmd
python source_msn_adapter_certification_bundle.py --root "C:\path\to\MSN_OUTPUT_FOLDER" --out "C:\path\to\MSN_OUTPUT_FOLDER\final_certification"
```
