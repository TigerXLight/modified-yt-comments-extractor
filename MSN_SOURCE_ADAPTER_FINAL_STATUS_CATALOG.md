# MSN Source Adapter Final Status Catalog

Canonical status wording for the MSN adapter:

- `READY_FOR_LIVE_EVIDENCE`: tooling exists and no-network self-tests pass.
- `RC_LOCKED_PENDING_LIVE_EVIDENCE`: release-candidate lock exists, but no positive live evidence has been supplied.
- `PROMOTION_BLOCKED`: positive completion cannot be asserted because a required live check failed or is missing.
- `CONFIDENT_WITH_MANUAL_REVIEW`: generated evidence is structurally strong but still needs or preserves manual review.
- `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`: final state only after a filled live evidence result confirms the required areas.

Forbidden wording:

- Do not write `COMPLETE` for a real MSN run from fixtures alone.
- Do not treat MSN as the primary source merely because MSN hosted the captured page.
- Do not collapse visible publisher/source credit, media credit, and original-source status into one field.
