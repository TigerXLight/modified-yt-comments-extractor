# Manual live smoke action execution kit

This document defines the runnable operator kit for approved manual live smoke actions.

The kit is implementation, not observation-only metadata. It writes local command files,
action plans, DevTools snippets, artifact collection templates, and observation packet
handoff templates so an approved operator can perform the named action and then collect
safe artifact metadata for review.

Supported flow:

1. Generate an execution kit for a named site/action/source URL.
2. Run the generated dry-run command to inspect the plan.
3. Run the generated approved command only when the operator has approved the live action.
4. Use the generated action-specific browser/devtools snippets and notes while performing the manual capture.
5. Save operator artifacts locally.
6. Run the generated artifact collection template with explicit `role=file` arguments.
7. Review the generated observation packet before any capture is marked accepted.

Safety boundary:

- browser launch requires the approval token and the explicit execute flag
- tests do not perform live HTTP or browser launches
- files are read only when explicitly supplied as `role=file` arguments
- no folder scan or file movement is performed
- raw artifact payloads are not serialized
- full local paths are not serialized; only safe file names, hashes, and byte counts are recorded
- archive submission, screenshot capture, WARC/WACZ capture, ArchiveBox, and media downloads remain manual/operator-run unless a later approved executable backend is implemented
- no completed or verified capture claim is made by this kit
