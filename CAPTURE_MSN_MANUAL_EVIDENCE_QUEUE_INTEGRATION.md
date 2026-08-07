# MSN manual capture Evidence Queue integration

This section connects the implemented MSN manual action-to-Total-Export pipeline to the
Source Evidence / Evidence Item Queue review flow.

This is an implementation layer, not an observation-only note. It:

- reads an explicit MSN manual action Total Export pipeline JSON report
- validates that the pipeline generated operator action kits and wrote a Total Export package
- extracts safe relative asset metadata for the manifest, article text, bundle JSON, packet JSON, and optional comments JSON
- builds a deterministic Evidence Queue item ready for review
- writes the queue item and queue index JSON to a user-selected directory
- exposes a local CLI so an operator can move an approved MSN manual package into the review queue

Safety boundary:

- it reads only the explicit JSON file named by the operator
- it does not perform live HTTP, browser automation, archive submission, media downloads, WARC/WACZ, ArchiveBox, credential reads, folder scans, or file moves
- it serializes safe filenames, relative asset names, hashes, and byte counts only
- it does not claim that a capture is complete or independently verified; review remains required
