# MSN Source Adapter Remaining Work Tracker

After this patch, the remaining work should no longer be broad architecture. It should be real-output validation and targeted fixes only.

## Done structurally

- Article extraction path.
- Comments/profile export path.
- Offline viewer/archive path.
- Media inventory/download workflow path.
- Readiness report.
- Release report.
- Final validation report.
- Completion CLI.
- Manual validation intake.
- Done gate.
- Acceptance suite.
- Operator final runner.
- Live result reconciler.

## Not claimed without real run

- Every future MSN page layout.
- Perfect ReplayWeb WACZ support.
- Every hidden streaming video URL.
- Primary source located when MSN is only republishing another source.

## Next evidence step

Run the operator final runner on an actual MSN output folder, fill the live acceptance result, then run the live result reconciler. The resulting report is the final answer for whether that MSN target is complete, partial, or blocked.
