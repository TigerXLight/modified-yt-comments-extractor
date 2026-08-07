# Source Adapter Source Selection

Shared source Adapter Source Selection consumes a reviewed Source Adapter Registry Rollout package and writes deterministic local app-facing source selection data.

This stage writes a source selection package, option catalogue, capture route index, capture setup handoff, and operator summary. It does not mutate app files, registry files, credentials, browser state, archive services, or provider configuration.

manual or live actions are not started here. The output is a local wiring package for a later UI/app integration slice.
