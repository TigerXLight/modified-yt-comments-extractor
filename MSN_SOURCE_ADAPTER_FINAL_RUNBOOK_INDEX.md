# MSN Final Runbook Index

Recommended operator sequence for one existing MSN output folder:

1. Generate or refresh total package.
2. Run final validator.
3. Run done gate.
4. Run acceptance suite.
5. Generate live evidence template.
6. Fill manual/live evidence after a real MSN run.
7. Run live evidence validator.
8. Run release promotion gate.
9. Run certification bundle/archive.
10. Run final readiness badge and end-state summary.

Do not mark COMPLETE until the promotion gate sees positive live evidence.
