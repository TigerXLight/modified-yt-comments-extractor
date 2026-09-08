# R42EI File Converter integration cleanup — 2026-09-08

R42EI corrects the R42EH namespace problem and deepens the two intended entry points.

## What changed

- Moves the file-converter smoke/probe/build/debug helpers out of `tools/webview2_source_role_editor_native` into `tools/profile_media_file_converter`.
- Keeps the converter backend in the main app modules: `profile_media_file_converter_r42eh.py` plus the R42EG compatibility wrapper.
- Adds a direct Convert button on each FILES row. The row action queues that one file and opens the main-app File Converter panel.
- Adds an Add active media action in the File Converter panel for the currently selected image/audio/video file.
- Adds Convert selected hooks in the image window and browser-native image grid: selected candidates are first downloaded/registered locally, then queued into the same converter backend.
- Adds Convert selected hooks in the browser-native Video & Audio grid: selected direct media candidates are downloaded/registered locally, then queued into the same converter backend after download completion.
- Preserves R42EH no-network conversion semantics: webpage/media windows may download the selected media candidate as before, but the conversion backend itself remains local-only and does not hit archive.ph, WebView2, or network.
- Preserves K semantics: K on keeps originals; K off deletes only after successful conversion and confirmation.

## Why

The file converter is a main-app utility, not a WebView2/source-role-editor feature. WebView2 is only one possible display/source discovery surface; it should not own converter scripts or naming.
