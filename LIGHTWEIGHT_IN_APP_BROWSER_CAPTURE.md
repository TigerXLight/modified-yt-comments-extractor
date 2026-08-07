# Lightweight in-app browser capture

Shared source-adapter browser capture boundary for operator-approved web sources.

This module is intentionally adapter-neutral. Source-specific work should be adapter metadata,
URL/domain bindings, artifact roles, and fixtures unless the source has a genuinely unique
surface such as a shadow-root comments tree.

Safety boundary:

- no browser is opened by tests;
- live navigation is off by default;
- generated launch scripts require an explicit approval token argument;
- only operator-supplied URLs are represented;
- outputs are capture packages, scripts, snippets, and artifact templates.
