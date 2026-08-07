# Source Adapter Fixture Authoring

This shared stage converts the adapter fixture matrix into deterministic fixture-authoring templates. It keeps new source work as adapter specs plus saved-source fixtures, not repeated MSN-sized per-site pipelines.

The stage is local-only. It does not fetch URLs, launch browsers, scan folders, read credentials, submit archive requests, validate online archive contents, upload releases, or start live/manual capture actions.

Outputs include a fixture-authoring package, template index, shared-stage route plan, review handoff, and operator summary. Templates use safe basenames and placeholders for later operator-supplied fixture artifacts and expected assertions.
