# MSN manual action-to-Total-Export pipeline

This section implements the runnable bridge between the manual live-smoke action system and the
MSN manual Total Export package writer.

It is not an observation-only layer. The pipeline:

- generates operator action kits for MSN article capture and MSN comments shadow-root capture
- reads explicit operator-supplied article/comment artifact files
- extracts article text and comments data
- writes a review-ready Total Export package with manifest, article text, comments JSON, capture bundle JSON, and packet JSON
- verifies the package shape and emits a safe pipeline report

Safety boundary:

- tests do not perform live HTTP, browser automation, archive submission, WARC/WACZ, ArchiveBox, media downloads, or credential reads
- generated `.cmd` files are the operator-run implementation path and still require explicit human approval before live browser launch
- only explicit file arguments are read; no folder scans or file moves are performed
- output metadata serializes safe relative names and hashes, not full local paths
- the pipeline does not claim completed or independently verified capture; review remains required
