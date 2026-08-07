# Shared source Evidence Queue

This shared stage turns a `source_total_export_package_v1` object into an Evidence Queue item for adapter-neutral review.

It consumes explicit JSON inputs only, writes deterministic queue outputs, and hands the result to `source_evidence_review`.
It does not fetch URLs, launch browsers, scan folders, read credentials, submit archive requests, or serialize full local paths. In other words, it does not serialize full local paths.

Per-source adapters should normally provide adapter specs and fixtures, then reuse this queue stage rather than cloning MSN-specific review modules.
