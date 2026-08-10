# MSN Source Adapter Final Operator Packet

This document describes the final operator packet layer for the MSN source adapter.

The adapter is release-candidate locked and operationally ready for live evidence collection, but the final `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE` state must only be used after a positive manual/live validation result is present.

## What this layer adds

- A single final operator packet generator.
- A repo artifact manifest generator.
- Machine-readable JSON, Markdown, and CSV outputs.
- A generated command file for the final live-evidence workflow.
- A locked wording boundary so no no-network self-test can be treated as live MSN completion evidence.

## Final state boundary

Allowed states:

- `READY_FOR_LIVE_EVIDENCE`
- `RC_LOCKED_PENDING_LIVE_EVIDENCE`
- `PROMOTION_BLOCKED`
- `COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE`

The packet may report that the repository is ready, but it must not claim the live MSN adapter is complete unless a positive live evidence file has been supplied and passed the validator.
