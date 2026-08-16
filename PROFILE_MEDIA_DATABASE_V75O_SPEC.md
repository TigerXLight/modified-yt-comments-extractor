# V75O — Profile/media square visual toggle runtime hardening

V75O keeps the Database sidebar control mode-only and fixes the runtime visual method pair so the square green/red toggle behaviour is the active implementation.

It removes the stale compact `✓ On` / `✕ Off` refresh implementation that could override the square visual methods at runtime.

Safety boundaries remain unchanged:

- no preview panel
- no filter box
- no filesystem scan
- no folder creation
- no folder move
- no folder rename
- no file copy
- no automatic classification
- no sensitive identifier inference

The sidebar intent remains:

```text
DATABASE
  [green ✓        ◻]  on
  [red   ◻        ✕]  off
FILES
```
