# R42BU native WebView2 source-role editor

Purpose: keep the true native toolbar above the WebView2 page, while replacing PNG toolbar button rendering with owner-drawn vector glyphs.

Key points:
- WebView2 stays in a lower native row, so the Wayback banner is not covered.
- Toolbar icons are drawn once in Paint; Button.Image is not used.
- The source-role copy icon is a crisp vector page with four role-colour chips rather than a scaled PNG that can look overlapped.
- The toolbar compacts counts and control widths for smaller window sizes while preserving instant mode/source navigation behavior.


R42BU: restores the project Icons8 PNG artwork using owner-drawn native toolbar buttons. The PNG is never assigned to Button.Image, so there is no WinForms image/text overlay or DPI cropping. Prev/next remain vector arrows.
