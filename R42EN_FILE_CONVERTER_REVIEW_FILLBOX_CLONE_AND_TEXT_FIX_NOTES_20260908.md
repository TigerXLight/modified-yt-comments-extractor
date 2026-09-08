# R42EN file converter Review-fillbox clone and text/rename fix

Purpose: replace the remaining shallow File Converter selection UI with an implementation that mirrors the already-existing Review DB fillbox interaction model.

Changes:
- File Converter held area now uses a master glyph fillbox and child glyph fillboxes, matching the Review DB `source_review_selected_keys` / visible-key / sync pattern.
- Held File Converter rows can contain mixed image/video/audio/text files. Conversion remains restricted to selected rows of one file type per run.
- The global `Convert to` dropdown follows the currently selected held rows. Mixed selected kinds expose only `auto` and instruct the user to use per-row dropdowns.
- `Take all:auto` takes all supported FILES entries, not just one type.
- K keep-original is an icon button inside held rows; toggling K updates in place and does not rebuild the held list.
- FILES drag has a lightweight cursor-following ghost label plus converter drop-highlight.
- Folder rename no longer commits on FocusOut; Enter/✓ saves, Esc/× cancels.
- Text Editor is explicitly raised, left editable, and focused after loading TXT files.

Still intentionally true:
- Converted outputs return to FILES only after successful conversion.
- The converter backend remains local-only and does not start WebView2, archive.ph, or network work.
- Normal FILES rows keep their selection tickbox for multi-select/drag, but not converter target/K controls.
