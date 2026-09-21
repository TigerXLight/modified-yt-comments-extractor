# R45AF Facebook text-rect fallback-first

The 05:40 video shows the live runner leaving visible expansion controls behind,
including `View hidden replies` and `View all 6 replies`, while it keeps moving
down the comments modal. Earlier frames also show the comment composer becoming
focused/expanded.

R45AF changes the expansion probe order and click target:

- run the real clickable role=button/link fallback before the older text-node probe;
- compute the rectangle of the visible label text itself;
- click the label text centre rather than the centre of a wide Facebook row/button;
- keep the comments-dialog lock;
- exclude composer/comment-box ancestors;
- detect the composer top and keep expansion clicks above it;
- retain telemetry for skipped visible labels and fallback-first labels.

Safety remains unchanged: visible-page clicks only; no hidden Facebook APIs; no
cookies/tokens/profile parsing; no WebView2 storage inspection; no login automation.
