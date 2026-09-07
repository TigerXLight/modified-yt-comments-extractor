# R42BW native WebView2 source-role editor

R42BW keeps the R42BU asset PNG owner-drawn icons, but changes the host layout to an Edge-like native chrome model:

- native toolbar is a fixed `DockStyle.Top` row
- WebView2 is `DockStyle.Fill` below it
- no `TableLayoutPanel` is used during live window resize
- toolbar controls keep fixed button/icon sizes; only the URL text label is elastic
- toolbar relayout is delayed during live resize so WebView2 can resize smoothly
- owner-drawn project PNG icons remain centred and are not assigned to `Button.Image`

This keeps the Wayback banner visible, preserves instant mode/source switching, and avoids the live resize jitter/clipping seen in R42BU.


R42BW notes:
- Fixes R42BV narrow/open-window toolbar overlap by switching count chips to compact labels earlier.
- Recomputes only cheap toolbar widths on each SizeChanged instead of freezing layout during resize.
- Keeps WebView2 as Dock=Fill below a fixed native top toolbar so the page is never covered.
