# R42EC archive role closeout / local fixture media-target probe

This patch is intentionally narrow and archive-safe.

What it closes:
- R42EB/R42DX/R42DY/R42DZ/R42EA already proved the archive.ph material and role payload can be generated without hitting archive.ph.
- The latest local fixture run proved the native helper receives the payload and paints 61 semantic text spans with non-zero counters.
- R42EC fixes the remaining false negative in the log probe by accepting the real native log format:
  `counts_semantic=P0/S35/T0/U15` and `counts_media=P0/S41/T0/U11`.
- R42EC adds an explicit native `native_toolbar_state` success log so the page-side toolbar-state bridge is observable in CMD logs.
- R42EC upgrades the local file fixture with deterministic fake media targets: a main video/player block and captioned local figures. These use only `file:///`/inline data resources, not archive.ph.

Boundaries:
- The smoke/probe commands do not open the project app.
- The smoke/probe commands do not open the native WebView2 helper.
- The smoke/probe commands do not hit archive.ph.
- The optional launch command opens only a local `file:///` fixture in the native helper.

After this:
- Move to the semantic/media comprehension matrix and text-colouring cleanup.
- Do not keep repeatedly opening archive.ph for paint testing.
