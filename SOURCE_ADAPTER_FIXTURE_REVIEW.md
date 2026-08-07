# Source Adapter Fixture Review

Shared, adapter-neutral review stage for operator-authored source adapter fixtures.

This stage consumes a Source Adapter Fixture Authoring package plus an explicit authored-fixtures JSON packet and writes a deterministic fixture-review package, authored fixture registry, shared pipeline fixture handoff, review report, and operator summary. It is local-fixture-only: it does not fetch URLs, launch browsers, scan folders, read credentials, submit archive requests, upload releases, or start live/manual actions.

Use this after `source_adapter_fixture_authoring.py` and before running fixtures through the shared local source pipeline contracts. Adapter-specific code remains unnecessary unless the fixture matrix marks a genuinely unique extraction surface.
