# R42EK File Converter window/files cleanup

Scope:
- Remove converter queue/checkbox and K controls from FILES rows.
- Keep conversion selection in the File Converter hold box and in image/video/audio windows.
- Move the converter list into the drop area rather than a separate activity-log-style box.
- Add a FILES header opened-folder icon for the latest converter output folder, separated from Clear all.
- Add Take all by file family for moving many existing FILES entries into File Converter.
- Change image/video/audio Convert selected to download first, convert locally, and add only converted outputs to FILES unless Keep original is checked.

Invariants:
- File Converter remains main-app tooling under tools/profile_media_file_converter.
- Conversion stays local-only.
- No archive.ph/WebView2/browser access path is used by the converter backend.
- No git add -A should be used on this working tree because unrelated dirty/untracked backlog remains present.
