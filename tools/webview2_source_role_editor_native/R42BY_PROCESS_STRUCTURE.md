# R42BY native WebView2 source-role editor patch

R42BY builds on R42BX.

Changes:

- Keeps the native toolbar as a real WinForms row above WebView2, with WebView2 explicitly bounded below it so Wayback is not covered.
- Removes previous/next arrow buttons; source switching remains dropdown-only.
- Restores full `Primary: 00`, `Secondary: 35`, `Tertiary: 00`, `Unknown: 15` labels at normal half-screen/minimum width.
- Compact labels now include a space: `P: 00`, `S: 35`, `T: 00`, `U: 15`.
- Replaces icon Button Paint-event drawing with a dedicated custom UserPaint icon button that paints one rounded button and one centred project PNG.
- Caches native counts by mode from the payload so counters update immediately on Semantic/Media clicks.
- Sends mode changes through both WebView2 PostWebMessageAsJson and a direct in-page ExecuteScript bridge so the colour painting changes even after archive/Wayback navigation.
