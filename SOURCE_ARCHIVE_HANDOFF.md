# Shared Source Archive Handoff

`source_archive_handoff.py` creates the shared manual archive handoff boundary for every source adapter. It consumes a verified `source_release_audit_v1` report and produces provider tasks, blank archive-result templates, and a result-intake handoff.

This stage is intentionally local and manual-safe: it does not fetch URLs, launch browsers, submit archive requests, validate online archive contents, read credentials, scan folders, upload releases, or mark any archive task as complete.

Outputs are deterministic JSON records with safe basenames only, including `source_archive_handoff_package`, `source_archive_provider_tasks`, `source_archive_result_templates`, `source_archive_result_intake_handoff`, and an operator summary.
