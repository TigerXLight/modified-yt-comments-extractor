# MSN manual Evidence Review decision implementation

This section implements the reviewer decision step for approved MSN manual captures.

The flow is local and explicit:

1. read a previously built MSN manual Evidence Review package JSON;
2. record a reviewer decision (`APPROVED`, `REJECTED`, or `REVISION_REQUESTED`);
3. validate required review actions and safe asset metadata;
4. write deterministic decision receipt and queue update JSON; and
5. expose CLI and verifier entry points for the next Total Export workflow step.

The implementation does not perform live HTTP, browser automation, archive submission, media download, WARC/WACZ capture, ArchiveBox calls, credential reads, folder scans, or unapproved external actions. Output reports contain safe filenames and hashes only, never full local filesystem paths.

The decision receipt enforces no full local filesystem paths in stored metadata.
