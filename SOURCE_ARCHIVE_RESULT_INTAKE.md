# Shared Source Archive Result Intake

`source_archive_result_intake.py` creates the shared manual archive-result intake boundary for every source adapter. It consumes a verified `source_archive_handoff_v1` package and explicit operator-supplied archive results, then produces a receipt index and an Archive Review handoff.

This stage is intentionally local and manual-safe: it does not fetch URLs, launch browsers, submit archive requests, does not validate online archive contents, read credentials, scan folders, upload releases, or mark archive receipts as reviewed.

Outputs are deterministic JSON records with safe basenames only, including `source_archive_result_intake_record`, `source_archive_receipt_index`, `source_archive_review_handoff`, and an operator summary. The required next stage is `source_archive_review`.
