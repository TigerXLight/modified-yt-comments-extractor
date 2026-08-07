# Shared Source Adapter Fixture Matrix

`source_adapter_fixture_matrix.py` creates the reusable adapter-spec and fixture-matrix boundary after the shared source pipeline closeout. It consumes explicit adapter specs and produces an adapter registry, fixture matrix, fixture authoring plan, shared pipeline binding, and operator summary.

This stage is intentionally local and manual-safe: it does not fetch URLs, launch browsers, scan folders, read credentials, submit archive requests, validate online archive contents, upload releases, or start live/manual actions.

The purpose is to keep future source work as one framework with many adapter specs. Per-site work should normally be metadata mapping plus fixture coverage; adapter-specific code is only flagged when a source has a genuinely unique extraction surface.

This is the adapter-mapping layer that prevents repeating MSN-sized pipelines for every website or source family.
