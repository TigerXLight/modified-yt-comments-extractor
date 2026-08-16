# V76I Profile/Media Reconciliation Closeout Pack

V76I adds the missing post-operation reconciliation layer for Database mode.

## Scope

- Fixes the main Database panel review lanes so nested workbench dashboard/review-report counts surface correctly.
- Adds a read-only batch-preview reconciliation planner after reviewed folder rename/move operations.
- Allows writing a new standalone reconciled batch-preview JSON only after the exact confirmation phrase:
  `WRITE_RECONCILED_PROFILE_MEDIA_BATCH_PREVIEW`.
- Adds CLI/tests/fixtures for the reconciliation workflow.

## Safety invariants

V76I does not scan folders, create folders, move folders, rename folders, copy media, download media, classify automatically, or infer sensitive identifiers. The only optional write is a standalone JSON preview selected by the caller.
