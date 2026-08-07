# MSN manual release index

This section implements the local release-index boundary for approved MSN manual captures.

Inputs are explicit JSON files only: an approved MSN manual release package, plus the optional release package store report. The implementation writes a deterministic release index, release inventory, and evidence queue release update for Total Export review.

Safety boundary: no live HTTP, no browser automation, no archive submission, no media downloads, no credential reads, no folder scans, and no full local path serialization.
