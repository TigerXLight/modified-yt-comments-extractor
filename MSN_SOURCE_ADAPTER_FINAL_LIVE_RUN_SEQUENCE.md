# MSN Final Live Run Sequence

This is the locked live-run sequence for MSN adapter closure.

1. Capture or select the real MSN output folder.
2. Run the operator final runner against that folder.
3. Run the final validation / done-gate / acceptance tooling.
4. Fill the live evidence template using the observed real MSN output.
5. Run the live evidence validator.
6. Run release promotion only after the positive live evidence file exists.
7. Generate certification/archive outputs.
8. Run post-certification audit.
9. Preserve the generated reports with the evidence package.

No step in this sequence allows a no-network self-test to become a claim that live MSN is complete.
