# Shared Source Archive Review

`source_archive_review.py` creates the shared manual archive-review boundary for every source adapter. It consumes a verified `source_archive_result_intake_v1` record and optional receipt index / review handoff, then produces an archive review package, checklist, decision record, closeout record, and operator summary.

This stage is intentionally local and manual-safe: it does not fetch URLs, launch browsers, submit archive requests, validate online archive contents, read credentials, scan folders, upload releases, mutate the archive-result intake record, or start live/manual actions.

`APPROVED` decisions close the shared source pipeline with `ARCHIVE_COMPLETE`. `REJECTED` and `REVISION_REQUESTED` decisions remain explicit follow-up states that can be retried through archive result intake/review without claiming online validation.
