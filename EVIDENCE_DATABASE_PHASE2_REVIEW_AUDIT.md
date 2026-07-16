# Evidence Database Phase 2 Review Workflow Audit

Date: 2026-07-16

Checkpoint: `f37cf62 Document evidence database phase 1`

## Scope

Evidence Database Phase 2 starts the review/controller layer around the Phase 1
model and index foundations.

This phase remains local, review-oriented, dry-run, and user-confirmation-first.
It does not approve broad folder scans, real evidence file moves, automatic
classification execution, live site capture, archive/provider calls, downloads,
scraping, browser automation, credential access, or sensitive-attribute
inference.

## Existing Coverage

- `evidence_database_index.py` provides deterministic database roots, taxonomy
  versions, stable item identities, path history, classification state, evidence
  basis, dry-run placement/reclassification proposals, index manifests, atomic
  JSON index storage, hierarchy recognition over supplied fixture paths, and
  converter-only queue/source-resource/Total Export integration.
- `evidence_database_taxonomy.py` provides the earlier read-only taxonomy and
  reclassification schema foundation.
- `evidence_item_queue.py`, `source_resource_state.py`, and
  `total_export_manifest.py` provide the explicit local metadata surfaces that
  Phase 1 converters can represent as index records.

## Review/UI Gap

The project does not yet have a review workflow object that can describe:

- a bounded evidence database review session;
- an explicitly supplied root registration draft;
- a preview request that uses supplied records only;
- grouped preview output;
- user decisions over dry-run proposals;
- a non-executing apply plan;
- a result that confirms no destructive action was performed.

## EDUI0 Decision

Add `evidence_database_review.py` as a controller-contract module. The first
batch is serialization-only and deterministic. Runtime controllers, preview
builders, and any optional UI hook will be added in later Phase 2 batches only
if they stay inside the dry-run/review boundary.

## Safety Notes

- Apply plans default to dry-run and cannot imply file movement.
- Review decisions require explicit confirmation by default.
- Preview requests are for explicit records only; they do not authorize scanning.
- Sensitive classifications remain governed by the Phase 1 safeguards.
- Destructive actions remain unimplemented and require a separate future
  approval.
