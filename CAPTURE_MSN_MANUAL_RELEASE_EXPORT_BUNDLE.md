# MSN manual release export bundle

This section implements the final local export-bundle boundary for approved MSN manual captures.

Inputs are explicit JSON files only: an MSN manual release index, plus the optional release index store report. The implementation writes a deterministic export bundle, export manifest, and final evidence queue release update for Total Export handoff.

Safety boundary: no live HTTP, no browser automation, no archive submission, no media downloads, no credential reads, no folder scans, no file moves, and no full local path serialization.
