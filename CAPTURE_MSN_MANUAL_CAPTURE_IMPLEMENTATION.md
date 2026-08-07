# MSN manual capture implementation

This section implements the data-processing side of approved MSN manual live smoke actions.

It is not observation-only. Operator-supplied article and comments artifacts can be read from
explicit file arguments and converted into normalized Total Export-ready JSON bundles:

- MSN article title/body/source metadata extraction from saved HTML or copied text
- MSN comments extraction from copied JSON, NDJSON, or transcript text
- bundle assembly with source URL, article content, normalized comments, artifact hashes, and review state
- safe bundle persistence and CLI entry point

Execution boundary:

- only explicitly supplied files are read
- no folder scans or file movement are performed
- no live HTTP, browser automation, archive submission, WARC/WACZ, ArchiveBox, or media download is performed by tests
- full local paths, credential values, and raw HTML payloads are not serialized
- article/comment text is captured because this section implements data extraction, not metadata-only observation
- output remains review-gated and does not claim completed or verified capture
