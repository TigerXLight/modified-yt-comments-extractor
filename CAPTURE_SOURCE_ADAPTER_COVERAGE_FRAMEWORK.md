# Source Adapter Coverage Framework

This slice stops the MSN pattern from being repeated as one huge bespoke implementation for every site.

The intended coverage model is now:

1. describe each source adapter with a small JSON adapter spec;
2. route all adapters through shared pipeline stages;
3. add adapter-specific code only when a site has a genuinely unique extraction surface;
4. keep lightweight in-app browser behaviour as an operator-approved local/manual boundary;
5. keep external archive actions manual unless a later explicit live-action approval gate is added.

The framework outputs four local artifacts: coverage report, stage matrix, shared implementation plan, and lightweight browser plan. It does not fetch pages, open browsers, submit archive requests, read credentials, or mark any live capture/archive as complete.
