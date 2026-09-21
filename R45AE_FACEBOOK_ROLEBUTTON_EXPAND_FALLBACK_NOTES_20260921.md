# R45AE Facebook role-button expand fallback

The R45AD screenshots showed visible reply openers such as `View all 2 replies`,
`View all 3 replies`, and `View all 4 replies` remaining on screen even though the
runner had moved past them.

The Facebook HTML shows those controls can exist as real clickable controls around
the visible text, not only as simple text nodes. R45AE therefore adds a fallback
probe over actual clickable elements inside the active comments dialog.

R45AE behaviour:

- keep the R45AB/R45AD comments-dialog lock;
- keep visible-page clicks only;
- first use the existing text-node probe;
- if it finds no candidate, use the role-button/link fallback;
- match only explicit expansion labels such as `View all N replies`,
  `View hidden replies`, `View more replies`, and `Name replied · N replies`;
- sort candidates by screen top then left;
- log `R45AE_ROLEBUTTON_EXPAND_FALLBACK` and `rolebutton_fallback=true` when the
  fallback supplies the next click;
- log skipped visible labels if a control is visible but outside the allowed band.

Safety remains unchanged: no hidden Facebook APIs, no cookies/tokens/profile
parsing, no WebView2 storage inspection, no login automation.
