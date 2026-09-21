# R45AG restore R45H bounded modal expansion engine

The user supplied the older 2026-09-19 R45J audit ZIP. That working R45J state
used `r45h.JS_BOUNDED_MODAL_AUTO_EXPAND` directly for `--auto-expand`.

The later R45V-R45AF mouse/text-rect path added many safeguards but still missed
visible controls such as `View all 5 replies` after long runs. R45AG therefore
keeps the newer target guards and screenshot/export pipeline, but restores the
older R45H bounded modal auto-expander as the default live expansion engine.

Runtime marker:

- `R45AG_RESTORED_R45H_MODAL_AUTO_EXPAND_START`
- `R45AG_RESTORED_R45H_MODAL_AUTO_EXPAND_DONE`

Safety remains unchanged: visible-page expansion only; no hidden Facebook APIs;
no cookies/tokens/profile parsing; no WebView2 storage inspection; no login
automation.
