# Shared Source Comment Extraction

This module is the shared comment/reply extraction boundary for the one-framework/many-adapters source capture plan.

It consumes only explicit operator-supplied artifacts or a source artifact collection manifest and produces normalized comment JSON, a comment index, and a capture-bundle handoff. It supports JSON, NDJSON, HTML-like snippets, copied text transcripts, comment/reply nesting, safe basenames, and deterministic SHA-256 hashes.

Safety boundaries:

- no URL fetching
- no browser launch
- no folder scanning
- no credential access
- no full local path serialization
- no claim that online archive or live capture has completed

Future adapters should supply adapter specs plus fixtures for their comment surfaces instead of creating MSN-sized bespoke chains unless a source has a genuinely unique extraction surface.
