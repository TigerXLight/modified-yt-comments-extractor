# Manual live smoke observation packet

This document defines the metadata-only boundary for importing operator-supplied
manual live site-smoke observations.

The observation packet is not a live smoke runner. It does not perform live HTTP,
browser automation, screenshots, archive submission, media downloads, WARC/WACZ,
ArchiveBox, credential reads, file moves, or user-folder scans.

The packet records only:

- named site id and display name
- named requested manual action
- operator-supplied observation summary
- safe artifact file names, roles, byte counts, and SHA-256 hashes
- review-required status and safety flags

The packet must not claim a completed or verified capture. A later explicit
review step may accept or reject the operator observation, but this boundary only
prepares the observation for review.
