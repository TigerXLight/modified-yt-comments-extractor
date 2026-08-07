# Source Adapter Capture Setup

Shared source Adapter Capture Setup consumes a Source Adapter Source Selection package and writes deterministic local capture setup data.

This stage writes a capture setup package, shared capture setup plan, artifact intake plan, lightweight browser capture setup handoff, and operator summary. It does not mutate app files, registry files, credentials, browser state, archive services, or provider configuration.

manual or live actions are not started here. The output is a local wiring package for a later approved capture session planning slice.
