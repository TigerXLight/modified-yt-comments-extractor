# R42EV - Converter runtime testing + cog/default fix

Scope:
- Fix Compression Advanced playback speed default showing `0.5x`; default and UI normalisation now stay at `1.0x` while backend options still convert it to numeric `1.0`.
- Keep File Converter cogs visible on first paint by raising the cog label above CTkButton repaints.
- Add no-network testing/audit scripts for UI contracts, backend plan structure, encoder capability, and optional tiny synthetic encoder benchmark.

Retained:
- R42ET dynamic video matcher / remux-copy behaviour.
- R42EU scrollable settings windows and Advanced Image/Video/Audio tabs.
- C remains Compression.
