# MSN Source Adapter Live Evidence Validator

This validator is the boundary between no-network confidence and a real MSN completion claim.

It scans an existing MSN output folder for a filled manual/live acceptance result JSON and writes:

- `MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_VALIDATION.json`
- `MSN_SOURCE_ADAPTER_LIVE_EVIDENCE_VALIDATION.md`

The validator accepts live evidence only when the filled operator result records all required checks as passing:

1. `article_extraction`
2. `comments_profile_extraction`
3. `offline_viewer_archive`
4. `media_registration`
5. `source_chain_review`

Optional checks such as video stream status, WARC/WACZ status, downloaded media hashes, and profile statistics are recorded but do not override the required checks.

Important rule: a template file, fixture-only report, or no-network self-test does not prove live MSN completion.

Example:

```cmd
C:\Users\fahad\AppData\Local\Programs\Python\Python311\python.exe source_msn_adapter_live_evidence_validator.py --root "C:\path\to\msn_output_folder"
```
