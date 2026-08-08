# Source Adapter Archive Submission Runner Runtime

This implementation milestone adds `source_adapter_archive_submission_runner_runtime` as a callable runtime surface for the shared Source Adapter pipeline.

It covers archive submission runner rows for archive.ph, Wayback, Ghostarchive, perma-like, and manual provider submissions behind explicit operator approval.

The milestone preserves the `KEYS/ACCOUNTS` label, carries credential references as identifiers/redacted hashes only, records receipt-required rows, and keeps provider/network execution behind explicit operator-approved runtime calls.

Tested status strings:

- `SOURCE_ADAPTER_ARCHIVE_SUBMISSION_RUNNER_RUNTIME_BUILT`
- `SOURCE_ADAPTER_ARCHIVE_SUBMISSION_RUNNER_RUNTIME_READY_FOR_NEXT_IMPLEMENTATION_BUNDLE`
- `SOURCE_ADAPTER_ARCHIVE_SUBMISSION_RUNNER_RUNTIME_ROWS_READY`
