# MSN Source Adapter Final Operator Status

The operator-facing state machine is:

- `RC_LOCKED_PENDING_LIVE_EVIDENCE`: all repo-side pieces are present, but no positive manual/live result was supplied.
- `COMPLETE_WITH_LIVE_EVIDENCE`: repo-side pieces are present and a positive manual/live result was supplied.
- `PARTIAL`: one or more expected repo-side pieces are missing.
- `BLOCKED`: the manual/live evidence exists but cannot be read or contains blocking/failing signals.

The intended final state before moving away from MSN is `RC_LOCKED_PENDING_LIVE_EVIDENCE` or stronger.  The intended final state after a named live MSN validation is `COMPLETE_WITH_LIVE_EVIDENCE`.
