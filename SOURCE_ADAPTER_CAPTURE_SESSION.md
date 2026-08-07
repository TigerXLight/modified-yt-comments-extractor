# Shared source Adapter Capture Session

This stage converts an approved Adapter Capture Action Kit plus explicit operator artifact receipts into a deterministic, local-only capture session package.

It writes a capture session record, artifact receipt index, artifact collection handoff, and operator summary. The package records what the operator supplied; it does not create, read, or validate the artifact bytes themselves.

Safety boundary: it does not fetch URLs, launch browsers, scan folders, read credentials, submit archives, upload releases, mutate app files, mutate registry files, or start live/manual actions. It only accepts explicit receipt metadata with safe basenames, byte counts, and SHA-256 hashes.
