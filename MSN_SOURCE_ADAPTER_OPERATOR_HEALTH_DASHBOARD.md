# MSN Source Adapter Operator Health Dashboard

Purpose: provide one conservative, no-network dashboard for the current MSN adapter state.

This module does **not** scrape MSN and does **not** claim live completion by itself. It checks that the repo-side MSN tooling exists and then inspects a selected MSN output/evidence folder for manual/live evidence.

Final status wording is intentionally conservative:

- `INCOMPLETE_TOOLING`: required repo tooling is missing.
- `READY_FOR_LIVE_EVIDENCE`: repo tooling is present, but no positive live evidence was found.
- `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`: repo tooling is present and a positive live evidence file is found.
- `PROMOTION_BLOCKED`: live evidence exists but reports failure/blocking conditions.

The dashboard writes JSON, Markdown, and CSV outputs.
