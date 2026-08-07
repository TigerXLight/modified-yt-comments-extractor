# Shared source Total Export package

This shared stage packages a `source_capture_bundle_v1` object for the generic Total Export path.

It consumes explicit JSON inputs only, writes deterministic JSON package outputs, and hands the result to `source_evidence_queue`.
It does not fetch URLs, launch browsers, scan folders, read credentials, submit archive requests, or serialize full local paths. In other words, it does not serialize full local paths.

Per-source adapters should normally provide adapter specs and fixtures, then reuse this package stage rather than cloning MSN-specific release modules.
