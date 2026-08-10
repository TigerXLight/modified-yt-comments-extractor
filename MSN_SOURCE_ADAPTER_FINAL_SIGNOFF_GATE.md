# MSN Source Adapter Final Signoff Gate

The final signoff gate produces JSON, Markdown, and CSV outputs for a selected repository/output folder.

Allowed states:

- `GOAL_TRACEABILITY_READY`
- `SIGNOFF_BLOCKED_MISSING_REPO_ARTIFACTS`
- `SIGNOFF_PENDING_POSITIVE_LIVE_EVIDENCE`
- `SIGNED_OFF_WITH_POSITIVE_LIVE_EVIDENCE`

The gate must not produce `SIGNED_OFF_WITH_POSITIVE_LIVE_EVIDENCE` from no-network tests alone.
