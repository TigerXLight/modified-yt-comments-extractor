# MSN Source Adapter Failure Guard

The failure guard rule is simple:

```text
A self-test traceback, assertion failure, non-zero return code, or failed validation state must stop the workflow before commit/push.
```

This protects the MSN adapter completion boundary from being weakened by scripts that print a failure but continue execution.

## Required behaviour

A future patch or local workflow must not treat the following as clean:

```text
Traceback
AssertionError
Self-test failed
SELFTEST_FAILURES_DETECTED
PROMOTION_BLOCKED
SIGNOFF_BLOCKED_MISSING_REPO_ARTIFACTS
```

## Completion boundary preserved

No offline/no-network test can promote MSN to final `COMPLETE` by itself.

The accepted live-complete wording remains tied to positive manual/live evidence only:

```text
COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE
CERTIFIED_COMPLETE_WITH_POSITIVE_LIVE_EVIDENCE
SIGNED_OFF_WITH_POSITIVE_LIVE_EVIDENCE
```

Absent that evidence, the honest state remains pending live evidence, such as:

```text
RC_LOCKED_PENDING_LIVE_EVIDENCE
READY_FOR_LIVE_EVIDENCE
SIGNOFF_PENDING_POSITIVE_LIVE_EVIDENCE
```
