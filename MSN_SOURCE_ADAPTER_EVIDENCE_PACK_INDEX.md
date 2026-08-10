# MSN Source Adapter Evidence Pack Index

This patch adds an evidence-pack indexer for MSN adapter output folders.

`source_msn_adapter_evidence_pack_index.py` hashes and lists key files from an existing MSN bundle:

- reports
- article outputs
- comments/profile outputs
- media outputs
- WARC/WACZ/archive outputs
- offline viewer outputs

It writes:

- `MSN_SOURCE_ADAPTER_EVIDENCE_PACK_INDEX.json`
- `MSN_SOURCE_ADAPTER_EVIDENCE_PACK_INDEX.md`

This gives the user a stable file manifest for handoff, audit, or future comparison.
