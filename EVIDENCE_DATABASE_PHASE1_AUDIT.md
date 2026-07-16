# Evidence Database Phase 1 Audit

Date: 2026-07-16

Checkpoint: `ee527fd Document operational site capture milestone`

## Scope

This audit starts the evidence-database implementation after the REV4 operational site-capture closeout. It is local/model-only for Batch ED0.

No live site access, archive provider call, provider/API call, browser automation, screenshot capture, media download, broad folder scan, credential access, evidence file move, or sensitive-attribute inference is approved here.

## Existing Coverage

- `EVIDENCE_DATABASE_TAXONOMY_SPEC.md` defines the user-defined taxonomy, read-only indexing, unknown/not identified, reclassification, sensitive-classification safeguards, Total Export relationship, queue relationship, and dry-run requirements.
- `evidence_database_taxonomy.py` already provides a schema-only taxonomy foundation with root registration, mapping entries, classification dimensions, dry-run reports, reclassification suggestions, alias suggestions, history records, and deterministic dictionary output.
- `evidence_item_queue.py` already provides immutable queue items, links, ASR pairing metadata, and a database-category-suggestion role without UI/storage/file movement.
- `total_export_manifest.py` and related Total Export helpers provide local package/manifests/assets/review metadata but do not implement database indexing or file movement.
- REV4 operational site-capture modules provide local/mock capture scaffolds and source UI capture-plan wiring only; they do not authorize live capture or evidence database work beyond local model integration.

## ED0 Gap

The existing taxonomy skeleton does not yet provide a focused Phase 1 index contract with stable item identities, path records, placement/reclassification proposals, and an index manifest suitable for a later atomic local index store.

## ED0 Implementation Decision

Add `evidence_database_index.py` as a serialization-only Phase 1 contract module. Keep it separate from the older taxonomy skeleton so the new index-layer model can evolve through ED1-ED4 without destabilizing existing tests.

Required ED0 contracts:

- `EvidenceDatabaseRoot`
- `EvidenceTaxonomyVersion`
- `EvidenceItemIdentity`
- `EvidencePathRecord`
- `EvidenceClassificationState`
- `EvidenceBasis`
- `EvidencePlacementProposal`
- `EvidenceReclassificationProposal`
- `EvidenceIndexRecord`
- `EvidenceIndexManifest`

## Safety Notes

- Stable IDs are deterministic hashes over explicit metadata strings only.
- Paths are metadata strings; ED0 does not check existence or walk directories.
- Sensitive dimensions require explicit evidence/user confirmation and keep weak inference prohibited by default.
- Placement and reclassification proposals are dry-run records only and state that no files were moved.
- Optional file movement remains a later explicit approval boundary.
