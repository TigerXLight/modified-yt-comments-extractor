# R42EL File Converter review-style held rows and FILES multi-select drag

Date: 2026-09-08

Purpose:
- Correct the R42EK live-GUI mismatch by reusing the established Review-window fill-box pattern for File Converter held items.
- Restore the normal FILES tickbox as a multi-select/highlight control for dragging many FILES rows into File Converter.
- Keep K/keep-original out of normal FILES rows; K is now interactive inside File Converter held rows and media-window conversion controls.

Behaviour:
- FILES rows have a normal tickbox again. It highlights/selects rows for drag/multi-select only; it does not queue conversion by itself.
- Dragging a ticked FILES row into the File Converter carries all ticked FILES rows.
- Drag-hover over the File Converter drop area changes border/text so it is visible where the cursor is being released.
- File Converter held files render as scrollable Review-style rows, not as a plain activity-log text list.
- Each held row has:
  - a fill-box/tickbox deciding whether it participates in the next Convert press;
  - per-row target-format dropdown, filtered by detected family;
  - K keep-original checkbox.
- The global Convert to dropdown applies only to selected/fill-boxed held rows.
- Convert runs only selected held rows, then removes processed rows from the hold box.
- Dropped external files remain only inside File Converter until conversion succeeds.
- Converted outputs continue to enter FILES after conversion.

Non-goals:
- No browser/WebView2/archive/network conversion path.
- No broad `git add -A`.
- No deletion of unrelated backlog files.

R42EL_REVIEW_STYLE_FILE_CONVERTER_ROWS
R42EL_FILES_TICKBOX_RESTORED_FOR_MULTISELECT_DRAG
R42EL_HELD_ITEM_PER_ROW_TARGET_DROPDOWNS
R42EL_DRAG_HOVER_CONVERTER_ANIMATION
R42EL_CONVERT_TO_APPLIES_TO_SELECTED_HELD_ROWS
