# MSN manual Total Export integration

This section connects approved MSN manual capture artifacts to the Total Export data path.

It implements the runnable local flow from explicitly supplied operator artifacts to a review-ready
Total Export package:

- extract MSN article title/body from a saved HTML or text artifact
- extract MSN comments from a saved JSON, NDJSON, or transcript artifact
- assemble a normalized capture bundle
- create a Total Export manifest with safe relative asset names
- write article text, comments JSON, bundle JSON, and manifest JSON into a selected output folder
- verify the stored package without serializing full local paths

Execution boundary:

- only explicit file arguments are read
- no folder scans, browser automation, live HTTP, archive submission, WARC/WACZ, ArchiveBox,
  media download, or credential reads are performed by this integration
- the exported files contain the operator-supplied article/comment content because this is the
  implemented data path, not an observation-only record
- outputs remain review-gated and do not claim completed or independently verified capture
