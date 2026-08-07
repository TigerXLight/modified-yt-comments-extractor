# Manual live smoke action implementation

This document defines the executable manual-live-smoke action boundary.

It is not an observation-only import layer. It provides concrete named actions,
step contracts, artifact contracts, approval rules, and a local CLI that can
prepare and, when explicitly approved, launch the operator's browser at the
named target URL.

Safety boundary:

- no live HTTP is performed by tests
- no browser launch happens without an explicit approval token and CLI flag
- no archive submission is performed automatically
- no screenshot, WARC/WACZ, ArchiveBox, or media download is performed automatically
- no credential values are read or serialized
- no raw media bytes are copied into reports
- no full local paths are serialized in output metadata
- no completed or verified capture is claimed by the action plan or dry run

The action implementation is intended to make manual actions runnable: it tells
the operator exactly what action is being requested, what URL to open, what
manual steps to perform, and which artifact roles must later be supplied to the
observation/review intake boundary.
