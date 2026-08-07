# Source Adapter Fixture Pipeline

This shared stage converts a passed Adapter Fixture Review package into a deterministic, local-only fixture pipeline package. It plans each reviewed adapter fixture against the shared source pipeline stages, records optional explicit local stage results, writes an assertion manifest, and produces a fixture pipeline closeout handoff.

It does not fetch URLs, launch browsers, scan folders, read credentials, submit archive requests, upload releases, or start live/manual actions. The only accepted inputs are explicit JSON packages and optional explicit local fixture result JSON supplied by the operator or tests.

Implemented files: `source_adapter_fixture_pipeline.py`, `source_adapter_fixture_pipeline_store.py`, `source_adapter_fixture_pipeline_cli.py`, and `source_adapter_fixture_pipeline_verifier.py`.

The stage keeps future site work as adapter specs plus reviewed fixtures routed through shared contracts, instead of repeating the MSN-specific pipeline for each new source.
