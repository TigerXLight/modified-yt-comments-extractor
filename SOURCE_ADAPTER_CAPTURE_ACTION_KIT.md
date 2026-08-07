# Shared source Adapter Capture Action Kit

This stage converts an accepted Adapter Capture Setup package into a deterministic, local-only operator action kit.

It writes an action index, artifact intake templates, capture-session handoff, and operator summary. The package is app-facing but does not execute the actions.

Safety boundary: it does not fetch URLs, launch browsers, scan folders, read credentials, submit archives, upload releases, mutate app files, mutate registry files, or start live/manual actions. Every action requires explicit operator approval and an execute-approved gate before any future capture session can run.
