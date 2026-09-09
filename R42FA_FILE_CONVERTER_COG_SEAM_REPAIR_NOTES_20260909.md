# R42FA — File Converter cog seam repair

Scope:
- Keep the R42EZ launch fix.
- Repair the File Converter Convert/Compression cog visuals.
- Revert the helper away from the sibling CTkButton cog that split the orange button shape.
- Restore a single full-width CTkButton plus a tk.Label cog overlay, matching the existing Local Web Archive/ASR-style cog pattern.
- Keep the CustomTkinter rule: width/height stay in constructors, not place().
- Add repeated first-paint `lift/tkraise` calls so the cog is visible immediately, not only after hover.

No network/WebView2/archive.ph actions are used by the smoke/probe scripts.
