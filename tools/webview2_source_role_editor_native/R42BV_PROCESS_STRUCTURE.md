# R42BV native WebView2 source-role editor

R42BV keeps the R42BU asset PNG owner-drawn icons, but changes the host layout to an Edge-like native chrome model:

- native toolbar is a fixed `DockStyle.Top` row
- WebView2 is `DockStyle.Fill` below it
- no `TableLayoutPanel` is used during live window resize
- toolbar controls keep fixed button/icon sizes; only the URL text label is elastic
- toolbar relayout is delayed during live resize so WebView2 can resize smoothly
- owner-drawn project PNG icons remain centred and are not assigned to `Button.Image`

This keeps the Wayback banner visible, preserves instant mode/source switching, and avoids the live resize jitter/clipping seen in R42BU.
