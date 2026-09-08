# R42EJ File Converter fill-box workflow

Purpose: correct the R42EI live-GUI behaviour so File Converter is a main-app conversion set, not a FILES-row arrow/queue action.

Changes:
- Removed the FILES-row arrow convert button.
- Added FILES-row fill-box selectors for conversion.
- Removed File Converter panel buttons for `Add selected FILES` and `Add active media`.
- File Converter drag/drop now holds dropped files inside the converter only; it does not add them to FILES until conversion succeeds.
- Converter accepts one detected file family per run: text, image, audio, or video.
- `Convert to` values are filtered by the selected/held file family.
- Converted outputs are added directly to FILES.
- If the original is kept, original plus converted output are shown together under a collapsible `Converted:` section, not a FILES folder.
- Open output folder uses the provided opened-folder icon asset.
- Media/image/video-audio windows still provide their own Convert selected chain into File Converter.

No network/browser/archive path is added. The converter remains local-only.
