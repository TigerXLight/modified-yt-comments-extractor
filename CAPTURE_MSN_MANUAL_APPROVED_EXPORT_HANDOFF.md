# MSN manual approved export handoff

This section implements the approved-review handoff from an MSN manual Evidence Review decision into the Total Export release path.

The handoff consumes explicit local JSON inputs only: a reviewer decision JSON and, optionally, the previously written Total Export package store JSON. It does not perform live HTTP, browser automation, screenshot capture, archive submission, media download, WARC/WACZ generation, ArchiveBox execution, credential reads, or folder scans.

Implemented outputs:

- approved export handoff JSON with queue identity, source URL, article title, reviewer decision, safe assets, and release steps
- release queue update JSON marking the MSN manual capture ready for Total Export release only when the decision is approved and clean
- local CLI to build and store the handoff from explicit JSON files
- verifier for schema, readiness, safety flags, safe filenames, hashes, and no full local paths
