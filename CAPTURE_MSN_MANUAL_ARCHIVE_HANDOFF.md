# MSN manual archive handoff

This section adds the external-archive handoff boundary for the completed MSN manual release flow.

The handoff consumes an explicit `msn_manual_release_audit_report_v1` JSON packet and a source URL supplied by the operator. It produces manual-only archive tasks, provider-specific result templates, and a deterministic archive handoff packet for later archive-result intake.

The implementation is local and operator-gated. It does not fetch live pages, submit archive requests, call archive services, read key material, or mark archive capture as complete.
