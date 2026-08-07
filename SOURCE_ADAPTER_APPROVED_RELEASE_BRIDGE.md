# Source Adapter Approved Release Bridge

Shared Adapter Approved Release Bridge consumes `source_adapter_evidence_review_bridge_v1` output and runs the shared `source_approved_release` implementation for each approved Evidence Review output.

The section builds approved-release output batches, a release-index batch handoff with `READY_FOR_SHARED_RELEASE_INDEX`, deterministic store artifacts, CLI, verifier, and tests. It supports multi-adapter batches through the shared approved-release builder rather than cloning site-specific release modules.

Execution uses explicit Evidence Review decisions and release handoffs as inputs. Approval gates and operator identities remain represented in JSON so live/release-facing features can be implemented through named, auditable sections when the roadmap reaches them.
