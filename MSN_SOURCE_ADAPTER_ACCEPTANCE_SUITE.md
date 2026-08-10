# MSN Source Adapter Acceptance Suite

This module is the capstone confidence layer for an already-produced MSN output
folder. It does not capture the web. It reads the existing artifact folder and
writes final acceptance reports:

- `MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.json`
- `MSN_SOURCE_ADAPTER_ACCEPTANCE_REPORT.md`
- `MSN_SOURCE_ADAPTER_ACCEPTANCE_CHECKS.csv`

The acceptance suite checks the adapter goal areas:

1. Article extraction.
2. Comments/profile extraction.
3. Offline webpage/archive viewer.
4. WARC/WACZ replay artifact status.
5. Image/video/media registration and download/hash status.
6. Source-role and media source-chain provenance.
7. Readiness/release/final/done report chain.

## Source-role rule preserved

MSN must not b/e silently treated as the original source when it republishes an
article from another publisher such as The Independent. Media credits such as
Google Street View must remain separate from the publisher and from any claimed
original uploader. Missing original-source chains should b/e recorded as gaps, not
filled with assumptions.

## Statuses

- `ACCEPTED`: required areas pass from the available artifact evidence.
- `CONFIDENT_WITH_MANUAL_REVIEW`: required areas exist b/ut one or more are
  partial, normally WARC/WACZ replay, streamed video, or original-source tracing.
- `BLOCKED`: one or more required areas failed.

## Example

```cmd
python source_msn_adapter_acceptance_suite.py --root "C:\path\to\msn-output" --output "C:\path\to\msn-output\reports"
```
